from __future__ import annotations
import logging
from celery import shared_task
from app.db import db
from app.models import Progress
from app.services.ai_summarizer_service import AiSummarizerService


log = logging.getLogger(__name__)


def _progress_update(progress_id, **kwargs):
    p = db.session.get(Progress, progress_id)
    if not p:
        return
    for k, v in kwargs.items():
        setattr(p, k, v)
    db.session.add(p)
    db.session.commit()


@shared_task(bind=True, max_retries=1, default_retry_delay=10, name="ai_summarizer.run")
def run_ai_summarizer(self, progress_id: str, input_payload: dict):
    try:
        _progress_update(progress_id, status="in_progress", percentage=10)
        result = AiSummarizerService.process(input_payload)
        _progress_update(progress_id, percentage=85)
        p = db.session.get(Progress, progress_id)
        if p:
            p.result_json = result
            db.session.add(p)
            db.session.commit()
        _progress_update(progress_id, status="completed", percentage=100)
    except Exception:
        log.exception("AI Summarizer task failed")
        _progress_update(progress_id, status="failed")
        raise