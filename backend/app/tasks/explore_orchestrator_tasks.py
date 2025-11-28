# app/tasks/explore_orchestrator_tasks.py

import logging
from celery import current_app, group, chord
from app.db import db
from app.models.status import Progress
from app.models import UploadedFile, FilePage, TopicModelResult, DocumentAnalysisResult, SegmentResult, ChronologyResult, SentimentResult
from datetime import datetime
import traceback

log = logging.getLogger(__name__)


@current_app.task(bind=True, max_retries=1, default_retry_delay=60)
def orchestrate_exploration_task(self, user_id: str, file_ids: list, requested_tools: list, progress_id: str, force_rerun: bool = False):
    """
    Orchestrates document exploration by:
    1. Validating what data already exists
    2. Determining which tools need to run (smart skip)
    3. Executing missing tools in parallel using Celery group()
    4. Tracking progress via tool_progress_ids
    5. Finalizing when all complete

    Args:
        user_id: ID of the user
        file_ids: List of file IDs to process
        requested_tools: List of tool names requested ["summary", "topics", "entities", ...]
        progress_id: Progress tracking ID
        force_rerun: If True, run all tools regardless of existing data
    """
    # Create a new session for this task
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()

    try:
        log.info(f"[Explore Orchestrator] Starting for user {user_id} with {len(file_ids)} files")

        # Get orchestrator progress record
        progress = session.query(Progress).filter(Progress.id == progress_id).first()
        if not progress:
            raise ValueError(f"Progress record {progress_id} not found")

        progress.status = "running"
        progress.percentage = 5
        session.commit()

        # Validate file ownership
        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()

        if not files:
            raise ValueError("No accessible files found")

        # Step 0: Check if files need preprocessing (text extraction)
        files_needing_preprocessing = []
        for file in files:
            page_count = session.query(FilePage).filter(FilePage.file_id == file.id).count()
            if page_count == 0:
                files_needing_preprocessing.append(file)
                log.warning(f"[Explore Orchestrator] File {file.id} ({file.original_file_name}) has no pages - needs preprocessing")

        if files_needing_preprocessing:
            log.info(f"[Explore Orchestrator] {len(files_needing_preprocessing)} files need preprocessing. Triggering text extraction...")

            # Import preprocessing wrapper tasks (these download files first)
            from app.tasks.summarizer_tasks import (
                process_audio_video_with_download,
                process_document_with_download,
                process_image_with_download,
                process_presentation_with_download,
                process_spreadsheet_with_download
            )
            from app.utils.file_utils import detect_file_type

            preprocessing_tasks = []
            preprocessing_progress_ids = {}

            for file in files_needing_preprocessing:
                # Create progress record for preprocessing
                preprocess_prog = Progress(
                    user_id=user_id,
                    tool="text_extraction",
                    status="pending",
                    percentage=0,
                    created_at=datetime.utcnow()
                )
                session.add(preprocess_prog)
                session.flush()

                preprocessing_progress_ids[str(file.id)] = str(preprocess_prog.id)

                # Determine file type and create preprocessing task
                # Pass stored_file_name (not full path) - wrapper tasks will download using download_blob_to_tmp
                try:
                    # Detect file type from original filename
                    file_type = detect_file_type(file.original_file_name)

                    # Create task signature with stored filename - wrapper tasks will handle download
                    # Pass stored_file_name so download_blob_to_tmp can look up user_id from DB
                    task_params = (file.stored_file_name, str(file.id), str(preprocess_prog.id))

                    # Route to appropriate preprocessing task
                    if file_type in ["audio", "video"]:
                        task = process_audio_video_with_download.s(*task_params)
                    elif file_type == "document":
                        task = process_document_with_download.s(*task_params)
                    elif file_type == "image":
                        task = process_image_with_download.s(*task_params)
                    elif file_type == "presentation":
                        task = process_presentation_with_download.s(*task_params)
                    elif file_type == "spreadsheet":
                        task = process_spreadsheet_with_download.s(*task_params)
                    else:
                        log.error(f"[Explore Orchestrator] Unsupported file type: {file_type} for file {file.id}")
                        continue

                    preprocessing_tasks.append(task)
                    log.info(f"[Explore Orchestrator] Scheduled {file_type} preprocessing for file {file.id}")

                except Exception as e:
                    log.error(f"[Explore Orchestrator] Failed to prepare preprocessing for file {file.id}: {e}")
                    log.error(traceback.format_exc())
                    continue

            # Store preprocessing info in progress
            progress.result_data = {
                "preprocessing_required": True,
                "preprocessing_progress_ids": preprocessing_progress_ids,
                "preprocessing_file_count": len(files_needing_preprocessing)
            }
            progress.percentage = 10
            session.commit()

            if preprocessing_tasks:
                # Execute preprocessing tasks in parallel and wait for completion
                log.info(f"[Explore Orchestrator] Starting {len(preprocessing_tasks)} preprocessing tasks...")

                # Use chord to wait for all preprocessing to complete before continuing
                preprocess_job = chord(preprocessing_tasks)(
                    continue_exploration_after_preprocessing.s(
                        progress_id=progress_id,
                        user_id=user_id,
                        file_ids=file_ids,
                        requested_tools=requested_tools,
                        force_rerun=force_rerun
                    )
                )

                log.info(f"[Explore Orchestrator] Preprocessing started, will continue exploration after completion")
                return {
                    "status": "preprocessing",
                    "progress_id": progress_id,
                    "message": f"Preprocessing {len(files_needing_preprocessing)} files before exploration"
                }

        # Step 1: Determine which tools need to run
        tools_to_run = []
        tools_skipped = []

        if force_rerun:
            tools_to_run = requested_tools
            log.info(f"[Explore Orchestrator] Force rerun enabled, running all {len(requested_tools)} tools")
        else:
            # Check what data already exists
            for tool_name in requested_tools:
                has_data = check_tool_data_exists(session, file_ids, tool_name)
                if has_data:
                    tools_skipped.append(tool_name)
                    log.info(f"[Explore Orchestrator] Skipping {tool_name} - data already exists")
                else:
                    tools_to_run.append(tool_name)
                    log.info(f"[Explore Orchestrator] Will run {tool_name} - data missing")

        # If no tools need to run, mark as complete
        if not tools_to_run:
            log.info(f"[Explore Orchestrator] All requested tools already complete. Skipped: {tools_skipped}")
            progress.status = "completed"
            progress.percentage = 100
            progress.result_data = {
                "tools_requested": requested_tools,
                "tools_skipped": tools_skipped,
                "tools_completed": [],
                "message": "All tools already completed"
            }
            progress.completed_at = datetime.utcnow()
            session.commit()
            return {
                "status": "success",
                "message": "All tools already completed",
                "tools_skipped": tools_skipped
            }

        # Step 2: Create individual Progress records for each tool-file combination
        tool_progress_ids = {}

        # Map 'entities' to 'doc_analysis' since that's what extracts entity data
        # (relationships and evidence are no longer part of orchestration)
        consolidated_tools = []
        for tool_name in tools_to_run:
            if tool_name == 'entities':
                if 'doc_analysis' not in consolidated_tools:
                    consolidated_tools.append('doc_analysis')
            else:
                consolidated_tools.append(tool_name)

        # Create progress records for each file-tool pair
        for file_id in file_ids:
            for tool_name in consolidated_tools:
                # Create unique key for this file-tool combination
                progress_key = f"{tool_name}_{file_id}"

                tool_progress = Progress(
                    user_id=user_id,
                    tool=get_tool_progress_name(tool_name),
                    status="pending",
                    percentage=0,
                    created_at=datetime.utcnow()
                )
                session.add(tool_progress)
                session.flush()
                tool_progress_ids[progress_key] = str(tool_progress.id)

        # Store tool progress IDs in orchestrator progress
        progress.result_data = {
            "tool_progress_ids": tool_progress_ids,
            "tools_requested": requested_tools,
            "tools_running": tools_to_run,
            "tools_skipped": tools_skipped,
            "file_ids": [str(fid) for fid in file_ids]
        }
        progress.percentage = 10
        session.commit()

        log.info(f"[Explore Orchestrator] Created {len(tool_progress_ids)} progress records for {len(consolidated_tools)} tools across {len(file_ids)} files")

        # Step 3: Create task signatures for parallel execution
        task_signatures = []

        for file_id in file_ids:
            for tool_name in consolidated_tools:
                progress_key = f"{tool_name}_{file_id}"
                tool_prog_id = tool_progress_ids[progress_key]

                task_signature = get_tool_task_signature(tool_name, str(file_id), tool_prog_id)
                if task_signature:
                    task_signatures.append(task_signature)
                    log.info(f"[Explore Orchestrator] Created task signature for {tool_name} on file {file_id}")
                else:
                    log.warning(f"[Explore Orchestrator] No task signature found for tool: {tool_name}")

        if not task_signatures:
            raise ValueError("No valid task signatures created")

        log.info(f"[Explore Orchestrator] Launching {len(task_signatures)} tasks in parallel")

        # Step 4: Execute tasks in parallel using Celery group with chord callback
        job = chord(task_signatures)(
            finalize_orchestration.s(progress_id=progress_id)
        )

        log.info(f"[Explore Orchestrator] Tasks launched with chord ID: {job.id}")

        return {
            "status": "success",
            "progress_id": progress_id,
            "tools_running": tools_to_run,
            "tools_skipped": tools_skipped
        }

    except Exception as e:
        log.error(f"[Explore Orchestrator] Error: {e}")
        log.error(traceback.format_exc())

        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            session.commit()

        raise e

    finally:
        session.close()


