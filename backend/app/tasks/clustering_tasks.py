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
def create_content_clusters_task(self, user_id: str, file_ids: list, progress_id: str = None, cluster_config: dict = None):
    """
    Celery task for creating content clusters using ML algorithms.

    Args:
        user_id: ID of the user
        file_ids: List of file IDs to process
        progress_id: Optional progress tracking ID
        cluster_config: Optional clustering configuration with 'mode' key
                       - 'document': cluster documents/files together (default for multiple files)
                       - 'content': cluster pages/sections within documents (default for single file)
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

        # Determine clustering mode
        config = cluster_config or {}
        clustering_mode = config.get("mode", "auto")

        # Auto-detect mode: single file = content clustering, multiple files = document clustering
        if clustering_mode == "auto":
            clustering_mode = "content" if len(file_ids) == 1 else "document"

        log.info(f"[Clustering Task] Using clustering mode: {clustering_mode}")

        # Prepare data based on clustering mode
        if clustering_mode == "content":
            # CONTENT MODE: Cluster semantic chunks within documents (not pages!)
            from app.services.stages.organize.semantic_chunker_service import SemanticChunkerService

            file_data = []
            file_metadata = {}  # Store file-level info
            chunker = SemanticChunkerService()

            for file in files:
                file_metadata[str(file.id)] = {
                    "file_id": str(file.id),
                    "file_name": file.original_file_name,
                    "file_type": file.file_type
                }

                # Get all pages for this file
                pages = session.query(FilePage).filter(
                    FilePage.file_id == file.id
                ).order_by(FilePage.page_number).all()

                if not pages:
                    log.warning(f"[Clustering Task] No pages found for file {file.id}")
                    continue

                # Get topics for reference
                topic_result = session.query(TopicModelResult).filter(
                    TopicModelResult.file_id == file.id,
                    TopicModelResult.is_active == True
                ).order_by(TopicModelResult.version.desc()).first()

                file_topics = []
                if topic_result and topic_result.topics:
                    file_topics = [t.get('label', '') for t in topic_result.topics if t.get('label')]

                # Get entities for reference
                doc_analysis = session.query(DocumentAnalysisResult).filter(
                    DocumentAnalysisResult.file_id == file.id,
                    DocumentAnalysisResult.is_active == True
                ).order_by(DocumentAnalysisResult.version.desc()).first()

                file_entities = {}
                if doc_analysis and doc_analysis.meta:
                    file_entities = doc_analysis.meta.get('entities_by_type', {})

                # Convert pages to format expected by chunker
                page_data = [
                    {
                        "page_number": page.page_number,
                        "page_summary": page.page_summary or ""
                    }
                    for page in pages
                ]

                # Extract SEMANTIC CHUNKS (not pages!)
                semantic_chunks = chunker.extract_semantic_chunks(page_data, file_topics, file_entities)

                log.info(f"[Clustering Task] Extracted {len(semantic_chunks)} semantic chunks from {len(pages)} pages")

                # Create data entry for each semantic chunk
                for chunk in semantic_chunks:
                    file_data.append({
                        "file_id": str(file.id),
                        "chunk_id": chunk.get("chunk_id", ""),
                        "pages": chunk.get("pages", []),  # Which pages this chunk spans
                        "file_name": file.original_file_name,
                        "summary": chunk.get("summary", ""),
                        "content": chunk.get("content", ""),  # Full content for better similarity
                        "topics": chunk.get("topics", []),
                        "entities": chunk.get("entities", {}),
                        "key_points": [],
                        "word_count": chunk.get("word_count", 0)
                    })

            if not file_data:
                raise ValueError("No semantic chunks found for clustering")

            log.info(f"[Clustering Task] Prepared {len(file_data)} semantic chunks for content clustering")

        else:
            # DOCUMENT MODE: Cluster entire documents together (original behavior)
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

        # Merge user config with clustering mode
        service_config = {
            "max_clusters": config.get("max_clusters", min(7, len(file_data))),
            "min_cluster_size": config.get("min_cluster_size", 1),
            "similarity_threshold": config.get("similarity_threshold", 0.3),
            "clustering_method": config.get("clustering_method", "semantic"),
            "clustering_mode": clustering_mode
        }

        # Create content clusters
        log.info(f"[Clustering Task] Clustering {len(file_data)} items with config: {service_config}")
        result = clustering_service.build_document_clusters(file_data, service_config)
        
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
