import os, json, logging, re
from typing import List, Dict, Any, Tuple
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Each segment object shape we’ll use everywhere:
# { "heading": "string", "level": 1-4, "summary": "string", "tags": ["..."] }

class SegmenterService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[SegmenterService] Using Azure slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.2, max_tokens=700, timeout=40) -> str:
        try:
            r = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return r["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit in segmentation: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def segment_page(self, text: str, max_segments: int = 10) -> List[Dict[str, Any]]:
        """
        Extract structured segments from a single page of text.
        """
        if not text or not text.strip():
            return []
        prompt = (
            "Segment the text below into up to {k} coherent sections.\n"
            "Return ONLY JSON: an array of objects with keys: heading, level, summary, tags.\n"
            "- heading: 3–10 words\n"
            "- level: 1 (main) to 4 (sub)\n"
            "- summary: one concise sentence\n"
            "- tags: 1–5 short keywords\n\n"
            "TEXT:\n{t}"
        ).format(k=max_segments, t=text[:12000])

        raw = self._chat(
            [
                {"role": "system", "content": "You are a precise document segmentation assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
            timeout=45,
        )

        # Robust JSON parse with fallback
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [self._normalize_segment(x) for x in data if isinstance(x, dict)]
        except Exception:
            pass

        # Fallback: try to split lines like "- Heading: Summary"
        segments = []
        for line in raw.splitlines():
            ln = line.strip("-* \t")
            if not ln:
                continue
            parts = ln.split(":", 1)
            heading = (parts[0] if parts else "Section").strip()[:80]
            summary = (parts[1] if len(parts) > 1 else "").strip()[:300]
            segments.append(self._normalize_segment({
                "heading": heading,
                "level": 2,
                "summary": summary,
                "tags": []
            }))
        return segments

    def _normalize_segment(self, s: Dict[str, Any]) -> Dict[str, Any]:
        heading = (s.get("heading") or "").strip()[:120]
        level = s.get("level", 2)
        try:
            level = int(level)
        except Exception:
            level = 2
        level = min(4, max(1, level))
        summary = (s.get("summary") or "").strip()[:500]
        tags = s.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        tags = [str(t).strip()[:32] for t in tags if str(t).strip()][:5]
        return {"heading": heading, "level": level, "summary": summary, "tags": tags}

    def merge_outline(self, per_page: List[Tuple[int, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        Produce a simple document-level outline: flatten pages, keep ordering by page then by level.
        Also dedupe repeated headings (case-insensitive) while preserving first summary/tags.
        """
        seen = set()
        outline: List[Dict[str, Any]] = []
        for page_no, segments in per_page:
            for seg in segments:
                key = (seg.get("heading", "").strip().lower(), seg.get("level", 2))
                if key in seen:
                    continue
                seen.add(key)
                outline.append({
                    **seg,
                    "pages": [page_no]
                })
        # Add pages list accumulation for repeated headings on different pages
        # (since we skipped dupes in outline, we’ll do a second pass to gather page refs)
        index = {(item["heading"].lower(), item["level"]): item for item in outline}
        for page_no, segments in per_page:
            for seg in segments:
                key = (seg.get("heading", "").strip().lower(), seg.get("level", 2))
                if key in index:
                    item = index[key]
                    if page_no not in item["pages"]:
                        item["pages"].append(page_no)
        # Sort by level then by first page number
        outline.sort(key=lambda x: (x["level"], x["pages"][0] if x.get("pages") else 10**9))
        for item in outline:
            item["pages"].sort()
        return outline