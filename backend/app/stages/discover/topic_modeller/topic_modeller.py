# app/stages/discover/topic_modeller/topic_modeller.py
import os, json, logging
import openai

openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

logger = logging.getLogger(__name__)

def extract_topics_for_text(text: str, top_k: int = 8):
    # proxy to the task’s inner function if you prefer to import; duplicated for clarity
    if not text or not text.strip():
        return []
    prompt = (
        "Extract up to {k} short, high-signal topics (2–4 words each) from the text below. "
        "Return a JSON array of strings only.\n\nTEXT:\n{t}"
    ).format(k=top_k, t=text[:12000])

    resp = openai.ChatCompletion.create(
        engine=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You are a precise topic extraction assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=150,
    )
    raw = resp["choices"][0]["message"]["content"].strip()
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            return [str(x).strip()[:80] for x in arr if str(x).strip()]
    except Exception:
        pass
    parts = [p.strip() for p in raw.replace("\n", ",").split(",")]
    return [p for p in parts if p][:top_k]