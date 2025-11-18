# app/tasks/collections_tasks.py

import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.organize.collections_service import CollectionsService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

def safe_commit(session, operation_description="database operation"):
    """Helper function to safely commit database operations with proper error handling."""
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        log.error(f"Failed to commit {operation_description}: {e}")
        raise

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_collections_task(self, user_id: str, file_ids: list, progress_id: str = None):
    """
    Celery task for creating content collections and boards.
    
    Args:
        user_id: ID of the user
        file_ids: List of file IDs to process
        progress_id: Optional progress tracking ID
    """
    # Create a new session for this task
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()
    progress = None
    
    try:
        log.info(f"[Collections Task] Starting for user {user_id} with {len(file_ids)} files")
        
        # Initialize or get progress record
        if progress_id:
            progress = session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                tool="collections_manager",
                stage="organize",
                status="running",
                percentage=0,
                created_at=datetime.utcnow()
            )
            session.add(progress)
            safe_commit(session, "progress record creation")
        
        # Update progress
        progress.status = "running"
        progress.percentage = 10
        safe_commit(session, "progress update to 10%")
        
        # Get file data from database
        from app.models import UploadedFile, FilePage
        from app.models.analysis_results import TopicModelResult, DocumentAnalysisResult, SegmentResult

        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()

        if not files:
            raise ValueError("No accessible files found")

        # Prepare file data for collections service
        file_data = []
        for file in files:
            # Get summary from FilePage
            summary = ""
            pages = session.query(FilePage).filter(FilePage.file_id == file.id).all()
            if pages:
                page_summaries = [p.page_summary for p in pages if p.page_summary]
                summary = " ".join(page_summaries) if page_summaries else ""

            # Get topics from TopicModelResult
            topics = []
            topic_result = session.query(TopicModelResult).filter(
                TopicModelResult.file_id == file.id,
                TopicModelResult.is_active == True
            ).order_by(TopicModelResult.version.desc()).first()

            if topic_result and topic_result.topics:
                # Extract topic labels from the topics JSONB field
                for topic in topic_result.topics:
                    if isinstance(topic, dict):
                        topic_label = topic.get('label') or topic.get('topic') or topic.get('name')
                        if topic_label:
                            topics.append(topic_label)
                    elif isinstance(topic, str):
                        topics.append(topic)

            # Get entities and keywords from DocumentAnalysisResult
            entities = {}
            keywords = []
            doc_analysis = session.query(DocumentAnalysisResult).filter(
                DocumentAnalysisResult.file_id == file.id,
                DocumentAnalysisResult.is_active == True
            ).order_by(DocumentAnalysisResult.version.desc()).first()

            if doc_analysis:
                # Get entities from meta field
                if doc_analysis.meta and 'entities_by_type' in doc_analysis.meta:
                    entities = doc_analysis.meta.get('entities_by_type', {})

                # Get keywords from key_points (treating them as keywords)
                if doc_analysis.key_points:
                    keywords = doc_analysis.key_points

            # Get sections/segments from SegmentResult
            sections = []
            segment_result = session.query(SegmentResult).filter(
                SegmentResult.file_id == file.id,
                SegmentResult.is_active == True
            ).order_by(SegmentResult.version.desc()).first()

            if segment_result and segment_result.segments:
                for segment in segment_result.segments:
                    if isinstance(segment, dict):
                        # Segments store a 'pages' array, not page_start/page_end
                        pages = segment.get("pages", [])
                        page_start = min(pages) if pages else 0
                        page_end = max(pages) if pages else 0

                        sections.append({
                            "section_id": segment.get("id", ""),
                            "title": segment.get("title", "") or segment.get("heading", ""),
                            "summary": segment.get("summary", ""),
                            "page_start": page_start,
                            "page_end": page_end,
                            "tags": segment.get("tags", []),
                            "entities": segment.get("entities", [])
                        })

            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "file_type": file.file_type,
                "summary": summary,
                "topics": topics,
                "entities": entities,
                "keywords": keywords,
                "sections": sections,  # NEW: Include section-level data
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        # Update progress
        progress.percentage = 30
        safe_commit(session, "progress update to 30%")
        
        # Initialize collections service
        collections_service = CollectionsService()
        
        # Create collections
        log.info(f"[Collections Task] Creating collections for {len(file_data)} files")
        result = collections_service.create_collections_for_files(file_data)

        # Update progress
        progress.percentage = 70
        safe_commit(session, "progress update to 70%")

        # Save to CollectionsResult table for each file
        from app.models.analysis_results import CollectionsResult

        for file_id in file_ids:
            # Check if result already exists for this file
            existing_result = session.query(CollectionsResult).filter(
                CollectionsResult.file_id == file_id,
                CollectionsResult.is_active == True
            ).first()

            # Deactivate old results
            if existing_result:
                session.query(CollectionsResult).filter(
                    CollectionsResult.file_id == file_id
                ).update({"is_active": False})

            # Create new result
            collection_result = CollectionsResult(
                file_id=file_id,
                version=(existing_result.version + 1) if existing_result else 1,
                is_active=True,
                total_collections=len(result.get('collections', [])),
                collections=result.get('collections', []),
                theme_analysis=result.get('themes', []),
                organization_insights=result.get('metadata', {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(collection_result)

        # Update progress
        progress.percentage = 90
        safe_commit(session, "progress update to 90%")

        # Store results
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()

        safe_commit(session, "final results")
        
        collections_count = len(result.get('collections', []))
        log.info(f"[Collections Task] Completed successfully. Created {collections_count} collections")
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "collections_count": collections_count
        }
        
    except Exception as e:
        log.error(f"[Collections Task] Error: {e}")
        log.error(traceback.format_exc())
        
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            try:
                safe_commit(session, "error status")
            except Exception as commit_error:
                log.error(f"[Collections Task] Failed to save error status: {commit_error}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            log.info(f"[Collections Task] Retrying... Attempt {self.request.retries + 1}")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise e
        
    finally:
        session.close()
