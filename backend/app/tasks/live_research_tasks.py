from uuid import UUID
from celery.utils.log import get_task_logger
from app.db import db
from celery import shared_task
from app.models.status import Progress
from app.services.live_research_service import LiveResearchService

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=5, default_retry_delay=10, acks_late=True)
def start_research_session_task(self, user_id: str, project_id: str, progress_id: str):
    session = db.session()
    try:
        svc = LiveResearchService(session=session)
        rs = svc.start_session(UUID(user_id), UUID(project_id))
        prog = session.get(Progress, UUID(progress_id))
        prog.percentage = 100
        prog.status = 'completed'
        session.commit()
    except Exception:
        session.rollback()
        logger.exception('start session failed')
        raise

@shared_task(bind=True, max_retries=3, default_retry_delay=8, acks_late=True)
def browser_search_task(self, search_id: str):
    session = db.session()
    try:
        svc = LiveResearchService(session=session)
        svc.run_browser_search(UUID(search_id))
        session.commit()
    except Exception:
        session.rollback()
        logger.exception('browser search failed')
        raise

@shared_task(bind=True, max_retries=3, default_retry_delay=8, acks_late=True)
def scraper_task(self, source_id: str):
    session = db.session()
    try:
        svc = LiveResearchService(session=session)
        svc.run_scrape(UUID(source_id))
        session.commit()
    except Exception:
        session.rollback()
        logger.exception('scrape failed')
        raise

@shared_task(bind=True, max_retries=3, default_retry_delay=12, acks_late=True)
def synthesize_notes_task(self, session_id: str, progress_id: str):
    session = db.session()
    try:
        svc = LiveResearchService(session=session)
        svc.summarize_session(UUID(session_id), UUID(progress_id))
        session.commit()
    except Exception:
        session.rollback()
        logger.exception('synthesis failed')
        raise
