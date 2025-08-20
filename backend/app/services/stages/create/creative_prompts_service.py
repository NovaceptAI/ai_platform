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
            return resp["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit in creative_prompts: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def generate_prompts_from_text(self, text: str, k_per_page: int = 10) -> List[Dict[str, Any]]:
        """
        From page text, produce up to k_per_page creative prompts.
        Returns list of objects: { prompt, genre|null, tone|null, tags:[...] }
        """
        if not (text or "").strip():
            return []

        prompt = (
            "From the TEXT below, craft up to {k} varied creative-writing prompts.\n"
            "Blend short and medium prompts; ensure variety across genre/tone/audience; avoid spoilers.\n"
            "Respond ONLY as a JSON array of objects with keys:\n"
            "- prompt: 8–35 words, direct instruction starting with an action verb.\n"
            "- genre: a compact label (e.g., 'fantasy', 'mystery', 'sci-fi') or null if N/A.\n"
            "- tone: a compact label (e.g., 'whimsical', 'somber') or null.\n"
            "- tags: 1–6 lowercase tags (strings) relevant to the prompt.\n\n"
            f"TEXT:\n{text[:12000]}"
        ).format(k=k_per_page)

        raw = self._ask(prompt, max_tokens=600)

        # Try JSON parse
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [self._normalize_prompt_obj(x) for x in data if isinstance(x, dict)]
        except Exception:
            pass

        # Fallback: one-per-line
        prompts = []
        for line in raw.splitlines():
            line = line.strip("-•* \t")
            if not line:
                continue
            prompts.append(self._normalize_prompt_obj({"prompt": line}))
        return prompts

    def _normalize_prompt_obj(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        p = (obj.get("prompt") or "").strip()
        if len(p) > 220:
            p = p[:220]
        genre = (obj.get("genre") or None) or None
        tone = (obj.get("tone") or None) or None

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
        }