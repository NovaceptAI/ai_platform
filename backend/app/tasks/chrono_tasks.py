import logging, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.discover.chrono_service import ChronologyService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_chronology_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    1) Iterate pages for file_id; extract per-page events from page_text.
    2) (Optionally) store per-page events in FilePage.page_chronology if column exists.
    3) Update Progress percentage as we go.
    Final results are merged in /chronology/results endpoint.
    """
    s = db.session()
    svc = ChronologyService()
    try:
        pages = (
            s.query(FilePage)
            .filter(FilePage.file_id == file_id)
            .order_by(asc(FilePage.page_number))
            .all()
        )
        total = len(pages)
        if total == 0:
            _finish_progress(s, progress_id, status="completed", pct=100)
            return

        # detect optional column existence once (SQLAlchemy attr check)
        has_col = hasattr(FilePage, "page_chronology")

        done = 0
        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_chronology", None):
                    pass  # already extracted
                else:
                    events = svc.extract_events_from_text(page.page_text or "")
                    if has_col:
                        setattr(page, "page_chronology", events)
                    s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Chronology] Failed page {page.id}: {e}")

            # progress update
            pct = int((done / total) * 100)
            _bump_progress(s, progress_id, pct)
            time.sleep(0.2)  # gentle pacing

        _finish_progress(s, progress_id, status="completed", pct=100)

    except Exception:
        s.rollback()
        log.exception("[Chronology] Task failed")
        _finish_progress(s, progress_id, status="failed")
        raise
    finally:
        s.close()


def _bump_progress(s, progress_id, pct: int):
    p = s.query(Progress).get(progress_id)
    if p:
        p.percentage = max(p.percentage or 0, int(pct))
        s.commit()

def _finish_progress(s, progress_id, status: str, pct: int = None):
    p = s.query(Progress).get(progress_id)
    if p:
        p.status = status
        if pct is not None:
            p.percentage = pct
        s.commit()