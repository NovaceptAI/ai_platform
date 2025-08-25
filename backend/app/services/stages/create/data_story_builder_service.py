from __future__ import annotations
from typing import Dict, Any, List
import logging, csv, io, statistics
log = logging.getLogger(__name__)

def _try_get_file_bytes(file_id: str) -> bytes | None:
    """
    Plug into your storage helper if present; else return None.
    """
    try:
        from app.services.file_service import get_file_bytes  # if you have it
        return get_file_bytes(file_id)
    except Exception:
        return None

class DataStoryBuilderService:
    """
    Reads CSV (file_id OR params.csv_text) and proposes insights + chart specs.
    """

    @staticmethod
    def _load_csv(file_id: str | None, csv_text: str | None) -> List[dict]:
        if file_id:
            raw = _try_get_file_bytes(file_id)
            if raw:
                text = raw.decode("utf-8", errors="ignore")
                return list(csv.DictReader(io.StringIO(text)))
        if csv_text:
            return list(csv.DictReader(io.StringIO(csv_text)))
        return []

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        file_id = payload.get("file_id")
        p = (payload.get("params") or {})
        csv_text = p.get("csv_text")
        rows = DataStoryBuilderService._load_csv(file_id, csv_text)
        if not rows:
            return {"title":"Data Story Builder","insights":["No CSV data provided"],"charts":[]}

        # detect numeric columns
        numeric_cols, sample = [], rows[:200]
        for k in rows[0].keys():
            vals = []
            for r in sample:
                try: vals.append(float(r[k]))
                except: pass
            if len(vals) > max(5, len(sample)//4):
                numeric_cols.append((k, vals))

        insights = []
        for name, vals in numeric_cols:
            try:
                insights += [f"{name}: mean {round(statistics.mean(vals),2)}, min {min(vals)}, max {max(vals)}"]
            except: pass

        charts = []
        keys = list(rows[0].keys())
        if "month" in keys and numeric_cols:
            charts.append({"type":"line","x":"month","y":numeric_cols[0][0],"series":None})
        elif numeric_cols:
            cat = next((k for k in keys if k not in [c[0] for c in numeric_cols]), None)
            if cat:
                charts.append({"type":"bar","x":cat,"y":numeric_cols[0][0],"series":None})

        return {"title":"Data Story Builder","insights":insights,"charts":charts}