@current_app.task
def continue_exploration_after_preprocessing(preprocessing_results, progress_id, user_id, file_ids, requested_tools, force_rerun):
    """
    Callback that runs after preprocessing completes.
    Continues with exploration tools on now-processed files.
    """
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()

    try:
        log.info(f"[Explore Orchestrator] Preprocessing complete, continuing exploration for progress {progress_id}")

        progress = session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            log.error(f"[Explore Orchestrator] Progress {progress_id} not found after preprocessing")
            return

        # Check preprocessing status
        result_data = progress.result_data or {}
        preprocessing_progress_ids = result_data.get("preprocessing_progress_ids", {})

        preprocessing_failed = []
        for file_id, preprocess_prog_id in preprocessing_progress_ids.items():
            preprocess_prog = session.query(Progress).filter_by(id=preprocess_prog_id).first()
            if preprocess_prog and preprocess_prog.status == "failed":
                preprocessing_failed.append(file_id)

        if preprocessing_failed:
            log.warning(f"[Explore Orchestrator] Preprocessing failed for {len(preprocessing_failed)} files")

        progress.percentage = 20
        session.commit()

        # Continue with exploration - determine which tools need to run
        tools_to_run = []
        tools_skipped = []

        if force_rerun:
            tools_to_run = requested_tools
        else:
            for tool_name in requested_tools:
                has_data = check_tool_data_exists(session, file_ids, tool_name)
                if has_data:
                    tools_skipped.append(tool_name)
                else:
                    tools_to_run.append(tool_name)

        if not tools_to_run:
            progress.status = "completed"
            progress.percentage = 100
            result_data["tools_skipped"] = tools_skipped
            result_data["message"] = "All tools already completed"
            progress.result_data = result_data
            progress.completed_at = datetime.utcnow()
            session.commit()
            return

        # Map entities to doc_analysis
        consolidated_tools = []
        for tool_name in tools_to_run:
            if tool_name == 'entities':
                if 'doc_analysis' not in consolidated_tools:
                    consolidated_tools.append('doc_analysis')
            else:
                consolidated_tools.append(tool_name)

        # Create progress records for each file-tool pair
        tool_progress_ids = {}
        for file_id in file_ids:
            for tool_name in consolidated_tools:
                progress_key = f"{tool_name}_{file_id}"
                tool_progress = Progress(
                    user_id=user_id,
                    tool=get_tool_progress_name(tool_name),
                    status="pending",
                    percentage=0,
                    created_at=datetime.utcnow()
                )
                session.add(tool_progress)
                session.flush()
                tool_progress_ids[progress_key] = str(tool_progress.id)

        result_data["tool_progress_ids"] = tool_progress_ids
        result_data["tools_running"] = tools_to_run
        result_data["tools_skipped"] = tools_skipped
        progress.result_data = result_data
        progress.percentage = 30
        session.commit()

        # Create task signatures
        task_signatures = []
        for file_id in file_ids:
            for tool_name in consolidated_tools:
                progress_key = f"{tool_name}_{file_id}"
                tool_prog_id = tool_progress_ids[progress_key]
                task_signature = get_tool_task_signature(tool_name, str(file_id), tool_prog_id)
                if task_signature:
                    task_signatures.append(task_signature)

        if task_signatures:
            log.info(f"[Explore Orchestrator] Launching {len(task_signatures)} exploration tasks")
            job = chord(task_signatures)(finalize_orchestration.s(progress_id=progress_id))
            log.info(f"[Explore Orchestrator] Exploration tasks launched")

    except Exception as e:
        log.error(f"[Explore Orchestrator] Error continuing after preprocessing: {e}")
        log.error(traceback.format_exc())
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            session.commit()

    finally:
        session.close()


