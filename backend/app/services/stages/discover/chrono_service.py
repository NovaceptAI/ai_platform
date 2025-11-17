# app/services/stages/discover/chrono_service.py
import os, json, logging, re, datetime as dt
import openai
from typing import List, Dict, Any, Tuple
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Accept ISO with 1-2 digit months/days (we'll still zero-pad when we produce)
_DATE_RX = re.compile(r"^\d{4}(-(0?[1-9]|1[0-2]))?(-(0?[1-9]|[12]\d|3[01]))?$")

_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# --- helpers to normalize natural dates into ISO ---
_DAY_WITH_SUFFIX = r"(\d{1,2})(?:st|nd|rd|th)?"
_MONTH_NAME = r"(January|February|March|April|May|June|July|August|September|Sept|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_YEAR = r"(\d{4})"

_RX_DMY = re.compile(rf"(?i)\b{_DAY_WITH_SUFFIX}\s+{_MONTH_NAME}\s+{_YEAR}\b")
_RX_MDY = re.compile(rf"(?i)\b{_MONTH_NAME}\s+{_DAY_WITH_SUFFIX}(?:,\s*)?{_YEAR}\b")
_RX_MY  = re.compile(rf"(?i)\b{_MONTH_NAME}\s+{_YEAR}\b")
_RX_YM  = re.compile(rf"(?i)\b{_YEAR}\s+{_MONTH_NAME}\b")

def _zero(n: int) -> str:
    return f"{n:02d}"

def _month_to_num(name: str) -> int:
    return _MONTHS.get(name.strip().lower(), 0)

def _nl_to_iso(s: str) -> str:
    """Convert natural-language date to ISO; return '' if unparseable or missing year."""
    if not isinstance(s, str):
        return ""
    t = s.strip()
    if not t:
        return ""

    # 1) 19th August 2025 -> 2025-08-19
    m = _RX_DMY.search(t)
    if m:
        day = int(m.group(1))
        mon = _month_to_num(m.group(2))
        year = int(m.group(3))
        if mon:
            return f"{year}-{_zero(mon)}-{_zero(day)}"

    # 2) August 19th 2025 -> 2025-08-19
    m = _RX_MDY.search(t)
    if m:
        mon = _month_to_num(m.group(1))
        day = int(m.group(2))
        year = int(m.group(3))
        if mon:
            return f"{year}-{_zero(mon)}-{_zero(day)}"

    # 3) August 2025 / Aug 2025 -> 2025-08
    m = _RX_MY.search(t)
    if m:
        mon = _month_to_num(m.group(1))
        year = int(m.group(2))
        if mon:
            return f"{year}-{_zero(mon)}"

    # 4) 2025 August -> 2025-08
    m = _RX_YM.search(t)
    if m:
        year = int(m.group(1))
        mon = _month_to_num(m.group(2))
        if mon:
            return f"{year}-{_zero(mon)}"

    # Don’t infer missing years (e.g., "19th August")
    return ""

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
                    {"role": "system", "content":
                        "You are a careful timeline extraction assistant. "
                        "Return ONLY items with resolvable dates and normalize dates to ISO."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
                timeout=30,
            )
            return resp["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit in chronology: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def _valid_date(self, s) -> bool:
        return isinstance(s, str) and _DATE_RX.match(s.strip()) is not None

    def _normalize_event(self, e: Dict[str, Any]) -> Dict[str, Any]:
        date = e.get("date", "")
        # If model returned natural text (e.g., "19th August 2025" / "August 2025"), try to normalize.
        if not self._valid_date(date):
            iso = _nl_to_iso(date)
            date = iso if iso else None
        else:
            date = date.strip()

        title = (e.get("title") or "").strip()[:160]
        desc  = (e.get("desc")  or "").strip()[:400]
        return {"date": date, "title": title, "desc": desc}

    def extract_events_from_text(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Returns only DATED events:
        [{ "date":"YYYY|YYYY-MM|YYYY-MM-DD", "title":"...", "desc":"..." }]
        """
        if not text or not text.strip():
            return []

        prompt = (
            "From the text below, extract up to {k} events that have explicit, resolvable dates.\n"
            "Return ONLY a JSON array of objects with keys exactly: date, title, desc.\n"
            "- Accept natural formats like '19th August 2025', 'August 2025', 'Aug 2025', "
            "  but CONVERT them to ISO: 'YYYY-MM-DD' or 'YYYY-MM'. Year-only is 'YYYY'.\n"
            "- If you cannot determine a year for an item, SKIP that item.\n"
            "- DO NOT include any item without a date.\n\n"
            "TEXT:\n{t}"
        ).format(k=top_k, t=text[:12000])

        raw = self._call_llm(prompt, max_tokens=500)

        # Prefer strict JSON from the model
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                out = []
                for e in data:
                    if not isinstance(e, dict):
                        continue
                    ne = self._normalize_event(e)
                    if ne.get("date"):  # keep only dated
                        out.append(ne)
                return out[:top_k]
        except Exception:
            pass

        # Heuristic fallback: scan lines; keep only those with a resolvable date, normalize to ISO
        events = []
        for line in raw.splitlines():
            ln = line.strip("-•* \t")
            if not ln:
                continue

            # Try to find a natural-language date in the line
            iso = _nl_to_iso(ln)
            if not iso:
                # Also try at line start like "2025-08-19: Title ..."
                m = re.match(r"^(\d{4}(?:-\d{1,2}){0,2})\b[:\s-]*", ln)
                if m and _DATE_RX.match(m.group(1)):
                    iso = m.group(1)

            if not iso:
                continue  # skip undated lines

            # Split into title/desc after the date if possible
            rest = ln
            if ln.lower().startswith(iso.lower()):
                rest = ln[len(m.group(1)):].lstrip(": -\t")

            parts = rest.split(":", 1)
            title = (parts[0] or "").strip()[:120] or "Event"
            desc  = (parts[1].strip() if len(parts) > 1 else "").strip()[:240]

            events.append({"date": iso, "title": title, "desc": desc})

        return events[:top_k]

    def merge_events(self, per_page: List[Tuple[int, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        Merge & dedupe events across pages; DATED items only; sorted by date then title.
        """
        bucket: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for page_no, events in per_page:
            for ev in events or []:
                d = (ev.get("date") or "").strip()
                if not _DATE_RX.match(d):
                    continue  # strictly skip undated
                key = (d, (ev.get("title") or "").lower())
                node = bucket.get(key)
                if not node:
                    node = {**ev, "date": d, "pages": [page_no]}
                    bucket[key] = node
                else:
                    if page_no not in node["pages"]:
                        node["pages"].append(page_no)

        def sort_key(item):
            date = item.get("date")
            if not date:
                return (dt.date.max, item.get("title") or "")
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
