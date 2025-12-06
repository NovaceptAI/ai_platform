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

def _check_data_exists(session, tool_key: str, file_id: str) -> bool:
    """
    Check if data already exists for a given tool and file_id.
    Returns True if data exists, False otherwise.
    """
    from app.models.files import FilePage, UploadedFile
    from app.models.analysis_results import (
        SegmentResult, DocumentAnalysisResult, ChronologyResult,
        EvidenceExtractionResult, ComparisonResult
    )

    try:
        if tool_key == "summarizer":
            # Check if file has page summaries
            uploaded_file = session.query(UploadedFile).filter_by(id=file_id).first()
            if not uploaded_file:
                return False
            # Check if overall summary exists or if any pages have summaries
            if uploaded_file.overall_summary:
                return True
            page_with_summary = session.query(FilePage).filter(
                FilePage.file_id == file_id,
                FilePage.page_summary.isnot(None)
            ).first()
            return page_with_summary is not None

        elif tool_key == "segmenter":
            # Check if SegmentResult exists for this file
            result = session.query(SegmentResult).filter_by(
                file_id=file_id,
                is_active=True
            ).first()
            return result is not None

        elif tool_key == "doc_analysis":
            # Check if DocumentAnalysisResult exists
            result = session.query(DocumentAnalysisResult).filter_by(
                file_id=file_id,
                is_active=True
            ).first()
            return result is not None

        elif tool_key in ["chronology_strict", "chronology"]:
            # Check if ChronologyResult exists
            result = session.query(ChronologyResult).filter_by(
                file_id=file_id,
                is_active=True
            ).first()
            return result is not None

        elif tool_key == "evidence_extractor":
            # Check if EvidenceExtractionResult exists
            result = session.query(EvidenceExtractionResult).filter_by(
                file_id=file_id,
                is_active=True
            ).first()
            return result is not None

        # For organize stage tools, we don't check existence (they process multiple files)
        elif tool_key in ["collections_boards", "tag_taxonomy_manager", "cluster_builder",
                          "concept_graph", "saved_views"]:
            return False

        # For comparison, we would need to check with a composite key of all file_ids
        elif tool_key == "comparison":
            return False  # Always run comparison as it depends on multiple files

        return False
    except Exception as e:
        log.error(f"Error checking data existence for {tool_key}, file {file_id}: {e}")
        return False


