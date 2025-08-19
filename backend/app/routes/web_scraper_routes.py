import os
import re
import json
import uuid
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


@web_bp.route('/search', methods=['POST'])
@jwt_required()
def search():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    # If Azure Bing/Web Search API is configured, call it; else return mock structured results
    # You can wire actual Bing later. Here we provide a deterministic fallback.
    mock = [
        {"title": f"Result for {query} #1", "snippet": "A helpful page about the topic.", "url": "https://example.com/1", "domain": "example.com"},
        {"title": f"Result for {query} #2", "snippet": "Another relevant resource.", "url": "https://example.com/2", "domain": "example.com"},
        {"title": f"Result for {query} #3", "snippet": "Background and insights.", "url": "https://example.com/3", "domain": "example.com"},
    ]
    return jsonify({"results": mock})


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

