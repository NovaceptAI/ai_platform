"""
WebSocket Infrastructure for Real-Time Collaboration.

Handles WebSocket connections, room management, and real-time event broadcasting
for collaborative learning features.
"""

import logging
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

# Global SocketIO instance (will be initialized in create_app)
socketio = None

# Active connections tracking
active_connections: Dict[str, Dict] = {}
room_participants: Dict[str, List[str]] = {}


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    global socketio
    
    # CORS configuration for WebSocket
    cors_allowed_origins = [
        "http://172.178.120.199:3000",
        "http://127.0.0.1:3000",
        "https://scoolish.com"
    ]
    
    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_allowed_origins,
        async_mode='threading',
        logger=True,
        engineio_logger=True,
        ping_timeout=60,
        ping_interval=25
    )
    
    # Register event handlers
    register_collaboration_events()
    register_document_events()
    register_notification_events()
    
    logger.info("SocketIO initialized for collaboration")
    return socketio


def authenticate_socket_user():
    """Authenticate user from WebSocket connection."""
    try:
        # Try to get token from auth header or query params
        token = None
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
        
        # Fallback to query parameters
        if not token:
            token = request.args.get('token')
        
        if not token:
            logger.warning("No authentication token provided for WebSocket connection")
            return None
        
        # Decode JWT token
        decoded_token = decode_token(token)
        user_id = decoded_token.get('sub') or decoded_token.get('user_id')
        username = decoded_token.get('username', 'unknown')
        
        return {
            'user_id': user_id,
            'username': username,
            'session_id': request.sid
        }
        
    except Exception as e:
        logger.error(f"Socket authentication failed: {str(e)}")
        return None


