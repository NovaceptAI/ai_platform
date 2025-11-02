# app/tasks/concept_graph_tasks.py

import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.organize.concept_graph_service import ConceptGraphService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def build_concept_graph_task(self, user_id: str, file_ids: list, progress_id: str = None):
    """
    Celery task for building knowledge graph of concepts and relationships.
    
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
        log.info(f"[Concept Graph Task] Starting for user {user_id} with {len(file_ids)} files")
        
        # Initialize or get progress record
        if progress_id:
            progress = session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                tool="concept-graph",
                stage="organize",
                status="running",
                percentage=0,
                created_at=datetime.utcnow()
            )
            session.add(progress)
            session.commit()
        
        # Update progress
        progress.status = "running"
        progress.percentage = 10
        session.commit()
        
        # Get file data from database
        from app.models import UploadedFile, FilePage, TopicModelResult, DocumentAnalysisResult
        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if not files:
            raise ValueError("No accessible files found")
        
        # Prepare file data for concept graph service by gathering from multiple tables
        file_data = []
        for file in files:
            log.info(f"[Concept Graph Task] Processing file: {file.original_file_name}")
            
            # Get file pages data (summary, topics)
            file_pages = session.query(FilePage).filter(
                FilePage.file_id == file.id
            ).all()
            
            # Get topics from topics table
            topics_data = session.query(TopicModelResult).filter(
                TopicModelResult.file_id == file.id
            ).all()
            
            # Get document analysis data (entities)
            doc_analysis = session.query(DocumentAnalysisResult).filter(
                DocumentAnalysisResult.file_id == file.id
            ).first()
            
            # Extract and organize data
            summaries = []
            page_topics = []
            
            for page in file_pages:
                if page.page_summary:
                    summaries.append(page.page_summary)
                if page.page_topics:
                    page_topics.extend(page.page_topics if isinstance(page.page_topics, list) else [page.page_topics])

            # Get topics from topics table
            all_topics = []
            for topic in topics_data:
                if topic.topics:
                    if isinstance(topic.topics, list):
                        for item in topic.topics:
                            # Extract string representation of topic
                            if isinstance(item, dict):
                                # If it's a dict, try to get 'text' or 'topic' field, or convert to string
                                topic_text = item.get('text') or item.get('topic') or item.get('name') or str(item)
                                all_topics.append(topic_text)
                            elif isinstance(item, str):
                                all_topics.append(item)
                            else:
                                all_topics.append(str(item))
                    else:
                        # Handle single topic item
                        if isinstance(topic.topics, dict):
                            topic_text = topic.topics.get('text') or topic.topics.get('topic') or topic.topics.get('name') or str(topic.topics)
                            all_topics.append(topic_text)
                        elif isinstance(topic.topics, str):
                            all_topics.append(topic.topics)
                        else:
                            all_topics.append(str(topic.topics))
            
            # Ensure page_topics are also strings
            clean_page_topics = []
            for item in page_topics:
                if isinstance(item, dict):
                    topic_text = item.get('text') or item.get('topic') or item.get('name') or str(item)
                    clean_page_topics.append(topic_text)
                elif isinstance(item, str):
                    clean_page_topics.append(item)
                else:
                    clean_page_topics.append(str(item))
            
            # Combine all topics (flatten and deduplicate)
            combined_topics = list(set(clean_page_topics + all_topics))
            
            # Get entities from document analysis
            entities = {}
            if doc_analysis and doc_analysis.meta:
                entities = doc_analysis.meta.get('entities_by_type', {})
            
            # Prepare comprehensive file data
            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "content": getattr(file, 'processed_content', ''),
                "summary": ' '.join(summaries) if summaries else '',
                "topics": combined_topics,
                "entities": entities,
                "keywords": [],  # Could be extracted from topics or analysis
                "relationships": [],  # Could be derived from entities and topics
                "concepts": combined_topics,  # Use topics as concepts for now
                "key_points": summaries,  # Use summaries as key points
                "evidence_items": []  # Could be populated from analysis results
            })
            
            log.info(f"[Concept Graph Task] File {file.original_file_name}: {len(combined_topics)} topics, {len(entities)} entity types")
        
        # Update progress
        progress.percentage = 20
        session.commit()
        
        # Initialize concept graph service
        concept_graph_service = ConceptGraphService()
        
        # Build concept graph
        log.info(f"[Concept Graph Task] Building concept graph for {len(file_data)} files")
        result = concept_graph_service.build_concept_graph(file_data)
        
        # Update progress
        progress.percentage = 90
        session.commit()
        
        # Store results
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()
        
        session.commit()
        
        # Get nodes and edges from the graph structure
        graph_data = result.get('graph', {})
        nodes_count = len(graph_data.get('nodes', []))
        edges_count = len(graph_data.get('edges', []))
        log.info(f"[Concept Graph Task] Completed successfully. Created {nodes_count} nodes and {edges_count} edges")
        
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "nodes_count": nodes_count,
            "edges_count": edges_count
        }
        
    except Exception as e:
        log.error(f"[Concept Graph Task] Error: {e}")
        log.error(traceback.format_exc())
        
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            session.commit()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            log.info(f"[Concept Graph Task] Retrying... Attempt {self.request.retries + 1}")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise e
        
    finally:
        session.close()
