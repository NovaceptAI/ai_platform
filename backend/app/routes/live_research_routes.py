from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import UUID
from datetime import datetime
from app.db import db
from app.models.research import ResearchProject, ProjectFile, ResearchSession, BrowserSearch, ScrapeSource, SessionNote
from app.models.status import Progress
from app.tasks.live_research_tasks import start_research_session_task, browser_search_task, scraper_task, synthesize_notes_task

live_research_bp = Blueprint('live_research', __name__, url_prefix='/api/research')

@live_research_bp.post('/projects')
@jwt_required()
def create_project():
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}
    if 'title' not in data:
        return jsonify({'error': 'title required'}), 400
    proj = ResearchProject(owner_id=user_id, title=data['title'], topic=data.get('topic'), description=data.get('description'), vault_folder=data.get('vault_folder'))
    db.session.add(proj)
    db.session.commit()
    return jsonify({'id': str(proj.id)}), 201

@live_research_bp.get('/projects')
@jwt_required()
def list_projects():
    user_id = UUID(get_jwt_identity())
    projs = db.session.query(ResearchProject).filter_by(owner_id=user_id).order_by(ResearchProject.created_at.desc()).all()
    return jsonify([{'id': str(p.id), 'title': p.title, 'topic': p.topic, 'status': p.status, 'vault_folder': p.vault_folder} for p in projs])

@live_research_bp.get('/projects/<uuid:project_id>')
@jwt_required()
def get_project(project_id):
    p = db.session.get(ResearchProject, project_id)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': str(p.id), 'title': p.title, 'topic': p.topic, 'description': p.description, 'status': p.status, 'vault_folder': p.vault_folder})

@live_research_bp.put('/projects/<uuid:project_id>')
@jwt_required()
def update_project(project_id):
    p = db.session.get(ResearchProject, project_id)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json() or {}
    for k in ['title', 'topic', 'description', 'status', 'vault_folder']:
        if k in data:
            setattr(p, k, data[k])
    db.session.commit()
    return jsonify({'ok': True})

@live_research_bp.delete('/projects/<uuid:project_id>')
@jwt_required()
def delete_project(project_id):
    p = db.session.get(ResearchProject, project_id)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})

@live_research_bp.post('/projects/<uuid:project_id>/sessions/start')
@jwt_required()
def start_session(project_id):
    user_id = UUID(get_jwt_identity())
    prog = Progress(user_id=str(user_id), tool='live_research_session', status='in_progress', percentage=0)
    db.session.add(prog)
    db.session.commit()
    start_research_session_task.apply_async(kwargs={'user_id': str(user_id), 'project_id': str(project_id), 'progress_id': str(prog.id)})
    return jsonify({'progress_id': str(prog.id)})

@live_research_bp.post('/sessions/<uuid:session_id>/end')
@jwt_required()
def end_session(session_id):
    s = db.session.get(ResearchSession, session_id)
    if not s:
        return jsonify({'error': 'Session not found'}), 404
    s.active = False
    s.ended_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})

@live_research_bp.post('/sessions/<uuid:session_id>/browser/search')
@jwt_required()
def queue_browser_search(session_id):
    data = request.get_json() or {}
    if 'query' not in data:
        return jsonify({'error': 'query required'}), 400
    bs = BrowserSearch(session_id=session_id, query=data['query'])
    db.session.add(bs)
    db.session.commit()
    browser_search_task.apply_async(kwargs={'search_id': str(bs.id)})
    return jsonify({'search_id': str(bs.id), 'status': 'queued'})

@live_research_bp.post('/sessions/<uuid:session_id>/scraper')
@jwt_required()
def queue_scrape(session_id):
    data = request.get_json() or {}
    if 'url' not in data:
        return jsonify({'error': 'url required'}), 400
    src = ScrapeSource(session_id=session_id, url=data['url'])
    db.session.add(src)
    db.session.commit()
    scraper_task.apply_async(kwargs={'source_id': str(src.id)})
    return jsonify({'source_id': str(src.id), 'status': 'queued'})

@live_research_bp.get('/sessions/<uuid:session_id>/browser/searches')
@jwt_required()
def list_searches(session_id):
    items = db.session.query(BrowserSearch).filter_by(session_id=session_id).order_by(BrowserSearch.created_at.desc()).all()
    return jsonify([{'id': str(i.id), 'query': i.query, 'status': i.status, 'results': i.results} for i in items])

@live_research_bp.get('/sessions/<uuid:session_id>/scrapes')
@jwt_required()
def list_scrapes(session_id):
    items = db.session.query(ScrapeSource).filter_by(session_id=session_id).all()
    return jsonify([{'id': str(i.id), 'url': i.url, 'status': i.status, 'content_ref': i.content_ref} for i in items])

@live_research_bp.post('/sessions/<uuid:session_id>/notes')
@jwt_required()
def add_note(session_id):
    data = request.get_json() or {}
    note = SessionNote(session_id=session_id, note_type=data.get('note_type', 'text'), content=data.get('content', ''), meta=data.get('meta', {}))
    db.session.add(note)
    db.session.commit()
    return jsonify({'id': str(note.id)})

@live_research_bp.post('/sessions/<uuid:session_id>/synthesize')
@jwt_required()
def synthesize(session_id):
    prog = Progress(user_id="system", tool='live_research_synthesis', status='in_progress', percentage=0)
    db.session.add(prog)
    db.session.commit()
    synthesize_notes_task.apply_async(kwargs={'session_id': str(session_id), 'progress_id': str(prog.id)})
    return jsonify({'progress_id': str(prog.id)})
