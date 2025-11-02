# app/tasks/clustering_tasks.py

import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.organize.cluster_builder_service import ClusterBuilderService
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
def create_content_clusters_task(self, user_id: str, file_ids: list, progress_id: str = None):
    """
    Celery task for creating content clusters using ML algorithms.
    
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
        log.info(f"[Clustering Task] Starting for user {user_id} with {len(file_ids)} files")
        
        # Initialize or get progress record
        if progress_id:
            progress = session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                tool="content_clusterer",
                stage="organize",
                status="running",
                percentage=0,
                created_at=datetime.utcnow()
            )
            session.add(progress)
            safe_commit(session, "progress record creation")
        
        # Update progress
        progress.status = "running"
        progress.percentage = 15
        safe_commit(session, "progress update to 15%")
        
        # Get file data from database
        from app.models import UploadedFile, FilePage
        from app.models.analysis_results import TopicModelResult, DocumentAnalysisResult

        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()

        if not files:
            raise ValueError("No accessible files found")

        # Prepare file data for clustering service
        file_data = []
        for file in files:
            # Get summary from FilePage
            summary = ""
            pages = session.query(FilePage).filter(FilePage.file_id == file.id).all()
            if pages:
                # Combine page summaries
                page_summaries = [p.page_summary for p in pages if p.page_summary]
                summary = " ".join(page_summaries) if page_summaries else ""

            # Get topics from TopicModelResult
            topics = []
            topic_result = session.query(TopicModelResult).filter(
                TopicModelResult.file_id == file.id,
                TopicModelResult.is_active == True
            ).order_by(TopicModelResult.version.desc()).first()

            if topic_result and topic_result.topics:
                # Extract topic labels from the topics JSONB
                topics = [t.get('label', '') for t in topic_result.topics if t.get('label')]

            # Get entities and key_points from DocumentAnalysisResult
            entities = {}
            key_points = []
            doc_analysis = session.query(DocumentAnalysisResult).filter(
                DocumentAnalysisResult.file_id == file.id,
                DocumentAnalysisResult.is_active == True
            ).order_by(DocumentAnalysisResult.version.desc()).first()

            if doc_analysis:
                # Get entities from meta field
                if doc_analysis.meta and 'entities_by_type' in doc_analysis.meta:
                    entities = doc_analysis.meta.get('entities_by_type', {})

                # Get key points
                if doc_analysis.key_points:
                    key_points = doc_analysis.key_points

            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "summary": summary,
                "topics": topics,
                "entities": entities,
                "key_points": key_points,
                "file_type": file.file_type
            })
        
        # Update progress
        progress.percentage = 25
        safe_commit(session, "progress update to 25%")
        
        # Initialize clustering service
        clustering_service = ClusterBuilderService()
        
        # Create content clusters
        log.info(f"[Clustering Task] Clustering {len(file_data)} files")
        result = clustering_service.build_document_clusters(file_data)
        
        # Update progress
        progress.percentage = 90
        safe_commit(session, "progress update to 90%")

        # Store results in Progress table
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()

        # Also save to DocumentClustersResult table for each file
        from app.models.analysis_results import DocumentClustersResult

        for file_id in file_ids:
            # Check if result already exists for this file
            existing_result = session.query(DocumentClustersResult).filter(
                DocumentClustersResult.file_id == file_id,
                DocumentClustersResult.is_active == True
            ).first()

            # Deactivate old results
            if existing_result:
                session.query(DocumentClustersResult).filter(
                    DocumentClustersResult.file_id == file_id
                ).update({"is_active": False})

            # Create new result
            cluster_result = DocumentClustersResult(
                file_id=file_id,
                version=(existing_result.version + 1) if existing_result else 1,
                is_active=True,
                method="semantic",
                total_clusters=len(result.get('clusters', [])),
                algorithm_used=result.get('configuration', {}).get('clustering_method', 'semantic'),
                clusters=result.get('clusters', []),
                similarity_data=result.get('visualization', {}),
                quality_metrics=result.get('insights', {}),
                visualization_data=result.get('visualization', {})
            )
            session.add(cluster_result)

        safe_commit(session, "final results")

        log.info(f"[Clustering Task] Completed successfully. Created {len(result.get('clusters', []))} clusters")
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "cluster_count": result.get('cluster_count', 0)
        }
        
    except Exception as e:
        log.error(f"[Clustering Task] Error: {e}")
        log.error(traceback.format_exc())
        
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            try:
                safe_commit(session, "error status")
            except Exception as commit_error:
                log.error(f"[Clustering Task] Failed to save error status: {commit_error}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            log.info(f"[Clustering Task] Retrying... Attempt {self.request.retries + 1}")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise e
        
    finally:
        session.close()
