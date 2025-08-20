import os
import re
import json
import uuid
import requests
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import WebScrapeJob, KnowledgeItem
from app.tasks.web_scraper_tasks import scrape_and_summarize

web_bp = Blueprint('web', __name__)


def _valid_url(u: str) -> bool:
    try:
        parsed = urlparse(u)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _ensure_bing_endpoint(raw: str) -> str:
    """
    Accepts either a full v7 endpoint or a base domain and normalizes it to:
      https://api.bing.microsoft.com/v7.0/search
    """
    raw = (raw or "").strip().rstrip("/")
    if not raw:
        return "https://api.bing.microsoft.com/v7.0/search"
    # If caller already provided a full path, keep it
    if raw.endswith("/v7.0/search"):
        return raw
    # If caller passed only the host, append the v7.0 path
    return raw + "/v7.0/search"


@web_bp.route('/search', methods=['POST'])
@jwt_required()
def search():
    data = request.get_json() or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    # Normalize endpoint to v7.0/search
    endpoint = _ensure_bing_endpoint(os.getenv('BING_SEARCH_ENDPOINT', 'https://api.bing.microsoft.com'))

    # Clamp and sanitize inputs
    market = (data.get('market') or os.getenv('BING_SEARCH_MARKET') or 'en-US').strip()
    try:
        count = int(data.get('count', os.getenv('BING_SEARCH_COUNT', '7')))
    except Exception:
        count = 7
    count = max(1, min(count, 50))  # Bing caps at 50 per request

    # Optional paging (each page is another transaction/query)
    try:
        offset = int(data.get('offset', 0))
    except Exception:
        offset = 0
    offset = max(0, offset)

    # Support multiple keys via BING_SEARCH_API_KEYS (comma-separated) or single BING_SEARCH_API_KEY/BING_V7_KEY
    keys_env = os.getenv('BING_SEARCH_API_KEYS') or os.getenv('BING_SEARCH_API_KEY') or os.getenv('BING_V7_KEY') or ''
    keys = [k.strip() for k in keys_env.split(',') if k.strip()]
    if not keys:
        return jsonify({"error": "no Bing API key configured"}), 500

    params = {
        'q': query,
        'mkt': market,
        'count': str(count),
        'offset': str(offset),
        'responseFilter': 'Webpages',
        'safeSearch': 'Moderate',
        'textDecorations': 'false',
        'setLang': market.split('-')[0] if '-' in market else market,  # e.g., 'en'
    }

    last_err = None
    # Try keys in order; on 401/403/429/5xx rotate to the next key
    for key in keys:
        try:
            headers = {'Ocp-Apim-Subscription-Key': key}
            r = requests.get(endpoint, headers=headers, params=params, timeout=15)
            # Rotate on typical auth/quota/server issues
            if r.status_code in (401, 403, 429, 500, 502, 503, 504):
                last_err = f"HTTP {r.status_code}"
                continue
            r.raise_for_status()
            data = r.json() or {}

            items = []
            web_values = ((data.get('webPages') or {}).get('value')) or []
            for w in web_values:
                url = w.get('url') or ''
                try:
                    domain = urlparse(url).netloc
                except Exception:
                    domain = ''
                items.append({
                    'title': w.get('name') or '',
                    'snippet': w.get('snippet') or '',
                    'url': url,
                    'domain': domain,
                })

            # If no web results, try to surface news links (optional bonus)
            if not items:
                news_values = ((data.get('news') or {}).get('value')) or []
                for n in news_values:
                    url = n.get('url') or ''
                    try:
                        domain = urlparse(url).netloc
                    except Exception:
                        domain = ''
                    items.append({
                        'title': n.get('name') or '',
                        'snippet': n.get('description') or '',
                        'url': url,
                        'domain': domain,
                    })

            return jsonify({'results': items})
        except Exception as e:
            last_err = str(e)
            continue

    # If all keys failed, return a clear error (keep your mock as a dev fallback if you want)
    return jsonify({
        "error": "bing_search_failed",
        "message": "All Bing API keys failed",
        "detail": last_err or "unknown"
    }), 502


@web_bp.route('/queue', methods=['POST'])
@jwt_required()
def enqueue_scrape():
    data = request.get_json() or {}
    urls = data.get('urls') or []
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.splitlines() if u.strip()]
    urls = [u for u in urls if _valid_url(u)]
    if not urls:
        return jsonify({"error": "no valid urls"}), 400

    user_id = get_jwt_identity()
    jobs = []
    for u in urls:
        job = WebScrapeJob(user_id=user_id, url=u, status="pending", progress=0)
        db.session.add(job)
        db.session.flush()
        async_res = scrape_and_summarize.apply_async(args=[str(job.id)])
        job.task_id = async_res.id
        db.session.add(job)
        jobs.append(job)
    db.session.commit()

    return jsonify({"queued": [j.to_dict() for j in jobs]})


@web_bp.route('/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    user_id = get_jwt_identity()
    q = WebScrapeJob.query.filter_by(user_id=user_id).order_by(WebScrapeJob.created_at.desc()).limit(100).all()
    return jsonify({"jobs": [j.to_dict() for j in q]})


@web_bp.route('/jobs/<job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    user_id = get_jwt_identity()
    job = WebScrapeJob.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return jsonify({"error": "not found"}), 404
    return jsonify(job.to_dict())


@web_bp.route('/results', methods=['GET'])
@jwt_required()
def list_results():
    user_id = get_jwt_identity()
    rows = KnowledgeItem.query.filter_by(user_id=user_id).order_by(KnowledgeItem.created_at.desc()).limit(200).all()
    return jsonify({"items": [r.to_dict() for r in rows]})


@web_bp.route('/results/<item_id>', methods=['GET'])
@jwt_required()
def get_result(item_id):
    user_id = get_jwt_identity()
    item = KnowledgeItem.query.filter_by(id=item_id, user_id=user_id).first()
    if not item:
        return jsonify({"error": "not found"}), 404
    return jsonify(item.to_dict())