def _dispatch_tool(tool_key: str, file_ids: List[str], user_id: str) -> dict:
    """
    Schedule work for a given tool across the provided file_ids by delegating
    to the existing individual tool tasks. Each tool manages its own progress.
    Only dispatches tasks if data doesn't already exist.
    Returns dict with: {'dispatched': bool, 'tasks_queued': int, 'tasks_skipped': int}
    """
    # Create a new session for this function
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()

    try:
        # For discover stage tools, create individual progress records and call tasks
        if tool_key == "summarizer":
            tasks_queued = 0
            for fid in file_ids or []:
                # Check if data already exists
                if _check_data_exists(session, tool_key, fid):
                    log.info(f"Summarizer data already exists for file {fid}, skipping")
                    continue
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
                tasks_queued += 1

            tasks_skipped = len(file_ids) - tasks_queued
            log.info(f"Summarizer: queued {tasks_queued} tasks, skipped {tasks_skipped} (data exists)")
            return {'dispatched': True, 'tasks_queued': tasks_queued, 'tasks_skipped': tasks_skipped}

        elif tool_key == "segmenter":
            from app.tasks.segmenter_tasks import build_segments_for_file
            tasks_queued = 0
            for fid in file_ids or []:
                # Check if data already exists
                if _check_data_exists(session, tool_key, fid):
                    log.info(f"Segmenter data already exists for file {fid}, skipping")
                    continue

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
                tasks_queued += 1

            tasks_skipped = len(file_ids) - tasks_queued
            log.info(f"Segmenter: queued {tasks_queued} tasks, skipped {tasks_skipped} (data exists)")
            return {'dispatched': True, 'tasks_queued': tasks_queued, 'tasks_skipped': tasks_skipped}

        elif tool_key == "doc_analysis":
            from app.tasks.doc_analysis_tasks import build_doc_analysis_for_file
            tasks_queued = 0
            for fid in file_ids or []:
                # Check if data already exists
                if _check_data_exists(session, tool_key, fid):
                    log.info(f"Doc analysis data already exists for file {fid}, skipping")
                    continue

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
                tasks_queued += 1

            tasks_skipped = len(file_ids) - tasks_queued
            log.info(f"Doc analysis: queued {tasks_queued} tasks, skipped {tasks_skipped} (data exists)")
            return {'dispatched': True, 'tasks_queued': tasks_queued, 'tasks_skipped': tasks_skipped}

        elif tool_key in ["chronology_strict", "chronology"]:
            from app.tasks.chrono_tasks import build_chronology_for_file
            tasks_queued = 0
            for fid in file_ids or []:
                # Check if data already exists
                if _check_data_exists(session, tool_key, fid):
                    log.info(f"Chronology data already exists for file {fid}, skipping")
                    continue

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
                tasks_queued += 1

            tasks_skipped = len(file_ids) - tasks_queued
            log.info(f"Chronology: queued {tasks_queued} tasks, skipped {tasks_skipped} (data exists)")
            return {'dispatched': True, 'tasks_queued': tasks_queued, 'tasks_skipped': tasks_skipped}

        elif tool_key == "evidence_extractor":
            from app.tasks.evidence_extractor_tasks import build_evidence_for_file
            tasks_queued = 0
            for fid in file_ids or []:
                # Check if data already exists
                if _check_data_exists(session, tool_key, fid):
                    log.info(f"Evidence extractor data already exists for file {fid}, skipping")
                    continue

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
                tasks_queued += 1

            tasks_skipped = len(file_ids) - tasks_queued
            log.info(f"Evidence extractor: queued {tasks_queued} tasks, skipped {tasks_skipped} (data exists)")
            return {'dispatched': True, 'tasks_queued': tasks_queued, 'tasks_skipped': tasks_skipped}

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
                return {'dispatched': True, 'tasks_queued': 1, 'tasks_skipped': 0}
            return {'dispatched': False, 'tasks_queued': 0, 'tasks_skipped': 0}

        # ORGANIZE STAGE TOOLS - These create their own progress internally
        elif tool_key == "collections_boards":
            from app.tasks.collections_tasks import create_collections_task
            create_collections_task.apply_async(args=[user_id, file_ids])
            return {'dispatched': True, 'tasks_queued': 1, 'tasks_skipped': 0}

        elif tool_key == "tag_taxonomy_manager":
            from app.tasks.tagging_tasks import build_tag_taxonomy_task
            build_tag_taxonomy_task.apply_async(args=[user_id, file_ids])
            return {'dispatched': True, 'tasks_queued': 1, 'tasks_skipped': 0}

        elif tool_key == "cluster_builder":
            from app.tasks.clustering_tasks import create_content_clusters_task
            create_content_clusters_task.apply_async(args=[user_id, file_ids])
            return {'dispatched': True, 'tasks_queued': 1, 'tasks_skipped': 0}

        elif tool_key == "concept_graph":
            from app.tasks.concept_graph_tasks import build_concept_graph_task
            build_concept_graph_task.apply_async(args=[user_id, file_ids])
            return {'dispatched': True, 'tasks_queued': 1, 'tasks_skipped': 0}

        elif tool_key == "saved_views":
            from app.tasks.saved_views_tasks import create_saved_views_task
            create_saved_views_task.apply_async(args=[user_id, file_ids])
            return {'dispatched': True, 'tasks_queued': 1, 'tasks_skipped': 0}

        # Unknown tool
        return {'dispatched': False, 'tasks_queued': 0, 'tasks_skipped': 0}

    except Exception as e:
        session.rollback()
        log.error(f"Tool dispatch failed for {tool_key}: {e}")
        return {'dispatched': False, 'tasks_queued': 0, 'tasks_skipped': 0}
    finally:
        session.close()





# ---- Stage Orchestration (chrono-style) --------------------------------------