def register_collaboration_events():
    """Register WebSocket events for general collaboration."""
    
    @socketio.on('connect', namespace='/collaborate')
    def on_collaborate_connect():
        """Handle collaboration namespace connection."""
        user = authenticate_socket_user()
        if not user:
            logger.warning("Unauthenticated WebSocket connection attempt")
            disconnect()
            return
        
        # Store connection info
        active_connections[request.sid] = {
            **user,
            'connected_at': datetime.utcnow().isoformat(),
            'namespace': '/collaborate'
        }
        
        logger.info(f"User {user['username']} connected to collaboration namespace")
        emit('connection_established', {
            'user_id': user['user_id'],
            'username': user['username'],
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('disconnect', namespace='/collaborate')
    def on_collaborate_disconnect():
        """Handle collaboration namespace disconnection."""
        if request.sid in active_connections:
            user = active_connections[request.sid]
            logger.info(f"User {user['username']} disconnected from collaboration")
            
            # Leave all rooms
            for room in room_participants:
                if request.sid in room_participants[room]:
                    leave_collaboration_room(room, user)
            
            # Remove from active connections
            del active_connections[request.sid]
    
    @socketio.on('join_session', namespace='/collaborate')
    def on_join_session(data):
        """Join a collaboration session room."""
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return
        
        session_id = data.get('session_id')
        if not session_id:
            emit('error', {'message': 'Session ID required'})
            return
        
        # TODO: Validate user has permission to join session
        # This would check the database for session permissions
        
        room_name = f"session_{session_id}"
        join_room(room_name)
        
        # Track room participation
        if room_name not in room_participants:
            room_participants[room_name] = []
        if request.sid not in room_participants[room_name]:
            room_participants[room_name].append(request.sid)
        
        # Notify other participants
        emit('user_joined', {
            'user_id': user['user_id'],
            'username': user['username'],
            'timestamp': datetime.utcnow().isoformat()
        }, room=room_name, include_self=False)
        
        # Send current participants to new user
        current_participants = []
        for sid in room_participants[room_name]:
            if sid in active_connections and sid != request.sid:
                participant = active_connections[sid]
                current_participants.append({
                    'user_id': participant['user_id'],
                    'username': participant['username']
                })
        
        emit('session_joined', {
            'session_id': session_id,
            'participants': current_participants,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"User {user['username']} joined session {session_id}")
    
    @socketio.on('leave_session', namespace='/collaborate')
    def on_leave_session(data):
        """Leave a collaboration session room."""
        user = active_connections.get(request.sid)
        if not user:
            return
        
        session_id = data.get('session_id')
        room_name = f"session_{session_id}"
        
        leave_collaboration_room(room_name, user)
    
    @socketio.on('send_message', namespace='/collaborate')
    def on_send_message(data):
        """Send a message to a collaboration session."""
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return
        
        session_id = data.get('session_id')
        message = data.get('message', '').strip()
        message_type = data.get('type', 'text')
        
        if not session_id or not message:
            emit('error', {'message': 'Session ID and message required'})
            return
        
        # TODO: Store message in database
        # This would create a CollaborationComment record
        
        room_name = f"session_{session_id}"
        message_data = {
            'id': f"msg_{datetime.utcnow().timestamp()}",  # Temporary ID
            'user_id': user['user_id'],
            'username': user['username'],
            'message': message,
            'type': message_type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('message_received', message_data, room=room_name)
        logger.info(f"Message sent by {user['username']} to session {session_id}")
    
    @socketio.on('typing_start', namespace='/collaborate')
    def on_typing_start(data):
        """Handle typing start indicator."""
        user = active_connections.get(request.sid)
        if not user:
            return
        
        session_id = data.get('session_id')
        room_name = f"session_{session_id}"
        
        emit('user_typing', {
            'user_id': user['user_id'],
            'username': user['username'],
            'typing': True
        }, room=room_name, include_self=False)
    
    @socketio.on('typing_stop', namespace='/collaborate')
    def on_typing_stop(data):
        """Handle typing stop indicator."""
        user = active_connections.get(request.sid)
        if not user:
            return
        
        session_id = data.get('session_id')
        room_name = f"session_{session_id}"
        
        emit('user_typing', {
            'user_id': user['user_id'],
            'username': user['username'],
            'typing': False
        }, room=room_name, include_self=False)


def register_document_events():
    """Register WebSocket events for collaborative document editing."""
    
    @socketio.on('connect', namespace='/documents')
    def on_document_connect():
        """Handle document editing namespace connection."""
        user = authenticate_socket_user()
        if not user:
            disconnect()
            return
        
        active_connections[request.sid] = {
            **user,
            'connected_at': datetime.utcnow().isoformat(),
            'namespace': '/documents'
        }
        
        logger.info(f"User {user['username']} connected to documents namespace")
    
    @socketio.on('join_document', namespace='/documents')
    def on_join_document(data):
        """Join a collaborative document room."""
        user = active_connections.get(request.sid)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return
        
        document_id = data.get('document_id')
        if not document_id:
            emit('error', {'message': 'Document ID required'})
            return
        
        room_name = f"document_{document_id}"
        join_room(room_name)
        
        # Track document participants
        if room_name not in room_participants:
            room_participants[room_name] = []
        if request.sid not in room_participants[room_name]:
            room_participants[room_name].append(request.sid)
        
        emit('document_joined', {
            'document_id': document_id,
            'user_id': user['user_id'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Notify others of new editor
        emit('editor_joined', {
            'user_id': user['user_id'],
            'username': user['username']
        }, room=room_name, include_self=False)
    
    @socketio.on('document_operation', namespace='/documents')
    def on_document_operation(data):
        """Handle document editing operations."""
        user = active_connections.get(request.sid)
        if not user:
            return
        
        document_id = data.get('document_id')
        operation = data.get('operation')
        
        if not document_id or not operation:
            emit('error', {'message': 'Document ID and operation required'})
            return
        
        # TODO: Process operational transform and store in database
        # This would handle conflict resolution and apply the operation
        
        room_name = f"document_{document_id}"
        operation_data = {
            'document_id': document_id,
            'operation': operation,
            'user_id': user['user_id'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        emit('operation_applied', operation_data, room=room_name, include_self=False)
    
    @socketio.on('cursor_position', namespace='/documents')
    def on_cursor_position(data):
        """Handle cursor position updates."""
        user = active_connections.get(request.sid)
        if not user:
            return
        
        document_id = data.get('document_id')
        position = data.get('position')
        
        room_name = f"document_{document_id}"
        emit('cursor_moved', {
            'user_id': user['user_id'],
            'username': user['username'],
            'position': position
        }, room=room_name, include_self=False)


def register_notification_events():
    """Register WebSocket events for notifications."""
    
    @socketio.on('connect', namespace='/notifications')
    def on_notification_connect():
        """Handle notification namespace connection."""
        user = authenticate_socket_user()
        if not user:
            disconnect()
            return
        
        # Join user-specific notification room
        user_room = f"user_{user['user_id']}"
        join_room(user_room)
        
        active_connections[request.sid] = {
            **user,
            'connected_at': datetime.utcnow().isoformat(),
            'namespace': '/notifications',
            'notification_room': user_room
        }
        
        logger.info(f"User {user['username']} connected to notifications")


def leave_collaboration_room(room_name: str, user: Dict):
    """Helper function to leave a collaboration room."""
    leave_room(room_name)
    
    # Remove from room participants
    if room_name in room_participants and request.sid in room_participants[room_name]:
        room_participants[room_name].remove(request.sid)
        
        # Clean up empty rooms
        if not room_participants[room_name]:
            del room_participants[room_name]
    
    # Notify others
    emit('user_left', {
        'user_id': user['user_id'],
        'username': user['username'],
        'timestamp': datetime.utcnow().isoformat()
    }, room=room_name)


def send_notification_to_user(user_id: str, notification_data: Dict):
    """Send a real-time notification to a specific user."""
    if not socketio:
        logger.warning("SocketIO not initialized")
        return False
    
    user_room = f"user_{user_id}"
    
    try:
        socketio.emit('notification', notification_data, 
                     room=user_room, namespace='/notifications')
        logger.info(f"Notification sent to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {str(e)}")
        return False


def send_session_update(session_id: str, update_data: Dict):
    """Send an update to all participants in a session."""
    if not socketio:
        logger.warning("SocketIO not initialized")
        return False
    
    room_name = f"session_{session_id}"
    
    try:
        socketio.emit('session_update', update_data, 
                     room=room_name, namespace='/collaborate')
        logger.info(f"Update sent to session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send session update {session_id}: {str(e)}")
        return False


def get_active_users_in_session(session_id: str) -> List[Dict]:
    """Get list of currently active users in a session."""
    room_name = f"session_{session_id}"
    active_users = []
    
    if room_name in room_participants:
        for sid in room_participants[room_name]:
            if sid in active_connections:
                user = active_connections[sid]
                active_users.append({
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'connected_at': user['connected_at']
                })
    
    return active_users


def get_connection_stats() -> Dict:
    """Get current WebSocket connection statistics."""
    return {
        'total_connections': len(active_connections),
        'active_rooms': len(room_participants),
        'connections_by_namespace': {
            ns: len([c for c in active_connections.values() if c.get('namespace') == ns])
            for ns in ['/collaborate', '/documents', '/notifications']
        }
    }
