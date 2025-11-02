"""
Group Discussion Routes for Collaborate Stage
Handles REST API endpoints and WebSocket events for group discussions
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import join_room, leave_room, emit
from app.services.group_discussion_service import GroupDiscussionService
from app.services.websocket_service import socketio

logger = logging.getLogger(__name__)

# Create blueprint for group discussion routes
group_discussion_bp = Blueprint('group_discussion', __name__, url_prefix='/api/collaborate/discussions')

# REST API Endpoints

@group_discussion_bp.route('/create', methods=['POST'])
@jwt_required()
def create_discussion():
    """Create a new group discussion session"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['learning_path_id', 'title']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Add creator_id to data
        data['creator_id'] = user_id
        
        result = GroupDiscussionService.create_discussion_session(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating discussion: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/join', methods=['POST'])
@jwt_required()
def join_discussion(session_id):
    """Join a discussion session"""
    try:
        user_id = get_jwt_identity()
        
        result = GroupDiscussionService.join_discussion(session_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error joining discussion: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/leave', methods=['POST'])
@jwt_required()
def leave_discussion(session_id):
    """Leave a discussion session"""
    try:
        user_id = get_jwt_identity()
        
        result = GroupDiscussionService.leave_discussion(session_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error leaving discussion: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(session_id):
    """Get message history for a discussion"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)
        
        result = GroupDiscussionService.get_discussion_history(
            session_id, user_id, page, per_page
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/messages', methods=['POST'])
@jwt_required()
def post_message(session_id):
    """Post a message to a discussion"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({"error": "Message content is required"}), 400
        
        if len(data['content'].strip()) == 0:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if len(data['content']) > 2000:
            return jsonify({"error": "Message too long (max 2000 characters)"}), 400
        
        message_data = {
            'session_id': session_id,
            'user_id': user_id,
            'content': data['content'].strip(),
            'parent_id': data.get('parent_id')
        }
        
        result = GroupDiscussionService.post_message(message_data)
        
        if result['success']:
            # Trigger auto-moderation asynchronously
            from app.tasks.group_discussion_tasks import moderate_discussion_content
            moderate_discussion_content.delay(session_id)
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error posting message: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/messages/<int:message_id>', methods=['PUT'])
@jwt_required()
def edit_message(message_id):
    """Edit an existing message"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({"error": "Message content is required"}), 400
        
        if len(data['content'].strip()) == 0:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if len(data['content']) > 2000:
            return jsonify({"error": "Message too long (max 2000 characters)"}), 400
        
        result = GroupDiscussionService.edit_message(
            message_id, user_id, data['content'].strip()
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error editing message: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/active', methods=['GET'])
@jwt_required()
def get_active_discussions():
    """Get active discussions for the current user"""
    try:
        user_id = get_jwt_identity()
        learning_path_id = request.args.get('learning_path_id', type=int)
        
        result = GroupDiscussionService.get_active_discussions(user_id, learning_path_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error getting active discussions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/messages/<int:message_id>/moderate', methods=['POST'])
@jwt_required()
def moderate_message(message_id):
    """Moderate a message (hide, flag, delete)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'action' not in data:
            return jsonify({"error": "Moderation action is required"}), 400
        
        valid_actions = ['hide', 'flag', 'delete']
        if data['action'] not in valid_actions:
            return jsonify({"error": f"Invalid action. Must be one of: {valid_actions}"}), 400
        
        result = GroupDiscussionService.moderate_message(
            message_id, user_id, data['action'], data.get('reason')
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error moderating message: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/digest', methods=['POST'])
@jwt_required()
def send_digest(session_id):
    """Send discussion digest to participants"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        digest_type = data.get('type', 'daily')
        valid_types = ['hourly', 'daily', 'weekly']
        
        if digest_type not in valid_types:
            return jsonify({"error": f"Invalid digest type. Must be one of: {valid_types}"}), 400
        
        # TODO: Add permission check - only facilitators/moderators should send digests
        
        # Send digest asynchronously
        from app.tasks.group_discussion_tasks import send_discussion_digest
        task = send_discussion_digest.delay(session_id, digest_type)
        
        return jsonify({
            "success": True,
            "message": f"Sending {digest_type} digest",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error sending digest: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/analytics', methods=['GET'])
@jwt_required()
def get_analytics(session_id):
    """Get discussion analytics"""
    try:
        user_id = get_jwt_identity()
        period_days = request.args.get('days', 7, type=int)
        
        # Limit period to reasonable range
        period_days = max(1, min(period_days, 90))
        
        # TODO: Add permission check - only facilitators should access analytics
        
        # Generate analytics asynchronously
        from app.tasks.group_discussion_tasks import generate_discussion_analytics
        task = generate_discussion_analytics.delay(session_id)
        
        return jsonify({
            "success": True,
            "message": f"Generating analytics for {period_days} days",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@group_discussion_bp.route('/<int:session_id>/reminders', methods=['POST'])
@jwt_required()
def send_reminders(session_id):
    """Send inactivity reminders to participants"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        hours_inactive = data.get('hours', 24)
        hours_inactive = max(1, min(hours_inactive, 168))  # 1 hour to 1 week
        
        # TODO: Add permission check - only facilitators should send reminders
        
        # Send reminders asynchronously
        from app.tasks.group_discussion_tasks import send_inactivity_reminders
        task = send_inactivity_reminders.delay(session_id, hours_inactive)
        
        return jsonify({
            "success": True,
            "message": f"Sending reminders to participants inactive for {hours_inactive} hours",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error sending reminders: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# WebSocket Event Handlers for Group Discussions
# These will be registered when socketio is available

def register_websocket_handlers():
    """Register WebSocket event handlers for group discussions"""
    from app.services.websocket_service import socketio
    
    if socketio is None:
        return
    
    @socketio.on('join_discussion_room', namespace='/collaborate')
    def handle_join_discussion_room(data):
        """Handle joining a discussion room via WebSocket"""
        try:
            session_id = data.get('session_id')
            if not session_id:
                return {'error': 'Session ID required'}
            
            # TODO: Add authentication check for WebSocket
            # user_id = get_current_user_id()
            
            # Join the discussion room
            room_name = f"discussion_{session_id}"
            join_room(room_name, namespace='/collaborate')
            
            # Emit confirmation
            emit('joined_discussion_room', {
                'session_id': session_id,
                'room': room_name,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/collaborate')
            
            logger.info(f"User joined discussion room {room_name}")
            
        except Exception as e:
            logger.error(f"Error joining discussion room: {str(e)}")
            emit('error', {'message': 'Failed to join discussion room'}, namespace='/collaborate')

    @socketio.on('leave_discussion_room', namespace='/collaborate')
    def handle_leave_discussion_room(data):
        """Handle leaving a discussion room via WebSocket"""
        try:
            session_id = data.get('session_id')
            if not session_id:
                return {'error': 'Session ID required'}
            
            # Leave the discussion room
            room_name = f"discussion_{session_id}"
            leave_room(room_name, namespace='/collaborate')
            
            # Emit confirmation
            emit('left_discussion_room', {
                'session_id': session_id,
                'room': room_name,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/collaborate')
            
            logger.info(f"User left discussion room {room_name}")
            
        except Exception as e:
            logger.error(f"Error leaving discussion room: {str(e)}")
            emit('error', {'message': 'Failed to leave discussion room'}, namespace='/collaborate')

    @socketio.on('typing_indicator', namespace='/collaborate')
    def handle_typing_indicator(data):
        """Handle typing indicator for discussions"""
        try:
            session_id = data.get('session_id')
            is_typing = data.get('is_typing', False)
            
            if not session_id:
                return {'error': 'Session ID required'}
            
            # TODO: Add authentication check
            # user_id = get_current_user_id()
            
            # Broadcast typing indicator to room (except sender)
            room_name = f"discussion_{session_id}"
            emit('user_typing', {
                'session_id': session_id,
                'user_id': 'anonymous',  # TODO: Replace with actual user_id
                'is_typing': is_typing,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name, include_self=False, namespace='/collaborate')
            
        except Exception as e:
            logger.error(f"Error handling typing indicator: {str(e)}")

    @socketio.on('request_discussion_sync', namespace='/collaborate')
    def handle_discussion_sync_request(data):
        """Handle request for discussion synchronization"""
        try:
            session_id = data.get('session_id')
            
            if not session_id:
                return {'error': 'Session ID required'}
            
            # TODO: Get recent messages and emit to requesting user
            # This would sync the user with recent discussion state
            
            emit('discussion_synced', {
                'session_id': session_id,
                'status': 'synced',
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/collaborate')
            
        except Exception as e:
            logger.error(f"Error handling discussion sync: {str(e)}")
            emit('error', {'message': 'Failed to sync discussion'}, namespace='/collaborate')

# Note: Call register_websocket_handlers() after socketio is initialized in main.py

# Export the blueprint
