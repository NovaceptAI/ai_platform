import os
import re
import tldextract
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from app.main import celery_app
from app.db import db
from app.models import WebScrapeJob, KnowledgeItem
from datetime import datetime
from celery.utils.log import get_task_logger
from azure.storage.blob import BlobServiceClient, ContentSettings
import openai
from app.services.openai_key_manager import key_manager

logger = get_task_logger(__name__)

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "scoolish")


def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9-_\.]+", "_", name.strip())
    if len(name) > 100:
        name = name[:100]
    return name or "untitled"


def _upload_blob_bytes(container_client, blob_path: str, data: bytes, content_type: str = "text/plain") -> str:
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
    return blob_client.url


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse whitespace
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _summarize_and_structure(text: str, url: str, title_hint: str = None):
    api_key, api_base, idx = key_manager.get_next()
    openai.api_type = "azure"
    openai.api_version = "2023-03-15-preview"
    openai.api_key = api_key
    openai.api_base = api_base

    system = "You are an assistant that summarizes webpages and produces structured JSON with fields: title, summary, key_points (list), entities (list), published_date (if found), author (if found), and recommended_actions (list)."
    user = f"Summarize and structure the following webpage content from {url}. If text is too long, focus on the most informative parts. Content:\n\n{text[:12000]}"

    resp = openai.ChatCompletion.create(
        engine=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=900,
        temperature=0.2
    )
    content = resp["choices"][0]["message"]["content"].strip()

    # Best-effort JSON extraction
    import json
    structured = None
    title = title_hint or ""
    try:
        structured = json.loads(content)
        title = structured.get("title") or title
    except Exception:
        # Fallback: simple summary
        structured = {"title": title or "Untitled", "summary": content}
    return structured, title or structured.get("title") or "Untitled"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def scrape_and_summarize(self, job_id: str):
    session = db.session()
    try:
        job = session.query(WebScrapeJob).get(job_id)
        if not job:
            return

        job.status = "in_progress"
        job.progress = 5
        session.add(job); session.commit()

        # Fetch
        headers = {"User-Agent": os.getenv("SCRAPER_UA", "Mozilla/5.0 (compatible; ScoolishBot/1.0)")}
        resp = requests.get(job.url, headers=headers, timeout=25)
        resp.raise_for_status()
        html = resp.text
        job.progress = 25
        session.add(job); session.commit()

        # Parse
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        title = (title_tag.text.strip() if title_tag else "")
        text = _extract_text_from_html(html)
        job.title = title
        session.add(job); session.commit()

        # Summarize
        structured, final_title = _summarize_and_structure(text, job.url, title_hint=title)
        job.progress = 70
        session.add(job); session.commit()

        # Store blobs
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(os.getenv("AZURE_BLOB_CONTAINER", "scoolish"))
        user_prefix = f"{job.user_id}/scrapes/{datetime.utcnow().strftime('%Y/%m/%d')}/"
        parsed = urlparse(job.url)
        host_part = _sanitize_filename(parsed.netloc)
        base_name = _sanitize_filename((final_title or title or parsed.path or "page").replace("/", "_"))

        raw_blob_path = f"{user_prefix}{host_part}/{base_name}.html"
        text_blob_path = f"{user_prefix}{host_part}/{base_name}.txt"

        _upload_blob_bytes(container_client, raw_blob_path, html.encode("utf-8"), content_type="text/html")
        _upload_blob_bytes(container_client, text_blob_path, text.encode("utf-8"), content_type="text/plain")

        # Persist KnowledgeItem
        item = KnowledgeItem(
            user_id=job.user_id,
            source_type="web",
            source_url=job.url,
            title=final_title or title or parsed.netloc,
            summary=structured.get("summary") if isinstance(structured, dict) else None,
            structured_json=structured if isinstance(structured, dict) else None,
            metadata_json={"domain": parsed.netloc},
            blob_path_raw=raw_blob_path,
            blob_path_text=text_blob_path,
        )
        session.add(item); session.commit()

        job.status = "done"
        job.progress = 100
        job.result_id = item.id
        session.add(job); session.commit()

        return {"job_id": str(job.id), "result_id": str(item.id)}

    except requests.RequestException as e:
        session.rollback()
        job = session.query(WebScrapeJob).get(job_id)
        if job:
            job.status = "failed"
            job.error = str(e)
            session.add(job); session.commit()
        raise
    except Exception as e:
        session.rollback()
        job = session.query(WebScrapeJob).get(job_id)
        if job:
            job.status = "failed"
            job.error = str(e)
            session.add(job); session.commit()
        raise
    finally:
        session.close()

