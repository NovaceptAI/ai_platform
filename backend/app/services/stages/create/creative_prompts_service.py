import os, json, logging, re
import openai
from typing import List, Dict, Any
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# basic sanitizer for tags
_TAG_RX = re.compile(r"[^a-z0-9\- ]+")

class CreativePromptsService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[CreativePromptsService] Using Azure slot #{idx} ({api_base})")

    def _ask(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a concise creative-writing prompt generator. Reply ONLY with compact JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=max_tokens,
                timeout=30,
            )
            # Log the full response for debugging
            log.debug(f"[CreativePromptsService] OpenAI response: {resp}")

            # Check response structure
            if "choices" not in resp or len(resp["choices"]) == 0:
                log.error(f"[CreativePromptsService] Invalid response structure: {resp}")
                raise ValueError("Invalid OpenAI API response: no choices")

            choice = resp["choices"][0]
            if "message" not in choice:
                log.error(f"[CreativePromptsService] No message in choice: {choice}")
                raise ValueError("Invalid OpenAI API response: no message")

            message = choice["message"]
            if "content" not in message:
                log.error(f"[CreativePromptsService] No content in message: {message}")
                # Check if there's a finish_reason that explains why
                finish_reason = choice.get("finish_reason", "unknown")
                log.error(f"[CreativePromptsService] Finish reason: {finish_reason}")
                raise ValueError(f"Invalid OpenAI API response: no content (finish_reason: {finish_reason})")

            content = message["content"]
            if content is None:
                log.error(f"[CreativePromptsService] Content is None")
                raise ValueError("Invalid OpenAI API response: content is None")

            return content.strip()

        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit in creative_prompts: {e}; rotating key.")
            self._use_new_credentials()
            raise
        except (KeyError, IndexError, ValueError) as e:
            log.error(f"[CreativePromptsService] Error parsing OpenAI response: {e}")
            raise
        except Exception as e:
            log.error(f"[CreativePromptsService] Unexpected error in _ask: {e}")
            raise

    def generate_prompts_from_text(
        self, text: str, k_per_page: int = 10, genre_filter: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        From page text, produce up to k_per_page creative prompts.
        Returns list of objects: { prompt, genre|null, tone|null, tags:[...], description|null }
        """
        if not (text or "").strip():
            return []

        # Genre-specific instructions
        genre_hints = {
            "fantasy": "Focus on magic, mythical creatures, alternate worlds, and epic quests.",
            "scifi": "Focus on technology, space exploration, futuristic societies, and scientific concepts.",
            "mystery": "Focus on puzzles, investigations, hidden clues, and suspenseful scenarios.",
            "romance": "Focus on relationships, emotional connections, character dynamics, and heartfelt moments.",
            "horror": "Focus on fear, suspense, eerie atmospheres, and psychological tension.",
            "mixed": "Blend diverse genres including fantasy, sci-fi, mystery, romance, horror, and contemporary fiction."
        }
        genre_hint = genre_hints.get(genre_filter.lower(), genre_hints["mixed"])

        prompt = (
            f"From the TEXT below, craft up to {k_per_page} varied creative-writing prompts.\n"
            f"Genre focus: {genre_hint}\n"
            "Blend short and medium prompts; ensure variety across genre/tone/audience; avoid spoilers.\n"
            "Respond ONLY as a JSON array of objects with keys:\n"
            "- prompt: 8–35 words, direct instruction starting with an action verb.\n"
            "- genre: a compact label (e.g., 'fantasy', 'mystery', 'sci-fi') or null if N/A.\n"
            "- tone: a compact label (e.g., 'whimsical', 'somber', 'dark') or null.\n"
            "- tags: 1–6 lowercase tags (strings) relevant to the prompt.\n"
            "- description: optional 1-sentence elaboration (10-20 words) or null.\n\n"
            f"TEXT:\n{text[:12000]}"
        )

        raw = self._ask(prompt, max_tokens=800)
        log.debug(f"[CreativePromptsService] Raw response: {raw[:500]}")

        # Try JSON parse
        try:
            # Remove markdown code blocks if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # Remove ```json or ``` at start
                cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                # Remove ``` at end
                cleaned = "\n".join(cleaned.split("\n")[:-1])

            data = json.loads(cleaned.strip())
            if isinstance(data, list):
                normalized = [self._normalize_prompt_obj(x) for x in data if isinstance(x, dict)]
                log.info(f"[CreativePromptsService] Successfully parsed {len(normalized)} prompts from JSON")
                return normalized
            else:
                log.warning(f"[CreativePromptsService] JSON response is not a list: {type(data)}")
        except json.JSONDecodeError as e:
            log.warning(f"[CreativePromptsService] JSON parse failed: {e}. Attempting fallback parsing.")
        except Exception as e:
            log.error(f"[CreativePromptsService] Unexpected error parsing JSON: {e}")

        # Fallback: one-per-line
        prompts = []
        for line in raw.splitlines():
            line = line.strip("-•* \t")
            if not line or line.startswith("```"):
                continue
            prompts.append(self._normalize_prompt_obj({"prompt": line}))

        log.info(f"[CreativePromptsService] Fallback parsing returned {len(prompts)} prompts")
        return prompts

    def _normalize_prompt_obj(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        p = (obj.get("prompt") or "").strip()
        if len(p) > 220:
            p = p[:220]
        genre = (obj.get("genre") or None) or None
        tone = (obj.get("tone") or None) or None
        description = (obj.get("description") or None) or None

        # normalize tags: lowercase, safe chars, trim, unique
        tags = obj.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        cleaned = []
        seen = set()
        for t in tags:
            t0 = _TAG_RX.sub("", (str(t).lower().strip()))
            t0 = re.sub(r"\s+", "-", t0).strip("-")  # spaces -> dashes
            if t0 and t0 not in seen:
                seen.add(t0)
                cleaned.append(t0)
            if len(cleaned) >= 6:
                break

        return {
            "prompt": p,
            "genre": (str(genre).strip() if genre else None) or None,
            "tone": (str(tone).strip() if tone else None) or None,
            "tags": cleaned,
            "description": (str(description).strip() if description else None) or None,
        }