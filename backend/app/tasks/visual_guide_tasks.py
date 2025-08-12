import logging, os, tempfile, json, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.discover.visual_guide_service import VisualGuideService

# Optional vault loader
try:
    from app.routes.upload import download_blob_to_tmp
except Exception:
    download_blob_to_tmp = None

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_visual_study_guide(self, progress_id: str, method: str, payload: dict):
    """
    Build study guide and stash it in Progress (or later a dedicated table).
    payload:
      - category (if method=category)
      - text (if method=text)
      - filename/fromVault (if method=document)
    We store JSON in Progress.status detail (or add a Progress.result_json column in DB if you want).
    """
    s = db.session()
    svc = VisualGuideService()
    tmp_path = None
    try:
        prog = s.query(Progress).get(progress_id)
        if not prog:
            return

        # simple 0%
        prog.percentage = 5
        prog.status = "in_progress"
        s.commit()

        method = (method or "category").lower()
        if method == "category":
            out = svc.from_category(payload.get("category",""))
        elif method == "text":
            out = svc.from_text(payload.get("text",""))
        elif method == "document":
            if payload.get("fromVault") and download_blob_to_tmp:
                tmp_path = download_blob_to_tmp(payload.get("filename"))
                out = svc.from_document(tmp_path)
            else:
                # if you want to pass a transient path in payload["tmp_path"] you can handle it here
                out = {"summary": "", "topics": []}
        else:
            out = {"summary": "", "topics": []}

        # simulate steps
        prog.percentage = 100
        prog.status = json.dumps({"result": out})  # TEMP: stash result in status
        s.commit()

    except Exception as e:
        s.rollback()
        log.exception("[VSG] task failed")
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