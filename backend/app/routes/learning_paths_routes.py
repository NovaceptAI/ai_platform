
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import UUID
from app.db import db
from app.models.learning_paths import LearningPath, LearningPathStep, UserLearningPath
from app.models.status import Progress
from app.tasks.learning_paths_tasks import run_learning_path

learning_paths_bp = Blueprint('learning_paths', __name__, url_prefix='/api/learning-paths')

@learning_paths_bp.get('/')
@jwt_required()
def list_paths():
    paths = db.session.query(LearningPath).filter_by(is_active=True).all()
    return jsonify([{
        'id': str(p.id), 'slug': p.slug, 'title': p.title,
        'description': p.description, 'est_minutes': p.est_minutes,
        'steps': [{'position': s.position, 'tool_key': s.tool_key, 'title': s.title, 'config': s.config} for s in p.steps]
    } for p in paths])

@learning_paths_bp.post('/')
@jwt_required()
def create_path():
    data = request.get_json() or {}
    req = ['slug', 'title']
    if not all(k in data for k in req):
        return jsonify({'error': 'slug and title required'}), 400
    path = LearningPath(slug=data['slug'], title=data['title'], description=data.get('description'), est_minutes=data.get('est_minutes', 60))
    db.session.add(path)
    for i, s in enumerate(data.get('steps', []), start=1):
        db.session.add(LearningPathStep(path=path, position=s.get('position', i), tool_key=s['tool_key'], title=s.get('title'), config=s.get('config', {})))
    db.session.commit()
    return jsonify({'id': str(path.id)}), 201

@learning_paths_bp.post('/<uuid:path_id>/enroll')
@jwt_required()
def enroll_path(path_id):
    user_id = UUID(get_jwt_identity())
    ulp = UserLearningPath(user_id=user_id, path_id=path_id)
    db.session.add(ulp)
    db.session.commit()
    return jsonify({'user_learning_path_id': str(ulp.id)})

@learning_paths_bp.post('/<uuid:path_id>/start')
@jwt_required()
def start_path(path_id):
    user_id = UUID(get_jwt_identity())
    prog = Progress(user_id=str(user_id), tool='learning_path', status='in_progress', percentage=0)
    db.session.add(prog)
    db.session.commit()

    ulp = db.session.query(UserLearningPath).filter_by(user_id=user_id, path_id=path_id).first()
    if not ulp:
        ulp = UserLearningPath(user_id=user_id, path_id=path_id)
        db.session.add(ulp)
        db.session.commit()
    ulp.progress_id = prog.id
    db.session.commit()

    run_learning_path.apply_async(kwargs={'user_id': str(user_id), 'path_id': str(path_id), 'progress_id': str(prog.id)})
    return jsonify({'progress_id': str(prog.id), 'status': 'queued'})

from app.tasks.learning_paths_stage_tasks import run_learning_path_stage

@learning_paths_bp.post('/<uuid:path_id>/start-stage/<stage>')
@jwt_required()
def start_path_stage(path_id, stage):
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}
    file_ids = data.get('file_ids', [])
    if stage not in ['discover','organize','mastery','create','collaborate']:
        return jsonify({'error':'Invalid stage'}), 400

    ulp = db.session.query(UserLearningPath).filter_by(user_id=user_id, path_id=path_id).first()
    if not ulp:
        ulp = UserLearningPath(user_id=user_id, path_id=path_id)
        ulp.stage_status = {'discover':'unlocked','organize':'locked','mastery':'locked','create':'locked','collaborate':'locked'}
        db.session.add(ulp); db.session.commit()

    order = ['discover','organize','mastery','create','collaborate']
    idx = order.index(stage)
    for prev in order[:idx]:
        if (ulp.stage_status or {}).get(prev) != 'completed':
            return jsonify({'error': f'Complete {prev} before {stage}'}), 403

    prog = Progress(user_id=str(user_id), tool=f'learning_path:{stage}', status='in_progress', percentage=0)
    db.session.add(prog); db.session.commit()

    meta = dict(ulp.meta or {}); meta['file_ids'] = file_ids
    ulp.meta = meta; ulp.current_stage = stage; ulp.progress_id = prog.id
    db.session.commit()

    run_learning_path_stage.apply_async(kwargs={'user_id': str(user_id), 'path_id': str(path_id), 'stage': stage, 'file_ids': file_ids, 'progress_id': str(prog.id)})
    return jsonify({'progress_id': str(prog.id), 'status':'queued'})

@learning_paths_bp.get('/<uuid:path_id>/results/<stage>')
@jwt_required()
def stage_results(path_id, stage):
    if stage not in ['discover','organize','mastery','create','collaborate']:
        return jsonify({'error':'Invalid stage'}), 400
    return jsonify({
        'stage': stage,
        'results_endpoints': {
            'summarizer': '/api/stages/discover/summarizer/results',
            'segmenter': '/api/stages/discover/segmenter/results',
            'document_analysis': '/api/stages/discover/document-analysis/results'
        }
    })
