from app.main import celery_app
from app.stages.discover.summarizer.summarizer import Summarizer
from app.db import db
from app.models import FilePage

@celery_app.task
def summarize_page(page_id):
    session = db.session()
    try:
        page = session.get(FilePage, page_id)
        if page:
            summarizer = Summarizer()
            summary = summarizer._summarize_text(page.page_text)
            page.page_summary = summary
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()