@current_app.task
def finalize_orchestration(results, progress_id):
    """
    Callback that runs when all tool tasks complete.
    Aggregates results and updates orchestrator progress.

    Args:
        results: List of results from individual tool tasks
        progress_id: Orchestrator progress ID
    """
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()

    try:
        log.info(f"[Explore Orchestrator] Finalizing orchestration for progress {progress_id}")

        progress = session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            log.error(f"[Explore Orchestrator] Progress {progress_id} not found during finalization")
            return

        # Get tool progress IDs from orchestrator progress
        result_data = progress.result_data or {}
        tool_progress_ids = result_data.get("tool_progress_ids", {})

        # Check status of each tool
        tools_completed = []
        tools_failed = []

        for tool_name, tool_prog_id in tool_progress_ids.items():
            tool_progress = session.query(Progress).filter_by(id=tool_prog_id).first()
            if tool_progress:
                if tool_progress.status == "completed":
                    tools_completed.append(tool_name)
                elif tool_progress.status == "failed":
                    tools_failed.append(tool_name)

        # Update orchestrator progress
        result_data["tools_completed"] = tools_completed
        result_data["tools_failed"] = tools_failed

        if tools_failed:
            progress.status = "completed_with_errors"
            result_data["message"] = f"Completed {len(tools_completed)} tools, {len(tools_failed)} failed"
        else:
            progress.status = "completed"
            result_data["message"] = f"All {len(tools_completed)} tools completed successfully"

        progress.result_data = result_data
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()
        session.commit()

        log.info(f"[Explore Orchestrator] Finalization complete. Completed: {tools_completed}, Failed: {tools_failed}")

    except Exception as e:
        log.error(f"[Explore Orchestrator] Finalization error: {e}")
        log.error(traceback.format_exc())

    finally:
        session.close()


