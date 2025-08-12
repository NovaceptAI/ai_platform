import logging, os, tempfile, json, time
from celery import shared_task
from app.db import db
from app.models import Progress
from app.services.stages.discover.timeline_explorer_service import TimelineExplorerService

# Optional vault fetch
try:
    from app.routes.upload import download_blob_to_tmp
except Exception:
    download_blob_to_tmp = None

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_timeline(self, progress_id: str, method: str, payload: dict):
    """
    Build timeline and store result JSON in Progress.status (or migrate to a dedicated table).
    payload:
      - category (method=category)
      - text (method=text)
      - filename/fromVault (method=document)
    """
    s = db.session()
    svc = TimelineExplorerService()
    tmp_path = None
    try:
        prog = s.query(Progress).get(progress_id)
        if not prog:
            return

        prog.status = "in_progress"
        prog.percentage = 5
        s.commit()

        method = (method or "category").lower()
        out = {"timeline": []}

        # simulate steps and update percentage
        if method == "category":
            out = svc.from_category(payload.get("category", ""))
            prog.percentage = 100
        elif method == "text":
            out = svc.from_text(payload.get("text", ""))
            prog.percentage = 100
        elif method == "document":
            if payload.get("fromVault") and download_blob_to_tmp:
                tmp_path = download_blob_to_tmp(payload.get("filename"))
                prog.percentage = 20; s.commit()
                out = svc.from_document(tmp_path)
                prog.percentage = 100
            else:
                # (if you want to support temp path passing, handle here)
                out = {"timeline": []}
                prog.percentage = 100
        else:
            prog.percentage = 100
            out = {"timeline": []}

        prog.status = json.dumps({"result": out})
        s.commit()

    except Exception:
        s.rollback()
        log.exception("[Timeline] task failed")
        try:
            prog = s.query(Progress).get(progress_id)
            if prog:
                prog.status = "failed"
                s.commit()
        except Exception:
            s.rollback()
        raise
    finally:
        s.close()
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
