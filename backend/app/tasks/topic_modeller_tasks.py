# app/tasks/topic_modeller_task.py
import logging, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import TopicModelResult
from app.services.stages.discover.topic_modeller_service import TopicModellerService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.topics.build_for_file")
def build_topics_for_file(self, file_id: str, progress_id: str, force: bool = False):
    svc = TopicModellerService()
    s = db.session()

    try:
        pages = (
            s.query(FilePage)
            .filter(FilePage.file_id == file_id)
            .order_by(asc(FilePage.page_number))
            .all()
        )
        total = len(pages)
        if total == 0:
            prog = s.query(Progress).get(progress_id)
            if prog:
                prog.percentage = 100
                prog.status = "completed"
                s.commit()
            return

        done = 0
        page_topics_map = {}  # {page_number: [topics]}

        for page in pages:
            try:
                if not force and page.page_topics:
                    topics = page.page_topics or []
                else:
                    topics = svc.extract_topics(page.page_text or "")
                    page.page_topics = topics
                    s.commit()

                page_topics_map[page.page_number] = topics
                done += 1

            except Exception as inner:
                s.rollback()
                logger.error(f"Topic extraction failed for page {page.id}: {inner}")

            # Update progress
            percent = int((done / total) * 100)
            prog = s.query(Progress).get(progress_id)
            if prog:
                prog.percentage = max(prog.percentage or 0, percent)
                s.commit()

            time.sleep(0.2)  # pacing

        # Aggregate & persist TopicModelResult
        try:
            agg = TopicModellerService.aggregate_topics(page_topics_map)

            last = (
                s.query(TopicModelResult)
                .filter(TopicModelResult.file_id == file_id)
                .order_by(TopicModelResult.version.desc())
                .first()
            )
            next_version = (last.version + 1) if last else 1
            s.query(TopicModelResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})

            rec = TopicModelResult(
                file_id=file_id,
                version=next_version,
                is_active=True,
                method="openai",
                model_version=svc.openai_engine,
                num_topics=agg.get("num_topics"),
                topics=agg.get("topics"),
                page_topics=agg.get("page_topics"),
            )
            s.add(rec)
            s.commit()
        except Exception as e:
            s.rollback()
            logger.error(f"[TopicModeller] Failed to persist TopicModelResult: {e}")

        # Mark complete
        prog = s.query(Progress).get(progress_id)
        if prog:
            prog.percentage = 100
            prog.status = "completed"
            s.commit()

    except Exception:
        s.rollback()
        logger.exception("build_topics_for_file failed")
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