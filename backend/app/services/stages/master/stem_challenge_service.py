import os, json, logging, re
import openai
from typing import List, Dict, Any
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Safe clamp helpers
def _clampi(v, lo, hi):
    try:
        v = int(v)
    except Exception:
        v = lo
    return max(lo, min(hi, v))

class StemChallengeService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[StemChallengeService] Using Azure slot #{idx} ({api_base})")

    def _ask(self, prompt: str, max_tokens: int = 1200) -> str:
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are an expert STEM educator who creates engaging, rigorous challenges. Reply ONLY with valid compact JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,      # slightly more creative than quiz
                max_tokens=max_tokens,
                timeout=60,
            )

            # Validate response structure
            if not resp or "choices" not in resp or len(resp["choices"]) == 0:
                log.error(f"[StemChallenge] Invalid API response structure: {resp}")
                return "[]"

            message = resp["choices"][0].get("message", {})
            content = message.get("content")

            # Check for content filtering
            if content is None:
                finish_reason = resp["choices"][0].get("finish_reason")
                log.warning(f"[StemChallenge] No content in response. Finish reason: {finish_reason}")

                # Check if content was filtered
                if finish_reason == "content_filter":
                    log.error("[StemChallenge] Content was filtered by Azure content policy")
                    return "[]"

                log.error(f"[StemChallenge] Missing content field. Full response: {resp}")
                return "[]"

            return content.strip()

        except openai.error.RateLimitError as e:
            log.warning(f"[StemChallenge] Rate limited: {e}; rotating key.")
            self._use_new_credentials()
            raise
        except Exception as e:
            log.error(f"[StemChallenge] Error in _ask: {e}", exc_info=True)
            return "[]"

    def generate_challenges_from_text(
        self,
        text: str,
        k: int = 3,
        difficulty: str = "medium",
        challenge_type: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        From page text, generate up to k STEM challenges.

        challenge_type options:
        - 'mixed': Mix of all types
        - 'problem_solving': Math/physics problems
        - 'design': Engineering/design challenges
        - 'experiment': Scientific investigation tasks
        - 'coding': Programming challenges

        Returns list of {
            type: str,
            problem: str,
            constraints: [str],
            hints: [str],
            solution_approach: str,
            difficulty: str
        }
        """
        if not (text or "").strip():
            return []

        k = _clampi(k, 1, 3)
        difficulty = (difficulty or "medium").lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        challenge_type = (challenge_type or "mixed").lower()
        if challenge_type not in {"mixed", "problem_solving", "design", "experiment", "coding"}:
            challenge_type = "mixed"

        type_instructions = self._get_type_instructions(challenge_type)

        prompt = (
            "Create up to {k} high-quality STEM CHALLENGES from the TEXT.\n"
            "Difficulty = '{difficulty}'. Type = '{challenge_type}'.\n"
            "{type_instructions}\n\n"
            "Return ONLY a JSON array of objects with keys:\n"
            "- type: challenge type (problem_solving/design/experiment/coding)\n"
            "- problem: clear problem statement (20-80 words)\n"
            "- constraints: array of 2-4 constraints or requirements\n"
            "- hints: array of 2-3 progressive hints\n"
            "- solution_approach: brief outline of solution method (30-60 words)\n"
            "- difficulty: '{difficulty}'\n\n"
            "Make challenges engaging, real-world applicable, and appropriately challenging.\n\n"
            "TEXT:\n{t}"
        ).format(
            k=k,
            difficulty=difficulty,
            challenge_type=challenge_type,
            type_instructions=type_instructions,
            t=(text[:12000])
        )

        raw = self._ask(prompt, max_tokens=1200)

        # Try JSON parse
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [self._normalize_challenge(x, difficulty) for x in data if isinstance(x, dict)]
        except Exception as e:
            log.warning(f"[StemChallenge] JSON parse failed: {e}")
            pass

        # Fallback: create simple challenge from text
        return [self._create_fallback_challenge(text, difficulty)]

    def _get_type_instructions(self, challenge_type: str) -> str:
        instructions = {
            "mixed": "Include diverse challenge types: problem_solving, design, experiment, or coding.",
            "problem_solving": "Focus on mathematical, physics, or analytical problems with clear solutions.",
            "design": "Focus on engineering design, optimization, or creative technical solutions.",
            "experiment": "Focus on scientific investigations, hypothesis testing, or data analysis.",
            "coding": "Focus on programming challenges, algorithms, or computational problems."
        }
        return instructions.get(challenge_type, instructions["mixed"])

    def _normalize_challenge(self, obj: Dict[str, Any], difficulty: str) -> Dict[str, Any]:
        ctype = (obj.get("type") or "problem_solving").strip().lower()
        if ctype not in {"problem_solving", "design", "experiment", "coding"}:
            ctype = "problem_solving"

        problem = (obj.get("problem") or "").strip()
        if len(problem) > 500:
            problem = problem[:500]
        if not problem:
            problem = "Challenge not available"

        constraints = obj.get("constraints") or []
        if not isinstance(constraints, list):
            constraints = [str(constraints)]
        constraints = [str(x or "").strip() for x in constraints if str(x or "").strip()][:4]
        if not constraints:
            constraints = ["Apply relevant concepts from the material"]

        hints = obj.get("hints") or []
        if not isinstance(hints, list):
            hints = [str(hints)]
        hints = [str(x or "").strip() for x in hints if str(x or "").strip()][:3]
        if not hints:
            hints = ["Review the key concepts", "Break the problem into steps"]

        solution_approach = (obj.get("solution_approach") or "").strip()
        if len(solution_approach) > 400:
            solution_approach = solution_approach[:400]
        if not solution_approach:
            solution_approach = "Apply systematic problem-solving methodology"

        return {
            "type": ctype,
            "problem": problem,
            "constraints": constraints,
            "hints": hints,
            "solution_approach": solution_approach,
            "difficulty": difficulty
        }

    def _create_fallback_challenge(self, text: str, difficulty: str) -> Dict[str, Any]:
        """Create a simple challenge when API fails"""
        snippet = text[:200].strip()
        return {
            "type": "problem_solving",
            "problem": f"Based on the provided material, analyze and explain the key concepts, then apply them to solve a related problem.",
            "constraints": [
                "Use concepts from the source material",
                "Show your work and reasoning",
                "Provide clear explanations"
            ],
            "hints": [
                "Identify the main topics in the material",
                "Connect concepts to real-world applications",
                "Break down complex problems into smaller steps"
            ],
            "solution_approach": "Review the material, identify key concepts, formulate a related problem, and solve it systematically using the principles discussed.",
            "difficulty": difficulty
        }
