from flask import Blueprint, request, jsonify
from app.models.status import Progress
from app.db import db
from app.tasks.report_builder_tasks import generate_report_task
import uuid
from datetime import datetime
import logging

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
report_builder_bp = Blueprint('report_builder', __name__)

@report_builder_bp.route('/start-report-generation', methods=['POST'])
def start_report_generation():
    """
    Start report generation task for uploaded files.
    
    Expected JSON payload:
    {
        "file_ids": ["uuid1", "uuid2", ...],
        "user_id": "user_uuid",  # Optional, will use test user if not provided
        "options": {
            "report_type": "research|business|technical|executive|survey",
            "format_style": "academic|professional|technical|executive",
            "length": "short|medium|comprehensive",
            "include_citations": true|false
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
        report_type = options.get('report_type', 'research')
        format_style = options.get('format_style', 'academic')
        length = options.get('length', 'medium')
        include_citations = options.get('include_citations', True)
        
        # Validate options
        valid_types = ['research', 'business', 'technical', 'executive', 'survey']
        valid_styles = ['academic', 'professional', 'technical', 'executive']
        valid_lengths = ['short', 'medium', 'comprehensive']
        
        if report_type not in valid_types:
            return jsonify({'error': f'report_type must be one of: {valid_types}'}), 400
        if format_style not in valid_styles:
            return jsonify({'error': f'format_style must be one of: {valid_styles}'}), 400
        if length not in valid_lengths:
            return jsonify({'error': f'length must be one of: {valid_lengths}'}), 400
        if not isinstance(include_citations, bool):
            return jsonify({'error': 'include_citations must be a boolean'}), 400
        
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
            task_type='report_generation',
            status='pending',
            progress_percentage=0,
            current_step='Initializing report generation task',
            created_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        
        log.info(f"[ReportBuilderAPI] Created progress record {progress_id} for user {user_id}")
        
        # Queue the Celery task
        task_options = {
            'report_type': report_type,
            'format_style': format_style,
            'length': length,
            'include_citations': include_citations
        }
        
        task = generate_report_task.delay(
            user_id=user_id,
            file_ids=file_ids,
            progress_id=progress_id,
            options=task_options
        )
        
        log.info(f"[ReportBuilderAPI] Queued report generation task {task.id} for progress {progress_id}")
        
        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Report generation task started successfully',
            'options_used': task_options,
            'files_count': len(file_ids)
        }), 202
        
    except Exception as e:
        log.error(f"[ReportBuilderAPI] Error starting report generation: {str(e)}")
        return jsonify({
            'error': 'Failed to start report generation task',
            'details': str(e)
        }), 500


@report_builder_bp.route('/report-generation-results/<progress_id>', methods=['GET'])
def get_report_generation_results(progress_id):
    """
    Get report generation results by progress ID.
    
    Returns:
    - If pending/in_progress: Current progress status
    - If completed: Full report results
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
                if 'consolidated_report' in result:
                    # Multi-file result
                    consolidated = result['consolidated_report']
                    consolidation_summary = consolidated.get('consolidation_summary', {})
                    response_data['summary'] = {
                        'type': 'consolidated_report',
                        'files_processed': result.get('files_processed', 0),
                        'successful_reports': result.get('successful_reports', 0),
                        'total_sections': consolidation_summary.get('total_sections', 0),
                        'estimated_word_count': consolidation_summary.get('estimated_word_count', 0),
                        'report_type': consolidation_summary.get('report_type', 'unknown'),
                        'format_style': consolidation_summary.get('format_style', 'unknown')
                    }
                elif 'report' in result:
                    # Single file result
                    report_data = result['report']
                    if report_data and 'report' in report_data:
                        report_content = report_data['report']
                        sections_summary = report_content.get('sections_summary', {})
                        response_data['summary'] = {
                            'type': 'single_report',
                            'filename': report_data.get('filename', 'unknown'),
                            'word_count': sections_summary.get('word_count_estimate', 0),
                            'total_sections': sections_summary.get('total_sections', 0),
                            'report_type': sections_summary.get('report_type', 'unknown'),
                            'format_style': sections_summary.get('format_style', 'unknown')
                        }
            
        elif progress.status == 'failed':
            response_data['error_message'] = progress.error_message
        
        return jsonify(response_data)
        
    except Exception as e:
        log.error(f"[ReportBuilderAPI] Error getting results for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve report generation results',
            'details': str(e)
        }), 500


