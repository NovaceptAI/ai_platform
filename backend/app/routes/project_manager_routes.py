"""
Project Manager Routes for Collaborate Stage
Handles REST API endpoints for project management and task coordination
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.project_manager_service import ProjectManagerService

logger = logging.getLogger(__name__)

# Create blueprint for project management routes
project_manager_bp = Blueprint('project_manager', __name__, url_prefix='/api/collaborate/projects')

# REST API Endpoints

@project_manager_bp.route('/create', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new collaborative project"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['learning_path_id', 'title']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate deadline format if provided
        if 'deadline' in data and data['deadline']:
            try:
                datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid deadline format. Use ISO format"}), 400
        
        # Add creator_id to data
        data['creator_id'] = user_id
        
        result = ProjectManagerService.create_project(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@project_manager_bp.route('/<int:session_id>/join', methods=['POST'])
@jwt_required()
def join_project(session_id):
    """Join a project"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        role = data.get('role', 'member')
        valid_roles = ['member', 'contributor', 'lead', 'specialist']
        
        if role not in valid_roles:
            return jsonify({"error": f"Invalid role. Must be one of: {valid_roles}"}), 400
        
        result = ProjectManagerService.join_project(session_id, user_id, role)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error joining project: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@project_manager_bp.route('/<int:session_id>/overview', methods=['GET'])
@jwt_required()
def get_project_overview(session_id):
    """Get project overview"""
    try:
        user_id = get_jwt_identity()
        
        result = ProjectManagerService.get_project_overview(session_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error getting project overview: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@project_manager_bp.route('/<int:session_id>/tasks', methods=['POST'])
@jwt_required()
def create_task(session_id):
    """Create a new task in the project"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'title' not in data:
            return jsonify({"error": "Task title is required"}), 400
        
        if len(data['title'].strip()) == 0:
            return jsonify({"error": "Task title cannot be empty"}), 400
        
        # Validate due_date format if provided
        if 'due_date' in data and data['due_date']:
            try:
                datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid due_date format. Use ISO format"}), 400
        
        task_data = {
            'session_id': session_id,
            'creator_id': user_id,
            'title': data['title'].strip(),
            'description': data.get('description', '').strip(),
            'assignee_id': data.get('assignee_id'),
            'priority': data.get('priority', 'medium'),
            'due_date': data.get('due_date'),
            'estimated_hours': data.get('estimated_hours', 0),
            'tags': data.get('tags', []),
            'dependencies': data.get('dependencies', []),
            'checklist': data.get('checklist', [])
        }
        
        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if task_data['priority'] not in valid_priorities:
            return jsonify({"error": f"Invalid priority. Must be one of: {valid_priorities}"}), 400
        
        result = ProjectManagerService.create_task(task_data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@project_manager_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@jwt_required()
def update_task_status(task_id):
    """Update task status"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({"error": "New status is required"}), 400
        
        new_status = data['status']
        valid_statuses = ['todo', 'in_progress', 'review', 'completed', 'cancelled']
        
        if new_status not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400
        
        progress_notes = data.get('progress_notes', '').strip()
        
        result = ProjectManagerService.update_task_status(
            task_id, user_id, new_status, progress_notes or None
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Export the blueprint
__all__ = ['project_manager_bp']
