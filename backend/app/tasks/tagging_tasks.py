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
        from app.models import UploadedFile, FilePage
        from app.models.analysis_results import TopicModelResult, DocumentAnalysisResult
        
        files = session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if not files:
            raise ValueError("No accessible files found")
        
        # Prepare file data for tagging service
        file_data = []
        for file in files:
            # Get pages for summary extraction
            file_pages = session.query(FilePage).filter(
                FilePage.file_id == file.id
            ).all()
            
            # Get topics from topics table
            topics_data = session.query(TopicModelResult).filter(
                TopicModelResult.file_id == file.id
            ).first()
            
            # Get document analysis data (entities)
            doc_analysis = session.query(DocumentAnalysisResult).filter(
                DocumentAnalysisResult.file_id == file.id
            ).first()
            
            # Extract topics
            all_topics = []
            page_topics = []
            
            # Get topics from page_topics in FilePage
            for page in file_pages:
                if page.page_topics:
                    if isinstance(page.page_topics, list):
                        page_topics.extend(page.page_topics)
                    else:
                        page_topics.append(page.page_topics)
            
            # Get topics from TopicModelResult
            if topics_data and topics_data.topics:
                if isinstance(topics_data.topics, list):
                    for item in topics_data.topics:
                        if isinstance(item, dict):
                            topic_text = item.get('label') or item.get('text') or item.get('topic') or str(item)
                            all_topics.append(topic_text)
                        elif isinstance(item, str):
                            all_topics.append(item)
            
            # Clean and combine page topics
            clean_page_topics = []
            for item in page_topics:
                if isinstance(item, dict):
                    topic_text = item.get('text') or item.get('topic') or item.get('name') or str(item)
                    clean_page_topics.append(topic_text)
                elif isinstance(item, str):
                    clean_page_topics.append(item)
                else:
                    clean_page_topics.append(str(item))
            
            # Combine all topics (deduplicate)
            combined_topics = list(set(clean_page_topics + all_topics))
            
            # Extract entities from document analysis
            entities = {}
            if doc_analysis and doc_analysis.meta:
                entities_by_type = doc_analysis.meta.get('entities_by_type', {})
                if entities_by_type:
                    entities = entities_by_type
            
            # Extract keywords from topics
            keywords = []
            if topics_data and topics_data.topics:
                if isinstance(topics_data.topics, list):
                    for topic in topics_data.topics:
                        if isinstance(topic, dict) and 'keywords' in topic:
                            keywords.extend(topic['keywords'])
            
            # Get summary text from page_summary fields
            summaries = []
            for page in file_pages:
                if page.page_summary:
                    summaries.append(page.page_summary)
            
            # Combine summaries into one text
            summary_text = " ".join(summaries) if summaries else ""
            
            # Collect key points from page summaries
            key_points = []
            for page in file_pages[:10]:  # First 10 pages for better coverage
                if page.page_summary:
                    key_points.append({"text": page.page_summary})
            
            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "topics": combined_topics,
                "entities": entities,
                "keywords": list(set(keywords)),  # Deduplicate
                "summary": summary_text,
                "key_points": key_points
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
        
        # Get tag count from statistics
        tag_stats = result.get('tag_statistics', {})
        total_tags = tag_stats.get('total_tags', 0)
        
        log.info(f"[Tagging Task] Completed successfully. Created {total_tags} tags in {tag_stats.get('total_categories', 0)} categories")
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "tags_count": total_tags
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
