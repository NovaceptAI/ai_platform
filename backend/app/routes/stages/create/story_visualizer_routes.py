from flask import Blueprint, request, jsonify
from app.models.status import Progress
from app.db import db
from app.tasks.story_visualizer_tasks import create_visualizer_task
import uuid
from datetime import datetime
import logging

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
story_visualizer_bp = Blueprint('story_visualizer', __name__)

@story_visualizer_bp.route('/start', methods=['POST'])
def start_story_visualization():
    """
    Start document visualization task for uploaded files.

    This endpoint analyzes document content and generates visual representations
    (diagrams, illustrations, infographics) of the actual content.

    Expected JSON payload:
    {
        "file_ids": ["uuid1", "uuid2", ...],
        "user_id": "user_uuid",  # Optional, will use test user if not provided
        "options": {
            "audience_level": "elementary|middle_school|high_school|adult|general"
        },
        "num_scenes": 5,  # Number of visualizations to generate
        "style": "vivid|natural",  # Image style
        "generate_images": true  # Whether to generate images
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
        audience_level = options.get('audience_level', 'general')

        # Image generation options
        num_scenes = data.get('num_scenes', 5)
        image_style = data.get('style', 'vivid')  # 'vivid' or 'natural'
        generate_images = data.get('generate_images', True)

        # Validate options
        valid_levels = ['elementary', 'middle_school', 'high_school', 'adult', 'general']
        valid_image_styles = ['vivid', 'natural']

        if audience_level not in valid_levels:
            return jsonify({'error': f'audience_level must be one of: {valid_levels}'}), 400
        if image_style not in valid_image_styles:
            return jsonify({'error': f'style must be one of: {valid_image_styles}'}), 400
        
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
        
        # Set file_id if only one file is being processed
        file_id_for_progress = file_ids[0] if len(file_ids) == 1 else None
        
        progress = Progress(
            id=progress_id,
            user_id=user_id,
            file_id=file_id_for_progress,
            tool='story_visualizer',
            status='pending',
            percentage=0,
            created_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        
        log.info(f"[DocumentVisualizerAPI] Created progress record {progress_id} for user {user_id}")

        # Queue the Celery task
        task_options = {
            'audience_level': audience_level,
            'num_scenes': num_scenes,
            'image_style': image_style,
            'generate_images': generate_images
        }

        task = create_visualizer_task.delay(
            user_id=user_id,
            file_ids=file_ids,
            progress_id=progress_id,
            options=task_options
        )

        log.info(f"[DocumentVisualizerAPI] Queued visualization task {task.id} for progress {progress_id}")

        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Document visualization task started successfully',
            'options_used': task_options,
            'files_count': len(file_ids)
        }), 202

    except Exception as e:
        log.error(f"[DocumentVisualizerAPI] Error starting visualization: {str(e)}")
        return jsonify({
            'error': 'Failed to start document visualization task',
            'details': str(e)
        }), 500


@story_visualizer_bp.route('/results', methods=['GET'])
def get_story_visualization_results():
    """
    Get story visualization results by progress ID or file ID.

    Query parameters:
    - progress_id: UUID of the progress record
    - file_id: UUID of the file (will get latest completed progress)
    
    Returns:
    - If pending/in_progress: Current progress status
    - If completed: Full story results
    - If failed: Error information
    """
    try:
        progress_id = request.args.get('progress_id')
        file_id = request.args.get('file_id')
        
        if not progress_id and not file_id:
            return jsonify({'error': 'Either progress_id or file_id is required'}), 400
        
        # Get progress record
        if progress_id:
            progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
        else:
            # Get the latest progress for this file (any status)
            # First try to find a completed one, otherwise get the latest
            progress = db.session.query(Progress).filter(
                Progress.file_id == file_id,
                Progress.tool == 'story_visualizer',
                Progress.status == 'completed'
            ).order_by(Progress.created_at.desc()).first()
            
            # If no completed progress found, get the latest one (any status)
            if not progress:
                progress = db.session.query(Progress).filter(
                    Progress.file_id == file_id,
                    Progress.tool == 'story_visualizer'
                ).order_by(Progress.created_at.desc()).first()
        
        if not progress:
            return jsonify({'error': 'No results found'}), 404
        
        # Return different responses based on status
        if progress.status == 'pending' or progress.status == 'in_progress':
            return jsonify({
                'progress_id': str(progress.id),
                'status': progress.status,
                'percentage': progress.percentage or 0,
                'message': 'Story creation is still in progress',
                'tool': progress.tool,
                'user_id': progress.user_id,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
            }), 202
        
        elif progress.status == 'failed':
            return jsonify({
                'progress_id': str(progress.id),
                'status': 'failed',
                'error': progress.error_message or 'Story creation failed',
                'tool': progress.tool,
                'user_id': progress.user_id,
                'percentage': progress.percentage or 0,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
            }), 500
        
        elif progress.status == 'completed':
            result_data = progress.result_data or {}
            
            # Extract story data
            story_content = None
            story_metadata = result_data.get('story_metadata', {})
            
            # Check if single or consolidated story
            if 'consolidated_story' in result_data:
                story_content = result_data['consolidated_story']
                individual_stories = result_data.get('individual_stories', [])
                files_processed = result_data.get('files_processed', 0)
                
                return jsonify({
                    'progress_id': str(progress.id),
                    'status': progress.status,
                    'story_type': 'consolidated',
                    'story_content': story_content,
                    'individual_stories': individual_stories,
                    'files_processed': files_processed,
                    'metadata': story_metadata,
                    'tool': progress.tool,
                    'user_id': progress.user_id,
                    'percentage': progress.percentage or 100,
                    'created_at': progress.created_at.isoformat() if progress.created_at else None,
                    'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                    'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
                })
            
            elif 'story' in result_data:
                story_data = result_data['story']
                
                # Check if the story has an error
                if 'error' in story_data:
                    return jsonify({
                        'progress_id': str(progress.id),
                        'status': 'failed',
                        'error': f"Story creation error: {story_data.get('error')}",
                        'file_id': str(story_data.get('file_id')) if story_data.get('file_id') else None,
                        'tool': progress.tool,
                        'user_id': progress.user_id,
                        'percentage': progress.percentage or 0,
                        'created_at': progress.created_at.isoformat() if progress.created_at else None,
                        'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                        'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
                    }), 500
                
                # Extract scene images if available
                scene_images = result_data.get('scene_images', [])
                
                return jsonify({
                    'progress_id': str(progress.id),
                    'status': progress.status,
                    'story_type': 'single',
                    'file_id': str(story_data.get('file_id')) if story_data.get('file_id') else None,
                    'filename': story_data.get('filename'),
                    'story_content': story_data.get('story', {}).get('story_content', {}),
                    'story_structure': story_data.get('story', {}).get('story_structure', {}),
                    'storytelling_guidelines': story_data.get('story', {}).get('storytelling_guidelines', {}),
                    'story_summary': story_data.get('story', {}).get('story_summary', {}),
                    'scene_images': scene_images,
                    'metadata': story_metadata,
                    'tool': progress.tool,
                    'user_id': progress.user_id,
                    'percentage': progress.percentage or 100,
                    'created_at': progress.created_at.isoformat() if progress.created_at else None,
                    'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                    'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
                })
            
            else:
                # Fallback for unexpected result structure
                return jsonify({
                    'progress_id': str(progress.id),
                    'status': progress.status,
                    'result': result_data,
                    'tool': progress.tool,
                    'user_id': progress.user_id,
                    'percentage': progress.percentage or 100,
                    'created_at': progress.created_at.isoformat() if progress.created_at else None,
                    'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                    'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
                })
        
        else:
            return jsonify({
                'progress_id': str(progress.id),
                'status': progress.status,
                'percentage': progress.percentage or 0,
                'tool': progress.tool,
                'user_id': progress.user_id,
                'message': f'Unknown status: {progress.status}',
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
            }), 400
            
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error getting results: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve story visualization results',
            'details': str(e)
        }), 500


@story_visualizer_bp.route('/progress/<uuid:progress_id>', methods=['GET'])
def get_story_creation_status(progress_id):
    """
    Get brief status information for story creation progress.
    
    Returns only status, percentage, and current step - lighter weight than full results.
    """
    try:
        progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
        
        if not progress:
            return jsonify({'error': 'Progress record not found'}), 404
        
        response = {
            'progress_id': str(progress.id),
            'status': progress.status,
            'percentage': progress.percentage or 0,
            'tool': progress.tool,
            'user_id': progress.user_id,
            'created_at': progress.created_at.isoformat() if progress.created_at else None,
            'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
        }
        
        # Add file_id if present
        if progress.file_id:
            response['file_id'] = str(progress.file_id)
        
        # Add completion timestamp if completed
        if progress.completed_at:
            response['completed_at'] = progress.completed_at.isoformat()
        
        # Add error message if failed
        if progress.status == 'failed' and progress.error_message:
            response['error_message'] = progress.error_message
        
        return jsonify(response)
        
    except Exception as e:
        log.error(f"[StoryCreatorAPI] Error getting status for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve story creation status',
            'details': str(e)
        }), 500


@story_visualizer_bp.route('/story-creation-history/<user_id>', methods=['GET'])
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
            Progress.tool == 'story_visualizer'
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
                'percentage': progress.percentage,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
            }
            
            # Add summary for completed tasks
            if progress.status == 'completed' and progress.result_data:
                result = progress.result_data
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


@story_visualizer_bp.route('/story-templates', methods=['GET'])
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


@story_visualizer_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for story visualizer service."""
    return jsonify({
        'service': 'story_visualizer',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@story_visualizer_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@story_visualizer_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
