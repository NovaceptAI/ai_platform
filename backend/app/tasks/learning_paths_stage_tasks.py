# app/tasks/learning_paths_stage_tasks.py
import logging
from uuid import UUID
from celery import shared_task
from sqlalchemy import exc as sa_exc

from app.db import db
from app.models.learning_paths import LearningPath, UserLearningPath
from app.models.status import Progress
from app.tasks.summarizer_tasks import summarize_file_kickoff as _summarize_file
from typing import List
from typing import Optional
# TODO: wire additional tool tasks here (segmenter, comparison, etc.)

log = logging.getLogger(__name__)


# ---- Tool Dispatch Map -------------------------------------------------------

def _dispatch_tool(tool_key: str, file_ids: List[str], user_id: str) -> bool:
    """
    Schedule work for a given tool across the provided file_ids.
    Return True if dispatched, False if the tool_key is unknown (no-op).
    """
    s = db.session()

    if tool_key == "summarizer":
        for fid in file_ids or []:
            sub_prog = Progress(user_id=user_id, tool="summarizer", status="in_progress", percentage=0)
            s.add(sub_prog); s.commit()
            _summarize_file.apply_async(kwargs={"file_id": fid, "progress_id": str(sub_prog.id)})
        return True

    # elif tool_key == "segmentation":
    #     from app.tasks.segmenter_tasks import segment_file_kickoff
    #     for fid in file_ids or []:
    #         sub_prog = Progress(user_id=user_id, tool="segmenter", status="in_progress", percentage=0)
    #         s.add(sub_prog); s.commit()
    #         segment_file_kickoff.apply_async(kwargs={"file_id": fid, "progress_id": str(sub_prog.id)})
    #     return True

    # elif tool_key == "document_analysis":
    #     ...
    #     return True

    # Add other tools similarly.
    return False


# ---- Stage Orchestration (chrono-style) --------------------------------------

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="learning_path.run_stage")
def run_learning_path_stage(self, user_id: str, path_id: str, stage: str, file_ids: List[str], progress_id: str):
    """
    Run all steps in a specific stage of a Learning Path.
    - Enforces valid stage name.
    - Iterates ordered steps filtered by stage.
    - Resilient per-step execution (log/continue).
    - Monotonic progress bumps and clean finish/fail.
    """
    s = db.session()
    try:
        lp = s.get(LearningPath, UUID(path_id))
        prog = s.query(Progress).get(progress_id)
        ulp = s.query(UserLearningPath).filter_by(user_id=UUID(user_id), path_id=UUID(path_id)).first()

        if not lp or not prog or not ulp:
            log.error("[LP:stage] Invalid LP/Progress/User-LP (path_id=%s, progress_id=%s, user_id=%s)",
                      path_id, progress_id, user_id)
            _finish_progress(s, progress_id, status="failed")
            return

        stages_order = ["discover", "organize", "mastery", "create", "collaborate"]
        if stage not in stages_order:
            log.error("[LP:stage] Invalid stage '%s'", stage)
            _finish_progress(s, progress_id, status="failed")
            return

        # Filter steps belonging to this stage (default discover if not set)
        steps = [st for st in (lp.steps or []) if (st.config or {}).get("stage", "discover") == stage]
        total = len(steps)
        if total == 0:
            # Nothing to run for this stage — mark completed & unlock next.
            _unlock_and_finish_stage(s, ulp, stage, progress_id)
            return

        done = 0
        for st in steps:
            try:
                dispatched = _dispatch_tool(getattr(st, "tool_key", None), file_ids or [], user_id)
                if not dispatched:
                    log.warning("[LP:stage] No dispatcher for tool '%s' (stage=%s)", getattr(st, "tool_key", "?"), stage)
                s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error("[LP:stage] Step failed (tool=%s, pos=%s, stage=%s): %s",
                          getattr(st, "tool_key", "?"), getattr(st, "position", "?"), stage, e)

            # Coarse progress bump per step dispatch
            _bump_progress(s, progress_id, int((done / max(total, 1)) * 100))

        # Mark stage completed & unlock next
        _unlock_and_finish_stage(s, ulp, stage, progress_id)

    except Exception:
        s.rollback()
        log.exception("[LP:stage] Orchestration failed (stage=%s)", stage)
        _finish_progress(s, progress_id, status="failed")
        raise
    finally:
        try:
            s.close()
        except sa_exc.ResourceClosedError:
            pass


# ---- Helpers (chrono-style) --------------------------------------------------

def _bump_progress(s, progress_id, pct: int):
    p = s.query(Progress).get(progress_id)
    if p:
        p.percentage = max(p.percentage or 0, int(pct))
        s.commit()


def _finish_progress(s, progress_id, status: str, pct: Optional[int] = None):
    p = s.query(Progress).get(progress_id)
    if p:
        p.status = status
        if pct is not None:
            p.percentage = pct
        s.commit()


def _unlock_and_finish_stage(s, ulp: UserLearningPath, stage: str, progress_id: str):
    """Mark the given stage as completed on the UserLearningPath and unlock the next stage."""
    order = ["discover", "organize", "mastery", "create", "collaborate"]
    ulp.current_stage = stage
    ss = dict(ulp.stage_status or {})
    ss[stage] = "completed"
    try:
        nxt = order[order.index(stage) + 1]
        if ss.get(nxt) == "locked":
            ss[nxt] = "unlocked"
    except Exception:
        # last stage or index issues — ignore
        pass
    ulp.stage_status = ss
    s.commit()

    _finish_progress(s, progress_id, status="completed", pct=100)