@shared_task(bind=True, max_retries=30, default_retry_delay=10, name="learning_path.monitor_completion")
def monitor_stage_completion(self, user_id: str, path_id: str, stage: str, progress_id: str):
    """
    Monitor all individual tool progress records for a stage and mark the stage
    as complete once all tools have finished (completed or failed).
    Retries every 10 seconds until all tasks are done (max 30 retries = 5 minutes).
    """
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    s = Session()

    try:
        # Get the stage progress record
        prog = s.query(Progress).get(progress_id)
        ulp = s.query(UserLearningPath).filter_by(user_id=UUID(user_id), path_id=UUID(path_id)).first()

        if not prog or not ulp:
            log.error("[LP:monitor] Invalid Progress/User-LP (progress_id=%s, user_id=%s, path_id=%s)",
                      progress_id, user_id, path_id)
            return

        # Find all progress records for individual tools in this stage
        # These were created by _dispatch_tool with file_id set
        tool_progress_records = s.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.file_id.isnot(None),  # Individual tool tasks have file_id
            Progress.tool.in_([
                'summarizer', 'segmenter', 'doc_analysis', 'chronology',
                'evidence_extractor', 'comparison',
                'collections_boards', 'tag_taxonomy_manager', 'cluster_builder',
                'concept_graph', 'saved_views'
            ])
        ).order_by(Progress.created_at.desc()).all()

        # Filter to only recent ones (created after this stage progress was created)
        stage_created_at = prog.created_at
        recent_tool_progress = [
            p for p in tool_progress_records
            if p.created_at >= stage_created_at
        ]

        if not recent_tool_progress:
            # No individual tool tasks found - possibly all data existed
            log.info("[LP:monitor] No tool progress records found, marking stage complete")
            _unlock_and_finish_stage(s, ulp, stage, progress_id)
            return

        # Check if all are completed or failed
        total = len(recent_tool_progress)
        completed = sum(1 for p in recent_tool_progress if p.status in ['completed', 'failed'])
        in_progress = sum(1 for p in recent_tool_progress if p.status in ['queued', 'in_progress', 'processing_media'])

        log.info(f"[LP:monitor] Stage '{stage}': {completed}/{total} tools finished, {in_progress} still running")

        # Update stage progress percentage based on individual tool completion
        stage_percentage = int((completed / max(total, 1)) * 100)
        _bump_progress(s, progress_id, stage_percentage)

        if in_progress > 0:
            # Still have tasks running, retry later
            log.info(f"[LP:monitor] Retrying in 10 seconds (attempt {self.request.retries + 1}/30)")
            raise self.retry(countdown=10, max_retries=30)
        else:
            # All tasks finished
            log.info(f"[LP:monitor] All tools finished for stage '{stage}', marking complete")
            _unlock_and_finish_stage(s, ulp, stage, progress_id)

    except Exception as e:
        if self.request.retries >= self.max_retries:
            log.error(f"[LP:monitor] Max retries reached for stage '{stage}', marking failed: {e}")
            _finish_progress(s, progress_id, status="failed")
        else:
            s.rollback()
            raise
    finally:
        try:
            s.close()
        except sa_exc.ResourceClosedError:
            pass


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

        # Track dispatched tools and their results
        total_tasks_queued = 0
        total_tasks_skipped = 0
        done = 0

        for step_data in steps_data:
            try:
                result = _dispatch_tool(step_data["tool_key"], file_ids or [], user_id)
                if not result.get('dispatched'):
                    log.warning("[LP:stage] No dispatcher for tool '%s' (stage=%s)", step_data["tool_key"], stage)
                else:
                    total_tasks_queued += result.get('tasks_queued', 0)
                    total_tasks_skipped += result.get('tasks_skipped', 0)
                s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error("[LP:stage] Step failed (tool=%s, pos=%s, stage=%s): %s",
                          step_data["tool_key"], step_data["position"], stage, e)

            # Coarse progress bump per step dispatch
            _bump_progress(s, progress_id, int((done / max(total, 1)) * 100))

        # Log summary
        log.info(f"[LP:stage] Stage '{stage}' dispatch complete: {total_tasks_queued} tasks queued, {total_tasks_skipped} skipped (data exists)")

        # If all tasks were skipped (data already exists), mark stage complete immediately
        if total_tasks_queued == 0 and total_tasks_skipped > 0:
            log.info(f"[LP:stage] All data exists for stage '{stage}', marking complete immediately")
            _unlock_and_finish_stage(s, ulp, stage, progress_id)
        elif total_tasks_queued == 0:
            # No tasks queued and none skipped - stage is empty or all tools failed
            log.info(f"[LP:stage] No tasks queued for stage '{stage}', marking complete")
            _unlock_and_finish_stage(s, ulp, stage, progress_id)
        else:
            # Tasks were queued - schedule a monitoring task to check completion
            log.info(f"[LP:stage] {total_tasks_queued} tasks queued, scheduling completion monitor")
            monitor_stage_completion.apply_async(
                args=[user_id, path_id, stage, progress_id],
                countdown=10  # Check after 10 seconds
            )

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
