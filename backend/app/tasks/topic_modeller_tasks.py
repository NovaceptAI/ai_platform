import os
import json
import logging
import time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.openai_key_manager import key_manager
import openai

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Azure OpenAI config
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")


class TopicModeller:
    def __init__(self, openai_engine=DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        logger.info(f"[TopicModeller] Using Azure OpenAI credential slot #{idx} ({openai.api_base})")

    def extract_topics(self, text, top_k=8):
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
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150,
                timeout=20
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
            logger.warning(f"Rate limit hit, rotating key and retrying: {e}")
            self._use_new_credentials()
            raise
        except openai.error.OpenAIError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected topic extraction error: {str(e)}")


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_topics_for_file(self, file_id: str, progress_id: str, force: bool = False):
    modeller = TopicModeller()
    s = db.session()

    try:
        pages = (
            s.query(FilePage)
            .filter(FilePage.file_id == file_id)
            .order_by(asc(FilePage.page_number))
            .all()
        )
        total = len(pages)
        if total == 0:
            prog = s.query(Progress).get(progress_id)
            if prog:
                prog.percentage = 100
                prog.status = "completed"
                s.commit()
            return

        done = 0
        for idx, page in enumerate(pages, start=1):
            try:
                if not force and page.page_topics:
                    pass
                else:
                    topics = modeller.extract_topics(page.page_text or "")
                    page.page_topics = topics
                s.commit()
                done += 1
            except Exception as inner:
                s.rollback()
                logger.error(f"Topic extraction failed for page {page.id}: {inner}")

            # Update progress
            percent = int((done / total) * 100)
            prog = s.query(Progress).get(progress_id)
            if prog:
                prog.percentage = max(prog.percentage or 0, percent)
                s.commit()

            time.sleep(0.2)  # pacing

        # Mark complete
        prog = s.query(Progress).get(progress_id)
        if prog:
            prog.percentage = 100
            prog.status = "completed"
            s.commit()

    except Exception:
        s.rollback()
        logger.exception("build_topics_for_file failed")
        try:
            prog = s.query(Progress).get(progress_id)
            if prog:
                prog.status = "failed"
                s.commit()
        except Exception:
            s.rollback()
        raise
    finally:
        s.close()