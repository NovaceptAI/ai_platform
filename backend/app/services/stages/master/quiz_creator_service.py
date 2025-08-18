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

class QuizCreatorService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[QuizCreatorService] Using Azure slot #{idx} ({api_base})")

    def _ask(self, prompt: str, max_tokens: int = 800) -> str:
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You generate precise, unambiguous quizzes. Reply ONLY with valid compact JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,      # keep it consistent/deterministic
                max_tokens=max_tokens,
                timeout=45,
            )
            return resp["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            log.warning(f"[QuizCreator] Rate limited: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def generate_questions_from_text(self, text: str, k: int = 5, difficulty: str = "medium") -> List[Dict[str, Any]]:
        """
        From page text, generate up to k MCQ questions.
        Returns list of {question, options:[str], correctIndex:int, explanation:str}
        """
        if not (text or "").strip():
            return []

        k = _clampi(k, 1, 6)
        difficulty = (difficulty or "medium").lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        prompt = (
            "Create up to {k} high-quality MULTIPLE-CHOICE questions from the TEXT.\n"
            "Respect difficulty = '{difficulty}'. Prefer factual, unambiguous items.\n"
            "Return ONLY a JSON array of objects with keys:\n"
            "- question: concise, clear, 8–28 words\n"
            "- options: 3–6 short options (strings)\n"
            "- correctIndex: 0-based index into options\n"
            "- explanation: one-sentence rationale\n\n"
            "TEXT:\n{t}"
        ).format(k=k, difficulty=difficulty, t=(text[:12000]))

        raw = self._ask(prompt, max_tokens=800)

        # Try JSON parse
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [self._normalize_q(x) for x in data if isinstance(x, dict)]
        except Exception:
            pass

        # Fallback: attempt to parse line-based items -> True/False stubs
        lines = [ln.strip("-•* \t") for ln in raw.splitlines() if ln.strip()]
        result = []
        for ln in lines[:k]:
            result.append(self._normalize_q({
                "question": ln,
                "options": ["True", "False", "Not Given"],
                "correctIndex": 0,
                "explanation": ""
            }))
        return result

    def _normalize_q(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        qtext = (obj.get("question") or "").strip()
        if len(qtext) > 240: 
            qtext = qtext[:240]

        opts = obj.get("options") or []
        if not isinstance(opts, list):
            opts = [str(opts)]
        opts = [str(x or "").strip() for x in opts if str(x or "").strip()]
        if len(opts) < 2:
            opts = ["True", "False"]
        opts = opts[:6]

        ci = obj.get("correctIndex")
        try:
            ci = int(ci)
        except Exception:
            ci = 0
        ci = _clampi(ci, 0, max(0, len(opts) - 1))

        expl = (obj.get("explanation") or "").strip()
        if len(expl) > 400:
            expl = expl[:400]

        return {
            "question": qtext,
            "options": opts,
            "correctIndex": ci,
            "explanation": expl
        }
