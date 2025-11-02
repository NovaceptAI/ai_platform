# app/tasks/tagging_tasks.py

import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.organize.tagging_service import TaggingService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def build_tag_taxonomy_task(self, user_id: str, file_ids: list, progress_id: str = None):
    """
    Celery task for building hierarchical tag taxonomy.
    
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
        log.info(f"[Tagging Task] Starting for user {user_id} with {len(file_ids)} files")
        
        # Initialize or get progress record
        if progress_id:
            progress = session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                tool="tag_taxonomy_manager",
                stage="organize",
                status="running",
                percentage=0,
                created_at=datetime.utcnow()
            )
            session.add(progress)
            session.commit()
        
        # Update progress
        progress.status = "running"
        progress.percentage = 20
        session.commit()
        
        # Get file data from database
        from app.models import UploadedFile
        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if not files:
            raise ValueError("No accessible files found")
        
        # Prepare file data for tagging service
        file_data = []
        for file in files:
            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "topics": getattr(file, 'topics', []),
                "entities": getattr(file, 'entities', {}),
                "keywords": getattr(file, 'keywords', []),
                "summary": getattr(file, 'summary', '')
            })
        
        # Update progress
        progress.percentage = 35
        session.commit()
        
        # Initialize tagging service
        tagging_service = TaggingService()
        
        # Build tag taxonomy
        log.info(f"[Tagging Task] Building tag taxonomy for {len(file_data)} files")
        result = tagging_service.build_tag_taxonomy(file_data)
        
        # Update progress
        progress.percentage = 90
        session.commit()
        
        # Store results
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()
        
        session.commit()
        
        log.info(f"[Tagging Task] Completed successfully. Created {result.get('total_tags', 0)} tags")
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "tags_count": result.get('total_tags', 0)
        }
        
    except Exception as e:
        log.error(f"[Tagging Task] Error: {e}")
        log.error(traceback.format_exc())
        
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            session.commit()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            log.info(f"[Tagging Task] Retrying... Attempt {self.request.retries + 1}")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise e
        
    finally:
        session.close()
