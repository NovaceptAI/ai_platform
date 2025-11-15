"""
Digital Debate Platform API Routes

RESTful endpoints for AI-assisted real-time debates.
Supports debate creation, participation, real-time messaging, and AI analysis.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.debates import Debate, DebateParticipant, DebateMessage, DebateAnalytics
from app.db import db
from app.services.stages.collaborate.debate_service import DebateService
from app.services.debate_websocket_service import send_debate_update
from datetime import datetime
import uuid
import logging

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
debate_bp = Blueprint('debate', __name__)


# ==================== Service Info ====================

@debate_bp.route('/info', methods=['GET'])
@jwt_required()
def get_service_info():
    """Get debate service information and capabilities."""
    try:
        service = DebateService()
        info = service.get_service_info()

        return jsonify({
            'success': True,
            'service_info': info
        }), 200

    except Exception as e:
        log.error(f"Error getting service info: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debate_bp.route('/formats', methods=['GET'])
def get_debate_formats():
    """Get available debate formats."""
    try:
        formats = [
            {
                'id': 'parliamentary',
                'name': 'Parliamentary Debate',
                'description': 'Structured format with opening, rebuttal, and closing rounds',
                'participants': 4,
                'rounds': 3,
                'time_per_speech': 300
            },
            {
                'id': 'lincoln_douglas',
                'name': 'Lincoln-Douglas',
                'description': '1v1 value debate focusing on philosophical questions',
                'participants': 2,
                'rounds': 4,
                'time_per_speech': 360
            },
            {
                'id': 'public_forum',
                'name': 'Public Forum',
                'description': 'Team-based accessible format for current events',
                'participants': 4,
                'rounds': 4,
                'time_per_speech': 240
            },
            {
                'id': 'free_form',
                'name': 'Free Form Discussion',
                'description': 'Unstructured collaborative discussion',
                'participants': None,
                'rounds': None,
                'time_per_speech': None
            }
        ]

        return jsonify({
            'success': True,
            'formats': formats
        }), 200

    except Exception as e:
        log.error(f"Error getting formats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debate_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get suggested debate categories."""
    try:
        categories = [
            {'id': 'politics', 'name': 'Politics & Policy', 'icon': '🏛️'},
            {'id': 'science', 'name': 'Science & Technology', 'icon': '🔬'},
            {'id': 'philosophy', 'name': 'Philosophy & Ethics', 'icon': '🤔'},
            {'id': 'education', 'name': 'Education', 'icon': '📚'},
            {'id': 'environment', 'name': 'Environment', 'icon': '🌍'},
            {'id': 'economics', 'name': 'Economics', 'icon': '💰'},
            {'id': 'social', 'name': 'Social Issues', 'icon': '👥'},
            {'id': 'health', 'name': 'Health & Medicine', 'icon': '🏥'},
        ]

        return jsonify({
            'success': True,
            'categories': categories
        }), 200

    except Exception as e:
        log.error(f"Error getting categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== Debate Management ====================

@debate_bp.route('/create', methods=['POST'])
@jwt_required()
def create_debate():
    """
    Create a new debate.

    Request body:
    {
        "motion": "This house believes...",
        "description": "Additional context",
        "category": "politics",
        "format": "parliamentary",
        "settings": {
            "allow_audience": true,
            "enable_voice": false,
            "enable_video": false,
            "auto_fact_check": true,
            "ai_moderation": true,
            "public_debate": false
        },
        "scheduled_start": "2025-01-15T10:00:00Z"
    }

    Returns:
        Debate ID and session info
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Validate required fields
        motion = data.get('motion', '').strip()
        if not motion:
            return jsonify({'error': 'motion is required'}), 400

        if len(motion) < 10:
            return jsonify({'error': 'motion must be at least 10 characters'}), 400

        # Get format with default
        debate_format = data.get('format', 'parliamentary')
        valid_formats = ['parliamentary', 'lincoln_douglas', 'public_forum', 'free_form']
        if debate_format not in valid_formats:
            return jsonify({'error': f'format must be one of: {valid_formats}'}), 400

        # Create debate
        debate_id = uuid.uuid4()
        session_id = f"debate_{debate_id.hex[:16]}"

        default_settings = {
            'allow_audience': data.get('settings', {}).get('allow_audience', True),
            'enable_voice': data.get('settings', {}).get('enable_voice', False),
            'enable_video': data.get('settings', {}).get('enable_video', False),
            'auto_fact_check': data.get('settings', {}).get('auto_fact_check', True),
            'ai_moderation': data.get('settings', {}).get('ai_moderation', True),
            'argument_analysis': data.get('settings', {}).get('argument_analysis', True),
            'enable_voting': data.get('settings', {}).get('enable_voting', True),
            'public_debate': data.get('settings', {}).get('public_debate', False),
            'agora_enabled': False
        }

        debate = Debate(
            id=debate_id,
            creator_id=user_id,
            motion=motion,
            description=data.get('description', ''),
            category=data.get('category', 'general'),
            tags=data.get('tags', []),
            format=debate_format,
            max_participants=data.get('max_participants', 4),
            time_limit_per_speech=data.get('time_limit_per_speech', 300),
            total_rounds=data.get('total_rounds', 3),
            settings=default_settings,
            status='created',
            session_id=session_id,
            scheduled_start=datetime.fromisoformat(data['scheduled_start'].replace('Z', '+00:00')) if data.get('scheduled_start') else None
        )

        db.session.add(debate)

        # Add creator as first participant (moderator or first debater)
        creator_role = data.get('creator_role', 'proposition')
        participant = DebateParticipant(
            id=uuid.uuid4(),
            debate_id=debate_id,
            user_id=user_id,
            role=creator_role,
            display_name=data.get('display_name', 'User'),
            is_active=True
        )

        db.session.add(participant)
        db.session.commit()

        log.info(f"[DebateAPI] Created debate {debate_id} by user {user_id}")

        return jsonify({
            'success': True,
            'debate_id': str(debate_id),
            'session_id': session_id,
            'status': 'created',
            'debate': debate.to_dict(include_participants=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error creating debate: {str(e)}")
        return jsonify({
            'error': 'Failed to create debate',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>', methods=['GET'])
@jwt_required()
def get_debate(debate_id):
    """
    Get debate details by ID.

    Returns:
        Complete debate data with participants and settings
    """
    try:
        user_id = get_jwt_identity()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        # Check if user has access
        is_participant = any(p.user_id == user_id for p in debate.participants)
        is_creator = debate.creator_id == user_id
        is_public = debate.settings.get('public_debate', False)

        if not (is_participant or is_creator or is_public):
            return jsonify({'error': 'Access denied'}), 403

        return jsonify({
            'success': True,
            'debate': debate.to_dict(include_participants=True)
        }), 200

    except Exception as e:
        log.error(f"[DebateAPI] Error getting debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve debate',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>', methods=['DELETE'])
@jwt_required()
def delete_debate(debate_id):
    """
    Delete a debate (only allowed in 'created' status by creator).

    Returns:
        Success message
    """
    try:
        user_id = get_jwt_identity()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        # Only creator can delete
        if debate.creator_id != user_id:
            return jsonify({'error': 'Only the creator can delete this debate'}), 403

        # Only allow deletion if status is 'created' (no one has joined yet)
        if debate.status != 'created':
            return jsonify({'error': 'Cannot delete debate after participants have joined or debate has started'}), 400

        # Delete the debate (CASCADE will delete participants, messages, analytics)
        db.session.delete(debate)
        db.session.commit()

        log.info(f"Debate {debate_id} deleted by user {user_id}")

        return jsonify({
            'success': True,
            'message': 'Debate deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error deleting debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to delete debate',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>/join', methods=['POST'])
@jwt_required()
def join_debate(debate_id):
    """
    Join an existing debate.

    Request body:
    {
        "role": "proposition|opposition|audience",
        "display_name": "John Doe"
    }

    Returns:
        Participant info and debate details
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        if debate.status not in ['created', 'waiting', 'ready']:
            return jsonify({'error': 'Debate is not accepting new participants'}), 400

        # Check if already joined
        existing_participant = DebateParticipant.query.filter_by(
            debate_id=debate_id,
            user_id=user_id
        ).first()

        if existing_participant:
            return jsonify({
                'success': True,
                'already_joined': True,
                'participant': existing_participant.to_dict(),
                'debate': debate.to_dict(include_participants=True)
            }), 200

        # Validate role
        role = data.get('role', 'audience')
        valid_roles = ['proposition', 'opposition', 'moderator', 'audience']
        if role not in valid_roles:
            return jsonify({'error': f'role must be one of: {valid_roles}'}), 400

        # Check participant limits
        if role != 'audience':
            current_count = DebateParticipant.query.filter_by(
                debate_id=debate_id,
                role=role
            ).count()

            max_per_role = debate.max_participants // 2  # Split between proposition and opposition
            if current_count >= max_per_role:
                return jsonify({'error': f'Role {role} is full'}), 400

        # Create participant
        participant = DebateParticipant(
            id=uuid.uuid4(),
            debate_id=debate_id,
            user_id=user_id,
            role=role,
            display_name=data.get('display_name', 'Anonymous'),
            avatar_url=data.get('avatar_url'),
            bio=data.get('bio'),
            is_active=True
        )

        db.session.add(participant)

        # Update debate status if needed
        total_active_debaters = DebateParticipant.query.filter(
            DebateParticipant.debate_id == debate_id,
            DebateParticipant.role.in_(['proposition', 'opposition'])
        ).count()

        if total_active_debaters + 1 >= debate.max_participants and debate.status == 'created':
            debate.status = 'ready'

        db.session.commit()

        log.info(f"[DebateAPI] User {user_id} joined debate {debate_id} as {role}")

        return jsonify({
            'success': True,
            'participant': participant.to_dict(),
            'debate': debate.to_dict(include_participants=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error joining debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to join debate',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>/start', methods=['POST'])
@jwt_required()
def start_debate(debate_id):
    """
    Start the debate (creator/moderator only).

    Returns:
        Updated debate status
    """
    try:
        user_id = get_jwt_identity()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        # Check permissions
        if debate.creator_id != user_id:
            participant = DebateParticipant.query.filter_by(
                debate_id=debate_id,
                user_id=user_id,
                role='moderator'
            ).first()

            if not participant:
                return jsonify({'error': 'Only creator or moderator can start debate'}), 403

        if debate.status not in ['created', 'ready']:
            return jsonify({'error': 'Debate cannot be started from current status'}), 400

        # Start debate
        debate.status = 'in_progress'
        debate.actual_start = datetime.utcnow()
        debate.current_round = 1

        db.session.commit()

        log.info(f"[DebateAPI] Debate {debate_id} started by user {user_id}")

        # Broadcast to all participants via WebSocket
        send_debate_update(str(debate_id), {
            'type': 'debate_started',
            'debate': debate.to_dict(include_participants=True),
            'timestamp': datetime.utcnow().isoformat()
        })

        return jsonify({
            'success': True,
            'debate': debate.to_dict(include_participants=True),
            'message': 'Debate started successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error starting debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to start debate',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>/end', methods=['POST'])
@jwt_required()
def end_debate(debate_id):
    """
    End the debate and generate final summary.

    Returns:
        Final debate results and AI summary
    """
    try:
        user_id = get_jwt_identity()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        # Check permissions
        if debate.creator_id != user_id:
            participant = DebateParticipant.query.filter_by(
                debate_id=debate_id,
                user_id=user_id,
                role='moderator'
            ).first()

            if not participant:
                return jsonify({'error': 'Only creator or moderator can end debate'}), 403

        if debate.status != 'in_progress':
            return jsonify({'error': 'Debate is not in progress'}), 400

        # Get all messages for summary
        messages = DebateMessage.query.filter_by(debate_id=debate_id).all()
        messages_data = [m.to_dict() for m in messages]

        # Generate AI summary
        service = DebateService()
        summary_result = service.generate_debate_summary(
            debate_data=debate.to_dict(),
            all_messages=messages_data
        )

        # Update debate
        debate.status = 'completed'
        debate.actual_end = datetime.utcnow()

        if summary_result.get('success'):
            debate.ai_summary = summary_result.get('summary', {})
            debate.results = {
                'winner': summary_result.get('summary', {}).get('winner'),
                'statistics': summary_result.get('summary', {}).get('statistics', {})
            }

        db.session.commit()

        log.info(f"[DebateAPI] Debate {debate_id} ended by user {user_id}")

        return jsonify({
            'success': True,
            'debate': debate.to_dict(include_participants=True),
            'summary': debate.ai_summary
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error ending debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to end debate',
            'details': str(e)
        }), 500


# ==================== Messages ====================

@debate_bp.route('/<uuid:debate_id>/messages', methods=['GET'])
@jwt_required()
def get_debate_messages(debate_id):
    """
    Get messages for a debate.

    Query parameters:
    - round: Filter by round number
    - type: Filter by message type
    - limit: Number of messages (default 100)

    Returns:
        List of messages with AI analysis
    """
    try:
        user_id = get_jwt_identity()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        # Check access
        is_participant = any(p.user_id == user_id for p in debate.participants)
        is_public = debate.settings.get('public_debate', False)

        if not (is_participant or is_public):
            return jsonify({'error': 'Access denied'}), 403

        # Get filters
        round_number = request.args.get('round', type=int)
        message_type = request.args.get('type')
        limit = min(request.args.get('limit', 100, type=int), 500)

        messages = DebateMessage.get_debate_messages(
            debate_id=debate_id,
            message_type=message_type,
            round_number=round_number,
            limit=limit
        )

        return jsonify({
            'success': True,
            'messages': [m.to_dict() for m in messages],
            'total': len(messages)
        }), 200

    except Exception as e:
        log.error(f"[DebateAPI] Error getting messages for debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve messages',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>/messages', methods=['POST'])
@jwt_required()
def post_message(debate_id):
    """
    Post a message/argument to the debate.

    Request body:
    {
        "message_type": "argument|rebuttal|opening|closing|chat",
        "content": "Message content",
        "reply_to_message_id": "uuid" (optional),
        "sources": [{"title": "...", "url": "..."}] (optional)
    }

    Returns:
        Posted message with AI analysis
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        # Check if user is participant
        participant = DebateParticipant.query.filter_by(
            debate_id=debate_id,
            user_id=user_id
        ).first()

        if not participant:
            return jsonify({'error': 'You are not a participant in this debate'}), 403

        # Validate content
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'content is required'}), 400

        message_type = data.get('message_type', 'chat')
        valid_types = ['opening', 'argument', 'rebuttal', 'closing', 'chat', 'system']
        if message_type not in valid_types:
            return jsonify({'error': f'message_type must be one of: {valid_types}'}), 400

        # Create message
        message = DebateMessage(
            id=uuid.uuid4(),
            debate_id=debate_id,
            participant_id=participant.id,
            message_type=message_type,
            content=content,
            round_number=debate.current_round,
            reply_to_message_id=data.get('reply_to_message_id'),
            sources=data.get('sources', []),
            attachments=data.get('attachments', [])
        )

        # Perform AI analysis if enabled
        if debate.settings.get('argument_analysis') and message_type in ['argument', 'rebuttal', 'opening', 'closing']:
            service = DebateService()

            # Get previous messages for context
            previous_messages = DebateMessage.query.filter_by(debate_id=debate_id).order_by(DebateMessage.created_at.desc()).limit(5).all()
            previous_data = [{'role': p.participant.role, 'content': p.content} for p in previous_messages]

            analysis_result = service.analyze_argument(
                argument_text=content,
                debate_context={
                    'motion': debate.motion,
                    'format': debate.format,
                    'role': participant.role
                },
                previous_arguments=previous_data
            )

            if analysis_result.get('success'):
                message.ai_analysis = analysis_result.get('analysis', {})

        db.session.add(message)

        # Update participant stats
        participant.messages_count += 1
        if message_type in ['argument', 'rebuttal']:
            if message_type == 'argument':
                participant.arguments_count += 1
            else:
                participant.rebuttals_count += 1

        db.session.commit()

        log.info(f"[DebateAPI] Message posted to debate {debate_id} by user {user_id}")

        return jsonify({
            'success': True,
            'message': message.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error posting message to debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to post message',
            'details': str(e)
        }), 500


# ==================== AI Features ====================

@debate_bp.route('/<uuid:debate_id>/fact-check', methods=['POST'])
@jwt_required()
def fact_check_claims(debate_id):
    """
    Fact-check claims in a message.

    Request body:
    {
        "claims": ["Claim 1", "Claim 2"],
        "context": "Additional context"
    }

    Returns:
        Fact-check results for each claim
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        if not debate.settings.get('auto_fact_check', True):
            return jsonify({'error': 'Fact-checking is disabled for this debate'}), 400

        claims = data.get('claims', [])
        if not claims:
            return jsonify({'error': 'claims array is required'}), 400

        service = DebateService()
        result = service.fact_check_claims(
            claims=claims,
            context=data.get('context', debate.motion)
        )

        return jsonify(result), 200 if result.get('success') else 500

    except Exception as e:
        log.error(f"[DebateAPI] Error fact-checking in debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to fact-check claims',
            'details': str(e)
        }), 500


@debate_bp.route('/<uuid:debate_id>/suggest-counter', methods=['POST'])
@jwt_required()
def suggest_counter_arguments(debate_id):
    """
    Get counter-argument suggestions (educational feature).

    Request body:
    {
        "message_id": "uuid"
    }

    Returns:
        Suggested counter-arguments
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        debate = Debate.query.filter_by(id=debate_id).first()

        if not debate:
            return jsonify({'error': 'Debate not found'}), 404

        message_id = data.get('message_id')
        if not message_id:
            return jsonify({'error': 'message_id is required'}), 400

        message = DebateMessage.query.filter_by(id=message_id, debate_id=debate_id).first()

        if not message:
            return jsonify({'error': 'Message not found'}), 404

        service = DebateService()
        result = service.suggest_counter_arguments(
            original_argument=message.content,
            debate_context={
                'motion': debate.motion,
                'format': debate.format
            }
        )

        return jsonify(result), 200 if result.get('success') else 500

    except Exception as e:
        log.error(f"[DebateAPI] Error suggesting counters in debate {debate_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to generate counter-arguments',
            'details': str(e)
        }), 500


# ==================== Analytics ====================

@debate_bp.route('/<uuid:debate_id>/analytics/<uuid:participant_id>', methods=['GET'])
@jwt_required()
def get_participant_analytics(debate_id, participant_id):
    """
    Get analytics for a specific participant.

    Returns:
        Comprehensive performance metrics
    """
    try:
        user_id = get_jwt_identity()

        # Check access
        participant = DebateParticipant.query.filter_by(id=participant_id, debate_id=debate_id).first()

        if not participant:
            return jsonify({'error': 'Participant not found'}), 404

        # Only the participant themselves or debate creator can view
        debate = Debate.query.filter_by(id=debate_id).first()
        if user_id != participant.user_id and user_id != debate.creator_id:
            return jsonify({'error': 'Access denied'}), 403

        # Check if analytics already exist
        analytics = DebateAnalytics.query.filter_by(
            debate_id=debate_id,
            participant_id=participant_id
        ).first()

        if analytics:
            return jsonify({
                'success': True,
                'analytics': analytics.to_dict()
            }), 200

        # Generate analytics if debate is completed
        if debate.status != 'completed':
            return jsonify({
                'success': False,
                'error': 'Analytics only available after debate completion'
            }), 400

        # Get participant messages
        messages = DebateMessage.query.filter_by(participant_id=participant_id).all()
        messages_data = [m.to_dict() for m in messages]

        # Calculate performance metrics
        service = DebateService()
        metrics_result = service.calculate_performance_metrics(
            participant_messages=messages_data,
            debate_context={
                'motion': debate.motion,
                'format': debate.format,
                'role': participant.role
            }
        )

        if not metrics_result.get('success'):
            return jsonify(metrics_result), 500

        # Create analytics record
        analytics = DebateAnalytics(
            id=uuid.uuid4(),
            debate_id=debate_id,
            participant_id=participant_id,
            metrics=metrics_result.get('metrics', {})
        )

        db.session.add(analytics)
        db.session.commit()

        return jsonify({
            'success': True,
            'analytics': analytics.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[DebateAPI] Error getting analytics: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve analytics',
            'details': str(e)
        }), 500


# ==================== Gallery & Discovery ====================

@debate_bp.route('/my-debates', methods=['GET'])
@jwt_required()
def get_my_debates():
    """
    Get user's debates.

    Query parameters:
    - status: Filter by status (optional)
    - limit: Number of results (default 50)
    - offset: Pagination offset

    Returns:
        List of debates where user is creator or participant
    """
    try:
        user_id = get_jwt_identity()

        status = request.args.get('status')
        limit = min(request.args.get('limit', 50, type=int), 100)
        offset = request.args.get('offset', 0, type=int)

        debates = Debate.get_user_debates(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'success': True,
            'debates': [d.to_dict(include_participants=True) for d in debates],
            'total': len(debates)
        }), 200

    except Exception as e:
        log.error(f"[DebateAPI] Error getting user debates: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve debates',
            'details': str(e)
        }), 500


@debate_bp.route('/public', methods=['GET'])
def get_public_debates():
    """
    Get public debates for discovery.

    Query parameters:
    - category: Filter by category (optional)
    - limit: Number of results (default 20)
    - offset: Pagination offset

    Returns:
        List of public debates
    """
    try:
        category = request.args.get('category')
        limit = min(request.args.get('limit', 20, type=int), 50)
        offset = request.args.get('offset', 0, type=int)

        debates = Debate.get_public_debates(
            category=category,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'success': True,
            'debates': [d.to_dict(include_participants=False) for d in debates],
            'total': len(debates)
        }), 200

    except Exception as e:
        log.error(f"[DebateAPI] Error getting public debates: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve public debates',
            'details': str(e)
        }), 500


# ==================== Health Check ====================

@debate_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for debate service."""
    return jsonify({
        'service': 'debate_platform',
        'status': 'healthy',
        'stage': 'collaborate',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@debate_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@debate_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
