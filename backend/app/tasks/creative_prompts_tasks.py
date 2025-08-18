import logging, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.create.creative_prompts_service import CreativePromptsService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="creative_prompts.build_for_file")
def build_prompts_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    1) Iterate pages for file_id; generate per-page creative prompts from page_text.
    2) (Optionally) store per-page prompts in FilePage.page_prompts if column exists.
    3) Update Progress percentage as we go.
    Final merged view is assembled in /creative_prompts/results.
    """
    s = db.session()
    svc = CreativePromptsService()
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

        has_col = hasattr(FilePage, "page_prompts")
        done = 0

        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_prompts", None):
                    pass  # already generated
                else:
                    prompts = svc.generate_prompts_from_text(page.page_text or "")
                    if has_col:
                        setattr(page, "page_prompts", prompts)
                    s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[CreativePrompts] Failed page {page.id}: {e}")

            _bump_progress(s, progress_id, int((done / total) * 100))
            time.sleep(0.2)

        _finish_progress(s, progress_id, status="completed", pct=100)

    except Exception:
        s.rollback()
        log.exception("[CreativePrompts] Task failed")
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