@report_builder_bp.route('/report-generation-status/<progress_id>', methods=['GET'])
def get_report_generation_status(progress_id):
    """
    Get brief status information for report generation progress.
    
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
        log.error(f"[ReportBuilderAPI] Error getting status for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve report generation status',
            'details': str(e)
        }), 500


@report_builder_bp.route('/report-generation-history/<user_id>', methods=['GET'])
def get_report_generation_history(user_id):
    """
    Get report generation history for a specific user.
    
    Query parameters:
    - limit: Number of records to return (default: 10, max: 100)
    - offset: Number of records to skip (default: 0)
    - status: Filter by status (pending, in_progress, completed, failed)
    - report_type: Filter by report type (research, business, etc.)
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 10)), 100)
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        report_type_filter = request.args.get('report_type')
        
        # Build query
        query = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.task_type == 'report_generation'
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
                report_metadata = result.get('report_metadata', {})
                record['report_info'] = {
                    'report_type': report_metadata.get('report_type', 'unknown'),
                    'format_style': report_metadata.get('format_style', 'unknown'),
                    'length': report_metadata.get('length', 'unknown')
                }
                
                # Filter by report_type if specified
                if report_type_filter and report_metadata.get('report_type') != report_type_filter:
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
        log.error(f"[ReportBuilderAPI] Error getting history for user {user_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve report generation history',
            'details': str(e)
        }), 500


@report_builder_bp.route('/report-templates', methods=['GET'])
def get_report_templates():
    """
    Get available report templates and their configurations.
    
    Returns information about supported report types, styles, and options.
    """
    try:
        templates = {
            'report_types': {
                'research': {
                    'name': 'Research Report',
                    'description': 'Academic or scientific research analysis',
                    'sections': ['abstract', 'introduction', 'methodology', 'findings', 'conclusions'],
                    'recommended_styles': ['academic', 'professional'],
                    'typical_length': 'medium to comprehensive'
                },
                'business': {
                    'name': 'Business Report',
                    'description': 'Business analysis and strategic insights',
                    'sections': ['executive_summary', 'situation_analysis', 'recommendations'],
                    'recommended_styles': ['professional', 'executive'],
                    'typical_length': 'short to medium'
                },
                'technical': {
                    'name': 'Technical Report',
                    'description': 'Technical analysis and specifications',
                    'sections': ['abstract', 'technical_background', 'analysis', 'results'],
                    'recommended_styles': ['technical', 'professional'],
                    'typical_length': 'medium to comprehensive'
                },
                'executive': {
                    'name': 'Executive Summary',
                    'description': 'High-level overview for leadership',
                    'sections': ['executive_summary', 'key_insights', 'recommendations'],
                    'recommended_styles': ['executive', 'professional'],
                    'typical_length': 'short'
                },
                'survey': {
                    'name': 'Survey Report',
                    'description': 'Analysis of survey or study results',
                    'sections': ['overview', 'key_findings', 'analysis', 'implications'],
                    'recommended_styles': ['professional', 'academic'],
                    'typical_length': 'medium'
                }
            },
            'format_styles': {
                'academic': {
                    'name': 'Academic Style',
                    'description': 'Formal academic formatting with citations',
                    'features': ['APA citations', 'formal language', 'detailed methodology']
                },
                'professional': {
                    'name': 'Professional Style',
                    'description': 'Business-appropriate professional formatting',
                    'features': ['clean layout', 'executive-friendly', 'action-oriented']
                },
                'technical': {
                    'name': 'Technical Style',
                    'description': 'Technical documentation style',
                    'features': ['precise language', 'detailed specifications', 'technical accuracy']
                },
                'executive': {
                    'name': 'Executive Style',
                    'description': 'High-level executive presentation',
                    'features': ['concise format', 'key insights', 'strategic focus']
                }
            },
            'length_options': {
                'short': {
                    'name': 'Short Report',
                    'description': '2-5 pages, key insights only',
                    'word_count': '500-1500 words'
                },
                'medium': {
                    'name': 'Medium Report',
                    'description': '5-15 pages, comprehensive analysis',
                    'word_count': '1500-4000 words'
                },
                'comprehensive': {
                    'name': 'Comprehensive Report',
                    'description': '15+ pages, detailed with appendices',
                    'word_count': '4000+ words'
                }
            }
        }
        
        return jsonify({
            'templates': templates,
            'defaults': {
                'report_type': 'research',
                'format_style': 'academic',
                'length': 'medium',
                'include_citations': True
            }
        })
        
    except Exception as e:
        log.error(f"[ReportBuilderAPI] Error getting templates: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve report templates',
            'details': str(e)
        }), 500


@report_builder_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for report builder service."""
    return jsonify({
        'service': 'report_builder',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@report_builder_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@report_builder_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
