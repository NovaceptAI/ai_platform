from flask import Blueprint, request, jsonify
from app.models.status import Progress
from app.db import db
from app.tasks.story_creator_tasks import create_story_task
import uuid
from datetime import datetime
import logging

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
story_creator_bp = Blueprint('story_creator', __name__)

@story_creator_bp.route('/start-story-creation', methods=['POST'])
def start_story_creation():
    """
    Start story creation task for uploaded files.
    
    Expected JSON payload:
    {
        "file_ids": ["uuid1", "uuid2", ...],
        "user_id": "user_uuid",  # Optional, will use test user if not provided
        "options": {
            "story_type": "educational|historical|biographical|fictional|case_study",
            "narrative_style": "engaging|formal|conversational|dramatic",
            "audience_level": "elementary|middle_school|high_school|adult",
            "creative_elements": true|false
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        file_ids = data.get('file_ids', [])
        if not file_ids:
            return jsonify({'error': 'file_ids is required and cannot be empty'}), 400
        
        # Use provided user_id or fallback to test user
        user_id = data.get('user_id', 'test-user-id')
        
        # Get options with defaults
        options = data.get('options', {})
        story_type = options.get('story_type', 'educational')
        narrative_style = options.get('narrative_style', 'engaging')
        audience_level = options.get('audience_level', 'general')
        creative_elements = options.get('creative_elements', True)
        
        # Validate options
        valid_types = ['educational', 'historical', 'biographical', 'fictional', 'case_study']
        valid_styles = ['engaging', 'formal', 'conversational', 'dramatic']
        valid_levels = ['elementary', 'middle_school', 'high_school', 'adult', 'general']
        
        if story_type not in valid_types:
            return jsonify({'error': f'story_type must be one of: {valid_types}'}), 400
        if narrative_style not in valid_styles:
            return jsonify({'error': f'narrative_style must be one of: {valid_styles}'}), 400
        if audience_level not in valid_levels:
            return jsonify({'error': f'audience_level must be one of: {valid_levels}'}), 400
        if not isinstance(creative_elements, bool):
            return jsonify({'error': 'creative_elements must be a boolean'}), 400
        
        # Validate that files exist
        from app.models.files import UploadedFile
        existing_files = db.session.query(UploadedFile).filter(UploadedFile.id.in_(file_ids)).all()
        existing_file_ids = [f.id for f in existing_files]
        
        if len(existing_file_ids) != len(file_ids):
            missing_files = set(file_ids) - set(existing_file_ids)
            return jsonify({
                'error': f'Files not found: {list(missing_files)}',
                'found_files': existing_file_ids
            }), 404
        
        # Create progress record
        progress_id = str(uuid.uuid4())
        progress = Progress(
            id=progress_id,
            user_id=user_id,
            task_type='story_creation',
            status='pending',
            progress_percentage=0,
            current_step='Initializing story creation task',
            created_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        
        log.info(f"[StoryCreatorAPI] Created progress record {progress_id} for user {user_id}")
        
        # Queue the Celery task
        task_options = {
            'story_type': story_type,
            'narrative_style': narrative_style,
            'audience_level': audience_level,
            'creative_elements': creative_elements
        }
        
        task = create_story_task.delay(
            user_id=user_id,
            file_ids=file_ids,
            progress_id=progress_id,
            options=task_options
        )
        
        log.info(f"[StoryCreatorAPI] Queued story creation task {task.id} for progress {progress_id}")
        
        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Story creation task started successfully',
            'options_used': task_options,
            'files_count': len(file_ids)
        }), 202
        
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error starting story creation: {str(e)}")
        return jsonify({
            'error': 'Failed to start story creation task',
            'details': str(e)
        }), 500


@story_creator_bp.route('/story-creation-results/<progress_id>', methods=['GET'])
def get_story_creation_results(progress_id):
    """
    Get story creation results by progress ID.
    
    Returns:
    - If pending/in_progress: Current progress status
    - If completed: Full story results
    - If failed: Error information
    """
    try:
        progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            return jsonify({'error': 'Progress record not found'}), 404
        
        response_data = {
            'progress_id': progress_id,
            'status': progress.status,
            'progress_percentage': progress.progress_percentage,
            'current_step': progress.current_step,
            'created_at': progress.created_at.isoformat() if progress.created_at else None,
            'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
        }
        
        if progress.status == 'completed':
            response_data.update({
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
                'result': progress.result
            })
            
            # Add summary information
            if progress.result:
                result = progress.result
                if 'consolidated_story' in result:
                    # Multi-file result
                    consolidated = result['consolidated_story']
                    consolidation_summary = consolidated.get('consolidation_summary', {})
                    response_data['summary'] = {
                        'type': 'consolidated_story',
                        'files_processed': result.get('files_processed', 0),
                        'successful_stories': result.get('successful_stories', 0),
                        'total_sections': consolidation_summary.get('total_sections', 0),
                        'estimated_reading_time': consolidation_summary.get('estimated_reading_time', 'unknown'),
                        'story_type': consolidation_summary.get('story_type', 'unknown'),
                        'narrative_style': consolidation_summary.get('narrative_style', 'unknown'),
                        'audience_level': consolidation_summary.get('audience_level', 'unknown')
                    }
                elif 'story' in result:
                    # Single file result
                    story_data = result['story']
                    if story_data and 'story' in story_data:
                        story_content = story_data['story']
                        story_summary = story_content.get('story_summary', {})
                        response_data['summary'] = {
                            'type': 'single_story',
                            'filename': story_data.get('filename', 'unknown'),
                            'reading_time': story_summary.get('estimated_reading_time', 'unknown'),
                            'story_type': story_summary.get('story_type', 'unknown'),
                            'narrative_style': story_summary.get('narrative_style', 'unknown'),
                            'audience_level': story_summary.get('audience_level', 'unknown'),
                            'educational_value': story_summary.get('educational_value', 'unknown')
                        }
            
        elif progress.status == 'failed':
            response_data['error_message'] = progress.error_message
        
        return jsonify(response_data)
        
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error getting results for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve story creation results',
            'details': str(e)
        }), 500


@story_creator_bp.route('/story-creation-status/<progress_id>', methods=['GET'])
def get_story_creation_status(progress_id):
    """
    Get brief status information for story creation progress.
    
    Returns only status, percentage, and current step - lighter weight than full results.
    """
    try:
        progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            return jsonify({'error': 'Progress record not found'}), 404
        
        return jsonify({
            'progress_id': progress_id,
            'status': progress.status,
            'progress_percentage': progress.progress_percentage,
            'current_step': progress.current_step,
            'task_type': progress.task_type,
            'created_at': progress.created_at.isoformat() if progress.created_at else None
        })
        
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error getting status for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve story creation status',
            'details': str(e)
        }), 500


@story_creator_bp.route('/story-creation-history/<user_id>', methods=['GET'])
def get_story_creation_history(user_id):
    """
    Get story creation history for a specific user.
    
    Query parameters:
    - limit: Number of records to return (default: 10, max: 100)
    - offset: Number of records to skip (default: 0)
    - status: Filter by status (pending, in_progress, completed, failed)
    - story_type: Filter by story type (educational, historical, etc.)
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 10)), 100)
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        story_type_filter = request.args.get('story_type')
        
        # Build query
        query = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.task_type == 'story_creation'
        )
        
        if status_filter:
            query = query.filter(Progress.status == status_filter)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        progress_records = query.order_by(Progress.created_at.desc()).offset(offset).limit(limit).all()
        
        # Format results
        history = []
        for progress in progress_records:
            record = {
                'progress_id': progress.id,
                'status': progress.status,
                'progress_percentage': progress.progress_percentage,
                'current_step': progress.current_step,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
            }
            
            # Add summary for completed tasks
            if progress.status == 'completed' and progress.result:
                result = progress.result
                story_metadata = result.get('story_metadata', {})
                record['story_info'] = {
                    'story_type': story_metadata.get('story_type', 'unknown'),
                    'narrative_style': story_metadata.get('narrative_style', 'unknown'),
                    'audience_level': story_metadata.get('audience_level', 'unknown'),
                    'creative_elements': story_metadata.get('creative_elements', False)
                }
                
                # Filter by story_type if specified
                if story_type_filter and story_metadata.get('story_type') != story_type_filter:
                    continue
            
            history.append(record)
        
        return jsonify({
            'user_id': user_id,
            'total_count': total_count,
            'returned_count': len(history),
            'offset': offset,
            'limit': limit,
            'history': history
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid query parameter: {str(e)}'}), 400
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error getting history for user {user_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve story creation history',
            'details': str(e)
        }), 500


@story_creator_bp.route('/story-templates', methods=['GET'])
def get_story_templates():
    """
    Get available story templates and their configurations.
    
    Returns information about supported story types, styles, and options.
    """
    try:
        templates = {
            'story_types': {
                'educational': {
                    'name': 'Educational Story',
                    'description': 'Transform learning content into engaging narratives',
                    'sections': ['discovery', 'challenge', 'learning', 'application'],
                    'recommended_styles': ['engaging', 'conversational'],
                    'best_audiences': ['elementary', 'middle_school', 'high_school']
                },
                'historical': {
                    'name': 'Historical Narrative',
                    'description': 'Bring historical events and figures to life',
                    'sections': ['setting', 'key_figures', 'events', 'significance'],
                    'recommended_styles': ['dramatic', 'engaging'],
                    'best_audiences': ['middle_school', 'high_school', 'adult']
                },
                'biographical': {
                    'name': 'Biographical Story',
                    'description': 'Tell the life stories of important figures',
                    'sections': ['early_life', 'challenges', 'achievements', 'legacy'],
                    'recommended_styles': ['engaging', 'formal'],
                    'best_audiences': ['middle_school', 'high_school', 'adult']
                },
                'case_study': {
                    'name': 'Case Study Narrative',
                    'description': 'Transform case studies into story format',
                    'sections': ['scenario', 'analysis', 'solutions', 'outcomes'],
                    'recommended_styles': ['conversational', 'engaging'],
                    'best_audiences': ['high_school', 'adult']
                },
                'fictional': {
                    'name': 'Educational Fiction',
                    'description': 'Create fictional stories that teach concepts',
                    'sections': ['world_building', 'adventure', 'lessons', 'resolution'],
                    'recommended_styles': ['engaging', 'dramatic'],
                    'best_audiences': ['elementary', 'middle_school']
                }
            },
            'narrative_styles': {
                'engaging': {
                    'name': 'Engaging Style',
                    'description': 'Active, exciting narrative with vivid descriptions',
                    'features': ['action-oriented', 'descriptive language', 'emotional engagement']
                },
                'formal': {
                    'name': 'Formal Style',
                    'description': 'Professional, structured narrative approach',
                    'features': ['clear structure', 'factual presentation', 'authoritative tone']
                },
                'conversational': {
                    'name': 'Conversational Style',
                    'description': 'Friendly, approachable narrative voice',
                    'features': ['direct address', 'casual language', 'interactive elements']
                },
                'dramatic': {
                    'name': 'Dramatic Style',
                    'description': 'Tension-filled narrative with emotional peaks',
                    'features': ['suspense building', 'conflict focus', 'emotional intensity']
                }
            },
            'audience_levels': {
                'elementary': {
                    'name': 'Elementary Level',
                    'age_range': '6-11 years',
                    'characteristics': ['simple vocabulary', 'short sentences', 'visual concepts']
                },
                'middle_school': {
                    'name': 'Middle School Level',
                    'age_range': '11-14 years',
                    'characteristics': ['moderate complexity', 'relatable scenarios', 'developing themes']
                },
                'high_school': {
                    'name': 'High School Level',
                    'age_range': '14-18 years',
                    'characteristics': ['complex themes', 'analytical elements', 'sophisticated vocabulary']
                },
                'adult': {
                    'name': 'Adult Level',
                    'age_range': '18+ years',
                    'characteristics': ['advanced concepts', 'professional context', 'nuanced themes']
                },
                'general': {
                    'name': 'General Audience',
                    'age_range': 'All ages',
                    'characteristics': ['accessible language', 'universal themes', 'broad appeal']
                }
            }
        }
        
        return jsonify({
            'templates': templates,
            'defaults': {
                'story_type': 'educational',
                'narrative_style': 'engaging',
                'audience_level': 'general',
                'creative_elements': True
            },
            'recommendations': {
                'for_students': {
                    'story_type': 'educational',
                    'narrative_style': 'engaging',
                    'creative_elements': True
                },
                'for_research': {
                    'story_type': 'case_study',
                    'narrative_style': 'conversational',
                    'creative_elements': False
                },
                'for_history': {
                    'story_type': 'historical',
                    'narrative_style': 'dramatic',
                    'creative_elements': True
                }
            }
        })
        
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error getting templates: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve story templates',
            'details': str(e)
        }), 500


@story_creator_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for story creator service."""
    return jsonify({
        'service': 'story_creator',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@story_creator_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@story_creator_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
