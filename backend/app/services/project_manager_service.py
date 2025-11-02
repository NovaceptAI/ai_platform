"""
Project Manager Service for Collaborate Stage
Handles group project coordination, task management, and timeline tracking
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import joinedload
from app.db import db
from app.models.collaboration import (
    CollaborationSession, SessionParticipant, 
    ProjectTask, CollaborationNotification
)
from app.models.users import Users
from app.models.learning_paths import LearningPath
from app.services.websocket_service import socketio
# import uuid

logger = logging.getLogger(__name__)

class ProjectManagerService:
    """Service for managing collaborative projects and task coordination"""
    
    @staticmethod
    def create_project(project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new collaborative project"""
        # Database operations
        try:
            # Database operations
            # Validate learning path exists
            learning_path = db.session.query(LearningPath).filter(
                LearningPath.id == project_data['learning_path_id']
            ).first()
            
            if not learning_path:
                return {"success": False, "error": "Learning path not found"}
            
            # Create collaboration session for project management
            collaboration_session = CollaborationSession(
                learning_path_id=project_data['learning_path_id'],
                creator_id=project_data['creator_id'],
                session_type='project_management',
                title=project_data.get('title', f"Project: {learning_path.title}"),
                description=project_data.get('description'),
                max_participants=project_data.get('max_participants', 10),
                is_active=True,
                is_public=project_data.get('is_public', True),
                metadata={
                    'project_type': project_data.get('project_type', 'collaborative'),  # collaborative, research, creative
                    'deadline': project_data.get('deadline'),
                    'milestones': project_data.get('milestones', []),
                    'deliverables': project_data.get('deliverables', []),
                    'project_status': 'planning',  # planning, active, review, completed
                    'methodology': project_data.get('methodology', 'agile'),  # agile, waterfall, custom
                    'progress_tracking': {
                        'total_tasks': 0,
                        'completed_tasks': 0,
                        'in_progress_tasks': 0,
                        'overdue_tasks': 0
                    }
                }
            )
            
            db.session.add(collaboration_session)
            db.session.flush()  # Get the ID
            
            # Add creator as project manager
            creator_participant = SessionParticipant(
                session_id=collaboration_session.id,
                user_id=project_data['creator_id'],
                role='project_manager',
                status='joined',
                metadata={
                    'responsibilities': ['project_oversight', 'task_assignment', 'timeline_management'],
                    'workload_capacity': project_data.get('creator_capacity', 40)  # hours per week
                }
            )
            
            db.session.add(creator_participant)
            db.session.commit()
            
            # Emit WebSocket event for new project
            socketio.emit('project_created', {
                'session_id': collaboration_session.id,
                'title': collaboration_session.title,
                'creator': project_data['creator_id'],
                'learning_path_id': collaboration_session.learning_path_id,
                'project_type': collaboration_session.metadata.get('project_type'),
                'deadline': project_data.get('deadline')
            }, namespace='/collaborate')
            
            logger.info(f"Created collaborative project {collaboration_session.id}")
            
            return {
                "success": True,
                "session_id": collaboration_session.id,
                "project": {
                    "id": collaboration_session.id,
                    "title": collaboration_session.title,
                    "description": collaboration_session.description,
                    "creator_id": collaboration_session.creator_id,
                    "project_type": collaboration_session.metadata.get('project_type'),
                    "deadline": project_data.get('deadline'),
                    "status": collaboration_session.metadata.get('project_status'),
                    "is_active": collaboration_session.is_active
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def join_project(session_id: int, user_id: int, role: str = 'member') -> Dict[str, Any]:
        """Add a user to a project"""
        # Database operations
        try:
            # Database operations
            # Check if session exists and is active
            collaboration_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id,
                CollaborationSession.is_active == True
            ).first()
            
            if not collaboration_session:
                return {"success": False, "error": "Project not found or inactive"}
            
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
                else:
                    return {"success": False, "error": "Already joined this project"}
            else:
                # Check participant limit
                current_participants = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.status == 'joined'
                    )
                ).count()
                
                if current_participants >= collaboration_session.max_participants:
                    return {"success": False, "error": "Project is full"}
                
                # Validate role
                valid_roles = ['member', 'contributor', 'lead', 'specialist']
                if role not in valid_roles:
                    role = 'member'
                
                # Add new participant
                new_participant = SessionParticipant(
                    session_id=session_id,
                    user_id=user_id,
                    role=role,
                    status='joined',
                    metadata={
                        'responsibilities': [],
                        'workload_capacity': 20,  # default hours per week
                        'skills': [],
                        'availability': {}
                    }
                )
                db.session.add(new_participant)
            
            db.session.commit()
            
            # Get user info
            user = db.session.query(Users).filter(Users.id == user_id).first()
            
            # Emit WebSocket event
            socketio.emit('member_joined', {
                'session_id': session_id,
                'user_id': user_id,
                'username': user.username if user else 'Unknown',
                'role': role,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"project_{session_id}", namespace='/collaborate')
            
            logger.info(f"User {user_id} joined project {session_id} as {role}")
            
            return {"success": True, "message": f"Joined project as {role}"}
                
        except Exception as e:
            logger.error(f"Error joining project: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project task"""
        # Database operations
        try:
            # Database operations
            # Verify user is project participant with appropriate permissions
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == task_data['session_id'],
                    SessionParticipant.user_id == task_data['creator_id'],
                    SessionParticipant.status == 'joined'
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to create tasks in this project"}
            
            # Check if user can create tasks (project_manager, lead roles)
            if participant.role not in ['project_manager', 'lead']:
                return {"success": False, "error": "Insufficient permissions to create tasks"}
            
            # Validate assignee if provided
            assignee_id = task_data.get('assignee_id')
            if assignee_id:
                assignee = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == task_data['session_id'],
                        SessionParticipant.user_id == assignee_id,
                        SessionParticipant.status == 'joined'
                    )
                ).first()
                
                if not assignee:
                    return {"success": False, "error": "Assignee is not a project member"}
            
            # Create task
            task = ProjectTask(
                session_id=task_data['session_id'],
                title=task_data['title'],
                description=task_data.get('description', ''),
                assignee_id=assignee_id,
                created_by=task_data['creator_id'],
                status='todo',  # todo, in_progress, review, completed, cancelled
                priority=task_data.get('priority', 'medium'),  # low, medium, high, urgent
                due_date=datetime.fromisoformat(task_data['due_date'].replace('Z', '+00:00')) if task_data.get('due_date') else None,
                estimated_hours=task_data.get('estimated_hours', 0),
                metadata={
                    'tags': task_data.get('tags', []),
                    'dependencies': task_data.get('dependencies', []),  # task IDs this depends on
                    'checklist': task_data.get('checklist', []),
                    'files': task_data.get('files', []),
                    'comments_count': 0
                }
            )
            
            db.session.add(task)
            db.session.flush()  # Get task ID
            
            # Update project progress tracking
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == task_data['session_id']
            ).first()
            
            if collab_session and collab_session.metadata:
                progress = collab_session.metadata.get('progress_tracking', {})
                progress['total_tasks'] = progress.get('total_tasks', 0) + 1
                collab_session.metadata['progress_tracking'] = progress
            
            db.session.commit()
            
            # Create notification for assignee
            if assignee_id and assignee_id != task_data['creator_id']:
                notification = CollaborationNotification(
                    user_id=assignee_id,
                    session_id=task_data['session_id'],
                    notification_type='task_assigned',
                    title='New Task Assigned',
                    message=f'You have been assigned task: "{task.title}"',
                    metadata={'task_id': task.id, 'due_date': task_data.get('due_date')}
                )
                db.session.add(notification)
                db.session.commit()
            
            # Emit WebSocket event
            socketio.emit('task_created', {
                'session_id': task_data['session_id'],
                'task_id': task.id,
                'title': task.title,
                'assignee_id': assignee_id,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'created_by': task_data['creator_id']
            }, room=f"project_{task_data['session_id']}", namespace='/collaborate')
            
            logger.info(f"Created task {task.id} in project {task_data['session_id']}")
            
            return {
                "success": True,
                "task_id": task.id,
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "assignee_id": task.assignee_id,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "estimated_hours": task.estimated_hours,
                    "created_at": task.created_at.isoformat()
                }
            }
                
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_task_status(task_id: int, user_id: int, new_status: str, progress_notes: str = None) -> Dict[str, Any]:
        """Update task status and progress"""
        # Database operations
        try:
            # Database operations
            # Get task
            task = db.session.query(ProjectTask).filter(
                ProjectTask.id == task_id
            ).first()
            
            if not task:
                return {"success": False, "error": "Task not found"}
            
            # Check permissions (assignee, creator, or project manager can update)
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == task.session_id,
                    SessionParticipant.user_id == user_id,
                    SessionParticipant.status == 'joined'
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to update this task"}
            
            can_update = (
                task.assignee_id == user_id or 
                task.created_by == user_id or 
                participant.role in ['project_manager', 'lead']
            )
            
            if not can_update:
                return {"success": False, "error": "Insufficient permissions to update task"}
            
            # Validate status
            valid_statuses = ['todo', 'in_progress', 'review', 'completed', 'cancelled']
            if new_status not in valid_statuses:
                return {"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}
            
            old_status = task.status
            task.status = new_status
            task.updated_at = datetime.utcnow()
            
            # Update completion date if completed
            if new_status == 'completed' and old_status != 'completed':
                task.completed_at = datetime.utcnow()
            elif new_status != 'completed':
                task.completed_at = None
            
            # Add progress note to metadata
            if progress_notes:
                if not task.metadata:
                    task.metadata = {}
                if 'progress_notes' not in task.metadata:
                    task.metadata['progress_notes'] = []
                
                task.metadata['progress_notes'].append({
                    'note': progress_notes,
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'status_change': f"{old_status} -> {new_status}"
                })
            
            # Update project progress tracking
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == task.session_id
            ).first()
            
            if collab_session and collab_session.metadata:
                progress = collab_session.metadata.get('progress_tracking', {})
                
                # Recalculate task counts
                all_tasks = db.session.query(ProjectTask).filter(
                    ProjectTask.session_id == task.session_id
                ).all()
                
                progress['total_tasks'] = len(all_tasks)
                progress['completed_tasks'] = len([t for t in all_tasks if t.status == 'completed'])
                progress['in_progress_tasks'] = len([t for t in all_tasks if t.status == 'in_progress'])
                progress['overdue_tasks'] = len([t for t in all_tasks if t.due_date and t.due_date < datetime.utcnow() and t.status not in ['completed', 'cancelled']])
                
                collab_session.metadata['progress_tracking'] = progress
            
            db.session.commit()
            
            # Emit WebSocket event
            socketio.emit('task_updated', {
                'session_id': task.session_id,
                'task_id': task.id,
                'title': task.title,
                'old_status': old_status,
                'new_status': new_status,
                'updated_by': user_id,
                'progress_notes': progress_notes,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"project_{task.session_id}", namespace='/collaborate')
            
            logger.info(f"Updated task {task_id} status from {old_status} to {new_status}")
            
            return {
                "success": True,
                "message": f"Task status updated to {new_status}",
                "task": {
                    "id": task.id,
                    "status": task.status,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_project_overview(session_id: int, user_id: int) -> Dict[str, Any]:
        """Get comprehensive project overview"""
        # Database operations
        try:
            # Database operations
            # Verify user is participant
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to view this project"}
            
            # Get project details
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Project not found"}
            
            # Get all participants
            participants = db.session.query(SessionParticipant).options(
                joinedload(SessionParticipant.user)
            ).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.status == 'joined'
                )
            ).all()
            
            # Get all tasks
            tasks = db.session.query(ProjectTask).options(
                joinedload(ProjectTask.assignee)
            ).filter(
                ProjectTask.session_id == session_id
            ).order_by(ProjectTask.created_at.desc()).all()
            
            # Format participants
            formatted_participants = []
            for p in participants:
                if p.user:
                    formatted_participants.append({
                        'user_id': p.user_id,
                        'username': p.user.username,
                        'role': p.role,
                        'responsibilities': p.metadata.get('responsibilities', []) if p.metadata else [],
                        'workload_capacity': p.metadata.get('workload_capacity', 0) if p.metadata else 0,
                        'last_active': p.last_active.isoformat() if p.last_active else None
                    })
            
            # Format tasks
            formatted_tasks = []
            for task in tasks:
                formatted_tasks.append({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'assignee_id': task.assignee_id,
                    'assignee_name': task.assignee.username if task.assignee else None,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'estimated_hours': task.estimated_hours,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'is_overdue': task.due_date and task.due_date < datetime.utcnow() and task.status not in ['completed', 'cancelled'],
                    'tags': task.metadata.get('tags', []) if task.metadata else []
                })
            
            # Calculate project statistics
            progress = collab_session.metadata.get('progress_tracking', {}) if collab_session.metadata else {}
            
            return {
                "success": True,
                "project": {
                    "id": collab_session.id,
                    "title": collab_session.title,
                    "description": collab_session.description,
                    "creator_id": collab_session.creator_id,
                    "project_type": collab_session.metadata.get('project_type') if collab_session.metadata else None,
                    "status": collab_session.metadata.get('project_status') if collab_session.metadata else None,
                    "deadline": collab_session.metadata.get('deadline') if collab_session.metadata else None,
                    "methodology": collab_session.metadata.get('methodology') if collab_session.metadata else None,
                    "created_at": collab_session.created_at.isoformat(),
                    "is_active": collab_session.is_active
                },
                "participants": formatted_participants,
                "tasks": formatted_tasks,
                "statistics": {
                    "total_participants": len(formatted_participants),
                    "total_tasks": progress.get('total_tasks', 0),
                    "completed_tasks": progress.get('completed_tasks', 0),
                    "in_progress_tasks": progress.get('in_progress_tasks', 0),
                    "overdue_tasks": progress.get('overdue_tasks', 0),
                    "completion_rate": round((progress.get('completed_tasks', 0) / max(progress.get('total_tasks', 1), 1)) * 100, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting project overview: {str(e)}")
            return {"success": False, "error": str(e)}
