# app/routes/stages/master/code_playground_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.stages.master.code_playground_service import CodePlaygroundService
import logging

log = logging.getLogger(__name__)

code_playground_bp = Blueprint('code_playground', __name__)
service = CodePlaygroundService()


@code_playground_bp.route('/info', methods=['GET'])
@jwt_required()
def get_info():
    """Get Code Playground service information."""
    return jsonify({
        'service': 'Code Playground for Kids',
        'description': 'Interactive coding environment for children to learn programming through fun exercises',
        'games': [
            {
                'id': 'turtle_graphics',
                'name': 'Turtle Graphics Adventure',
                'description': 'Learn programming by controlling a turtle to draw shapes and patterns',
                'difficulty': 'beginner',
                'languages': ['python', 'javascript']
            },
            {
                'id': 'code_blocks',
                'name': 'Block-Based Coding',
                'description': 'Drag and drop blocks to create programs',
                'difficulty': 'beginner',
                'status': 'coming_soon'
            }
        ],
        'features': [
            'Safe code execution in sandboxed environment',
            'Visual output with canvas/turtle graphics',
            'Step-by-step tutorials and challenges',
            'AI-powered hints and debugging help',
            'Achievement system and progress tracking'
        ]
    }), 200


@code_playground_bp.route('/turtle/start', methods=['POST'])
@jwt_required()
def start_turtle_session():
    """
    Start a new turtle graphics session.
    
    Request body:
    {
        "challenge_id": "draw_square" | "draw_triangle" | "spiral" | "custom",
        "language": "python" | "javascript"
    }
    """
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        challenge_id = data.get('challenge_id', 'custom')
        language = data.get('language', 'python')
        
        # Validate inputs
        if language not in ['python', 'javascript']:
            return jsonify({'error': 'Invalid language. Must be python or javascript'}), 400
        
        result = service.start_turtle_session(
            user_id=user_id,
            challenge_id=challenge_id,
            language=language
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        log.error(f"Error starting turtle session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to start session'}), 500


@code_playground_bp.route('/turtle/execute', methods=['POST'])
@jwt_required()
def execute_turtle_code():
    """
    Execute turtle graphics code.
    
    Request body:
    {
        "session_id": "uuid",
        "code": "turtle code string",
        "language": "python" | "javascript"
    }
    """
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        session_id = data.get('session_id')
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        if not code.strip():
            return jsonify({'error': 'code cannot be empty'}), 400
        
        result = service.execute_turtle_code(
            session_id=session_id,
            code=code,
            language=language,
            user_id=user_id
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        log.error(f"Error executing turtle code: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to execute code'}), 500


@code_playground_bp.route('/turtle/hint', methods=['POST'])
@jwt_required()
def get_turtle_hint():
    """
    Get AI-powered hint for current challenge.
    
    Request body:
    {
        "session_id": "uuid",
        "code": "current code",
        "error_message": "optional error message"
    }
    """
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        session_id = data.get('session_id')
        code = data.get('code', '')
        error_message = data.get('error_message')
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        result = service.get_turtle_hint(
            session_id=session_id,
            code=code,
            error_message=error_message,
            user_id=user_id
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        log.error(f"Error getting hint: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get hint'}), 500


@code_playground_bp.route('/turtle/validate', methods=['POST'])
@jwt_required()
def validate_turtle_solution():
    """
    Validate solution against challenge requirements.
    
    Request body:
    {
        "session_id": "uuid",
        "code": "solution code",
        "output": "execution output/drawing commands"
    }
    """
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        session_id = data.get('session_id')
        code = data.get('code', '')
        output = data.get('output', [])
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        result = service.validate_turtle_solution(
            session_id=session_id,
            code=code,
            output=output,
            user_id=user_id
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        log.error(f"Error validating solution: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to validate solution'}), 500


@code_playground_bp.route('/turtle/challenges', methods=['GET'])
@jwt_required()
def get_turtle_challenges():
    """Get list of available turtle graphics challenges."""
    try:
        challenges = service.get_turtle_challenges()
        return jsonify({'challenges': challenges}), 200
        
    except Exception as e:
        log.error(f"Error getting challenges: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get challenges'}), 500


@code_playground_bp.route('/turtle/end', methods=['POST'])
@jwt_required()
def end_turtle_session():
    """
    End turtle session and get statistics.
    
    Request body:
    {
        "session_id": "uuid"
    }
    """
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        result = service.end_turtle_session(
            session_id=session_id,
            user_id=user_id
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        log.error(f"Error ending session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to end session'}), 500
