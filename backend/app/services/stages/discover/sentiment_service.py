import os, json, logging, statistics
import openai
from typing import Dict, Any, List, Tuple
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

SENTIMENT_LABELS = ["very_negative", "negative", "neutral", "positive", "very_positive"]

class SentimentService:
    """
    Per-page sentiment:
      { "label": one of SENTIMENT_LABELS, "score": float in [-1,1], "rationale": str }
    Aggregation:
      doc summary with average score and label distribution.
    """
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[SentimentService] Using Azure slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.0, max_tokens=300, timeout=25) -> str:
        try:
            r = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return r["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit in sentiment: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def analyze_page(self, text: str) -> Dict[str, Any]:
        """
        Returns {"label": str, "score": float [-1,1], "rationale": str}
        """
        if not text or not text.strip():
            return {"label": "neutral", "score": 0.0, "rationale": ""}

        prompt = (
            "Analyze the sentiment of the text below. "
            "Respond ONLY as JSON with keys: label, score, rationale.\n"
            "- label ∈ {very_negative, negative, neutral, positive, very_positive}\n"
            "- score ∈ [-1.0, 1.0] (negative→-1, positive→+1)\n"
            "- rationale: 1–2 concise sentences.\n\n"
            f"TEXT:\n{text[:12000]}"
        )
        raw = self._chat(
            [
                {"role": "system", "content": "You are a strict sentiment analysis assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=250,
        )

        try:
            data = json.loads(raw)
            label = str(data.get("label", "neutral")).strip()
            if label not in SENTIMENT_LABELS:
                label = "neutral"
            score = float(data.get("score", 0.0))
            score = max(-1.0, min(1.0, score))
            rationale = (data.get("rationale") or "").strip()
            return {"label": label, "score": score, "rationale": rationale[:500]}
        except Exception:
            # Fallback: naive rule if model returned non-JSON
            return {"label": "neutral", "score": 0.0, "rationale": raw[:500]}

    def aggregate_document(self, per_page: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Input: list of (page_number, sentiment_dict)
        Output: {
          "avg_score": float,
          "label_hist": {"neutral":N,...},
          "dominant_label": str
        }
        """
        scores = []
        hist = {k: 0 for k in SENTIMENT_LABELS}
        for _, s in per_page:
            label = s.get("label", "neutral")
            if label in hist:
                hist[label] += 1
            else:
                hist["neutral"] += 1
            try:
                scores.append(float(s.get("score", 0.0)))
            except Exception:
                pass

        avg = statistics.fmean(scores) if scores else 0.0
        dominant = max(hist.items(), key=lambda kv: kv[1])[0] if hist else "neutral"
        return {"avg_score": round(avg, 4), "label_hist": hist, "dominant_label": dominant}