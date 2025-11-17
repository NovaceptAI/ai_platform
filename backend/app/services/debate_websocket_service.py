"""
Debate WebSocket Event Handlers

Handles real-time debate events including:
- Participant connections
- Live messaging
- Typing indicators
- Round transitions
- Speaking time tracking
- AI analysis broadcasting
"""

import logging
from flask import request
from flask_socketio import emit, join_room, leave_room
from app.services.websocket_service import socketio, active_connections, room_participants
from app.services.stages.collaborate.debate_service import DebateService
from app.models.debates import Debate, DebateParticipant, DebateMessage
from app.db import db
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


def register_debate_events():
    """Register debate-specific WebSocket events."""

    @socketio.on('join_debate', namespace='/collaborate')
    def on_join_debate(data):
        """
        Join a debate room.

        Expected data:
        {
            "debate_id": "uuid",
            "participant_id": "uuid"
        }
        """
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return

        debate_id = data.get('debate_id')
        participant_id = data.get('participant_id')

        if not debate_id:
            emit('error', {'message': 'debate_id is required'})
            return

        try:
            # Validate debate exists
            debate = Debate.query.filter_by(id=debate_id).first()
            if not debate:
                emit('error', {'message': 'Debate not found'})
                return

            # Validate participant
            participant = DebateParticipant.query.filter_by(
                id=participant_id,
                debate_id=debate_id,
                user_id=user['user_id']
            ).first()

            if not participant:
                emit('error', {'message': 'You are not a participant in this debate'})
                return

            # Join debate room
            room_name = f"debate_{debate_id}"
            join_room(room_name)

            # Track room participation
            if room_name not in room_participants:
                room_participants[room_name] = []
            if request.sid not in room_participants[room_name]:
                room_participants[room_name].append(request.sid)

            # Update participant connection status
            participant.is_connected = True
            participant.last_seen = datetime.utcnow()
            db.session.commit()

            # Notify other participants
            emit('participant_joined', {
                'participant_id': str(participant_id),
                'user_id': user['user_id'],
                'username': user.get('username', 'Anonymous'),
                'role': participant.role,
                'display_name': participant.display_name,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name, include_self=False)

            # Get current participants for new joiner
            current_participants = []
            for p in debate.participants:
                if p.is_connected and p.id != participant_id:
                    current_participants.append({
                        'participant_id': str(p.id),
                        'user_id': p.user_id,
                        'display_name': p.display_name,
                        'role': p.role,
                        'is_connected': p.is_connected
                    })

            emit('debate_joined', {
                'debate_id': str(debate_id),
                'debate': debate.to_dict(include_participants=True),
                'current_participants': current_participants,
                'timestamp': datetime.utcnow().isoformat()
            })

            logger.info(f"User {user['username']} joined debate {debate_id}")

        except Exception as e:
            logger.error(f"Error joining debate: {str(e)}")
            emit('error', {'message': f'Failed to join debate: {str(e)}'})

    @socketio.on('leave_debate', namespace='/collaborate')
    def on_leave_debate(data):
        """Leave a debate room."""
        user = active_connections.get(request.sid)
        if not user:
            return

        debate_id = data.get('debate_id')
        participant_id = data.get('participant_id')

        if not debate_id or not participant_id:
            return

        try:
            room_name = f"debate_{debate_id}"
            leave_room(room_name)

            # Remove from room participants
            if room_name in room_participants and request.sid in room_participants[room_name]:
                room_participants[room_name].remove(request.sid)

            # Update participant connection status
            participant = DebateParticipant.query.filter_by(id=participant_id).first()
            if participant:
                participant.is_connected = False
                participant.last_seen = datetime.utcnow()
                db.session.commit()

            # Notify others
            emit('participant_left', {
                'participant_id': str(participant_id),
                'user_id': user['user_id'],
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name)

            logger.info(f"User {user['username']} left debate {debate_id}")

        except Exception as e:
            logger.error(f"Error leaving debate: {str(e)}")

    @socketio.on('debate_message', namespace='/collaborate')
    def on_debate_message(data):
        """
        Send a message in the debate.

        Expected data:
        {
            "debate_id": "uuid",
            "participant_id": "uuid",
            "message_type": "argument|rebuttal|opening|closing|chat",
            "content": "message content",
            "reply_to": "message_id" (optional)
        }
        """
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return

        debate_id = data.get('debate_id')
        participant_id = data.get('participant_id')
        message_type = data.get('message_type', 'chat')
        content = data.get('content', '').strip()

        if not all([debate_id, participant_id, content]):
            emit('error', {'message': 'debate_id, participant_id, and content are required'})
            return

        try:
            # Validate debate and participant
            debate = Debate.query.filter_by(id=debate_id).first()
            if not debate:
                emit('error', {'message': 'Debate not found'})
                return

            participant = DebateParticipant.query.filter_by(
                id=participant_id,
                debate_id=debate_id
            ).first()

            if not participant:
                emit('error', {'message': 'Participant not found'})
                return

            # Create message record
            message = DebateMessage(
                id=uuid.uuid4(),
                debate_id=debate_id,
                participant_id=participant_id,
                message_type=message_type,
                content=content,
                round_number=debate.current_round,
                reply_to_message_id=data.get('reply_to'),
                sources=data.get('sources', [])
            )

            # Perform AI analysis if enabled and appropriate message type
            if debate.settings.get('argument_analysis') and message_type in ['argument', 'rebuttal', 'opening', 'closing']:
                service = DebateService()

                # Get recent messages for context
                recent_messages = DebateMessage.query.filter_by(
                    debate_id=debate_id
                ).order_by(DebateMessage.created_at.desc()).limit(5).all()

                previous_data = [{
                    'role': m.participant.role,
                    'content': m.content
                } for m in recent_messages]

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
            if message_type == 'argument':
                participant.arguments_count += 1
            elif message_type == 'rebuttal':
                participant.rebuttals_count += 1

            db.session.commit()

            # Broadcast message to all debate participants
            room_name = f"debate_{debate_id}"
            message_data = {
                'message_id': str(message.id),
                'debate_id': str(debate_id),
                'participant_id': str(participant_id),
                'display_name': participant.display_name,
                'role': participant.role,
                'message_type': message_type,
                'content': content,
                'round_number': debate.current_round,
                'reply_to': str(data.get('reply_to')) if data.get('reply_to') else None,
                'sources': message.sources,
                'ai_analysis': message.ai_analysis,
                'timestamp': datetime.utcnow().isoformat()
            }

            emit('message_received', message_data, room=room_name)

            logger.info(f"Message sent in debate {debate_id} by participant {participant_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending debate message: {str(e)}")
            emit('error', {'message': f'Failed to send message: {str(e)}'})

    @socketio.on('typing_indicator', namespace='/collaborate')
    def on_typing_indicator(data):
        """Handle typing indicators in debate."""
        user = active_connections.get(request.sid)
        if not user:
            return

        debate_id = data.get('debate_id')
        participant_id = data.get('participant_id')
        is_typing = data.get('is_typing', False)

        if not all([debate_id, participant_id]):
            return

        try:
            participant = DebateParticipant.query.filter_by(id=participant_id).first()
            if not participant:
                return

            room_name = f"debate_{debate_id}"
            emit('typing_status', {
                'participant_id': str(participant_id),
                'display_name': participant.display_name,
                'role': participant.role,
                'is_typing': is_typing
            }, room=room_name, include_self=False)

        except Exception as e:
            logger.error(f"Error handling typing indicator: {str(e)}")

    @socketio.on('advance_round', namespace='/collaborate')
    def on_advance_round(data):
        """Advance to next round (moderator/creator only)."""
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return

        debate_id = data.get('debate_id')

        if not debate_id:
            emit('error', {'message': 'debate_id is required'})
            return

        try:
            debate = Debate.query.filter_by(id=debate_id).first()
            if not debate:
                emit('error', {'message': 'Debate not found'})
                return

            # Check permissions
            is_creator = debate.creator_id == user['user_id']
            is_moderator = any(
                p.user_id == user['user_id'] and p.role == 'moderator'
                for p in debate.participants
            )

            if not (is_creator or is_moderator):
                emit('error', {'message': 'Only creator or moderator can advance rounds'})
                return

            # Advance round
            if debate.current_round < debate.total_rounds:
                debate.current_round += 1
                db.session.commit()

                # Notify all participants
                room_name = f"debate_{debate_id}"
                emit('round_advanced', {
                    'debate_id': str(debate_id),
                    'current_round': debate.current_round,
                    'total_rounds': debate.total_rounds,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=room_name)

                logger.info(f"Debate {debate_id} advanced to round {debate.current_round}")
            else:
                emit('error', {'message': 'Debate is already at final round'})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error advancing round: {str(e)}")
            emit('error', {'message': f'Failed to advance round: {str(e)}'})

    @socketio.on('reaction', namespace='/collaborate')
    def on_reaction(data):
        """React to a debate message."""
        user = active_connections.get(request.sid)
        if not user:
            return

        debate_id = data.get('debate_id')
        message_id = data.get('message_id')
        reaction_type = data.get('reaction_type')  # applause, disagree, etc.

        if not all([debate_id, message_id, reaction_type]):
            return

        try:
            message = DebateMessage.query.filter_by(id=message_id).first()
            if not message:
                return

            # Update reactions in database
            if not message.reactions:
                message.reactions = {}

            if reaction_type not in message.reactions:
                message.reactions[reaction_type] = 0

            message.reactions[reaction_type] += 1
            db.session.commit()

            # Broadcast reaction
            room_name = f"debate_{debate_id}"
            emit('reaction_added', {
                'message_id': str(message_id),
                'user_id': user['user_id'],
                'reaction_type': reaction_type,
                'total_reactions': message.reactions,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name)

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding reaction: {str(e)}")

    @socketio.on('request_fact_check', namespace='/collaborate')
    def on_request_fact_check(data):
        """Request fact-check for claims in a message."""
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return

        debate_id = data.get('debate_id')
        message_id = data.get('message_id')
        claims = data.get('claims', [])

        if not all([debate_id, message_id, claims]):
            emit('error', {'message': 'debate_id, message_id, and claims are required'})
            return

        try:
            debate = Debate.query.filter_by(id=debate_id).first()
            if not debate or not debate.settings.get('auto_fact_check', True):
                emit('error', {'message': 'Fact-checking not available'})
                return

            # Perform fact-checking
            service = DebateService()
            result = service.fact_check_claims(
                claims=claims,
                context=debate.motion
            )

            if result.get('success'):
                # Broadcast fact-check results
                room_name = f"debate_{debate_id}"
                emit('fact_check_results', {
                    'message_id': str(message_id),
                    'fact_checks': result.get('fact_checks', []),
                    'overall_accuracy': result.get('overall_accuracy', 0),
                    'timestamp': datetime.utcnow().isoformat()
                }, room=room_name)
            else:
                emit('error', {'message': 'Fact-checking failed'})

        except Exception as e:
            logger.error(f"Error fact-checking: {str(e)}")
            emit('error', {'message': f'Failed to fact-check: {str(e)}'})

    logger.info("Debate WebSocket events registered")


def send_debate_update(debate_id: str, update_data: dict):
    """Send an update to all participants in a debate."""
    if not socketio:
        logger.warning("SocketIO not initialized")
        return False

    room_name = f"debate_{debate_id}"

    try:
        socketio.emit('debate_update', update_data,
                     room=room_name, namespace='/collaborate')
        logger.info(f"Update sent to debate {debate_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send debate update {debate_id}: {str(e)}")
        return False


def notify_debate_started(debate_id: str, debate_data: dict):
    """Notify all participants that debate has started."""
    return send_debate_update(debate_id, {
        'type': 'debate_started',
        'debate': debate_data,
        'timestamp': datetime.utcnow().isoformat()
    })


def notify_debate_ended(debate_id: str, results: dict):
    """Notify all participants that debate has ended."""
    return send_debate_update(debate_id, {
        'type': 'debate_ended',
        'results': results,
        'timestamp': datetime.utcnow().isoformat()
    })
