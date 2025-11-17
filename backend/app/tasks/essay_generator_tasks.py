import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.create.essay_generator_service import EssayGeneratorService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_essay_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to generate essays from uploaded files.
    
    Args:
        user_id: ID of the user requesting essay generation
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        options: Optional configuration for essay generation
    """
    # Create a new session for this task
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[EssayGeneratorTask] Starting essay generation for user {user_id}, files: {file_ids}")
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.current_step = 'Initializing essay generation'
                    progress.progress_percentage = 10
                    db.session.commit()
            
            # Initialize service
            essay_service = EssayGeneratorService()
            
            all_essays = []
            total_files = len(file_ids)
            
            for i, file_id in enumerate(file_ids):
                try:
                    log.info(f"[EssayGeneratorTask] Processing file {file_id} ({i+1}/{total_files})")
                    
                    # Update progress
                    if progress:
                        progress.current_step = f'Generating essay for file {i+1}/{total_files}'
                        progress.progress_percentage = 20 + (60 * i // total_files)
                        db.session.commit()
                    
                    # Get file data from database
                    file_data = get_file_analysis_data(file_id)
                    
                    if not file_data:
                        log.warning(f"[EssayGeneratorTask] No analysis data found for file {file_id}")
                        continue
                    
                    # Generate essay for this file
                    essay_result = essay_service.generate_essay(file_data, options)
                    
                    # Add file identification
                    essay_result['file_id'] = file_id
                    essay_result['file_name'] = file_data.get('file_name', f'File {file_id}')
                    
                    all_essays.append(essay_result)
                    
                    log.info(f"[EssayGeneratorTask] Generated essay for file {file_id}")
                    
                except Exception as e:
                    log.error(f"[EssayGeneratorTask] Error processing file {file_id}: {e}")
                    # Continue with other files
                    continue
            
            if not all_essays:
                raise Exception("No essays could be generated from the provided files")
            
            # Create consolidated result
            consolidated_result = consolidate_essays(all_essays)
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.current_step = 'Essay generation completed'
                progress.progress_percentage = 100
                progress.result_data = consolidated_result
                progress.completed_at = datetime.utcnow()
                db.session.commit()
            
            log.info(f"[EssayGeneratorTask] Successfully generated essays for {len(all_essays)} files")
            return consolidated_result
            
        except Exception as e:
            log.error(f"[EssayGeneratorTask] Task failed: {e}")
            log.error(traceback.format_exc())
            
            # Update progress to failed
            if progress:
                try:
                    progress.status = 'failed'
                    progress.current_step = f'Error: {str(e)}'
                    progress.error_message = str(e)
                    db.session.commit()
                except Exception as commit_error:
                    log.error(f"Failed to update progress on error: {commit_error}")
            
            raise

def get_file_analysis_data(file_id: int) -> dict:
    """Get file analysis data needed for essay generation."""
    
    try:
        # Import here to avoid circular imports
        from app.models.files import UploadedFile
        
        # Get file info
        file_record = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not file_record:
            log.warning(f"File {file_id} not found")
            return None
        
        # For now, get basic analysis from Progress table (similar to other tools)
        analysis_progress = db.session.query(Progress).filter(
            Progress.file_ids.contains([file_id]),
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
        
        # If no analysis data, create minimal data structure for essay writing
        if not content and not summary:
            content = f"Analysis content for {file_record.filename}"
            summary = f"This document {file_record.filename} contains material suitable for essay analysis."
            topics = ["document analysis", "main themes", "key arguments"]
            key_points = [
                {"text": f"Key insight from {file_record.filename}"},
                {"text": "Supporting evidence for main argument"},
                {"text": "Critical analysis of presented information"}
            ]
        
        # Prepare file data
        file_data = {
            'file_id': file_id,
            'file_name': file_record.filename,
            'content': content,
            'summary': summary,
            'topics': topics,
            'entities': entities,
            'key_points': key_points,
            'metadata': {
                'file_type': file_record.file_type,
                'file_size': file_record.file_size,
                'uploaded_at': file_record.uploaded_at.isoformat() if file_record.uploaded_at else None
            }
        }
        
        return file_data
        
    except Exception as e:
        log.error(f"Error getting file analysis data for file {file_id}: {e}")
        return None

def consolidate_essays(essays_list: list) -> dict:
    """Consolidate essays from multiple files into a unified result."""
    
    if not essays_list:
        return {}
    
    if len(essays_list) == 1:
        return essays_list[0]
    
    # Consolidate multiple files
    consolidated = {
        'essays': essays_list,
        'files_processed': [],
        'metadata': {
            'total_files': len(essays_list),
            'total_word_count': 0,
            'essay_types': set(),
            'academic_levels': set()
        },
        'compilation_options': {
            'combined_essay': {
                'available': True,
                'description': 'Option to combine essays into a single comprehensive analysis'
            },
            'comparative_essay': {
                'available': len(essays_list) > 1,
                'description': 'Option to create a comparative analysis across documents'
            }
        },
        'writing_resources': {
            'style_guides': ['MLA', 'APA', 'Chicago'],
            'revision_checklist': [
                'Clear thesis statement',
                'Logical paragraph organization',
                'Strong evidence and analysis',
                'Proper citations and formatting',
                'Smooth transitions between ideas'
            ],
            'common_improvements': [
                'Strengthen topic sentences',
                'Add more specific examples',
                'Deepen analytical discussions',
                'Improve conclusion impact'
            ]
        },
        'created_at': datetime.utcnow().isoformat()
    }
    
    total_words = 0
    
    for essay in essays_list:
        file_info = {
            'file_id': essay.get('file_id'),
            'file_name': essay.get('file_name'),
            'word_count': 0
        }
        
        metadata = essay.get('metadata', {})
        
        # Collect metadata
        if metadata.get('essay_type'):
            consolidated['metadata']['essay_types'].add(metadata['essay_type'])
        if metadata.get('academic_level'):
            consolidated['metadata']['academic_levels'].add(metadata['academic_level'])
        
        word_count = metadata.get('word_count', 0)
        total_words += word_count
        file_info['word_count'] = word_count
        
        consolidated['files_processed'].append(file_info)
    
    # Update metadata
    consolidated['metadata']['total_word_count'] = total_words
    consolidated['metadata']['average_word_count'] = total_words // len(essays_list) if essays_list else 0
    consolidated['metadata']['essay_types'] = list(consolidated['metadata']['essay_types'])
    consolidated['metadata']['academic_levels'] = list(consolidated['metadata']['academic_levels'])
    
    # Add combined essay option if multiple essays
    if len(essays_list) > 1:
        consolidated['combined_analysis'] = {
            'suggested_approach': 'Create a comprehensive analysis that synthesizes insights from all documents',
            'structure_recommendation': 'Introduction → Document 1 Analysis → Document 2 Analysis → Comparative Analysis → Conclusion',
            'thesis_suggestion': 'Develop a thesis that encompasses themes across all documents'
        }
    
    return consolidated
