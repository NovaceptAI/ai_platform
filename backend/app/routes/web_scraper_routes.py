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
from app.services.search_source_manager import SearchSourceManager

web_bp = Blueprint('web', __name__)

# Initialize source manager
source_manager = SearchSourceManager()


def _valid_url(u: str) -> bool:
    try:
        parsed = urlparse(u)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@web_bp.route('/sources', methods=['GET'])
@jwt_required()
def list_sources():
    """List all available search sources with metadata"""
    try:
        sources = source_manager.get_available_sources()
        return jsonify({
            'sources': sources,
            'total': len(sources)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@web_bp.route('/sources/<source_name>/test', methods=['GET'])
@jwt_required()
def test_source(source_name):
    """Test if a specific source is working"""
    try:
        result = source_manager.test_source(source_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@web_bp.route('/search', methods=['POST'])
@jwt_required()
def search():
    """Search using one or multiple sources"""
    data = request.get_json() or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({"error": "query required"}), 400
    
    # Get source parameter (default to 'duckduckgo' for free option, or 'all' for comprehensive)
    source = (data.get('source') or 'duckduckgo').strip().lower()
    
    # Get limit
    try:
        limit = int(data.get('limit', data.get('count', 10)))
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))
    
    try:
        # Use the new source manager
        result = source_manager.search(query, source=source, limit=limit)
        
        # Return results in the format expected by frontend
        return jsonify({
            'results': result['results'],
            'sources_searched': result['sources_searched'],
            'total_results': result['total_results'],
            'errors': result['errors'] if result['errors'] else None
        })
    
    except Exception as e:
        return jsonify({
            "error": "search_failed",
            "message": str(e)
        }), 500


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

