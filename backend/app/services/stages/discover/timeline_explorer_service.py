import os, json, logging, re
from typing import Dict, Any, List
import openai

from app.services.openai_key_manager import key_manager

# Optional: reuse your robust extractor
try:
    from app.utils.file_utils import extract_text_from_document
except Exception:
    extract_text_from_document = None

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class TimelineExplorerService:
    """
    Builds timelines from category/text/document.
    Output shape:
    { "timeline": [ { "date": "YYYY[-MM[-DD]]" | "ca. 1200", "title": "Event", "description": "..." }, ... ] }
    Always sorted ascending by date when parseable.
    """
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[Timeline] Using Azure slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.3, max_tokens=1400, timeout=60) -> str:
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
            log.warning(f"[Timeline] Rate limit: {e}; rotating key.")
            self._use_new_credentials()
            raise

    # -------- public entry points --------
    def from_category(self, category: str) -> Dict[str, Any]:
        seed = (category or "").strip()
        if not seed:
            return {"timeline": []}
        seed_text = f"TOPIC: {seed}"
        return self._build(seed_text)

    def from_text(self, text: str) -> Dict[str, Any]:
        t = (text or "").strip()
        if not t:
            return {"timeline": []}
        return self._build(t)

    def from_document(self, file_path: str) -> Dict[str, Any]:
        if not file_path or not os.path.exists(file_path):
            return {"timeline": []}
        if extract_text_from_document:
            try:
                chunks = extract_text_from_document(file_path)
                doc_text = "\n\n".join(chunks) if isinstance(chunks, list) else str(chunks)
            except Exception as e:
                log.warning(f"[Timeline] extractor failed, fallback read: {e}")
                doc_text = self._read_small_text(file_path)
        else:
            doc_text = self._read_small_text(file_path)
        return self._build(doc_text)

    # -------- core builder --------
    def _build(self, seed_text: str) -> Dict[str, Any]:
        prompt = (
            "From the content below, extract a concise historical/chronological timeline.\n"
            "Return ONLY JSON with this shape:\n"
            "{ \"timeline\": [\n"
            "  {\"date\": \"YYYY[-MM[-DD]] or 'ca. 1200' or a short era\", "
            "\"title\": \"short event title\", "
            "\"description\": \"1–3 sentences\"}\n"
            "]}\n"
            "Guidelines: 10–40 events max, sort chronologically, prefer specific dates if present.\n\n"
            f"CONTENT:\n{seed_text[:24000]}"
        )
        raw = self._chat(
            [
                {"role": "system", "content": "You are a precise timeline extraction assistant. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            max_tokens=1600,
            timeout=70,
        )
        return self._parse_and_sort(raw)

    # -------- parsing & sorting --------
    def _parse_and_sort(self, raw: str) -> Dict[str, Any]:
        data = {"timeline": []}
        try:
            data = json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, flags=re.S)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    pass
        events = data.get("timeline") or []
        out: List[Dict[str, Any]] = []
        for e in events:
            if not isinstance(e, dict):
                continue
            date = str(e.get("date") or "").strip()[:40]
            title = str(e.get("title") or "").strip()[:140]
            desc = str(e.get("description") or "").strip()
            if title:
                out.append({"date": date, "title": title, "description": desc})

        def parse_year(d: str) -> int:
            # Try YYYY, YYYY-MM, YYYY-MM-DD; fallback big value to push unknown to end
            m = re.match(r"^\s*(\d{1,4})", d or "")
            try:
                return int(m.group(1)) if m else 10**9
            except Exception:
                return 10**9

        out.sort(key=lambda x: parse_year(x["date"]))
        return {"timeline": out[:40]}

    def _read_small_text(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                data = f.read(2_000_000)
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return data.decode("latin-1", errors="ignore")
        except Exception:
            return ""