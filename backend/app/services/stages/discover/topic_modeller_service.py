# app/services/stages/discover/topic_modeller_service.py
from __future__ import annotations
import os, json, logging
from collections import Counter
from typing import List, Dict, Any
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class TopicModellerService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[TopicModeller] Using Azure OpenAI slot #{idx} ({openai.api_base})")

    def extract_topics(self, text: str, top_k: int = 8) -> List[str]:
        if not text or not text.strip():
            return []

        prompt = (
            f"Extract up to {top_k} short, high-signal topics (2–4 words each) "
            f"from the text below. Return a JSON array of strings only.\n\nTEXT:\n{text[:12000]}"
        )
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a precise topic extraction assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=150,
                timeout=20,
            )
            raw = resp["choices"][0]["message"]["content"].strip()
            try:
                arr = json.loads(raw)
                if isinstance(arr, list):
                    return [str(x).strip()[:80] for x in arr if str(x).strip()]
            except Exception:
                pass

            # fallback if model doesn't return valid JSON
            parts = [p.strip() for p in raw.replace("\n", ",").split(",")]
            return [p for p in parts if p][:top_k]

        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit hit, rotating key and retrying: {e}")
            self._use_new_credentials()
            raise
        except openai.error.OpenAIError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected topic extraction error: {str(e)}")

    @staticmethod
    def aggregate_topics(page_topics_map: Dict[int, List[str]]) -> Dict[str, Any]:
        """
        page_topics_map: {page_number: [topics]}
        returns {"topics":[{"label":..., "weight":...}, ...], "page_topics": {"1":[...], ...}}
        """
        counter = Counter()
        page_map: Dict[str, List[str]] = {}

        for pn, arr in page_topics_map.items():
            labels: List[str] = []
            for t in (arr or []):
                label = (t if isinstance(t, str) else str(t)).strip()
                if label:
                    counter[label] += 1
                    labels.append(label)
            page_map[str(pn)] = labels

        total = sum(counter.values()) or 1
        topics = [
            {"label": lbl, "weight": round(cnt / total, 6)}
            for lbl, cnt in counter.most_common(200)
        ]
        return {"topics": topics, "page_topics": page_map, "num_topics": len(topics)}