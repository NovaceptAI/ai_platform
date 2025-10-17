# app/tasks/saved_views_tasks.py

import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.models import UploadedFile, FilePage
from app.services.stages.organize.saved_views_service import SavedViewsService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_saved_views_task(self, user_id: str, file_ids: list, progress_id: str = None):
    """
    Celery task for creating and managing saved organizational views.
    
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
        log.info(f"[Saved Views Task] Starting for user {user_id} with {len(file_ids)} files")
        
        # Initialize or get progress record
        if progress_id:
            progress = session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                tool="saved_views_manager",
                stage="organize",
                status="running",
                percentage=0,
                created_at=datetime.utcnow()
            )
            session.add(progress)
            session.commit()
        
        # Update progress
        progress.status = "running"
        progress.percentage = 15
        session.commit()
        
        # Get file data from database
        from app.models import UploadedFile
        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if not files:
            raise ValueError("No accessible files found")
        
        # Prepare file data for saved views service
        file_data = []
        for file in files:
            # Get additional data from discovery stage if available
            file_pages = session.query(FilePage).filter(FilePage.file_id == file.id).all()
            
            # Extract topics from analysis results if available
            topics_data = []
            entities_data = {}
            evidence_items = []
            
            # Try to get discovery stage data
            try:
                from app.models.analysis_results import TopicsResult, EntitiesResult, EvidenceResult
                
                topics_result = session.query(TopicsResult).filter(
                    TopicsResult.file_id == file.id,
                    TopicsResult.is_active == True
                ).order_by(TopicsResult.version.desc()).first()
                
                if topics_result and topics_result.topics:
                    topics_data = [topic.get('topic', topic) if isinstance(topic, dict) else topic 
                                 for topic in topics_result.topics[:10]]  # Limit to 10 topics
                
                entities_result = session.query(EntitiesResult).filter(
                    EntitiesResult.file_id == file.id,
                    EntitiesResult.is_active == True
                ).order_by(EntitiesResult.version.desc()).first()
                
                if entities_result and entities_result.entities:
                    entities_data = entities_result.entities
                    
                evidence_result = session.query(EvidenceResult).filter(
                    EvidenceResult.file_id == file.id,
                    EvidenceResult.is_active == True
                ).order_by(EvidenceResult.version.desc()).first()
                
                if evidence_result and evidence_result.evidence_items:
                    evidence_items = evidence_result.evidence_items[:20]  # Limit to 20 items
                    
            except Exception as discovery_error:
                log.warning(f"[Saved Views Task] Could not load discovery data for file {file.id}: {discovery_error}")
            
            file_info = {
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "file_type": file.file_type,
                "summary": getattr(file, 'summary', ''),
                "topics": topics_data,
                "entities": entities_data,
                "evidence_items": evidence_items,
                "keywords": getattr(file, 'keywords', []),
                "collections": getattr(file, 'collections', []),
                "tags": getattr(file, 'tags', []),
                "cluster_id": getattr(file, 'cluster_id', None),
                "metadata": getattr(file, 'extracted_metadata', {}),
                "page_count": len(file_pages),
                "created_at": file.created_at.isoformat() if file.created_at else None
            }
            
            file_data.append(file_info)
            
        log.info(f"[Saved Views Task] Prepared file data: {len(file_data)} files with enhanced discovery data")
        
        # Update progress
        progress.percentage = 30
        session.commit()
        
        # Initialize saved views service
        saved_views_service = SavedViewsService()
        
        # Create saved views
        log.info(f"[Saved Views Task] Creating saved views for {len(file_data)} files")
        
        # Prepare organization data (could be enhanced with other organize tool results)
        organization_data = {
            "user_id": user_id,
            "file_count": len(file_data),
            "processing_date": datetime.utcnow().isoformat()
        }
        
        result = saved_views_service.create_saved_views(file_data, organization_data)
        
        # Update progress
        progress.percentage = 90
        session.commit()
        
        # Store results
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()
        
        session.commit()
        
        views_count = len(result.get('default_views', [])) + len(result.get('contextual_views', []))
        log.info(f"[Saved Views Task] Completed successfully. Created {views_count} saved views ({len(result.get('default_views', []))} default, {len(result.get('contextual_views', []))} contextual)")
        
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "views_count": views_count
        }
        
    except Exception as e:
        log.error(f"[Saved Views Task] Error: {e}")
        log.error(traceback.format_exc())
        
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            session.commit()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            log.info(f"[Saved Views Task] Retrying... Attempt {self.request.retries + 1}")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise e
        
    finally:
        session.close()
