# app/services/stages/master/language_lab_service.py

import os
import json
import logging
import random
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests
import redis

# OpenAI for AI-powered hints and word meanings
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Redis configuration for session storage
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_EXPIRY = 3600  # 1 hour expiry for sessions


class LanguageLabService:
    """
    Service for Language Learning Lab games.
    Focuses on Word Builder (Morpho Quest) game initially.
    
    Redis-backed session storage for multi-worker support.
    """
    
    # Starting words by difficulty
    EASY_WORDS = [
        "cat", "dog", "run", "sun", "bat", "hat", "mat", "rat", "sit", "hit",
        "pen", "ten", "den", "men", "can", "fan", "man", "pan", "tan", "van"
    ]
    
    MEDIUM_WORDS = [
        "plant", "train", "brain", "chain", "grain", "stain", "plain", "Spain",
        "house", "mouse", "horse", "sport", "start", "heart", "smart", "chart",
        "light", "night", "fight", "right", "might", "sight", "tight", "flight"
    ]
    
    HARD_WORDS = [
        "strange", "chamber", "thunder", "wander", "chapter", "shelter", "weather",
        "capture", "culture", "feature", "measure", "picture", "texture", "mixture",
        "question", "function", "junction", "fraction", "raction", "traction"
    ]
    
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()
        
        # Use Redis for session storage (works across multiple gunicorn workers)
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()  # Test connection
            log.info("Language Lab connected to Redis for session storage")
        except Exception as e:
            log.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        if not self.redis_client:
            return None
        try:
            session_key = f"language_lab:session:{session_id}"
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
            session_key = f"language_lab:session:{session_id}"
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
            session_key = f"language_lab:session:{session_id}"
            self.redis_client.delete(session_key)
            return True
        except Exception as e:
            log.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def _use_new_credentials(self):
        """Rotate OpenAI API credentials."""
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[LanguageLabService] Using Azure slot #{idx} ({api_base})")
    
    def start_word_builder_game(
        self, 
        difficulty: str = "medium",
        time_limit: int = 300,
        min_word_length: int = 3
    ) -> Dict[str, Any]:
        """
        Start a new Word Builder game session.
        
        Args:
            difficulty: Game difficulty (easy/medium/hard)
            time_limit: Time limit in seconds
            min_word_length: Minimum word length accepted
            
        Returns:
            Dict with session info and starting word
        """
        # Select starting word based on difficulty
        if difficulty == "easy":
            starting_word = random.choice(self.EASY_WORDS)
        elif difficulty == "hard":
            starting_word = random.choice(self.HARD_WORDS)
        else:
            starting_word = random.choice(self.MEDIUM_WORDS)
        
        # Create session
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "difficulty": difficulty,
            "time_limit": time_limit,
            "min_word_length": min_word_length,
            "starting_word": starting_word,
            "started_at": datetime.utcnow().isoformat(),
            "chain": [starting_word],
            "score": 0,
            "hints_used": 0
        }
        
        # Store session in Redis
        self._set_session(session_id, session_data)
        
        return {
            "session_id": session_id,
            "starting_word": starting_word,
            "time_limit": time_limit,
            "difficulty": difficulty,
            "min_word_length": min_word_length,
            "rules": {
                "objective": "Create new words by changing ONE letter at a time",
                "scoring": {
                    "valid_word": 10,
                    "rare_word_bonus": 5,
                    "long_word_bonus": "1 point per letter above 5",
                    "chain_multiplier": "x1.1 for every 5 words in chain"
                },
                "restrictions": [
                    "Must be a valid English word",
                    "Must differ by exactly ONE letter from previous word",
                    f"Must be at least {min_word_length} letters long",
                    "Cannot reuse words in the same chain"
                ]
            }
        }
    
    def validate_word_builder_move(
        self,
        session_id: str,
        previous_word: str,
        new_word: str,
        chain: List[str]
    ) -> Dict[str, Any]:
        """
        Validate a word submission in Word Builder.
        
        Args:
            session_id: Game session ID
            previous_word: Previous word in chain
            new_word: New word submitted
            chain: Current word chain
            
        Returns:
            Validation result with word info and points
        """
        # Normalize inputs
        previous_word = previous_word.lower().strip()
        new_word = new_word.lower().strip()
        
        # Get session from Redis
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session ID")
        
        min_length = session.get('min_word_length', 3)
        
        # Validation checks
        errors = []
        
        # 1. Length check
        if len(new_word) < min_length:
            errors.append(f"Word must be at least {min_length} letters long")
        
        # 2. Already used check
        if new_word in chain:
            errors.append("Word already used in this chain")
        
        # 3. One letter difference check
        if previous_word and not self._is_one_letter_different(previous_word, new_word):
            errors.append("Word must differ by exactly ONE letter from previous word")
        
        # 4. Dictionary validation
        is_valid_word, word_info = self._validate_dictionary(new_word)
        if not is_valid_word:
            errors.append(f"'{new_word}' is not a valid English word")
        
        # If any errors, return invalid
        if errors:
            return {
                "valid": False,
                "message": " | ".join(errors),
                "points": 0,
                "word_info": None,
                "chain_length": len(chain),
                "total_score": session.get('score', 0)
            }
        
        # Calculate points
        points = self._calculate_points(new_word, len(chain), word_info)
        
        # Update session
        session['chain'].append(new_word)
        session['score'] += points
        
        # Save updated session to Redis
        self._set_session(session_id, session)
        
        return {
            "valid": True,
            "message": "Valid word! Well done!",
            "points": points,
            "word_info": word_info,
            "chain_length": len(chain) + 1,
            "total_score": session['score']
        }
    
    def _is_one_letter_different(self, word1: str, word2: str) -> bool:
        """
        Check if two words differ by exactly one letter.
        Allows: addition, removal, or substitution of one letter.
        """
        len1, len2 = len(word1), len(word2)
        
        # Case 1: Same length (substitution)
        if len1 == len2:
            diff_count = sum(c1 != c2 for c1, c2 in zip(word1, word2))
            return diff_count == 1
        
        # Case 2: One letter longer (addition)
        if len1 + 1 == len2:
            return self._is_one_insertion(word1, word2)
        
        # Case 3: One letter shorter (removal)
        if len1 - 1 == len2:
            return self._is_one_insertion(word2, word1)
        
        return False
    
    def _is_one_insertion(self, shorter: str, longer: str) -> bool:
        """Check if longer word is shorter word with one letter inserted."""
        i = 0
        for j, char in enumerate(longer):
            if i < len(shorter) and shorter[i] == char:
                i += 1
            elif j - i > 0:
                return False
        return True
    
    def _validate_dictionary(self, word: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate word using Free Dictionary API.
        Returns (is_valid, word_info)
        """
        try:
            # Use Free Dictionary API
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    entry = data[0]
                    
                    # Extract word info
                    meanings = entry.get('meanings', [])
                    definition = ""
                    part_of_speech = ""
                    
                    if meanings:
                        part_of_speech = meanings[0].get('partOfSpeech', 'unknown')
                        definitions = meanings[0].get('definitions', [])
                        if definitions:
                            definition = definitions[0].get('definition', '')
                    
                    # Get AI-generated usage example
                    usage_example = self._generate_usage_example(word, definition)
                    
                    word_info = {
                        "definition": definition,
                        "part_of_speech": part_of_speech,
                        "usage_example": usage_example,
                        "phonetic": entry.get('phonetic', '')
                    }
                    
                    return True, word_info
            
            return False, None
            
        except Exception as e:
            log.warning(f"[LanguageLab] Dictionary API error for '{word}': {e}")
            # Fallback: basic validation (check if it's alphabetic and reasonable length)
            if word.isalpha() and 2 <= len(word) <= 20:
                return True, {
                    "definition": f"A valid English word: {word}",
                    "part_of_speech": "unknown",
                    "usage_example": f"Example with {word}",
                    "phonetic": ""
                }
            return False, None
    
    def _generate_usage_example(self, word: str, definition: str) -> str:
        """Generate a usage example using AI."""
        try:
            prompt = f"Create a simple, natural example sentence using the word '{word}' (meaning: {definition}). Just return the sentence, nothing else."
            
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a helpful language teacher creating example sentences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=60,
                timeout=10
            )
            
            if resp and "choices" in resp and len(resp["choices"]) > 0:
                content = resp["choices"][0].get("message", {}).get("content", "")
                return content.strip()
            
        except Exception as e:
            log.warning(f"[LanguageLab] AI example generation failed: {e}")
        
        # Fallback
        return f"The word '{word}' can be used in everyday conversation."
    
    def _calculate_points(self, word: str, chain_length: int, word_info: Dict[str, Any]) -> int:
        """Calculate points for a valid word."""
        points = 10  # Base points
        
        # Long word bonus (1 point per letter above 5)
        if len(word) > 5:
            points += (len(word) - 5)
        
        # Rare word bonus (words with uncommon definitions)
        if word_info and len(word_info.get('definition', '')) > 100:
            points += 5
        
        # Chain multiplier (every 5 words = 10% bonus)
        if chain_length >= 5:
            multiplier = 1 + (chain_length // 5) * 0.1
            points = int(points * multiplier)
        
        return points
    
    def get_word_builder_hint(self, session_id: str, current_word: str) -> Dict[str, Any]:
        """
        Get an AI-powered hint for the next word.
        
        Args:
            session_id: Game session ID
            current_word: Current word in chain
            
        Returns:
            Hint information
        """
        # Get session from Redis
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session ID")
        
        # Increment hint counter
        session['hints_used'] = session.get('hints_used', 0) + 1
        
        # Save updated session
        self._set_session(session_id, session)
        
        try:
            prompt = f"""Given the word '{current_word}', suggest ONE possible English word that differs by exactly one letter (add, remove, or change one letter).
Just return the word and a brief hint, like: "Try 'plans' - change the last letter to 's'". Keep it short and helpful."""
            
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a helpful word game assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=50,
                timeout=10
            )
            
            if resp and "choices" in resp and len(resp["choices"]) > 0:
                hint_text = resp["choices"][0].get("message", {}).get("content", "").strip()
                
                return {
                    "hint": hint_text,
                    "hints_used": session['hints_used'],
                    "hint_penalty": session['hints_used'] * 5  # 5 points per hint
                }
        
        except Exception as e:
            log.error(f"[LanguageLab] Hint generation failed: {e}")
        
        # Fallback hint
        return {
            "hint": f"Try changing one letter in '{current_word}' to make a new word!",
            "hints_used": session['hints_used'],
            "hint_penalty": session['hints_used'] * 5
        }
    
    def end_word_builder_game(
        self,
        session_id: str,
        final_chain: List[str],
        total_score: int
    ) -> Dict[str, Any]:
        """
        End game and calculate final statistics.
        
        Args:
            session_id: Game session ID
            final_chain: Final word chain
            total_score: Total score achieved
            
        Returns:
            Final game statistics and achievements
        """
        # Get session from Redis
        session = self._get_session(session_id)
        if not session:
            # Return basic stats even if session not found
            return {
                "session_id": session_id,
                "total_score": total_score,
                "words_count": len(final_chain),
                "longest_chain": len(final_chain),
                "unique_words": len(set(final_chain)),
                "statistics": {},
                "achievements": []
            }
        
        # Calculate time played
        started_at = datetime.fromisoformat(session['started_at'])
        time_played = int((datetime.utcnow() - started_at).total_seconds())
        
        # Calculate statistics
        unique_words = len(set(final_chain))
        avg_word_length = sum(len(w) for w in final_chain) / len(final_chain) if final_chain else 0
        
        # Determine achievements
        achievements = []
        if len(final_chain) >= 10:
            achievements.append({"name": "Chain Master", "description": "Created a chain of 10+ words"})
        if len(final_chain) >= 20:
            achievements.append({"name": "Word Wizard", "description": "Created a chain of 20+ words"})
        if unique_words == len(final_chain):
            achievements.append({"name": "No Repeats", "description": "All unique words!"})
        if session.get('hints_used', 0) == 0:
            achievements.append({"name": "No Hints Needed", "description": "Completed without hints"})
        if avg_word_length >= 6:
            achievements.append({"name": "Long Words Pro", "description": "Average word length 6+ letters"})
        
        # Clean up session from Redis
        self._delete_session(session_id)
        
        return {
            "session_id": session_id,
            "total_score": total_score,
            "words_count": len(final_chain),
            "longest_chain": len(final_chain),
            "unique_words": unique_words,
            "time_played": time_played,
            "hints_used": session.get('hints_used', 0),
            "statistics": {
                "average_word_length": round(avg_word_length, 1),
                "difficulty": session.get('difficulty'),
                "time_limit": session.get('time_limit'),
                "words_per_minute": round(len(final_chain) / (time_played / 60), 1) if time_played > 0 else 0
            },
            "achievements": achievements,
            "final_chain": final_chain[:50]  # Limit to first 50 words for response size
        }
