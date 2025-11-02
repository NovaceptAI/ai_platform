# app/tasks/learning_paths_tasks.py
import logging
from uuid import UUID
from celery import shared_task
from sqlalchemy import exc as sa_exc

from app.db import db
from app.models.learning_paths import LearningPath
from app.models.status import Progress
from app.services.learning_paths_service import LearningPathRunner
from typing import List
from typing import Optional
log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="learning_path.run")
def run_learning_path(self, user_id: str, path_id: str, progress_id: str, force: bool = False):
    """
    Orchestrates all steps in a Learning Path (in-order).
    Mirrors the structure used in chrono tasks:
      - explicit session handling
      - incremental progress bumps
      - resilient per-step try/except with logging
    """
    s = db.session()
    try:
        lp = s.get(LearningPath, UUID(path_id))
        prog = s.query(Progress).get(progress_id)

        if not lp or not prog:
            log.error("[LP] Invalid path/progress refs (path_id=%s, progress_id=%s)", path_id, progress_id)
            _finish_progress(s, progress_id, status="failed")
            return

        steps = list(lp.steps or [])
        total = len(steps)
        if total == 0:
            _finish_progress(s, progress_id, status="completed", pct=100)
            return

        done = 0
        runner = LearningPathRunner(user_id=UUID(user_id), progress=prog)

        for step in steps:
            try:
                # Execute the tool step (runner dispatches by step.tool_key)
                runner.run_step(step)
                s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                # Stay resilient like chronology page loop: log and continue
                log.error("[LP] Step failed (tool=%s, position=%s): %s",
                          getattr(step, "tool_key", "?"), getattr(step, "position", "?"), e)

            # Progress bump after each step (coarse-grained)
            pct = int((done / max(total, 1)) * 100)
            _bump_progress(s, progress_id, pct)

        _finish_progress(s, progress_id, status="completed", pct=100)

    except Exception:
        s.rollback()
        log.exception("[LP] Orchestration task failed")
        _finish_progress(s, progress_id, status="failed")
        raise
    finally:
        try:
            s.close()
        except sa_exc.ResourceClosedError:
            pass


# ----------------------------
# Progress helpers (chrono-style)
# ----------------------------
def _bump_progress(s, progress_id, pct: int):
    p = s.query(Progress).get(progress_id)
    if p:
        # keep monotonic non-decreasing
        p.percentage = max(p.percentage or 0, int(pct))
        s.commit()


def _finish_progress(s, progress_id, status: str, pct: Optional[int] = None):
    p = s.query(Progress).get(progress_id)
    if p:
        p.status = status
        if pct is not None:
            p.percentage = pct
        s.commit()
