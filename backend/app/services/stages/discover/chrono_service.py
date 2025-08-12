import os, json, logging, re, datetime as dt
import openai
from typing import List, Dict, Any, Tuple
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

_DATE_RX = re.compile(r"^\d{4}(-\d{2}){0,2}$")  # YYYY or YYYY-MM or YYYY-MM-DD

class ChronologyService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[ChronologyService] Using Azure slot #{idx} ({api_base})")

    def _call_llm(self, prompt: str, max_tokens: int = 400) -> str:
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a careful timeline extraction assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
                timeout=30,
            )
            return resp["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            # rotate and bubble; task-level retry will handle
            log.warning(f"Rate limit in chronology: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def extract_events_from_text(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Returns a list of events for a single page:
        [{ "date":"YYYY[-MM[-DD]]" or null, "title":"...", "desc":"..." }]
        """
        if not text or not text.strip():
            return []

        prompt = (
            "From the text below, extract up to {k} dated or ordered events.\n"
            "Respond ONLY as compact JSON array of objects with keys: date, title, desc.\n"
            "- date: ISO 'YYYY' or 'YYYY-MM' or 'YYYY-MM-DD' if known, else null.\n"
            "- title: 3–8 words.\n"
            "- desc: one concise sentence.\n\n"
            "TEXT:\n{t}"
        ).format(k=top_k, t=text[:12000])

        raw = self._call_llm(prompt, max_tokens=500)
        # Robust JSON parse fallback
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [self._normalize_event(e) for e in data if isinstance(e, dict)]
        except Exception:
            pass

        # Heuristic fallback: split lines, attempt to parse "YYYY..." lines.
        events = []
        for line in raw.splitlines():
            line = line.strip("-•* \t")
            if not line:
                continue
            # naive split
            parts = line.split(":", 1)
            title = parts[0].strip()[:120]
            desc = (parts[1].strip() if len(parts) > 1 else "")[:240]
            # guess date at start of title
            date = None
            m = re.match(r"^(\d{4}(?:-\d{2}){0,2})\s*(.+)$", title)
            if m:
                maybe, rest = m.group(1), m.group(2)
                date = maybe if _DATE_RX.match(maybe) else None
                title = rest.strip() or title
            events.append(self._normalize_event({"date": date, "title": title, "desc": desc}))
        return events

    def _normalize_event(self, e: Dict[str, Any]) -> Dict[str, Any]:
        date = e.get("date")
        if isinstance(date, str):
            date = date.strip()
            if not _DATE_RX.match(date):
                date = None
        elif date is None:
            pass
        else:
            date = None
        title = (e.get("title") or "").strip()
        desc  = (e.get("desc")  or "").strip()
        return {"date": date, "title": title[:160], "desc": desc[:400]}

    def merge_events(self, per_page: List[Tuple[int, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        Merge & dedupe events across pages; keep earliest date, aggregate page refs.
        Input: [(page_number, [events...]), ...]
        Output: [{date,title,desc,pages:[...]}] sorted by date then title.
        """
        bucket: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for page_no, events in per_page:
            for ev in events:
                key = (ev.get("date") or "", (ev.get("title") or "").lower())
                node = bucket.get(key)
                if not node:
                    node = {**ev, "pages": [page_no]}
                    bucket[key] = node
                else:
                    if page_no not in node["pages"]:
                        node["pages"].append(page_no)

        def sort_key(item):
            date = item.get("date")
            if not date:
                return (dt.date.max, item.get("title") or "")
            # pad YYYY / YYYY-MM to full date for sorting
            parts = date.split("-")
            y = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 12
            d = int(parts[2]) if len(parts) > 2 else 31
            try:
                return (dt.date(y, m, d), item.get("title") or "")
            except Exception:
                return (dt.date.max, item.get("title") or "")

        merged = list(bucket.values())
        merged.sort(key=sort_key)
        for m in merged:
            m["pages"].sort()
        return merged