# app/routes/stages/master/language_lab_routes.py

import logging
from flask import Blueprint, request, jsonify
from app.services.stages.master.language_lab_service import LanguageLabService

log = logging.getLogger(__name__)

language_lab_bp = Blueprint('language_lab', __name__)

@language_lab_bp.route('/word-builder/start', methods=['POST'])
def start_word_builder():
    """
    Start a new Word Builder game session.
    
    Expected JSON (optional):
    {
        "difficulty": "easy" | "medium" | "hard",
        "time_limit": 300 (seconds, default 5 minutes),
        "min_word_length": 3
    }
    
    Returns:
    {
        "session_id": "unique-id",
        "starting_word": "plant",
        "time_limit": 300,
        "difficulty": "medium",
        "rules": {...}
    }
    """
    try:
        data = request.get_json() or {}
        
        difficulty = data.get('difficulty', 'medium')
        time_limit = int(data.get('time_limit', 300))  # 5 minutes default
        min_word_length = int(data.get('min_word_length', 3))
        
        # Validate inputs
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'
        
        if time_limit < 60 or time_limit > 1800:  # 1-30 minutes
            time_limit = 300
        
        if min_word_length < 2 or min_word_length > 8:
            min_word_length = 3
        
        service = LanguageLabService()
        result = service.start_word_builder_game(
            difficulty=difficulty,
            time_limit=time_limit,
            min_word_length=min_word_length
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        log.error(f"[LanguageLab] Error starting word builder: {e}")
        return jsonify({"error": "Failed to start game"}), 500


@language_lab_bp.route('/word-builder/validate', methods=['POST'])
def validate_word():
    """
    Validate a word submission in Word Builder game.
    
    Expected JSON:
    {
        "session_id": "unique-id",
        "previous_word": "plant",
        "new_word": "plans",
        "chain": ["plant", "plans"]
    }
    
    Returns:
    {
        "valid": true,
        "message": "Valid word!",
        "points": 10,
        "word_info": {
            "definition": "...",
            "usage_example": "...",
            "part_of_speech": "noun"
        },
        "chain_length": 2,
        "total_score": 10
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        previous_word = data.get('previous_word', '')
        new_word = data.get('new_word', '')
        chain = data.get('chain', [])
        
        if not session_id or not new_word:
            return jsonify({"error": "session_id and new_word are required"}), 400
        
        service = LanguageLabService()
        result = service.validate_word_builder_move(
            session_id=session_id,
            previous_word=previous_word,
            new_word=new_word,
            chain=chain
        )
        
        return jsonify(result), 200
        
    except ValueError as ve:
        return jsonify({"error": str(ve), "valid": False}), 400
    except Exception as e:
        log.error(f"[LanguageLab] Error validating word: {e}")
        return jsonify({"error": "Failed to validate word", "valid": False}), 500


@language_lab_bp.route('/word-builder/hint', methods=['POST'])
def get_hint():
    """
    Get a hint for the next word.
    
    Expected JSON:
    {
        "session_id": "unique-id",
        "current_word": "plant"
    }
    
    Returns:
    {
        "hint": "Try changing the last letter...",
        "possible_words_count": 5
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        current_word = data.get('current_word', '')
        
        if not session_id or not current_word:
            return jsonify({"error": "session_id and current_word are required"}), 400
        
        service = LanguageLabService()
        result = service.get_word_builder_hint(
            session_id=session_id,
            current_word=current_word
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        log.error(f"[LanguageLab] Error getting hint: {e}")
        return jsonify({"error": "Failed to get hint"}), 500


@language_lab_bp.route('/word-builder/end', methods=['POST'])
def end_game():
    """
    End a Word Builder game session and get final statistics.
    
    Expected JSON:
    {
        "session_id": "unique-id",
        "final_chain": ["plant", "plans", "plane", ...],
        "total_score": 150
    }
    
    Returns:
    {
        "session_id": "unique-id",
        "total_score": 150,
        "words_count": 15,
        "longest_chain": 15,
        "unique_words": 15,
        "time_played": 240,
        "statistics": {...},
        "achievements": [...]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        final_chain = data.get('final_chain', [])
        total_score = data.get('total_score', 0)
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        service = LanguageLabService()
        result = service.end_word_builder_game(
            session_id=session_id,
            final_chain=final_chain,
            total_score=total_score
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        log.error(f"[LanguageLab] Error ending game: {e}")
        return jsonify({"error": "Failed to end game"}), 500


@language_lab_bp.route('/info', methods=['GET'])
def get_info():
    """Get information about available language learning games."""
    return jsonify({
        "service": "Language Learning Lab",
        "games": [
            {
                "id": "word_builder",
                "name": "Word Builder (Morpho Quest)",
                "description": "Create word chains by changing one letter at a time",
                "difficulty_levels": ["easy", "medium", "hard"],
                "features": ["dictionary validation", "AI hints", "scoring system"]
            }
        ],
        "version": "1.0.0"
    }), 200
