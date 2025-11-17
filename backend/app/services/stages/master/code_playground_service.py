# app/services/stages/master/code_playground_service.py

import os
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import redis

# OpenAI for hints and code assistance
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Redis configuration for session storage
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_EXPIRY = 3600  # 1 hour expiry for sessions


class CodePlaygroundService:
    """
    Service for Code Playground for Kids.
    Focuses on Turtle Graphics as the first interactive coding game.
    
    Design: Stateless with Redis session storage for multi-worker support.
    """
    
    def __init__(self):
        # Use Redis for session storage (works across multiple gunicorn workers)
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()  # Test connection
            log.info("Code Playground connected to Redis for session storage")
        except Exception as e:
            log.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
        
        # Initialize turtle challenges
        self._init_turtle_challenges()
    
    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        if not self.redis_client:
            return None
        try:
            session_key = f"code_playground:session:{session_id}"
            data = self.redis_client.get(session_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            log.error(f"Error getting session {session_id}: {e}")
            return None
    
    def _set_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Save session data to Redis with expiry."""
        if not self.redis_client:
            return False
        try:
            session_key = f"code_playground:session:{session_id}"
            self.redis_client.setex(
                session_key,
                SESSION_EXPIRY,
                json.dumps(session_data)
            )
            return True
        except Exception as e:
            log.error(f"Error saving session {session_id}: {e}")
            return False
    
    def _delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        if not self.redis_client:
            return False
        try:
            session_key = f"code_playground:session:{session_id}"
            self.redis_client.delete(session_key)
            return True
        except Exception as e:
            log.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def _init_turtle_challenges(self):
        """Initialize turtle graphics challenges."""
        # Turtle Graphics Challenges
        self.turtle_challenges = {
            'draw_square': {
                'id': 'draw_square',
                'name': 'Draw a Square',
                'description': 'Use turtle commands to draw a perfect square',
                'difficulty': 'easy',
                'instructions': [
                    'Move the turtle forward',
                    'Turn right 90 degrees',
                    'Repeat 4 times to make a square'
                ],
                'starter_code_python': '''# Draw a square
# Use forward(distance) to move
# Use right(angle) to turn

# Your code here:
''',
                'starter_code_javascript': '''// Draw a square
// Use forward(distance) to move
// Use right(angle) to turn

// Your code here:
''',
                'validation_criteria': {
                    'min_moves': 4,
                    'turns': 4,
                    'shape': 'square'
                },
                'hints': [
                    'A square has 4 equal sides',
                    'Each corner is a 90-degree turn',
                    'Try using a loop to repeat the pattern'
                ]
            },
            'draw_triangle': {
                'id': 'draw_triangle',
                'name': 'Draw a Triangle',
                'description': 'Create an equilateral triangle using turtle graphics',
                'difficulty': 'easy',
                'instructions': [
                    'Move the turtle forward',
                    'Turn right 120 degrees',
                    'Repeat 3 times to make a triangle'
                ],
                'starter_code_python': '''# Draw an equilateral triangle
# Each angle in a triangle is 120 degrees

# Your code here:
''',
                'starter_code_javascript': '''// Draw an equilateral triangle
// Each angle in a triangle is 120 degrees

// Your code here:
''',
                'validation_criteria': {
                    'min_moves': 3,
                    'turns': 3,
                    'shape': 'triangle'
                },
                'hints': [
                    'A triangle has 3 sides',
                    'Each exterior angle is 120 degrees',
                    'Use a loop for cleaner code'
                ]
            },
            'draw_star': {
                'id': 'draw_star',
                'name': 'Draw a Star',
                'description': 'Draw a 5-pointed star',
                'difficulty': 'medium',
                'instructions': [
                    'Move the turtle forward',
                    'Turn right 144 degrees',
                    'Repeat 5 times to make a star'
                ],
                'starter_code_python': '''# Draw a 5-pointed star
# Star tip angle is 144 degrees

# Your code here:
''',
                'starter_code_javascript': '''// Draw a 5-pointed star
// Star tip angle is 144 degrees

// Your code here:
''',
                'validation_criteria': {
                    'min_moves': 5,
                    'turns': 5,
                    'shape': 'star'
                },
                'hints': [
                    'A star has 5 points',
                    'Turn 144 degrees at each point',
                    'All sides should be equal length'
                ]
            },
            'spiral': {
                'id': 'spiral',
                'name': 'Create a Spiral',
                'description': 'Draw a beautiful spiral pattern',
                'difficulty': 'medium',
                'instructions': [
                    'Start with a small forward movement',
                    'Increase the distance each time',
                    'Turn and repeat to create a spiral'
                ],
                'starter_code_python': '''# Draw a spiral
# Increase distance with each step

# Your code here:
''',
                'starter_code_javascript': '''// Draw a spiral
// Increase distance with each step

// Your code here:
''',
                'validation_criteria': {
                    'min_moves': 10,
                    'increasing_distances': True,
                    'shape': 'spiral'
                },
                'hints': [
                    'Use a loop with an increasing variable',
                    'Each forward movement should be longer than the last',
                    'Try turning the same angle each time'
                ]
            },
            'rainbow_circle': {
                'id': 'rainbow_circle',
                'name': 'Rainbow Circles',
                'description': 'Draw multiple colorful circles',
                'difficulty': 'hard',
                'instructions': [
                    'Change the pen color',
                    'Draw a circle',
                    'Move to a new position',
                    'Repeat with different colors'
                ],
                'starter_code_python': '''# Draw rainbow circles
# Use color(name) to change colors
# Use circle(radius) to draw circles

# Your code here:
''',
                'starter_code_javascript': '''// Draw rainbow circles
// Use color(name) to change colors
// Use circle(radius) to draw circles

// Your code here:
''',
                'validation_criteria': {
                    'min_circles': 3,
                    'different_colors': True,
                    'shape': 'circles'
                },
                'hints': [
                    'Try colors like "red", "blue", "green", "yellow"',
                    'Use penup() and pendown() to move without drawing',
                    'Change position between circles'
                ]
            },
            'custom': {
                'id': 'custom',
                'name': 'Free Drawing',
                'description': 'Create your own masterpiece!',
                'difficulty': 'any',
                'instructions': [
                    'Use your imagination!',
                    'Try different turtle commands',
                    'Experiment with colors and shapes'
                ],
                'starter_code_python': '''# Free drawing mode
# Available commands:
# forward(distance), backward(distance)
# right(angle), left(angle)
# color(name), penup(), pendown()
# circle(radius), goto(x, y)

# Your code here:
''',
                'starter_code_javascript': '''// Free drawing mode
// Available commands:
// forward(distance), backward(distance)
// right(angle), left(angle)
// color(name), penup(), pendown()
// circle(radius), goto(x, y)

// Your code here:
''',
                'validation_criteria': {},
                'hints': [
                    'Try combining different shapes',
                    'Experiment with loops and patterns',
                    'Use colors to make it more interesting'
                ]
            }
        }
    
    def start_turtle_session(self, user_id: str, challenge_id: str, language: str) -> Dict[str, Any]:
        """
        Start a new turtle graphics session.
        """
        session_id = str(uuid.uuid4())
        
        # Get challenge details
        challenge = self.turtle_challenges.get(challenge_id)
        if not challenge:
            raise ValueError(f"Invalid challenge_id: {challenge_id}")
        
        # Select starter code based on language
        starter_code = challenge.get(f'starter_code_{language}', '')
        
        # Create session
        session = {
            'session_id': session_id,
            'user_id': user_id,
            'challenge_id': challenge_id,
            'language': language,
            'start_time': datetime.utcnow().isoformat(),
            'executions': 0,
            'hints_used': 0,
            'completed': False,
            'code_history': []
        }
        
        # Save session to Redis
        self._set_session(session_id, session)
        
        return {
            'session_id': session_id,
            'challenge': {
                'id': challenge['id'],
                'name': challenge['name'],
                'description': challenge['description'],
                'difficulty': challenge['difficulty'],
                'instructions': challenge['instructions']
            },
            'starter_code': starter_code,
            'language': language,
            'available_commands': self._get_turtle_commands(language)
        }
    
    def execute_turtle_code(self, session_id: str, code: str, language: str, user_id: str) -> Dict[str, Any]:
        """
        Execute turtle graphics code and return drawing commands.
        
        Note: Actual code execution would be done client-side for safety.
        This method validates and tracks execution.
        """
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session_id")
        
        if session['user_id'] != user_id:
            raise ValueError("Unauthorized access to session")
        
        # Update session
        session['executions'] += 1
        session['code_history'].append({
            'code': code,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Save updated session
        self._set_session(session_id, session)
        
        # In a real implementation, we'd parse the code safely
        # For now, return success and let client handle execution
        return {
            'success': True,
            'message': 'Code ready for execution',
            'execution_id': str(uuid.uuid4()),
            'session_id': session_id,
            'executions': session['executions'],
            'note': 'Execute code in browser sandbox for safety'
        }
    
    def get_turtle_hint(self, session_id: str, code: str, error_message: Optional[str], user_id: str) -> Dict[str, Any]:
        """
        Get AI-powered hint for turtle graphics challenge.
        """
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session_id")
        
        if session['user_id'] != user_id:
            raise ValueError("Unauthorized access to session")
        
        challenge_id = session['challenge_id']
        challenge = self.turtle_challenges.get(challenge_id)
        language = session['language']
        
        # Increment hints counter
        session['hints_used'] += 1
        hint_number = session['hints_used']
        
        # Save updated session
        self._set_session(session_id, session)
        
        # Get pre-defined hints first
        predefined_hints = challenge.get('hints', [])
        if hint_number <= len(predefined_hints):
            hint = predefined_hints[hint_number - 1]
            return {
                'hint': hint,
                'hints_used': hint_number,
                'type': 'predefined'
            }
        
        # Generate AI hint
        try:
            ai_hint = self._generate_ai_hint(
                challenge=challenge,
                code=code,
                error_message=error_message,
                language=language
            )
            
            return {
                'hint': ai_hint,
                'hints_used': hint_number,
                'type': 'ai_generated'
            }
            
        except Exception as e:
            log.error(f"Error generating AI hint: {str(e)}", exc_info=True)
            # Fallback to generic hint
            return {
                'hint': "Try breaking down the problem into smaller steps. What shape are you trying to create?",
                'hints_used': hint_number,
                'type': 'fallback'
            }
    
    def validate_turtle_solution(self, session_id: str, code: str, output: List[Dict], user_id: str) -> Dict[str, Any]:
        """
        Validate turtle graphics solution against challenge criteria.
        """
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session_id")
        
        if session['user_id'] != user_id:
            raise ValueError("Unauthorized access to session")
        
        challenge_id = session['challenge_id']
        challenge = self.turtle_challenges.get(challenge_id)
        criteria = challenge.get('validation_criteria', {})
        
        # If no criteria (custom mode), always pass
        if not criteria:
            session['completed'] = True
            self._set_session(session_id, session)
            return {
                'valid': True,
                'completed': True,
                'message': 'Great job! Your drawing looks awesome!',
                'feedback': []
            }
        
        # Validate against criteria
        feedback = []
        valid = True
        
        # Count moves and turns from output
        moves = sum(1 for cmd in output if cmd.get('type') in ['forward', 'backward'])
        turns = sum(1 for cmd in output if cmd.get('type') in ['right', 'left'])
        
        if 'min_moves' in criteria and moves < criteria['min_moves']:
            valid = False
            feedback.append(f"Need at least {criteria['min_moves']} forward movements")
        
        if 'turns' in criteria and turns < criteria['turns']:
            valid = False
            feedback.append(f"Need {criteria['turns']} turns to complete the shape")
        
        if valid:
            session['completed'] = True
            self._set_session(session_id, session)
            
        return {
            'valid': valid,
            'completed': valid,
            'message': 'Excellent work! Challenge completed!' if valid else 'Keep trying! You\'re close!',
            'feedback': feedback,
            'stats': {
                'moves': moves,
                'turns': turns,
                'executions': session['executions'],
                'hints_used': session['hints_used']
            }
        }
    
    def get_turtle_challenges(self) -> List[Dict[str, Any]]:
        """Get list of available turtle graphics challenges."""
        return [
            {
                'id': ch['id'],
                'name': ch['name'],
                'description': ch['description'],
                'difficulty': ch['difficulty']
            }
            for ch in self.turtle_challenges.values()
        ]
    
    def end_turtle_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """End session and return statistics."""
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session_id")
        
        if session['user_id'] != user_id:
            raise ValueError("Unauthorized access to session")
        
        # Calculate duration
        start_time = datetime.fromisoformat(session['start_time'])
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Prepare statistics
        stats = {
            'session_id': session_id,
            'challenge_id': session['challenge_id'],
            'completed': session['completed'],
            'duration_seconds': int(duration),
            'executions': session['executions'],
            'hints_used': session['hints_used'],
            'code_iterations': len(session['code_history'])
        }
        
        # Achievements
        achievements = []
        if session['completed']:
            achievements.append({
                'name': 'Challenge Complete',
                'description': 'Successfully completed the challenge!'
            })
        
        if session['hints_used'] == 0 and session['completed']:
            achievements.append({
                'name': 'No Hints Needed',
                'description': 'Completed without using any hints!'
            })
        
        if session['executions'] <= 3 and session['completed']:
            achievements.append({
                'name': 'First Try Pro',
                'description': 'Completed in 3 tries or less!'
            })
        
        # Clean up session from Redis
        self._delete_session(session_id)
        
        return {
            'statistics': stats,
            'achievements': achievements,
            'message': 'Great coding session! Keep practicing!' if session['completed'] else 'Good effort! Try again next time!'
        }
    
    def _get_turtle_commands(self, language: str) -> Dict[str, str]:
        """Get available turtle commands for the language."""
        commands = {
            'forward': 'Move turtle forward by distance',
            'backward': 'Move turtle backward by distance',
            'right': 'Turn turtle right by angle (degrees)',
            'left': 'Turn turtle left by angle (degrees)',
            'penup': 'Lift pen (stop drawing)',
            'pendown': 'Put pen down (start drawing)',
            'color': 'Change pen color',
            'circle': 'Draw a circle with given radius',
            'goto': 'Move turtle to x, y coordinates',
            'home': 'Return turtle to starting position'
        }
        
        return commands
    
    def _generate_ai_hint(self, challenge: Dict, code: str, error_message: Optional[str], language: str) -> str:
        """Generate AI-powered hint using OpenAI."""
        try:
            # Get OpenAI credentials
            credentials = key_manager.get_credentials()
            openai.api_type = OPENAI_API_TYPE
            openai.api_version = OPENAI_API_VERSION
            openai.api_key = credentials['api_key']
            openai.api_base = credentials['api_base']
            
            # Build prompt
            system_prompt = f"""You are a friendly coding teacher for kids learning to program with turtle graphics in {language}.
Give short, encouraging hints that guide them without giving away the solution.
Use simple language appropriate for children ages 8-12."""
            
            user_prompt = f"""Challenge: {challenge['name']}
Description: {challenge['description']}

Instructions:
{chr(10).join(f"- {inst}" for inst in challenge['instructions'])}

Student's current code:
```{language}
{code if code else '(no code yet)'}
```

{f"Error message: {error_message}" if error_message else ""}

Give a helpful hint to help the student progress. Keep it short and encouraging!"""
            
            response = openai.ChatCompletion.create(
                engine=DEFAULT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            hint = response.choices[0].message.content.strip()
            return hint
            
        except Exception as e:
            log.error(f"Error generating AI hint: {str(e)}", exc_info=True)
            raise
