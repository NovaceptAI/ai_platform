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
        from app.models import UploadedFile
        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if not files:
            raise ValueError("No accessible files found")
        
        # Prepare file data for collections service
        file_data = []
        for file in files:
            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "file_type": file.file_type,
                "summary": getattr(file, 'summary', ''),
                "topics": getattr(file, 'topics', []),
                "entities": getattr(file, 'entities', {}),
                "keywords": getattr(file, 'keywords', []),
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
        progress.percentage = 90
        safe_commit(session, "progress update to 90%")
        
        # Store results
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()
        
        safe_commit(session, "final results")
        
        log.info(f"[Collections Task] Completed successfully. Created {result.get('collections_count', 0)} collections")
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "collections_count": result.get('collections_count', 0)
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
