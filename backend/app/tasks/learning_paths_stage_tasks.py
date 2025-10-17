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
    Schedule work for a given tool across the provided file_ids by delegating 
    to the existing individual tool tasks. Each tool manages its own progress.
    Return True if dispatched, False if the tool_key is unknown (no-op).
    """
    # Create a new session for this function
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        # For discover stage tools, create individual progress records and call tasks
        if tool_key == "summarizer":
            for fid in file_ids or []:
                # Create progress record for this file
                from uuid import uuid4
                progress = Progress(
                    id=uuid4(),
                    user_id=user_id,
                    file_id=fid,
                    tool="summarizer",
                    status="queued"
                )
                session.add(progress)
                session.commit()
                
                # Call the individual summarizer task
                _summarize_file.apply_async(args=[fid, str(progress.id)])
            return True

        elif tool_key == "segmenter":
            from app.tasks.segmenter_tasks import build_segments_for_file
            for fid in file_ids or []:
                # Create progress record for this file  
                from uuid import uuid4
                progress = Progress(
                    id=uuid4(),
                    user_id=user_id,
                    file_id=fid,
                    tool="segmenter", 
                    status="queued"
                )
                session.add(progress)
                session.commit()
                
                build_segments_for_file.apply_async(args=[fid, str(progress.id), False])
            return True

        elif tool_key == "doc_analysis":
            from app.tasks.doc_analysis_tasks import build_doc_analysis_for_file
            for fid in file_ids or []:
                from uuid import uuid4
                progress = Progress(
                    id=uuid4(),
                    user_id=user_id,
                    file_id=fid,
                    tool="doc_analysis",
                    status="queued"
                )
                session.add(progress)
                session.commit()
                
                build_doc_analysis_for_file.apply_async(args=[fid, str(progress.id), False])
            return True

        elif tool_key in ["chronology_strict", "chronology"]:
            from app.tasks.chrono_tasks import build_chronology_for_file
            for fid in file_ids or []:
                from uuid import uuid4
                progress = Progress(
                    id=uuid4(),
                    user_id=user_id,
                    file_id=fid,
                    tool="chronology",
                    status="queued"
                )
                session.add(progress)
                session.commit()
                
                build_chronology_for_file.apply_async(args=[fid, str(progress.id), False])
            return True

        elif tool_key == "evidence_extractor":
            from app.tasks.evidence_extractor_tasks import build_evidence_for_file
            for fid in file_ids or []:
                from uuid import uuid4
                progress = Progress(
                    id=uuid4(),
                    user_id=user_id,
                    file_id=fid,
                    tool="evidence_extractor",
                    status="queued"
                )
                session.add(progress)
                session.commit()
                
                build_evidence_for_file.apply_async(args=[fid, str(progress.id), False])
            return True

        elif tool_key == "comparison":
            from app.tasks.comparison_tasks import build_comparison_for_files
            if len(file_ids or []) >= 2:
                from uuid import uuid4
                progress = Progress(
                    id=uuid4(),
                    user_id=user_id,
                    tool="comparison",
                    status="queued"
                )
                session.add(progress)
                session.commit()
                
                build_comparison_for_files.apply_async(args=[file_ids, str(progress.id)])
            return True

        # ORGANIZE STAGE TOOLS - These create their own progress internally
        elif tool_key == "collections_boards":
            from app.tasks.collections_tasks import create_collections_task
            create_collections_task.apply_async(args=[user_id, file_ids])
            return True

        elif tool_key == "tag_taxonomy_manager":
            from app.tasks.tagging_tasks import build_tag_taxonomy_task
            build_tag_taxonomy_task.apply_async(args=[user_id, file_ids])
            return True

        elif tool_key == "cluster_builder":
            from app.tasks.clustering_tasks import create_content_clusters_task
            create_content_clusters_task.apply_async(args=[user_id, file_ids])
            return True

        elif tool_key == "concept_graph":
            from app.tasks.concept_graph_tasks import build_concept_graph_task
            build_concept_graph_task.apply_async(args=[user_id, file_ids])
            return True

        elif tool_key == "saved_views":
            from app.tasks.saved_views_tasks import create_saved_views_task
            create_saved_views_task.apply_async(args=[user_id, file_ids])
            return True

        # Unknown tool
        return False
    
    except Exception as e:
        session.rollback()
        log.error(f"Tool dispatch failed for {tool_key}: {e}")
        return False
    finally:
        session.close()





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
    # Create a new session for this task
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    s = Session()
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
        # Load step data while session is active to avoid detached instance errors
        steps_data = []
        for st in (lp.steps or []):
            step_config = st.config or {}
            step_stage = step_config.get("stage", "discover")
            if step_stage == stage:
                steps_data.append({
                    "tool_key": st.tool_key,
                    "position": st.position,
                    "config": step_config
                })
        
        total = len(steps_data)
        if total == 0:
            # Nothing to run for this stage — mark completed & unlock next.
            _unlock_and_finish_stage(s, ulp, stage, progress_id)
            return

        done = 0
        for step_data in steps_data:
            try:
                dispatched = _dispatch_tool(step_data["tool_key"], file_ids or [], user_id)
                if not dispatched:
                    log.warning("[LP:stage] No dispatcher for tool '%s' (stage=%s)", step_data["tool_key"], stage)
                s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error("[LP:stage] Step failed (tool=%s, pos=%s, stage=%s): %s",
                          step_data["tool_key"], step_data["position"], stage, e)

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
