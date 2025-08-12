import logging, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.discover.segmenter_service import SegmenterService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_segments_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Iterate pages -> segment page_text -> (optionally) store FilePage.page_segments -> update Progress.
    """
    s = db.session()
    svc = SegmenterService()
    try:
        pages = (
            s.query(FilePage)
            .filter(FilePage.file_id == file_id)
            .order_by(asc(FilePage.page_number))
            .all()
        )
        total = len(pages)
        if total == 0:
            _finish_progress(s, progress_id, "completed", 100)
            return

        has_col = hasattr(FilePage, "page_segments")  # optional JSONB column

        done = 0
        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_segments", None):
                    pass
                else:
                    segs = svc.segment_page(page.page_text or "")
                    if has_col:
                        setattr(page, "page_segments", segs)
                    s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Segmentation] Failed page {page.id}: {e}")

            _bump_progress(s, progress_id, int(done * 100 / total))
            time.sleep(0.2)  # gentle pacing

        _finish_progress(s, progress_id, "completed", 100)

    except Exception:
        s.rollback()
        log.exception("[Segmentation] Task failed")
        _finish_progress(s, progress_id, "failed")
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