def check_tool_data_exists(session, file_ids, tool_name):
    """
    Check if data already exists for a given tool across all files.

    Args:
        session: Database session
        file_ids: List of file IDs
        tool_name: Tool name (summary, topics, entities, etc.)

    Returns:
        bool: True if data exists for ALL files, False otherwise
    """
    try:
        for file_id in file_ids:
            if tool_name == "summary":
                # Check FilePage for summaries
                file_pages = session.query(FilePage).filter(FilePage.file_id == file_id).all()
                if not any(page.page_summary for page in file_pages):
                    return False

            elif tool_name == "topics":
                # Check TopicModelResult for topics
                topics_data = session.query(TopicModelResult).filter(TopicModelResult.file_id == file_id).all()
                if not any(topic.topics for topic in topics_data):
                    return False

            elif tool_name == "entities":
                # Check DocumentAnalysisResult for entities
                doc_analysis = session.query(DocumentAnalysisResult).filter(DocumentAnalysisResult.file_id == file_id).first()
                if not (doc_analysis and doc_analysis.meta and doc_analysis.meta.get('entities_by_type')):
                    return False

            elif tool_name == "segments":
                # Check SegmentResult for segments
                segment_data = session.query(SegmentResult).filter(SegmentResult.file_id == file_id).first()
                if not (segment_data and segment_data.segments):
                    return False

            elif tool_name == "chronology":
                # Check ChronologyResult for chronology data
                chronology_data = session.query(ChronologyResult).filter(ChronologyResult.file_id == file_id).first()
                if not (chronology_data and chronology_data.events):
                    return False

            elif tool_name == "sentiment":
                # Check SentimentResult for sentiment data
                sentiment_data = session.query(SentimentResult).filter(SentimentResult.file_id == file_id).first()
                if not (sentiment_data and sentiment_data.overall_label):
                    return False

        # All files have data for this tool
        return True

    except Exception as e:
        log.error(f"Error checking tool data for {tool_name}: {e}")
        return False


