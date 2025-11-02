from flask import Blueprint, request, jsonify
from app.models.status import Progress
from app.db import db
from app.tasks.infographic_creator_tasks import generate_infographic_task
import uuid
from datetime import datetime
import logging

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
infographic_creator_bp = Blueprint('infographic_creator', __name__)

@infographic_creator_bp.route('/start-infographic-creation', methods=['POST'])
def start_infographic_creation():
    """
    Start infographic creation task for uploaded files.
    
    Expected JSON payload:
    {
        "file_ids": ["uuid1", "uuid2", ...],
        "user_id": "user_uuid",  # Optional, will use test user if not provided
        "options": {
            "infographic_type": "educational|business|research|marketing",
            "layout": "vertical|horizontal|grid|timeline",
            "color_scheme": "professional|vibrant|minimal|academic",
            "complexity_level": "simple|medium|advanced"
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
        infographic_type = options.get('infographic_type', 'educational')
        layout = options.get('layout', 'vertical')
        color_scheme = options.get('color_scheme', 'professional')
        complexity_level = options.get('complexity_level', 'medium')
        
        # Validate options
        valid_types = ['educational', 'business', 'research', 'marketing']
        valid_layouts = ['vertical', 'horizontal', 'grid', 'timeline']
        valid_schemes = ['professional', 'vibrant', 'minimal', 'academic']
        valid_levels = ['simple', 'medium', 'advanced']
        
        if infographic_type not in valid_types:
            return jsonify({'error': f'infographic_type must be one of: {valid_types}'}), 400
        if layout not in valid_layouts:
            return jsonify({'error': f'layout must be one of: {valid_layouts}'}), 400
        if color_scheme not in valid_schemes:
            return jsonify({'error': f'color_scheme must be one of: {valid_schemes}'}), 400
        if complexity_level not in valid_levels:
            return jsonify({'error': f'complexity_level must be one of: {valid_levels}'}), 400
        
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
            task_type='infographic_creation',
            status='pending',
            progress_percentage=0,
            current_step='Initializing infographic creation task',
            created_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        
        log.info(f"[InfographicCreatorAPI] Created progress record {progress_id} for user {user_id}")
        
        # Queue the Celery task
        task_options = {
            'infographic_type': infographic_type,
            'layout': layout,
            'color_scheme': color_scheme,
            'complexity_level': complexity_level
        }
        
        task = generate_infographic_task.delay(
            user_id=user_id,
            file_ids=file_ids,
            progress_id=progress_id,
            options=task_options
        )
        
        log.info(f"[InfographicCreatorAPI] Queued infographic creation task {task.id} for progress {progress_id}")
        
        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Infographic creation task started successfully',
            'options_used': task_options,
            'files_count': len(file_ids)
        }), 202
        
    except Exception as e:
        log.error(f"[InfographicCreatorAPI] Error starting infographic creation: {str(e)}")
        return jsonify({
            'error': 'Failed to start infographic creation task',
            'details': str(e)
        }), 500


@infographic_creator_bp.route('/infographic-creation-results/<progress_id>', methods=['GET'])
def get_infographic_creation_results(progress_id):
    """
    Get infographic creation results by progress ID.
    
    Returns:
    - If pending/in_progress: Current progress status
    - If completed: Full infographic design results
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
                if 'consolidated_infographic' in result:
                    # Multi-file result
                    consolidated = result['consolidated_infographic']
                    response_data['summary'] = {
                        'type': 'consolidated_infographic',
                        'files_processed': result.get('files_processed', 0),
                        'successful_designs': result.get('successful_designs', 0),
                        'total_sections': len(consolidated.get('sections', [])),
                        'has_data_visualizations': bool(consolidated.get('data_visualizations')),
                        'key_points_count': len(consolidated.get('key_points_layout', {}).get('points', [])),
                        'layout_type': consolidated.get('layout_specification', {}).get('type', 'unknown')
                    }
                elif 'infographic_design' in result:
                    # Single file result
                    design = result['infographic_design']
                    if design and 'design' in design:
                        infographic = design['design']
                        response_data['summary'] = {
                            'type': 'single_infographic',
                            'filename': design.get('filename', 'unknown'),
                            'total_sections': len(infographic.get('sections', [])),
                            'has_data_visualizations': bool(infographic.get('data_visualizations')),
                            'key_points_count': len(infographic.get('key_points_layout', {}).get('points', [])),
                            'layout_type': infographic.get('layout_specification', {}).get('type', 'unknown')
                        }
            
        elif progress.status == 'failed':
            response_data['error_message'] = progress.error_message
        
        return jsonify(response_data)
        
    except Exception as e:
        log.error(f"[InfographicCreatorAPI] Error getting results for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve infographic creation results',
            'details': str(e)
        }), 500


@infographic_creator_bp.route('/infographic-creation-status/<progress_id>', methods=['GET'])
def get_infographic_creation_status(progress_id):
    """
    Get brief status information for infographic creation progress.
    
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
        log.error(f"[InfographicCreatorAPI] Error getting status for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve infographic creation status',
            'details': str(e)
        }), 500


@infographic_creator_bp.route('/infographic-creation-history/<user_id>', methods=['GET'])
def get_infographic_creation_history(user_id):
    """
    Get infographic creation history for a specific user.
    
    Query parameters:
    - limit: Number of records to return (default: 10, max: 100)
    - offset: Number of records to skip (default: 0)
    - status: Filter by status (pending, in_progress, completed, failed)
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 10)), 100)
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        
        # Build query
        query = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.task_type == 'infographic_creation'
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
                if 'consolidated_infographic' in result:
                    record['summary'] = {
                        'type': 'consolidated',
                        'files_processed': result.get('files_processed', 0)
                    }
                elif 'infographic_design' in result:
                    design = result['infographic_design']
                    record['summary'] = {
                        'type': 'single',
                        'filename': design.get('filename', 'unknown') if design else 'unknown'
                    }
            
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
        log.error(f"[InfographicCreatorAPI] Error getting history for user {user_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve infographic creation history',
            'details': str(e)
        }), 500


@infographic_creator_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for infographic creator service."""
    return jsonify({
        'service': 'infographic_creator',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@infographic_creator_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@infographic_creator_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
