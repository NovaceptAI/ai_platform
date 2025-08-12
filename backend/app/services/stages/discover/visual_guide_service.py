import os, json, logging, re
from typing import Dict, Any, List, Tuple
import openai

# rotation
from app.services.openai_key_manager import key_manager

# (optional) robust text extraction if you already use this in summarizer
try:
    from app.utils.file_utils import extract_text_from_document
except Exception:
    extract_text_from_document = None

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class VisualGuideService:
    """
    Builds a visual study guide from:
      - category (topic name)
      - free text
      - document file path
    Returns:
      {
        "summary": str (markdown optional),
        "topics": [
          { "name": str, "study_method": str (markdown ok),
            "time": int (minutes, optional), "order": int, "resources": [str,...]? }
        ]
      }
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
        log.info(f"[VSG] Using Azure slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.3, max_tokens=1200, timeout=60) -> str:
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
            log.warning(f"[VSG] Rate limit: {e}; rotating key.")
            self._use_new_credentials()
            raise

    # ---------- Public entry points ----------
    def from_category(self, category: str) -> Dict[str, Any]:
        seed = category.strip()
        if not seed:
            return {"summary": "", "topics": []}
        return self._build(seed_text=f"TOPIC: {seed}")

    def from_text(self, text: str) -> Dict[str, Any]:
        t = (text or "").strip()
        if not t:
            return {"summary": "", "topics": []}
        return self._build(seed_text=t)

    def from_document(self, file_path: str) -> Dict[str, Any]:
        if not file_path or not os.path.exists(file_path):
            return {"summary": "", "topics": []}
        # Prefer your extractor if present (handles pdf/docx robustly).
        if extract_text_from_document:
            try:
                chunks = extract_text_from_document(file_path)
                doc_text = "\n\n".join(chunks) if isinstance(chunks, list) else str(chunks)
            except Exception as e:
                log.warning(f"[VSG] extract_text_from_document failed, fallback to raw read: {e}")
                doc_text = self._read_small_text(file_path)
        else:
            doc_text = self._read_small_text(file_path)
        return self._build(seed_text=doc_text)

    # ---------- Core builder ----------
    def _build(self, seed_text: str) -> Dict[str, Any]:
        """
        Ask LLM for a compact visual study guide. Hard constrain JSON.
        """
        prompt = (
            "Create a concise visual study guide from the content below.\n"
            "Return ONLY valid JSON with the following shape:\n"
            "{\n"
            '  "summary": "1-3 sentence overview in markdown allowed",\n'
            '  "topics": [\n'
            '    {"name":"string","study_method":"markdown string","time":30,"order":1,"resources":["optional","chips"]},\n'
            "    ... up to 12 topics, logical order ...\n"
            "  ]\n"
            "}\n\n"
            "Guidelines:\n"
            "- time is minutes (integer). Omit if unknown.\n"
            "- order starts at 1 and increases.\n"
            "- keep study_method practical (bullets, checklists ok).\n"
            "- topics should be specific, 3–7 words.\n\n"
            f"CONTENT:\n{seed_text[:24000]}"
        )

        raw = self._chat(
            [
                {"role": "system", "content": "You are a precise curriculum designer. Output JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.35,
            max_tokens=1500,
            timeout=70,
        )
        return self._parse_result(raw)

    # ---------- Parse & normalize ----------
    def _parse_result(self, raw: str) -> Dict[str, Any]:
        try:
            data = json.loads(raw)
        except Exception:
            # super-tolerant fallback: try to yank a JSON object block
            import re
            m = re.search(r"\{.*\}", raw, flags=re.S)
            data = json.loads(m.group(0)) if m else {"summary": "", "topics": []}

        out = {"summary": str(data.get("summary") or "").strip(), "topics": []}
        topics = data.get("topics") or []
        if isinstance(topics, list):
            for i, t in enumerate(topics, start=1):
                if not isinstance(t, dict):  # allow string
                    name = str(t)[:80]
                    if name:
                        out["topics"].append({"name": name, "study_method": "", "order": i})
                    continue
                name = str(t.get("name") or "").strip()[:120]
                study = str(t.get("study_method") or "").strip()
                time_m = t.get("time")
                try:
                    time_m = int(time_m) if time_m is not None else None
                except Exception:
                    time_m = None
                order = t.get("order")
                try:
                    order = int(order) if order is not None else i
                except Exception:
                    order = i
                res = t.get("resources") or []
                if not isinstance(res, list):
                    res = [str(res)]
                res = [str(x).strip()[:60] for x in res if str(x).strip()][:8]

                if name:
                    out["topics"].append({
                        "name": name,
                        "study_method": study,
                        "time": time_m,
                        "order": order,
                        "resources": res if res else None
                    })
        # clamp & sort
        out["topics"] = sorted(out["topics"][:12], key=lambda x: x.get("order", 10**9))
        return out

    # ---------- tiny raw reader fallback ----------
    def _read_small_text(self, file_path: str) -> str:
        try:
            # best effort for txt-like files
            with open(file_path, "rb") as f:
                data = f.read(2_000_000)  # 2MB safety
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return data.decode("latin-1", errors="ignore")
        except Exception:
            return ""