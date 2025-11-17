# app/services/mind_map_websocket_service.py
import logging
from flask_socketio import emit, join_room, leave_room
from flask import request
from app.db import db
from app.models.mind_maps import MindMap, MindMapCollaborator
from datetime import datetime

log = logging.getLogger(__name__)

# Store active connections per mind map
active_mindmap_sessions = {}  # {mind_map_id: {session_id: user_data}}

def register_mind_map_handlers(socketio):
    """Register all WebSocket handlers for collaborative mind mapping."""

    @socketio.on('connect', namespace='/mindmap')
    def on_mindmap_connect():
        """Handle mind map namespace connection."""
        from app.services.websocket_service import authenticate_socket_user, active_connections
        
        user = authenticate_socket_user()
        if not user:
            log.warning("Unauthenticated Mind Map WebSocket connection attempt")
            from flask_socketio import disconnect
            disconnect()
            return False
        
        # Store connection info
        active_connections[request.sid] = {
            **user,
            'connected_at': datetime.utcnow().isoformat(),
            'namespace': '/mindmap'
        }
        
        log.info(f"[MindMap] User {user['username']} connected to mind map namespace")
        emit('connection_established', {
            'user_id': user['user_id'],
            'username': user['username'],
            'timestamp': datetime.utcnow().isoformat()
        })
        return True

    @socketio.on('join_mindmap', namespace='/mindmap')
    def on_join_mindmap(data):
        """User joins a mind map collaboration session."""
        mind_map_id = data.get('mind_map_id')
        user_id = data.get('user_id')
        username = data.get('username', 'Anonymous')

        if not mind_map_id or not user_id:
            emit('error', {'message': 'mind_map_id and user_id required'})
            return

        session_id = request.sid

        # Verify access permissions
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            log.error(f"[MindMap] Mind map not found: {mind_map_id}")
            emit('error', {'message': 'Mind map not found'})
            return

        # Check if user is owner, collaborator, or map is public
        is_owner = str(mind_map.owner_id) == str(user_id)
        is_public = mind_map.is_public
        collaborator = db.session.query(MindMapCollaborator).filter_by(
            mind_map_id=mind_map_id,
            user_id=str(user_id)
        ).first()

        log.info(f"[MindMap] Access check - user_id: {user_id}, owner_id: {mind_map.owner_id}, is_owner: {is_owner}, is_public: {is_public}, has_collab: {collaborator is not None}")

        # Allow access if user is owner, collaborator, OR the mind map is public
        if not (is_owner or is_public or collaborator):
            log.warning(f"[MindMap] Access denied for user {user_id} to mind map {mind_map_id}")
            emit('error', {'message': 'Access denied - you must be the owner, a collaborator, or the mind map must be public'})
            return

        # Join room
        join_room(mind_map_id)

        # Track session
        if mind_map_id not in active_mindmap_sessions:
            active_mindmap_sessions[mind_map_id] = {}

        active_mindmap_sessions[mind_map_id][session_id] = {
            'user_id': user_id,
            'username': username,
            'joined_at': datetime.utcnow().isoformat(),
            'cursor': None
        }

        # Update collaborator status
        if collaborator:
            collaborator.is_online = True
            collaborator.last_active_at = datetime.utcnow()
            db.session.commit()

        # Notify others
        emit('user_joined', {
            'user_id': user_id,
            'username': username,
            'session_id': session_id
        }, room=mind_map_id, skip_sid=session_id)

        # Send updated active users list to ALL users in the room (including joiner)
        active_users = [
            {'user_id': u['user_id'], 'username': u['username'], 'session_id': sid}
            for sid, u in active_mindmap_sessions[mind_map_id].items()
        ]
        emit('active_users', {'users': active_users}, room=mind_map_id)

        log.info(f"[MindMap] User {username} joined mind map {mind_map_id}")

    @socketio.on('leave_mindmap', namespace='/mindmap')
    def on_leave_mindmap(data):
        """User leaves mind map."""
        mind_map_id = data.get('mind_map_id')
        session_id = request.sid

        if mind_map_id in active_mindmap_sessions:
            user_data = active_mindmap_sessions[mind_map_id].pop(session_id, None)
            if user_data:
                leave_room(mind_map_id)

                # Update collaborator status
                user_id = user_data['user_id']
                collaborator = db.session.query(MindMapCollaborator).filter_by(
                    mind_map_id=mind_map_id,
                    user_id=user_id
                ).first()
                if collaborator:
                    collaborator.is_online = False
                    db.session.commit()

                emit('user_left', {
                    'user_id': user_id,
                    'username': user_data['username']
                }, room=mind_map_id)

                log.info(f"[MindMap] User {user_data['username']} left mind map {mind_map_id}")

    @socketio.on('node_created', namespace='/mindmap')
    def on_node_created(data):
        """Broadcast new node creation."""
        mind_map_id = data.get('mind_map_id')
        node_data = data.get('node')
        created_by = data.get('created_by')

        emit('node_created', {
            'node': node_data,
            'created_by': created_by
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('node_updated', namespace='/mindmap')
    def on_node_updated(data):
        """Broadcast node updates (position, content, style)."""
        mind_map_id = data.get('mind_map_id')
        node_id = data.get('node_id')
        updates = data.get('updates')
        updated_by = data.get('updated_by')

        emit('node_updated', {
            'node_id': node_id,
            'updates': updates,
            'updated_by': updated_by
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('node_deleted', namespace='/mindmap')
    def on_node_deleted(data):
        """Broadcast node deletion."""
        mind_map_id = data.get('mind_map_id')
        node_id = data.get('node_id')
        deleted_by = data.get('deleted_by')

        emit('node_deleted', {
            'node_id': node_id,
            'deleted_by': deleted_by
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('connection_created', namespace='/mindmap')
    def on_connection_created(data):
        """Broadcast new connection."""
        mind_map_id = data.get('mind_map_id')
        connection_data = data.get('connection')
        created_by = data.get('created_by')

        emit('connection_created', {
            'connection': connection_data,
            'created_by': created_by
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('connection_deleted', namespace='/mindmap')
    def on_connection_deleted(data):
        """Broadcast connection deletion."""
        mind_map_id = data.get('mind_map_id')
        connection_id = data.get('connection_id')
        deleted_by = data.get('deleted_by')

        emit('connection_deleted', {
            'connection_id': connection_id,
            'deleted_by': deleted_by
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('cursor_moved', namespace='/mindmap')
    def on_cursor_moved(data):
        """Broadcast cursor position for live presence."""
        mind_map_id = data.get('mind_map_id')
        user_id = data.get('user_id')
        username = data.get('username')
        cursor = data.get('cursor')  # {x, y, node_id}

        session_id = request.sid
        if mind_map_id in active_mindmap_sessions and session_id in active_mindmap_sessions[mind_map_id]:
            active_mindmap_sessions[mind_map_id][session_id]['cursor'] = cursor

        emit('cursor_moved', {
            'user_id': user_id,
            'username': username,
            'cursor': cursor
        }, room=mind_map_id, skip_sid=session_id)

    @socketio.on('comment_added', namespace='/mindmap')
    def on_comment_added(data):
        """Broadcast new comment."""
        mind_map_id = data.get('mind_map_id')
        comment_data = data.get('comment')

        emit('comment_added', {
            'comment': comment_data
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('comment_resolved', namespace='/mindmap')
    def on_comment_resolved(data):
        """Broadcast comment resolution."""
        mind_map_id = data.get('mind_map_id')
        comment_id = data.get('comment_id')
        resolved_by = data.get('resolved_by')

        emit('comment_resolved', {
            'comment_id': comment_id,
            'resolved_by': resolved_by
        }, room=mind_map_id, skip_sid=request.sid)

    @socketio.on('disconnect', namespace='/mindmap')
    def on_disconnect():
        """Handle disconnection."""
        session_id = request.sid

        # Find which mind map this session was in
        for mind_map_id, sessions in list(active_mindmap_sessions.items()):
            if session_id in sessions:
                user_data = sessions.pop(session_id)

                # Update database (only if user is a collaborator)
                user_id = user_data['user_id']
                collaborator = db.session.query(MindMapCollaborator).filter_by(
                    mind_map_id=mind_map_id,
                    user_id=user_id
                ).first()
                if collaborator:
                    collaborator.is_online = False
                    db.session.commit()

                # Notify others that user left
                emit('user_left', {
                    'user_id': user_id,
                    'username': user_data['username']
                }, room=mind_map_id)

                # Send updated active users list to remaining users
                active_users = [
                    {'user_id': u['user_id'], 'username': u['username'], 'session_id': sid}
                    for sid, u in active_mindmap_sessions[mind_map_id].items()
                ]
                emit('active_users', {'users': active_users}, room=mind_map_id)

                log.info(f"[MindMap] User {user_data['username']} disconnected from {mind_map_id}, {len(active_users)} users remaining")
                break

    log.info("[MindMap] WebSocket handlers registered for /mindmap namespace")
