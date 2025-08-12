import logging, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.doc_analysis_service import DocAnalysisService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_doc_analysis_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Page-by-page analysis (entities, tags, length) with progress. We do not persist yet.
    Results are aggregated on the results endpoint.
    """
    s = db.session()
    svc = DocAnalysisService()
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

        # Compute per-page (no persistence now)
        done = 0
        for page in pages:
            try:
                # Just a ping to LLM to distribute load and reflect progress;
                # final results will be computed in /results again per your request.
                svc.analyze_page(page.page_text or "")
                done += 1
            except Exception as e:
                log.error(f"[DocAnalysis] Failed page {page.id}: {e}")

            _bump_progress(s, progress_id, int(done*100/total))
            time.sleep(0.2)

        _finish_progress(s, progress_id, "completed", 100)
    except Exception:
        s.rollback()
        log.exception("[DocAnalysis] Task failed")
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
