import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.master.visual_study_guide_service import VisualStudyGuideService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_visual_study_guide_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to create visual study guides from uploaded files.
    
    Args:
        user_id: ID of the user requesting visual study guide
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        options: Optional configuration for visual guide creation
    """
    # Create a new session for this task
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[VisualStudyGuideTask] Starting visual study guide creation for user {user_id}, files: {file_ids}")
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.current_step = 'Initializing visual study guide creation'
                    progress.progress_percentage = 10
                    db.session.commit()
            
            # Initialize service
            visual_guide_service = VisualStudyGuideService()
            
            all_guides = []
            total_files = len(file_ids)
            
            for i, file_id in enumerate(file_ids):
                try:
                    log.info(f"[VisualStudyGuideTask] Processing file {file_id} ({i+1}/{total_files})")
                    
                    # Update progress
                    if progress:
                        progress.current_step = f'Creating visual study guide for file {i+1}/{total_files}'
                        progress.progress_percentage = 20 + (60 * i // total_files)
                        db.session.commit()
                    
                    # Get file data from database
                    file_data = get_file_analysis_data(file_id)
                    
                    if not file_data:
                        log.warning(f"[VisualStudyGuideTask] No analysis data found for file {file_id}")
                        continue
                    
                    # Create visual study guide for this file
                    guide_result = visual_guide_service.create_visual_study_guide(file_data, options)
                    
                    # Add file identification
                    guide_result['file_id'] = file_id
                    guide_result['file_name'] = file_data.get('file_name', f'File {file_id}')
                    
                    all_guides.append(guide_result)
                    
                    log.info(f"[VisualStudyGuideTask] Created visual study guide for file {file_id}")
                    
                except Exception as e:
                    log.error(f"[VisualStudyGuideTask] Error processing file {file_id}: {e}")
                    # Continue with other files
                    continue
            
            if not all_guides:
                raise Exception("No visual study guides could be created from the provided files")
            
            # Create consolidated result
            consolidated_result = consolidate_visual_study_guides(all_guides)
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.current_step = 'Visual study guide creation completed'
                progress.progress_percentage = 100
                progress.result_data = consolidated_result
                progress.completed_at = datetime.utcnow()
                db.session.commit()
            
            log.info(f"[VisualStudyGuideTask] Successfully created visual study guides for {len(all_guides)} files")
            return consolidated_result
            
        except Exception as e:
            log.error(f"[VisualStudyGuideTask] Task failed: {e}")
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
    """Get file analysis data needed for visual study guide creation."""
    
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
        
        # If no analysis data, create minimal data structure
        if not content and not summary:
            content = f"Content for {file_record.filename}"
            summary = f"This is {file_record.filename} uploaded by the user."
            topics = ["visual learning", "study techniques", "concept mapping"]
            key_points = [
                {"text": f"Review the content of {file_record.filename}"},
                {"text": "Create visual representations of key concepts"},
                {"text": "Use diagrams and mind maps for understanding"}
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

def consolidate_visual_study_guides(guides_list: list) -> dict:
    """Consolidate visual study guides from multiple files into a unified result."""
    
    if not guides_list:
        return {}
    
    if len(guides_list) == 1:
        return guides_list[0]
    
    # Consolidate multiple files
    consolidated = {
        'visual_study_guide': {
            'overview': {},
            'visual_topics': [],
            'study_timeline': {},
            'concept_diagrams': [],
            'interactive_elements': []
        },
        'files_processed': [],
        'metadata': {
            'total_files': len(guides_list),
            'total_topics': 0,
            'styles': set(),
            'difficulty_levels': set()
        },
        'study_plan': {
            'recommended_sequence': [
                "overview", 
                "visual_topics", 
                "concept_diagrams", 
                "interactive_elements",
                "study_timeline"
            ],
            'estimated_time': f"{len(guides_list) * 30}-{len(guides_list) * 50} minutes",
            'study_modes': ["visual", "interactive", "sequential"]
        },
        'created_at': datetime.utcnow().isoformat()
    }
    
    all_topics = []
    all_diagrams = []
    all_interactive = []
    
    for guide in guides_list:
        file_info = {
            'file_id': guide.get('file_id'),
            'file_name': guide.get('file_name'),
            'sections_count': 0
        }
        
        guide_data = guide.get('visual_study_guide', {})
        metadata = guide.get('metadata', {})
        
        # Consolidate visual topics
        visual_topics = guide_data.get('visual_topics', [])
        for topic in visual_topics:
            topic['source_file'] = guide.get('file_name', 'Unknown')
            all_topics.append(topic)
        
        # Consolidate concept diagrams
        diagrams = guide_data.get('concept_diagrams', [])
        for diagram in diagrams:
            diagram['source_file'] = guide.get('file_name', 'Unknown')
            all_diagrams.append(diagram)
        
        # Consolidate interactive elements
        interactive = guide_data.get('interactive_elements', [])
        for element in interactive:
            element['source_file'] = guide.get('file_name', 'Unknown')
            all_interactive.append(element)
        
        # Update metadata
        file_info['sections_count'] = len(visual_topics) + len(diagrams) + len(interactive)
        consolidated['files_processed'].append(file_info)
        
        if metadata.get('style'):
            consolidated['metadata']['styles'].add(metadata['style'])
        if metadata.get('difficulty_level'):
            consolidated['metadata']['difficulty_levels'].add(metadata['difficulty_level'])
    
    # Assign consolidated data
    consolidated['visual_study_guide']['visual_topics'] = all_topics
    consolidated['visual_study_guide']['concept_diagrams'] = all_diagrams
    consolidated['visual_study_guide']['interactive_elements'] = all_interactive
    
    # Create consolidated overview
    consolidated['visual_study_guide']['overview'] = {
        'title': 'Consolidated Visual Study Guide',
        'summary': f'Comprehensive visual learning guide covering {len(guides_list)} documents',
        'key_concepts': [t.get('name', 'Concept') for t in all_topics[:10]],
        'total_sections': len(all_topics) + len(all_diagrams) + len(all_interactive)
    }
    
    # Create consolidated timeline
    total_time = sum(
        int(t.get('time_estimate', '25').split('-')[0]) if isinstance(t.get('time_estimate'), str) 
        else t.get('time_estimate', 25) 
        for t in all_topics
    )
    
    consolidated['visual_study_guide']['study_timeline'] = {
        'title': 'Consolidated Learning Timeline',
        'total_duration': f"{total_time}-{total_time + 30} minutes",
        'phases': [
            {
                'phase': 'Preparation',
                'duration': '10-15 minutes',
                'activities': ['Set up visual materials', 'Review all overviews', 'Plan study sequence']
            },
            {
                'phase': 'Visual Learning',
                'duration': f"{total_time}-{total_time + 15} minutes",
                'activities': ['Work through visual topics', 'Create concept diagrams', 'Complete interactive elements']
            },
            {
                'phase': 'Integration',
                'duration': '15-20 minutes',
                'activities': ['Connect concepts across files', 'Create unified visual summary', 'Review key learnings']
            }
        ]
    }
    
    # Update metadata
    consolidated['metadata']['total_topics'] = len(all_topics)
    consolidated['metadata']['styles'] = list(consolidated['metadata']['styles'])
    consolidated['metadata']['difficulty_levels'] = list(consolidated['metadata']['difficulty_levels'])
    
    return consolidated
