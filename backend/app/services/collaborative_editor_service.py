"""
Collaborative Editor Service for Collaborate Stage
Handles real-time document editing with operational transforms and conflict resolution
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import joinedload
from app.db import db
from app.models.collaboration import (
    CollaborationSession, SessionParticipant, 
    CollaborativeDocument, DocumentOperation, CollaborationNotification
)
from app.models.users import Users
from app.models.learning_paths import LearningPath
from app.services.websocket_service import socketio
import json
import uuid

logger = logging.getLogger(__name__)

class CollaborativeEditorService:
    """Service for managing collaborative document editing with operational transforms"""
    
    @staticmethod
    def create_document(document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new collaborative document"""
        # Database operations
            # Database operations
                # Validate learning path exists
                learning_path = db.session.query(LearningPath).filter(
                    LearningPath.id == document_data['learning_path_id']
                ).first()
                
                if not learning_path:
                    return {"success": False, "error": "Learning path not found"}
                
                # Create collaboration session for document editing
                collaboration_session = CollaborationSession(
                    learning_path_id=document_data['learning_path_id'],
                    creator_id=document_data['creator_id'],
                    session_type='collaborative_editing',
                    title=document_data.get('title', f"Collaborative Document: {learning_path.title}"),
                    description=document_data.get('description'),
                    max_participants=document_data.get('max_participants', 20),
                    is_active=True,
                    is_public=document_data.get('is_public', True),
                    metadata={
                        'document_type': document_data.get('document_type', 'markdown'),  # markdown, html, plain_text
                        'auto_save_interval': document_data.get('auto_save_interval', 30),  # seconds
                        'version_control': document_data.get('version_control', True),
                        'conflict_resolution': document_data.get('conflict_resolution', 'operational_transform'),
                        'permissions': document_data.get('permissions', {
                            'default_role': 'editor',  # viewer, editor, owner
                            'allow_anonymous': False
                        })
                    }
                )
                
                db.session.add(collaboration_session)
                db.session.flush()  # Get the ID
                
                # Create the collaborative document
                document = CollaborativeDocument(
                    session_id=collaboration_session.id,
                    title=document_data.get('title', 'Untitled Document'),
                    content=document_data.get('initial_content', ''),
                    document_type=document_data.get('document_type', 'markdown'),
                    version=1,
                    metadata={
                        'created_by': document_data['creator_id'],
                        'initial_length': len(document_data.get('initial_content', '')),
                        'operation_counter': 0
                    }
                )
                
                db.session.add(document)
                db.session.flush()  # Get document ID
                
                # Add creator as owner participant
                creator_participant = SessionParticipant(
                    session_id=collaboration_session.id,
                    user_id=document_data['creator_id'],
                    role='owner',
                    status='joined',
                    metadata={
                        'permissions': ['read', 'write', 'admin', 'share'],
                        'cursor_position': 0
                    }
                )
                
                db.session.add(creator_participant)
                db.session.commit()
                
                # Emit WebSocket event for new document
                socketio.emit('document_created', {
                    'session_id': collaboration_session.id,
                    'document_id': document.id,
                    'title': document.title,
                    'creator': document_data['creator_id'],
                    'document_type': document.document_type
                }, namespace='/documents')
                
                logger.info(f"Created collaborative document {document.id} in session {collaboration_session.id}")
                
                return {
                    "success": True,
                    "session_id": collaboration_session.id,
                    "document_id": document.id,
                    "document": {
                        "id": document.id,
                        "title": document.title,
                        "content": document.content,
                        "document_type": document.document_type,
                        "version": document.version,
                        "created_at": document.created_at.isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Error creating collaborative document: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def join_document(session_id: int, user_id: int) -> Dict[str, Any]:
        """Join a collaborative document session"""
        # Database operations
            # Database operations
                # Check if session exists and is active
                collaboration_session = db.session.query(CollaborationSession).filter(
                    CollaborationSession.id == session_id,
                    CollaborationSession.is_active == True
                ).first()
                
                if not collaboration_session:
                    return {"success": False, "error": "Document session not found or inactive"}
                
                # Get the document
                document = db.session.query(CollaborativeDocument).filter(
                    CollaborativeDocument.session_id == session_id
                ).first()
                
                if not document:
                    return {"success": False, "error": "Document not found"}
                
                # Check if already joined
                existing_participant = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.user_id == user_id
                    )
                ).first()
                
                if existing_participant:
                    if existing_participant.status == 'left':
                        existing_participant.status = 'joined'
                        existing_participant.last_active = datetime.utcnow()
                    # Return document state regardless
                else:
                    # Check participant limit
                    current_participants = db.session.query(SessionParticipant).filter(
                        and_(
                            SessionParticipant.session_id == session_id,
                            SessionParticipant.status == 'joined'
                        )
                    ).count()
                    
                    if current_participants >= collaboration_session.max_participants:
                        return {"success": False, "error": "Document session is full"}
                    
                    # Determine default role
                    default_role = collaboration_session.metadata.get('permissions', {}).get('default_role', 'editor')
                    
                    # Add new participant
                    new_participant = SessionParticipant(
                        session_id=session_id,
                        user_id=user_id,
                        role=default_role,
                        status='joined',
                        metadata={
                            'permissions': ['read', 'write'] if default_role == 'editor' else ['read'],
                            'cursor_position': len(document.content)
                        }
                    )
                    db.session.add(new_participant)
                
                db.session.commit()
                
                # Get user info
                user = db.session.query(Users).filter(Users.id == user_id).first()
                
                # Get current active participants for presence
                active_participants = db.session.query(SessionParticipant).options(
                    joinedload(SessionParticipant.user)
                ).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.status == 'joined'
                    )
                ).all()
                
                participants_info = []
                for p in active_participants:
                    if p.user:
                        participants_info.append({
                            'user_id': p.user_id,
                            'username': p.user.username,
                            'role': p.role,
                            'cursor_position': p.metadata.get('cursor_position', 0) if p.metadata else 0,
                            'last_active': p.last_active.isoformat() if p.last_active else None
                        })
                
                # Emit WebSocket event to document room
                socketio.emit('user_joined', {
                    'session_id': session_id,
                    'document_id': document.id,
                    'user_id': user_id,
                    'username': user.username if user else 'Unknown',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"document_{session_id}", namespace='/documents')
                
                logger.info(f"User {user_id} joined document {document.id}")
                
                return {
                    "success": True,
                    "document": {
                        "id": document.id,
                        "title": document.title,
                        "content": document.content,
                        "document_type": document.document_type,
                        "version": document.version,
                        "last_modified": document.updated_at.isoformat() if document.updated_at else document.created_at.isoformat()
                    },
                    "participants": participants_info,
                    "permissions": existing_participant.metadata.get('permissions', []) if existing_participant and existing_participant.metadata else ['read', 'write']
                }
                
        except Exception as e:
            logger.error(f"Error joining document: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def apply_operation(operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an operational transform to the document"""
        # Database operations
            # Database operations
                # Verify user permissions
                participant = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == operation_data['session_id'],
                        SessionParticipant.user_id == operation_data['user_id'],
                        SessionParticipant.status == 'joined'
                    )
                ).first()
                
                if not participant:
                    return {"success": False, "error": "Not authorized to edit this document"}
                
                # Check write permissions
                permissions = participant.metadata.get('permissions', []) if participant.metadata else []
                if 'write' not in permissions:
                    return {"success": False, "error": "No write permissions for this document"}
                
                # Get the document
                document = db.session.query(CollaborativeDocument).filter(
                    CollaborativeDocument.session_id == operation_data['session_id']
                ).first()
                
                if not document:
                    return {"success": False, "error": "Document not found"}
                
                # Validate operation
                operation_type = operation_data.get('type')
                if operation_type not in ['insert', 'delete', 'retain']:
                    return {"success": False, "error": "Invalid operation type"}
                
                position = operation_data.get('position', 0)
                content_length = len(document.content)
                
                if position < 0 or position > content_length:
                    return {"success": False, "error": "Invalid operation position"}
                
                # Apply operational transform
                result = CollaborativeEditorService._apply_operational_transform(
                    document, operation_data
                )
                
                if not result['success']:
                    return result
                
                # Create operation record
                operation = DocumentOperation(
                    document_id=document.id,
                    user_id=operation_data['user_id'],
                    operation_type=operation_type,
                    position=position,
                    content=operation_data.get('content', ''),
                    length=operation_data.get('length', 0),
                    client_id=operation_data.get('client_id'),
                    operation_id=operation_data.get('operation_id', str(uuid.uuid4())),
                    metadata={
                        'document_version': document.version,
                        'timestamp': datetime.utcnow().isoformat(),
                        'cursor_after': operation_data.get('cursor_after', position)
                    }
                )
                
                db.session.add(operation)
                
                # Update document version and metadata
                document.version += 1
                document.updated_at = datetime.utcnow()
                if not document.metadata:
                    document.metadata = {}
                document.metadata['operation_counter'] = document.metadata.get('operation_counter', 0) + 1
                document.metadata['last_editor'] = operation_data['user_id']
                
                # Update participant cursor position
                if participant.metadata:
                    participant.metadata['cursor_position'] = operation_data.get('cursor_after', position)
                else:
                    participant.metadata = {'cursor_position': operation_data.get('cursor_after', position)}
                
                participant.last_active = datetime.utcnow()
                
                db.session.commit()
                
                # Broadcast operation to other participants
                socketio.emit('operation_applied', {
                    'session_id': operation_data['session_id'],
                    'document_id': document.id,
                    'operation': {
                        'id': operation.id,
                        'type': operation_type,
                        'position': position,
                        'content': operation_data.get('content', ''),
                        'length': operation_data.get('length', 0),
                        'user_id': operation_data['user_id'],
                        'operation_id': operation.operation_id,
                        'document_version': document.version
                    },
                    'document_version': document.version,
                    'timestamp': operation.created_at.isoformat()
                }, room=f"document_{operation_data['session_id']}", include_self=False, namespace='/documents')
                
                logger.info(f"Applied operation {operation.id} to document {document.id}")
                
                return {
                    "success": True,
                    "operation_id": operation.id,
                    "document_version": document.version,
                    "new_content": document.content
                }
                
        except Exception as e:
            logger.error(f"Error applying operation: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _apply_operational_transform(document: CollaborativeDocument, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply operational transform logic to document content"""
        # Database operations
            operation_type = operation_data['type']
            position = operation_data['position']
            content = document.content
            
            if operation_type == 'insert':
                # Insert text at position
                text_to_insert = operation_data.get('content', '')
                new_content = content[:position] + text_to_insert + content[position:]
                document.content = new_content
                
            elif operation_type == 'delete':
                # Delete specified length of text at position
                length = operation_data.get('length', 1)
                if position + length > len(content):
                    length = len(content) - position
                new_content = content[:position] + content[position + length:]
                document.content = new_content
                
            elif operation_type == 'retain':
                # Retain operation - no change to content, just cursor movement
                pass
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error in operational transform: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_cursor_position(session_id: int, user_id: int, position: int) -> Dict[str, Any]:
        """Update user's cursor position in the document"""
        # Database operations
            # Database operations
                participant = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.user_id == user_id,
                        SessionParticipant.status == 'joined'
                    )
                ).first()
                
                if not participant:
                    return {"success": False, "error": "Not a participant in this document"}
                
                # Update cursor position
                if not participant.metadata:
                    participant.metadata = {}
                participant.metadata['cursor_position'] = position
                participant.last_active = datetime.utcnow()
                
                db.session.commit()
                
                # Get user info for broadcast
                user = db.session.query(Users).filter(Users.id == user_id).first()
                
                # Broadcast cursor position to other participants
                socketio.emit('cursor_moved', {
                    'session_id': session_id,
                    'user_id': user_id,
                    'username': user.username if user else 'Unknown',
                    'position': position,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"document_{session_id}", include_self=False, namespace='/documents')
                
                return {"success": True}
                
        except Exception as e:
            logger.error(f"Error updating cursor position: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_document_version(session_id: int, user_id: int, version_name: str = None) -> Dict[str, Any]:
        """Create a named version/snapshot of the document"""
        # Database operations
            # Database operations
                # Verify permissions
                participant = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.user_id == user_id,
                        SessionParticipant.status == 'joined'
                    )
                ).first()
                
                if not participant:
                    return {"success": False, "error": "Not authorized to create versions"}
                
                # Get the document
                document = db.session.query(CollaborativeDocument).filter(
                    CollaborativeDocument.session_id == session_id
                ).first()
                
                if not document:
                    return {"success": False, "error": "Document not found"}
                
                # Create version snapshot
                version_name = version_name or f"Version {document.version} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                
                # Store version in document metadata
                if not document.metadata:
                    document.metadata = {}
                if 'versions' not in document.metadata:
                    document.metadata['versions'] = {}
                
                version_id = str(uuid.uuid4())
                document.metadata['versions'][version_id] = {
                    'name': version_name,
                    'content': document.content,
                    'version_number': document.version,
                    'created_by': user_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'content_length': len(document.content)
                }
                
                db.session.commit()
                
                # Emit version creation event
                socketio.emit('version_created', {
                    'session_id': session_id,
                    'document_id': document.id,
                    'version_id': version_id,
                    'version_name': version_name,
                    'created_by': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"document_{session_id}", namespace='/documents')
                
                logger.info(f"Created version {version_id} for document {document.id}")
                
                return {
                    "success": True,
                    "version_id": version_id,
                    "version_name": version_name
                }
                
        except Exception as e:
            logger.error(f"Error creating document version: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_document_history(session_id: int, user_id: int, limit: int = 100) -> Dict[str, Any]:
        """Get operation history for a document"""
        # Database operations
            # Database operations
                # Verify permissions
                participant = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.user_id == user_id
                    )
                ).first()
                
                if not participant:
                    return {"success": False, "error": "Not authorized to view document history"}
                
                # Get the document
                document = db.session.query(CollaborativeDocument).filter(
                    CollaborativeDocument.session_id == session_id
                ).first()
                
                if not document:
                    return {"success": False, "error": "Document not found"}
                
                # Get operations history
                operations = db.session.query(DocumentOperation).options(
                    joinedload(DocumentOperation.user)
                ).filter(
                    DocumentOperation.document_id == document.id
                ).order_by(desc(DocumentOperation.created_at)).limit(limit).all()
                
                # Format operations
                formatted_operations = []
                for op in operations:
                    formatted_operations.append({
                        'id': op.id,
                        'type': op.operation_type,
                        'position': op.position,
                        'content': op.content,
                        'length': op.length,
                        'user_id': op.user_id,
                        'username': op.user.username if op.user else 'Unknown',
                        'operation_id': op.operation_id,
                        'created_at': op.created_at.isoformat(),
                        'document_version': op.metadata.get('document_version') if op.metadata else None
                    })
                
                # Get saved versions
                versions = []
                if document.metadata and 'versions' in document.metadata:
                    for version_id, version_data in document.metadata['versions'].items():
                        versions.append({
                            'id': version_id,
                            'name': version_data['name'],
                            'version_number': version_data['version_number'],
                            'created_by': version_data['created_by'],
                            'created_at': version_data['created_at'],
                            'content_length': version_data['content_length']
                        })
                
                return {
                    "success": True,
                    "document": {
                        "id": document.id,
                        "title": document.title,
                        "current_version": document.version,
                        "content_length": len(document.content),
                        "created_at": document.created_at.isoformat(),
                        "updated_at": document.updated_at.isoformat() if document.updated_at else None
                    },
                    "operations": formatted_operations,
                    "versions": versions,
                    "total_operations": document.metadata.get('operation_counter', 0) if document.metadata else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting document history: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def leave_document(session_id: int, user_id: int) -> Dict[str, Any]:
        """Leave a collaborative document session"""
        # Database operations
            # Database operations
                participant = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.user_id == user_id,
                        SessionParticipant.status == 'joined'
                    )
                ).first()
                
                if not participant:
                    return {"success": False, "error": "Not a participant in this document"}
                
                participant.status = 'left'
                participant.last_active = datetime.utcnow()
                db.session.commit()
                
                # Get user info
                user = db.session.query(Users).filter(Users.id == user_id).first()
                
                # Emit WebSocket event
                socketio.emit('user_left', {
                    'session_id': session_id,
                    'user_id': user_id,
                    'username': user.username if user else 'Unknown',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"document_{session_id}", namespace='/documents')
                
                logger.info(f"User {user_id} left document session {session_id}")
                
                return {"success": True, "message": "Left document successfully"}
                
        except Exception as e:
            logger.error(f"Error leaving document: {str(e)}")
            return {"success": False, "error": str(e)}
