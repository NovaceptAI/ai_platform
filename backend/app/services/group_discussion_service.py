"""
Group Discussion Service for Collaborate Stage
Handles threaded discussions, real-time messaging, and moderation
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import joinedload
from app.db import db
from app.models.collaboration import (
    CollaborationSession, SessionParticipant, 
    CollaborationComment, CollaborationNotification
)
from app.models.users import Users
from app.models.learning_paths import LearningPath
from app.services.websocket_service import socketio

logger = logging.getLogger(__name__)

class GroupDiscussionService:
    """Service for managing group discussions and threaded conversations"""
    
    @staticmethod
    def create_discussion_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new group discussion session"""
        try:
            # Validate learning path exists
            learning_path = db.db.session.query(LearningPath).filter(
                LearningPath.id == session_data['learning_path_id']
            ).first()
            
            if not learning_path:
                return {"success": False, "error": "Learning path not found"}
            
            # Create collaboration session
            collaboration_session = CollaborationSession(
                learning_path_id=session_data['learning_path_id'],
                creator_id=session_data['creator_id'],
                session_type='group_discussion',
                title=session_data.get('title', f"Discussion: {learning_path.title}"),
                description=session_data.get('description'),
                max_participants=session_data.get('max_participants', 20),
                is_active=True,
                is_public=session_data.get('is_public', True)
            )
            
            db.db.session.add(collaboration_session)
            db.db.session.flush()  # Get the ID
            
            # Add creator as participant with facilitator role
            creator_participant = SessionParticipant(
                session_id=collaboration_session.id,
                user_id=session_data['creator_id'],
                role='facilitator',
                status='joined'
            )
            
            db.db.session.add(creator_participant)
            db.db.session.commit()
            
            # Emit WebSocket event for new discussion
            socketio.emit('discussion_created', {
                'session_id': collaboration_session.id,
                'title': collaboration_session.title,
                'creator': session_data['creator_id'],
                'learning_path_id': collaboration_session.learning_path_id
            }, namespace='/collaborate')
            
            logger.info(f"Created discussion session {collaboration_session.id}")
            
            return {
                "success": True,
                "session_id": collaboration_session.id,
                "session": {
                    "id": collaboration_session.id,
                    "title": collaboration_session.title,
                    "description": collaboration_session.description,
                    "creator_id": collaboration_session.creator_id,
                    "participant_count": 1,
                    "is_active": collaboration_session.is_active
                }
            }
                
        except Exception as e:
            logger.error(f"Error creating discussion session: {str(e)}")
            return {"success": False, "error": str(e)}    @staticmethod
    def join_discussion(session_id: int, user_id: int) -> Dict[str, Any]:
        """Add a user to a discussion session"""
        try:
            # Check if session exists and is active
            collaboration_session = db.db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id,
                CollaborationSession.is_active == True
            ).first()
            
            if not collaboration_session:
                return {"success": False, "error": "Discussion session not found or inactive"}
            
            # Check if already joined
            existing_participant = db.db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id
                )
            ).first()
            
            if existing_participant:
                if existing_participant.status == 'left':
                    existing_participant.status = 'joined'
                    existing_participant.last_active = datetime.utcnow()
                else:
                    return {"success": False, "error": "Already joined this discussion"}
            else:
                # Check participant limit
                current_participants = db.db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.status == 'joined'
                    )
                ).count()
                
                if current_participants >= collaboration_session.max_participants:
                    return {"success": False, "error": "Discussion is full"}
                
                # Add new participant
                new_participant = SessionParticipant(
                    session_id=session_id,
                    user_id=user_id,
                    role='participant',
                    status='joined'
                )
                db.db.session.add(new_participant)
            
            db.db.session.commit()
            
            # Get user info for notification
            user = db.db.session.query(Users).filter(Users.id == user_id).first()
                
            # Emit WebSocket event to session room
            socketio.emit('participant_joined', {
                'session_id': session_id,
                'user_id': user_id,
                'username': user.username if user else 'Unknown',
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"discussion_{session_id}", namespace='/collaborate')
            
            logger.info(f"User {user_id} joined discussion {session_id}")
            
            return {"success": True, "message": "Joined discussion successfully"}
                
        except Exception as e:
            logger.error(f"Error joining discussion: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def leave_discussion(session_id: int, user_id: int) -> Dict[str, Any]:
        """Remove a user from a discussion session"""
        try:
            participant = db.db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id,
                    SessionParticipant.status == 'joined'
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not a participant in this discussion"}
            
            participant.status = 'left'
            participant.last_active = datetime.utcnow()
            db.db.session.commit()
            
            # Get user info for notification
            user = db.db.session.query(Users).filter(Users.id == user_id).first()
            
            # Emit WebSocket event to session room
            socketio.emit('participant_left', {
                'session_id': session_id,
                'user_id': user_id,
                'username': user.username if user else 'Unknown',
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"discussion_{session_id}", namespace='/collaborate')
            
            logger.info(f"User {user_id} left discussion {session_id}")
            
            return {"success": True, "message": "Left discussion successfully"}
                
        except Exception as e:
            logger.error(f"Error leaving discussion: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def post_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Post a message to a discussion"""
        try:
            # Verify user is participant
            participant = db.db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == message_data['session_id'],
                    SessionParticipant.user_id == message_data['user_id'],
                    SessionParticipant.status == 'joined'
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to post in this discussion"}
            
            # Create comment
            comment = CollaborationComment(
                session_id=message_data['session_id'],
                user_id=message_data['user_id'],
                content=message_data['content'],
                comment_type='message',
                parent_id=message_data.get('parent_id')  # For threaded replies
            )
            
            db.db.session.add(comment)
            db.db.session.flush()  # Get the ID
            
            # Update participant last activity
            participant.last_active = datetime.utcnow()
            db.db.session.commit()
            
            # Get user info for broadcast
            user = db.db.session.query(Users).filter(Users.id == message_data['user_id']).first()
                
            # Prepare message for broadcast
            message_broadcast = {
                'id': comment.id,
                'session_id': comment.session_id,
                'user_id': comment.user_id,
                'username': user.username if user else 'Unknown',
                'content': comment.content,
                'parent_id': comment.parent_id,
                'created_at': comment.created_at.isoformat(),
                'edited': False
            }
            
            # Emit WebSocket event to all session participants
            socketio.emit('new_message', message_broadcast, 
                        room=f"discussion_{message_data['session_id']}", 
                        namespace='/collaborate')
            
            # Create notifications for mentioned users or replies
            if comment.parent_id:
                GroupDiscussionService._notify_reply(comment.id, session)
            
            logger.info(f"Posted message {comment.id} in discussion {message_data['session_id']}")
            
            return {
                "success": True,
                "message_id": comment.id,
                "message": message_broadcast
            }
                
        except Exception as e:
            logger.error(f"Error posting message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def edit_message(message_id: int, user_id: int, new_content: str) -> Dict[str, Any]:
        """Edit an existing message"""
        try:
            comment = db.session.query(CollaborationComment).filter(
                and_(
                    CollaborationComment.id == message_id,
                    CollaborationComment.user_id == user_id
                )
            ).first()
            
            if not comment:
                return {"success": False, "error": "Message not found or not authorized"}
            
            # Check if message is within edit time limit (30 minutes)
            if datetime.utcnow() - comment.created_at > timedelta(minutes=30):
                return {"success": False, "error": "Edit time limit exceeded"}
            
            comment.content = new_content
            comment.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Emit WebSocket event for message update
            socketio.emit('message_edited', {
                'message_id': message_id,
                'session_id': comment.session_id,
                'content': new_content,
                'edited_at': comment.updated_at.isoformat()
            }, room=f"discussion_{comment.session_id}", namespace='/collaborate')
            
            logger.info(f"Edited message {message_id}")
            
            return {"success": True, "message": "Message edited successfully"}
            
        except Exception as e:
            logger.error(f"Error editing message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_discussion_history(session_id: int, user_id: int, page: int = 1, 
                             per_page: int = 50) -> Dict[str, Any]:
        """Get message history for a discussion"""
        try:
            # Verify user is participant
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to view this discussion"}
            
            # Get messages with pagination
            offset = (page - 1) * per_page
            messages = db.session.query(CollaborationComment).options(
                joinedload(CollaborationComment.user)
            ).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message'
                )
            ).order_by(desc(CollaborationComment.created_at)).offset(offset).limit(per_page).all()
            
            # Get total count
            total_messages = db.session.query(CollaborationComment).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message'
                )
            ).count()
            
            # Format messages
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    'id': msg.id,
                    'user_id': msg.user_id,
                    'username': msg.user.username if msg.user else 'Unknown',
                    'content': msg.content,
                    'parent_id': msg.parent_id,
                    'created_at': msg.created_at.isoformat(),
                    'updated_at': msg.updated_at.isoformat() if msg.updated_at else None,
                    'edited': msg.updated_at is not None
                })
            
            return {
                "success": True,
                "messages": formatted_messages,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_messages,
                    "pages": (total_messages + per_page - 1) // per_page
                }
            }
                
        except Exception as e:
            logger.error(f"Error getting discussion history: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_active_discussions(user_id: int, learning_path_id: Optional[int] = None) -> Dict[str, Any]:
        """Get active discussions for a user"""
        try:
            query = db.session.query(CollaborationSession).join(
                SessionParticipant,
                and_(
                    SessionParticipant.session_id == CollaborationSession.id,
                    SessionParticipant.user_id == user_id,
                    SessionParticipant.status == 'joined'
                )
            ).filter(
                and_(
                    CollaborationSession.session_type == 'group_discussion',
                    CollaborationSession.is_active == True
                )
            )
            
            if learning_path_id:
                query = query.filter(CollaborationSession.learning_path_id == learning_path_id)
            
            sessions = query.all()
            
            # Format session data
            formatted_sessions = []
            for sess in sessions:
                # Get participant count
                participant_count = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == sess.id,
                        SessionParticipant.status == 'joined'
                    )
                ).count()
                
                # Get latest message
                latest_message = db.session.query(CollaborationComment).filter(
                    and_(
                        CollaborationComment.session_id == sess.id,
                        CollaborationComment.comment_type == 'message'
                    )
                ).order_by(desc(CollaborationComment.created_at)).first()
                
                formatted_sessions.append({
                    'id': sess.id,
                    'title': sess.title,
                    'description': sess.description,
                    'learning_path_id': sess.learning_path_id,
                    'creator_id': sess.creator_id,
                    'participant_count': participant_count,
                    'created_at': sess.created_at.isoformat(),
                    'last_activity': latest_message.created_at.isoformat() if latest_message else sess.created_at.isoformat()
                })
            
            return {"success": True, "discussions": formatted_sessions}
                
        except Exception as e:
            logger.error(f"Error getting active discussions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def moderate_message(message_id: int, moderator_id: int, action: str, reason: str = None) -> Dict[str, Any]:
        """Moderate a message (hide, flag, etc.)"""
        try:
            # Verify moderator has permission
            comment = db.session.query(CollaborationComment).filter(
                CollaborationComment.id == message_id
            ).first()
            
            if not comment:
                return {"success": False, "error": "Message not found"}
            
            moderator_participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == comment.session_id,
                    SessionParticipant.user_id == moderator_id,
                    SessionParticipant.role.in_(['facilitator', 'moderator'])
                )
            ).first()
            
            if not moderator_participant:
                return {"success": False, "error": "Not authorized to moderate"}
            
            # Apply moderation action
            if action == 'hide':
                comment.is_hidden = True
            elif action == 'flag':
                comment.is_flagged = True
            elif action == 'delete':
                comment.is_deleted = True
            else:
                return {"success": False, "error": "Invalid moderation action"}
            
            comment.moderation_reason = reason
            comment.moderated_by = moderator_id
            comment.moderated_at = datetime.utcnow()
            db.session.commit()
            
            # Emit moderation event
            socketio.emit('message_moderated', {
                'message_id': message_id,
                'session_id': comment.session_id,
                'action': action,
                'moderator_id': moderator_id
            }, room=f"discussion_{comment.session_id}", namespace='/collaborate')
            
            logger.info(f"Message {message_id} moderated by {moderator_id}: {action}")
            
            return {"success": True, "message": f"Message {action}ed successfully"}
            
        except Exception as e:
            logger.error(f"Error moderating message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _notify_reply(comment_id: int, session) -> None:
        """Create notification for reply to a message"""
        try:
            comment = db.session.query(CollaborationComment).filter(
                CollaborationComment.id == comment_id
            ).first()
            
            if comment and comment.parent_id:
                parent_comment = db.session.query(CollaborationComment).filter(
                    CollaborationComment.id == comment.parent_id
                ).first()
                
                if parent_comment and parent_comment.user_id != comment.user_id:
                    notification = CollaborationNotification(
                        user_id=parent_comment.user_id,
                        session_id=comment.session_id,
                        notification_type='reply',
                        title='New Reply',
                        message=f'Someone replied to your message',
                        metadata={'comment_id': comment_id, 'parent_id': comment.parent_id}
                    )
                    db.session.add(notification)
                    
                    # Emit real-time notification
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'type': 'reply',
                        'title': notification.title,
                        'message': notification.message,
                        'session_id': comment.session_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=f"user_{parent_comment.user_id}", namespace='/notifications')
                    
        except Exception as e:
            logger.error(f"Error creating reply notification: {str(e)}")
