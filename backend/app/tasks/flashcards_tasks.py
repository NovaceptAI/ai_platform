import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.master.flashcards_service import FlashcardsService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_flashcards_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None, artifact_id: str = None):
    """
    Celery task for creating flashcards from document content.
    
    Args:
        user_id: ID of the user
        file_ids: List of file IDs to process
        progress_id: Optional progress tracking ID
        options: Optional dict with max_cards, difficulty, include_definitions, include_concepts, include_facts
        artifact_id: Optional research artifact ID (for research workspace integration)
    """
    # Create a new session for this task
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db.engine)
    session = Session()
    progress = None
    
    # Default options
    if options is None:
        options = {}
    
    max_cards = options.get('max_cards', 20)
    difficulty = options.get('difficulty', 'medium')
    include_definitions = options.get('include_definitions', True)
    include_concepts = options.get('include_concepts', True)
    include_facts = options.get('include_facts', True)
    
    try:
        log.info(f"[Flashcards Task] Starting for user {user_id} with {len(file_ids)} files")
        
        # Initialize or get progress record
        if progress_id:
            progress = session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                tool="flashcards",
                stage="master",
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
        
        # Process each file
        all_flashcards = []
        for i, file in enumerate(files):
            log.info(f"[Flashcards Task] Processing file: {file.original_file_name}")
            
            # Get file pages data (summary, content)
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
            content_text = ""
            
            for page in file_pages:
                if page.page_summary:
                    summaries.append(page.page_summary)
                if page.page_topics:
                    if isinstance(page.page_topics, list):
                        page_topics.extend(page.page_topics)
                    else:
                        page_topics.append(page.page_topics)
                if page.page_text:
                    content_text += f" {page.page_text}"
            
            # Get topics from topics table
            all_topics = []
            for topic in topics_data:
                if topic.topics:
                    if isinstance(topic.topics, list):
                        all_topics.extend(topic.topics)
                    else:
                        all_topics.append(topic.topics)
            
            # Combine all topics and clean them
            combined_topics = []
            for topic in page_topics + all_topics:
                if isinstance(topic, dict):
                    topic_text = topic.get('text') or topic.get('topic') or topic.get('name') or str(topic)
                    combined_topics.append(topic_text)
                elif isinstance(topic, str):
                    combined_topics.append(topic)
                else:
                    combined_topics.append(str(topic))
            
            combined_topics = list(set(combined_topics))  # Remove duplicates
            
            # Get entities from document analysis
            entities = {}
            if doc_analysis and doc_analysis.meta:
                entities = doc_analysis.meta.get('entities_by_type', {})
            
            # Prepare file data for flashcards service
            file_data = {
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "content": content_text.strip(),
                "summary": ' '.join(summaries) if summaries else '',
                "topics": combined_topics,
                "entities": entities,
                "key_points": summaries,  # Use summaries as key points
            }
            
            # Update progress
            progress.percentage = 20 + (i * 60 // len(files))
            session.commit()
            
            # Initialize flashcards service
            flashcards_service = FlashcardsService()
            
            # Prepare options for service
            service_options = {
                'max_cards': max_cards,
                'difficulty': difficulty,
                'include_definitions': include_definitions,
                'include_concepts': include_concepts,
                'include_facts': include_facts
            }
            
            # Create flashcards for this file with options
            log.info(f"[Flashcards Task] Creating flashcards for file {file.original_file_name} with options: {service_options}")
            file_flashcards = flashcards_service.create_flashcards_for_file(file_data, service_options)
            
            # Add file context to flashcards
            file_flashcards["file_id"] = str(file.id)
            file_flashcards["file_name"] = file.original_file_name
            all_flashcards.append(file_flashcards)
            
            log.info(f"[Flashcards Task] Created {len(file_flashcards.get('flashcards', []))} flashcards for {file.original_file_name}")
        
        # Update progress
        progress.percentage = 90
        session.commit()
        
        # Combine all flashcards into final result
        combined_flashcards = []
        total_cards = 0
        
        for file_flashcards in all_flashcards:
            combined_flashcards.extend(file_flashcards.get("flashcards", []))
            total_cards += len(file_flashcards.get("flashcards", []))
        
        result = {
            "flashcards": combined_flashcards,
            "files_processed": len(files),
            "total_cards": total_cards,
            "files_data": all_flashcards,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store results
        progress.result_data = result
        progress.status = "completed"
        progress.percentage = 100
        progress.completed_at = datetime.utcnow()
        
        session.commit()
        
        # Update research artifact if provided
        if artifact_id:
            try:
                from app.models.research import ResearchArtifact
                artifact = session.query(ResearchArtifact).filter(ResearchArtifact.id == artifact_id).first()
                if artifact:
                    artifact.result_data = result
                    artifact.status = "completed"
                    artifact.updated_at = datetime.utcnow()
                    session.commit()
                    log.info(f"[Flashcards Task] Updated research artifact {artifact_id}")
            except Exception as e:
                log.error(f"[Flashcards Task] Error updating artifact: {e}")
        
        log.info(f"[Flashcards Task] Completed successfully. Created {total_cards} total flashcards for {len(files)} files")
        
        return {
            "status": "success",
            "progress_id": str(progress.id),
            "result": result,
            "total_cards": total_cards
        }
        
    except Exception as e:
        log.error(f"[Flashcards Task] Error: {e}")
        log.error(traceback.format_exc())
        
        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.utcnow()
            session.commit()
        
        # Update research artifact if provided
        if artifact_id:
            try:
                from app.models.research import ResearchArtifact
                artifact = session.query(ResearchArtifact).filter(ResearchArtifact.id == artifact_id).first()
                if artifact:
                    artifact.status = "failed"
                    artifact.error_message = str(e)
                    artifact.updated_at = datetime.utcnow()
                    session.commit()
                    log.info(f"[Flashcards Task] Marked research artifact {artifact_id} as failed")
            except Exception as ae:
                log.error(f"[Flashcards Task] Error updating artifact: {ae}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            log.info(f"[Flashcards Task] Retrying... Attempt {self.request.retries + 1}")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise e
        
    finally:
        session.close()
