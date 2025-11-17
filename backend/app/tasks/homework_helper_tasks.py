import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.master.homework_helper_service import HomeworkHelperService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_homework_assistance_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to create homework assistance materials from uploaded files.
    
    Args:
        user_id: ID of the user requesting homework assistance
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        options: Optional configuration for homework assistance
    """
    # Create a new session for this task
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[HomeworkHelperTask] Starting homework assistance creation for user {user_id}, files: {file_ids}")
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.percentage = 10
                    db.session.commit()
            
            # Initialize service
            homework_service = HomeworkHelperService()
            
            all_assistance = []
            total_files = len(file_ids)
            
            for i, file_id in enumerate(file_ids):
                try:
                    log.info(f"[HomeworkHelperTask] Processing file {file_id} ({i+1}/{total_files})")
                    
                    # Update progress
                    if progress:
                        progress.percentage = 20 + (60 * i // total_files)
                        db.session.commit()
                    
                    # Get file data from database
                    file_data = get_file_analysis_data(file_id)
                    
                    if not file_data:
                        log.warning(f"[HomeworkHelperTask] No analysis data found for file {file_id}")
                        continue
                    
                    # Create homework assistance for this file
                    assistance_result = homework_service.create_homework_assistance(file_data, options)
                    
                    # Add file identification
                    assistance_result['file_id'] = file_id
                    assistance_result['file_name'] = file_data.get('file_name', f'File {file_id}')
                    
                    all_assistance.append(assistance_result)
                    
                    log.info(f"[HomeworkHelperTask] Created homework assistance for file {file_id}")
                    
                except Exception as e:
                    log.error(f"[HomeworkHelperTask] Error processing file {file_id}: {e}")
                    # Continue with other files
                    continue
            
            if not all_assistance:
                raise Exception("No homework assistance could be created from the provided files")
            
            # Create consolidated result
            consolidated_result = consolidate_homework_assistance(all_assistance)
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.percentage = 100
                progress.result_data = consolidated_result
                progress.completed_at = datetime.utcnow()
                db.session.commit()
            
            log.info(f"[HomeworkHelperTask] Successfully created homework assistance for {len(all_assistance)} files")
            return consolidated_result
            
        except Exception as e:
            log.error(f"[HomeworkHelperTask] Task failed: {e}")
            log.error(traceback.format_exc())
            
            # Update progress to failed
            if progress:
                try:
                    progress.status = 'failed'
                    progress.error_message = str(e)
                    db.session.commit()
                except Exception as commit_error:
                    log.error(f"Failed to update progress on error: {commit_error}")
            
            raise

def get_file_analysis_data(file_id: int) -> dict:
    """Get file analysis data needed for homework assistance creation."""
    
    try:
        # Import here to avoid circular imports
        from app.models.files import UploadedFile
        
        # Get file info
        file_record = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not file_record:
            log.warning(f"File {file_id} not found")
            return None
        
        # For now, get basic analysis from Progress table (similar to concept graph approach)
        analysis_progress = db.session.query(Progress).filter(
            Progress.file_id == file_id,
            Progress.status == 'completed',
            Progress.result_data.isnot(None)
        ).order_by(Progress.completed_at.desc()).first()
        
        content = ""
        summary = ""
        topics = []
        entities = {}
        key_points = []
        
        if analysis_progress and analysis_progress.result_data:
            result_data = analysis_progress.result_data
            if isinstance(result_data, dict):
                # Extract from document analysis or similar results
                if 'document_analysis' in result_data:
                    doc_data = result_data['document_analysis']
                    content = doc_data.get('content', '')
                    summary = doc_data.get('summary', '')
                    topics = doc_data.get('topics', [])
                    entities = doc_data.get('entities', {})
                    key_points = doc_data.get('key_points', [])
                elif 'content' in result_data:
                    content = result_data.get('content', '')
                    summary = result_data.get('summary', '')
                    topics = result_data.get('topics', [])
                    entities = result_data.get('entities', {})
                    key_points = result_data.get('key_points', [])
        
        # If no analysis data, create minimal data structure
        if not content and not summary:
            content = f"Content for {file_record.original_file_name}"
            summary = f"This is {file_record.original_file_name} uploaded by the user."
            topics = ["general study", "document analysis"]
            key_points = [{"text": f"Review the content of {file_record.original_file_name}"}]
        
        # Prepare file data
        file_data = {
            'file_id': file_id,
            'file_name': file_record.original_file_name,
            'content': content,
            'summary': summary,
            'topics': topics,
            'entities': entities,
            'key_points': key_points,
            'metadata': {
                'file_type': file_record.file_type,
                'created_at': file_record.created_at.isoformat() if file_record.created_at else None
            }
        }
        
        return file_data
        
    except Exception as e:
        log.error(f"Error getting file analysis data for file {file_id}: {e}")
        return None

def consolidate_homework_assistance(assistance_list: list) -> dict:
    """Consolidate homework assistance from multiple files into a unified result."""
    
    if not assistance_list:
        return {}
    
    if len(assistance_list) == 1:
        return assistance_list[0]
    
    # Consolidate multiple files
    consolidated = {
        'homework_assistance': {
            'explanations': [],
            'examples': [],
            'practice_recommendations': [],
            'study_guidance': {}
        },
        'files_processed': [],
        'metadata': {
            'total_files': len(assistance_list),
            'total_items': 0,
            'subject_areas': set(),
            'difficulty_levels': set()
        },
        'study_plan': {
            'recommended_order': ["explanations", "examples", "practice_recommendations"],
            'estimated_time': f"{len(assistance_list) * 30}-{len(assistance_list) * 45} minutes",
            'difficulty_progression': "basic → intermediate → advanced"
        },
        'created_at': datetime.utcnow().isoformat()
    }
    
    all_study_guidance = {}
    
    for assistance in assistance_list:
        file_info = {
            'file_id': assistance.get('file_id'),
            'file_name': assistance.get('file_name'),
            'items_count': 0
        }
        
        homework_data = assistance.get('homework_assistance', {})
        metadata = assistance.get('metadata', {})
        
        # Consolidate explanations
        explanations = homework_data.get('explanations', [])
        for exp in explanations:
            exp['source_file'] = assistance.get('file_name', 'Unknown')
            consolidated['homework_assistance']['explanations'].append(exp)
        
        # Consolidate examples
        examples = homework_data.get('examples', [])
        for ex in examples:
            ex['source_file'] = assistance.get('file_name', 'Unknown')
            consolidated['homework_assistance']['examples'].append(ex)
        
        # Consolidate practice recommendations
        practice = homework_data.get('practice_recommendations', [])
        for pr in practice:
            pr['source_file'] = assistance.get('file_name', 'Unknown')
            consolidated['homework_assistance']['practice_recommendations'].append(pr)
        
        # Collect study guidance
        study_guidance = homework_data.get('study_guidance', {})
        for key, value in study_guidance.items():
            if key not in all_study_guidance:
                all_study_guidance[key] = []
            if isinstance(value, list):
                all_study_guidance[key].extend(value)
            else:
                all_study_guidance[key].append(value)
        
        # Update metadata
        file_info['items_count'] = len(explanations) + len(examples) + len(practice)
        consolidated['files_processed'].append(file_info)
        
        if metadata.get('subject_area'):
            consolidated['metadata']['subject_areas'].add(metadata['subject_area'])
        if metadata.get('difficulty_level'):
            consolidated['metadata']['difficulty_levels'].add(metadata['difficulty_level'])
    
    # Consolidate study guidance
    consolidated_guidance = {}
    for key, values in all_study_guidance.items():
        if key == 'study_approach':
            # Take the most common approach
            consolidated_guidance[key] = values[0] if values else ""
        elif key in ['key_strategies', 'common_mistakes', 'success_tips']:
            # Combine and deduplicate
            unique_items = []
            for item in values:
                if isinstance(item, list):
                    unique_items.extend(item)
                else:
                    unique_items.append(item)
            consolidated_guidance[key] = list(set(unique_items))[:5]  # Limit to 5 items
        else:
            consolidated_guidance[key] = values[0] if values else ""
    
    consolidated['homework_assistance']['study_guidance'] = consolidated_guidance
    
    # Update metadata
    consolidated['metadata']['total_items'] = (
        len(consolidated['homework_assistance']['explanations']) +
        len(consolidated['homework_assistance']['examples']) +
        len(consolidated['homework_assistance']['practice_recommendations'])
    )
    consolidated['metadata']['subject_areas'] = list(consolidated['metadata']['subject_areas'])
    consolidated['metadata']['difficulty_levels'] = list(consolidated['metadata']['difficulty_levels'])
    
    return consolidated