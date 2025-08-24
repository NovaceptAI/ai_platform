from __future__ import annotations
from celery import shared_task
from app.db import db
from app.models import Progress
from app.services.stages.create.interactive_comic_strip_builder_service import InteractiveComicStripBuilderService
import logging

log = logging.getLogger(__name__)


def _progress_update(progress_id, **kwargs):
    p = db.session.get(Progress, progress_id)
    if not p:
        return
    for k, v in kwargs.items():
        setattr(p, k, v)
    db.session.add(p)
    db.session.commit()


@shared_task(bind=True, max_retries=1, default_retry_delay=10, name="interactive_comic_strip_builder.run")
def run_interactive_comic_strip_builder(self, progress_id: str, input_payload: dict):
    try:
        _progress_update(progress_id, status="running", percentage=10)
        _ = InteractiveComicStripBuilderService.process(input_payload)
        _progress_update(progress_id, status="running", percentage=85)
        _progress_update(progress_id, status="done", percentage=100)
    except Exception:
        log.exception("Interactive Comic Strip Builder task failed")
        _progress_update(progress_id, status="failed")
        raise