from app.main import celery_app
from app.stages.discover.summarizer.summarizer import Summarizer
from app.db import db
from app.models import FilePage, Progress
from celery.utils.log import get_task_logger
from celery import states, group
from celery.exceptions import Ignore
from math import ceil

CHUNK_SIZE = 8            # tune for your page size & rate limits
STAGGER_SECONDS = 10      # gentle ramp to avoid bursts
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


@celery_app.task(bind=True, acks_late=True)
def summarize_file_kickoff(self, file_id: str, progress_id: str):
    """
    Fan-out a file's pages into multiple summarize_page_batch tasks.
    Uses small countdown offsets to avoid rate-limit spikes.
    """
    session = db.session()
    try:
        # 1) Collect all page IDs for this file
        page_ids = [
            pid for (pid,) in session.query(FilePage.id)
                                     .filter(FilePage.file_id == file_id)
                                     .order_by(FilePage.page_number.asc())
                                     .all()
        ]
        if not page_ids:
            # empty file: mark progress completed
            prog = session.query(Progress).get(progress_id)
            if prog:
                prog.percentage = 100
                prog.status = "completed"
                session.add(prog); session.commit()
            return {"file_id": file_id, "percent": 100, "message": "No pages"}

        # 2) Slice into batches
        chunks = [page_ids[i:i+CHUNK_SIZE] for i in range(0, len(page_ids), CHUNK_SIZE)]

        # 3) Schedule batches with light staggering
        for idx, chunk in enumerate(chunks):
            summarize_page_batch.apply_async(args=[chunk], countdown=idx * STAGGER_SECONDS)

        # Option A (simple): rely on each page-batch to update Progress (you already do this).
        # Option B (optional): schedule a lightweight polling/finisher to flip 'completed'
        # after the last batch should have finished. Often not needed because your per-batch
        # task already computes Progress percentage.

        return {"file_id": file_id, "scheduled_batches": len(chunks)}

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()