def get_tool_progress_name(tool_name):
    """Map tool name to Progress.tool name."""
    tool_mapping = {
        "summary": "summarizer",
        "topics": "topic_modeling",
        "entities": "entity_extraction",
        "relationships": "relationship_extraction",
        "evidence": "evidence_extraction",
        "segments": "segmentation",
        "doc_analysis": "document_analysis"  # Consolidated tool for entities/relationships/evidence
    }
    return tool_mapping.get(tool_name, tool_name)


def get_tool_task_signature(tool_name, file_id, progress_id):
    """
    Get the Celery task signature for a given tool and file.

    Args:
        tool_name: Tool name (summary, topics, doc_analysis, segments, etc.)
        file_id: Single file ID
        progress_id: Progress ID for this tool

    Returns:
        Celery task signature or None
    """
    try:
        # Note: For summarizer, we use summarize_file_kickoff which handles the full workflow
        if tool_name == "summary":
            from app.tasks.summarizer_tasks import summarize_file_kickoff
            return summarize_file_kickoff.s(file_id, progress_id)

        elif tool_name == "topics":
            from app.tasks.topic_modeller_tasks import build_topics_for_file
            return build_topics_for_file.s(file_id, progress_id, force=False)

        elif tool_name == "doc_analysis":
            # Consolidated: handles entities, relationships, and evidence
            from app.tasks.doc_analysis_tasks import build_doc_analysis_for_file
            return build_doc_analysis_for_file.s(file_id, progress_id, force=False)

        elif tool_name == "segments":
            from app.tasks.segmenter_tasks import build_segments_for_file
            return build_segments_for_file.s(file_id, progress_id, force=False)

        elif tool_name == "chronology":
            from app.tasks.chrono_tasks import build_chronology_for_file
            return build_chronology_for_file.s(file_id, progress_id, force=False)

        elif tool_name == "sentiment":
            from app.tasks.sentiment_tasks import build_sentiment_for_file
            return build_sentiment_for_file.s(file_id, progress_id, force=False)

        else:
            log.warning(f"Unknown tool name: {tool_name}")
            return None

    except ImportError as e:
        log.error(f"Failed to import task for {tool_name}: {e}")
        return None
