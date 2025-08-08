from app.main import celery_app
from app.stages.discover.summarizer.summarizer import Summarizer
from app.db import db
from app.models import FilePage, Progress
from celery.utils.log import get_task_logger
from celery import states
from celery.exceptions import Ignore

logger = get_task_logger(__name__)

# Tip: You can also configure autoretry at the decorator level for specific exceptions
@celery_app.task(bind=True, max_retries=5, default_retry_delay=10, acks_late=True)
def summarize_page_batch(self, page_ids):
    """
    Summarize a batch of pages.
    Rotation: Each task instantiates Summarizer(), which selects the next Azure key/base.
    Retries: on RateLimitError or transient errors, Celery retry kicks in with backoff.
    """
    session = db.session()
    summarizer = Summarizer()

    try:
        pages = session.query(FilePage).filter(FilePage.id.in_(page_ids)).all()
        if not pages:
            logger.warning("No pages found for batch.")
            self.update_state(state=states.SUCCESS, meta={"message": "Empty batch"})
            return

        file_id = pages[0].file_id

        for page in pages:
            if page.page_summary:
                logger.info(f"Page {page.id} already summarized. Skipping.")
                continue

            try:
                summary = summarizer._summarize_text(page.page_text)
                page.page_summary = summary
                session.add(page)
            except Exception as inner_e:
                # Exponential backoff with jitter
                countdown = min(60, 10 * (2 ** self.request.retries))
                logger.error(f"Failed to summarize page {page.id}. Retrying in {countdown}s. Error: {inner_e}")
                session.rollback()
                raise self.retry(exc=inner_e, countdown=countdown)

        session.commit()

        # Update progress (idempotent)
        total_pages = session.query(FilePage).filter_by(file_id=file_id).count()
        summarized_pages = session.query(FilePage).filter(
            FilePage.file_id == file_id, FilePage.page_summary.isnot(None)
        ).count()
        percent = int((summarized_pages / total_pages) * 100) if total_pages else 0

        progress_record = session.query(Progress).filter_by(file_id=file_id).first()
        if progress_record:
            dirty = False
            if progress_record.percentage != percent:
                progress_record.percentage = percent
                dirty = True
            if percent == 100 and progress_record.status != "completed":
                progress_record.status = "completed"
                dirty = True
            if dirty:
                session.add(progress_record)
                session.commit()
            logger.info(f"Progress for file {file_id} updated to {percent}%")

        return {"file_id": file_id, "percent": percent}

    except Exception as e:
        session.rollback()
        logger.error(f"Batch summarization failed: {e}")
        # Re-raise for Celery's retry; if out of retries, mark as failure
        if self.request.retries >= self.max_retries:
            self.update_state(state=states.FAILURE, meta={"exc": str(e)})
            raise
        raise
    finally:
        session.close()