
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import asc
from uuid import UUID
from datetime import datetime
from app.db import db
from app.models.learning_paths import LearningPath, LearningPathStep, UserLearningPath
from app.models.status import Progress
from app.models.files import UploadedFile
from app.tasks.learning_paths_tasks import run_learning_path

learning_paths_bp = Blueprint('learning_paths', __name__)

@learning_paths_bp.get('/')
@jwt_required()
def list_paths():
    paths = db.session.query(LearningPath).filter_by(is_active=True).all()
    return jsonify([{
        'id': str(p.id), 'slug': p.slug, 'title': p.title,
        'description': p.description, 'est_minutes': p.est_minutes,
        'steps': [{'position': s.position, 'tool_key': s.tool_key, 'title': s.title, 'config': s.config} for s in p.steps]
    } for p in paths])

@learning_paths_bp.get('/by-slug/<slug>')
@jwt_required()
def get_path_by_slug(slug):
    """Get a specific learning path by its slug."""
    path = db.session.query(LearningPath).filter_by(slug=slug, is_active=True).first()

    if not path:
        return jsonify({'error': f'Learning path with slug "{slug}" not found'}), 404

    return jsonify({
        'id': str(path.id),
        'slug': path.slug,
        'title': path.title,
        'description': path.description,
        'est_minutes': path.est_minutes,
        'steps': [{
            'id': str(s.id),
            'position': s.position,
            'tool_key': s.tool_key,
            'title': s.title,
            'instructions': s.instructions,
            'config': s.config
        } for s in path.steps]
    })

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
    session_id = data.get('session_id')  # NEW: Get session ID from request body

    if stage not in ['discover','organize','master','create','collaborate']:
        return jsonify({'error':'Invalid stage'}), 400

    # If session_id provided, use THAT SPECIFIC session
    if session_id:
        ulp = db.session.query(UserLearningPath).filter_by(
            id=UUID(session_id),
            user_id=user_id,
            path_id=path_id
        ).first()
        if not ulp:
            return jsonify({'error': 'Session not found or unauthorized'}), 404
    else:
        # Fallback to old behavior for backwards compatibility
        ulp = db.session.query(UserLearningPath).filter_by(user_id=user_id, path_id=path_id).first()
        if not ulp:
            ulp = UserLearningPath(user_id=user_id, path_id=path_id)
            ulp.stage_status = {'discover':'unlocked','organize':'locked','master':'locked','create':'locked','collaborate':'locked'}
            db.session.add(ulp); db.session.commit()

    order = ['discover','organize','master','create','collaborate']
    idx = order.index(stage)
    for prev in order[:idx]:
        if (ulp.stage_status or {}).get(prev) != 'completed':
            return jsonify({'error': f'Complete {prev} before {stage}'}), 403

    # Store the first file_id in the Progress record for tracking
    first_file_id = UUID(file_ids[0]) if file_ids and len(file_ids) > 0 else None
    prog = Progress(
        user_id=str(user_id),
        tool=f'learning_path:{stage}',
        status='in_progress',
        percentage=0,
        file_id=first_file_id  # Store the first file for progress tracking
    )
    db.session.add(prog); db.session.commit()

    meta = dict(ulp.meta or {}); meta['file_ids'] = file_ids
    ulp.meta = meta; ulp.current_stage = stage; ulp.progress_id = prog.id
    db.session.commit()

    run_learning_path_stage.apply_async(kwargs={'user_id': str(user_id), 'path_id': str(path_id), 'stage': stage, 'file_ids': file_ids, 'progress_id': str(prog.id)})
    return jsonify({'progress_id': str(prog.id), 'status':'queued'})

@learning_paths_bp.get('/<uuid:path_id>/results/<stage>')
@jwt_required()
def stage_results(path_id, stage):
    if stage not in ['discover','organize','master','create','collaborate']:
        return jsonify({'error':'Invalid stage'}), 400
    
    # Define stage-wise result endpoints
    stage_endpoints = {
        'discover': {
            'summarizer': '/api/summarizer/results',
            'segmenter': '/api/segmenter/results',
            'document_analysis': '/api/doc_analysis/results',
            'evidence_extractor': '/api/stages/discover/evidence_extractor/results',
            'chronology_strict': '/api/chronology/results',
            'comparison': '/api/stages/discover/comparison/results'
        },
        'organize': {
            'collections': '/api/organize/results/collections',
            'tags': '/api/organize/results/tags',
            'clusters': '/api/organize/results/clusters',
            'concept_graph': '/api/organize/results/concept-graph',
            'saved_views': '/api/organize/results/saved-views',
            'full_stage': '/api/organize/results/organize_stage_full'
        },
        'master': {
            'flashcards': '/api/mastery/results/flashcards',
            'homework_helper': '/api/homework_helper/results',
            'visual_study_guide': '/api/study_guide/results',
            'quiz_creator': '/api/quiz_creator/results'
        },
        'create': {
            'creative_writing_prompts': '/api/creative_prompts/results',
            'data_story_builder': '/api/data_story_builder/results',
            'ai_presentation_builder': '/api/ai_presentation_builder/results'
        },
        'collaborate': {
            'coauthor_peer_review': '/api/collaborate/results/peer_review',
            'showcase_share': '/api/collaborate/results/showcase'
        }
    }
    
    return jsonify({
        'stage': stage,
        'results_endpoints': stage_endpoints.get(stage, {}),
        'progress_endpoint': f'/api/progress/{stage}',
        'status_endpoint': f'/api/learning_paths/{path_id}/status/{stage}'
    })

@learning_paths_bp.get('/<uuid:path_id>/status/<stage>')
@jwt_required()
def stage_status(path_id, stage):
    """Get the current status of a specific stage for a learning path."""
    if stage not in ['discover','organize','master','create','collaborate']:
        return jsonify({'error':'Invalid stage'}), 400
    
    user_id = UUID(get_jwt_identity())
    
    # Get user learning path
    ulp = db.session.query(UserLearningPath).filter_by(
        user_id=user_id, 
        path_id=path_id
    ).first()
    
    if not ulp:
        return jsonify({
            'stage': stage,
            'status': 'not_enrolled',
            'message': 'User not enrolled in this learning path'
        }), 404
    
    # Get stage status
    stage_status_map = ulp.stage_status or {}
    current_status = stage_status_map.get(stage, 'locked')
    
    # Get latest progress for this stage
    latest_progress = db.session.query(Progress).filter(
        Progress.user_id == str(user_id),
        Progress.tool.like(f'learning_path:{stage}%')
    ).order_by(Progress.created_at.desc()).first()
    
    response = {
        'stage': stage,
        'status': current_status,
        'learning_path_id': str(path_id),
        'user_id': str(user_id),
        'current_stage': ulp.current_stage,
        'progress': None
    }
    
    if latest_progress:
        response['progress'] = {
            'id': str(latest_progress.id),
            'status': latest_progress.status,
            'percentage': latest_progress.percentage,
            'created_at': latest_progress.created_at.isoformat() if latest_progress.created_at else None,
            'updated_at': latest_progress.updated_at.isoformat() if latest_progress.updated_at else None,
            'error_message': latest_progress.error_message
        }
    
    return jsonify(response)


@learning_paths_bp.get('/<uuid:path_id>/status')
@jwt_required()
def learning_path_overall_status(path_id):
    """Return overall status for a learning path: stage counts, next stage, etc."""
    STAGES = ['discover', 'organize', 'master', 'create', 'collaborate']

    user_id = UUID(get_jwt_identity())
    ulp = db.session.query(UserLearningPath).filter_by(user_id=user_id, path_id=path_id).first()
    if not ulp:
        return jsonify({'error': 'User not enrolled in this learning path'}), 404

    stage_status_map = ulp.stage_status or {}
    # Normalize & order
    stages = [{'name': s, 'status': stage_status_map.get(s, 'locked')} for s in STAGES]

    completed = sum(1 for s in stages if s['status'] == 'completed')
    unlocked  = sum(1 for s in stages if s['status'] == 'unlocked')
    locked    = sum(1 for s in stages if s['status'] == 'locked')
    total     = len(STAGES)
    percent_complete = round((completed / total) * 100, 2)

    # First non-completed stage = next actionable
    next_stage = next((s['name'] for s in stages if s['status'] != 'completed'), None)

    # Latest LP progress across any stage (optional)
    latest_lp_progress = (
        db.session.query(Progress)
        .filter(Progress.user_id == str(user_id), Progress.tool.like('learning_path:%'))
        .order_by(Progress.created_at.desc())
        .first()
    )
    latest_progress = None
    if latest_lp_progress:
        latest_progress = {
            'id': str(latest_lp_progress.id),
            'status': latest_lp_progress.status,
            'percentage': latest_lp_progress.percentage,
            'created_at': latest_lp_progress.created_at.isoformat() if latest_lp_progress.created_at else None,
            'updated_at': latest_lp_progress.updated_at.isoformat() if latest_lp_progress.updated_at else None,
            'error_message': latest_lp_progress.error_message,
        }

    # Pull file_ids (if you store them in ulp.meta)
    file_ids = None
    try:
        if ulp.meta:
            meta = ulp.meta if isinstance(ulp.meta, dict) else json.loads(ulp.meta)
            file_ids = meta.get('file_ids')
    except Exception:
        pass

    return jsonify({
        'learning_path_id': str(path_id),
        'user_id': str(user_id),
        'status': ulp.status,                 # e.g., active/paused/completed
        'current_stage': ulp.current_stage,   # e.g., "organize"
        'current_step': ulp.current_step,     # numeric if you track steps inside a stage
        'stages': stages,                     # ordered list with per-stage status
        'counts': {
            'total': total,
            'completed': completed,
            'unlocked': unlocked,
            'locked': locked,
        },
        'percent_complete': percent_complete, # 0–100
        'next_stage': next_stage,             # first non-completed stage or None
        'latest_progress': latest_progress,   # last LP-wide progress row
        'file_ids': file_ids,
        'created_at': ulp.created_at.isoformat() if ulp.created_at else None,
        'updated_at': ulp.updated_at.isoformat() if ulp.updated_at else None,
    }), 200

@learning_paths_bp.get('/<uuid:path_id>/session/<uuid:session_id>/status')
@jwt_required()
def get_session_status(path_id, session_id):
    """Return status for a SPECIFIC learning path session (ULP)."""
    STAGES = ['discover', 'organize', 'master', 'create', 'collaborate']

    user_id = UUID(get_jwt_identity())

    # Get the SPECIFIC session (ULP), not just any session for this user+path
    ulp = db.session.query(UserLearningPath).filter_by(
        id=session_id,
        user_id=user_id,
        path_id=path_id
    ).first()

    if not ulp:
        return jsonify({'error': 'Session not found or unauthorized'}), 404

    stage_status_map = ulp.stage_status or {}
    stages = [{'name': s, 'status': stage_status_map.get(s, 'locked')} for s in STAGES]

    completed = sum(1 for s in stages if s['status'] == 'completed')
    unlocked  = sum(1 for s in stages if s['status'] == 'unlocked')
    locked    = sum(1 for s in stages if s['status'] == 'locked')
    total     = len(STAGES)
    percent_complete = round((completed / total) * 100, 2)

    next_stage = next((s['name'] for s in stages if s['status'] != 'completed'), None)

    # Pull file_ids from THIS session's meta
    file_ids = []
    try:
        if ulp.meta:
            meta = ulp.meta if isinstance(ulp.meta, dict) else json.loads(ulp.meta)
            file_ids = meta.get('file_ids', [])
    except Exception:
        pass

    return jsonify({
        'learning_path_id': str(path_id),
        'user_learning_path_id': str(ulp.id),
        'user_id': str(user_id),
        'status': ulp.status,
        'current_stage': ulp.current_stage,
        'current_step': ulp.current_step,
        'stages': stages,
        'counts': {
            'total': total,
            'completed': completed,
            'unlocked': unlocked,
            'locked': locked,
        },
        'percent_complete': percent_complete,
        'next_stage': next_stage,
        'file_ids': file_ids,
        'created_at': ulp.created_at.isoformat() if ulp.created_at else None,
        'updated_at': ulp.updated_at.isoformat() if ulp.updated_at else None,
    }), 200

@learning_paths_bp.get('/<uuid:path_id>/active-sessions')
@jwt_required()
def get_active_learning_path_sessions(path_id):
    """Get all active learning path sessions for current user and this path."""
    user_id = UUID(get_jwt_identity())

    # Get all active UserLearningPath records
    active_sessions = db.session.query(UserLearningPath).filter_by(
        user_id=user_id,
        path_id=path_id,
        status='active'
    ).order_by(UserLearningPath.updated_at.desc()).all()

    results = []
    for ulp in active_sessions:
        # Extract file info
        file_ids = []
        file_names = []
        try:
            if ulp.meta:
                meta = ulp.meta if isinstance(ulp.meta, dict) else {}
                file_ids = meta.get('file_ids', [])

                if file_ids:
                    # Convert string UUIDs to UUID objects for query
                    uuid_file_ids = []
                    for fid in file_ids:
                        try:
                            uuid_file_ids.append(UUID(fid) if isinstance(fid, str) else fid)
                        except (ValueError, AttributeError):
                            pass

                    if uuid_file_ids:
                        files = db.session.query(UploadedFile).filter(UploadedFile.id.in_(uuid_file_ids)).all()
                        file_names = [f.original_filename or f.stored_filename for f in files]
        except Exception as e:
            print(f"Error extracting file info: {e}")

        # Calculate progress
        stage_status = ulp.stage_status or {}
        stages = ['discover', 'organize', 'master', 'create', 'collaborate']
        completed = sum(1 for s in stages if stage_status.get(s) == 'completed')
        progress_pct = round((completed / len(stages)) * 100)

        results.append({
            'user_learning_path_id': str(ulp.id),
            'current_stage': ulp.current_stage or 'discover',
            'file_ids': [str(fid) for fid in file_ids],
            'file_names': file_names,
            'file_count': len(file_ids),
            'progress_percentage': progress_pct,
            'stages_completed': completed,
            'total_stages': len(stages),
            'stage_status': stage_status,
            'created_at': ulp.created_at.isoformat() if ulp.created_at else None,
            'updated_at': ulp.updated_at.isoformat() if ulp.updated_at else None
        })

    return jsonify({'active_sessions': results, 'count': len(results)})

@learning_paths_bp.post('/<uuid:path_id>/create-session')
@jwt_required()
def create_new_learning_path_session(path_id):
    """Create a new learning path session for the user."""
    user_id = UUID(get_jwt_identity())

    # Verify the learning path exists
    path = db.session.query(LearningPath).filter_by(id=path_id, is_active=True).first()
    if not path:
        return jsonify({'error': 'Learning path not found'}), 404

    # Create new UserLearningPath record
    ulp = UserLearningPath(
        user_id=user_id,
        path_id=path_id,
        status='active',
        current_stage='discover',
        stage_status={
            'discover': 'unlocked',
            'organize': 'locked',
            'master': 'locked',
            'create': 'locked',
            'collaborate': 'locked'
        },
        meta={}
    )
    db.session.add(ulp)
    db.session.commit()

    return jsonify({
        'message': 'New session created',
        'session': {
            'user_learning_path_id': str(ulp.id),
            'current_stage': ulp.current_stage,
            'status': ulp.status,
            'stage_status': ulp.stage_status,
            'file_ids': []
        }
    }), 201

@learning_paths_bp.post('/<uuid:path_id>/resume/<uuid:session_id>')
@jwt_required()
def resume_learning_path_session(path_id, session_id):
    """Resume a specific learning path session."""
    user_id = UUID(get_jwt_identity())

    # Verify ownership
    ulp = db.session.query(UserLearningPath).filter_by(
        id=session_id,
        user_id=user_id,
        path_id=path_id
    ).first()

    if not ulp:
        return jsonify({'error': 'Session not found or unauthorized'}), 404

    # Mark as active and update timestamp
    ulp.status = 'active'
    ulp.updated_at = datetime.utcnow()
    db.session.commit()

    # Extract file IDs
    file_ids = []
    try:
        if ulp.meta:
            meta = ulp.meta if isinstance(ulp.meta, dict) else {}
            file_ids = meta.get('file_ids', [])
    except Exception:
        pass

    return jsonify({
        'message': 'Session resumed',
        'session': {
            'user_learning_path_id': str(ulp.id),
            'current_stage': ulp.current_stage or 'discover',
            'file_ids': [str(fid) for fid in file_ids],
            'stage_status': ulp.stage_status or {}
        }
    })

@learning_paths_bp.post('/<uuid:path_id>/session/<uuid:session_id>/files')
@jwt_required()
def update_session_files(path_id, session_id):
    """Update files for a learning path session."""
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}
    file_ids = data.get('file_ids', [])

    # Verify ownership
    ulp = db.session.query(UserLearningPath).filter_by(
        id=session_id,
        user_id=user_id,
        path_id=path_id
    ).first()

    if not ulp:
        return jsonify({'error': 'Session not found or unauthorized'}), 404

    # Update meta with file_ids
    meta = ulp.meta if isinstance(ulp.meta, dict) else {}
    meta['file_ids'] = file_ids
    ulp.meta = meta
    ulp.updated_at = datetime.utcnow()

    # Use flag_modified to ensure SQLAlchemy detects JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(ulp, 'meta')

    db.session.commit()

    return jsonify({
        'message': 'Files updated',
        'file_ids': file_ids
    })

def _group_steps_by_stage(steps):
    grouped = {"discover": [], "organize": [], "master": [], "create": [], "collaborate": []}
    for s in steps:
        stage = (s.config or {}).get("stage", "discover")
        grouped.setdefault(stage, []).append({
            "id": str(s.id),
            "position": s.position,
            "tool_key": s.tool_key,
            "title": s.title,
            "config": s.config or {},
            "instructions": s.instructions,
        })
    # sort by position inside each stage
    for k in grouped:
        grouped[k] = sorted(grouped[k], key=lambda x: x["position"])
    return grouped

def _serialize_path(lp, include_steps=False, grouped=True):
    obj = {
        "id": str(lp.id),
        "slug": lp.slug,
        "title": lp.title,
        "description": lp.description,
        "est_minutes": lp.est_minutes,
        "is_active": lp.is_active,
        "created_at": lp.created_at.isoformat() if lp.created_at else None,
        "updated_at": lp.updated_at.isoformat() if lp.updated_at else None,
    }
    if include_steps:
        steps = (db.session.query(LearningPathStep)
                 .filter(LearningPathStep.path_id == lp.id)
                 .order_by(asc(LearningPathStep.position))
                 .all())
        if grouped:
            obj["stages"] = _group_steps_by_stage(steps)
        else:
            obj["steps"] = [{
                "id": str(s.id),
                "position": s.position,
                "tool_key": s.tool_key,
                "title": s.title,
                "config": s.config or {},
                "instructions": s.instructions,
            } for s in steps]
    return obj

@learning_paths_bp.get("/")
@jwt_required()
def list_learning_paths():
    """
    GET /api/learning_paths
      ?include_steps=true|false (default false)
      ?grouped=true|false       (default true; only used if include_steps=true)
      ?active_only=true|false   (default true)
    """
    include_steps = (request.args.get("include_steps", "false").lower() == "true")
    grouped = (request.args.get("grouped", "true").lower() == "true")
    active_only = (request.args.get("active_only", "true").lower() == "true")

    q = db.session.query(LearningPath).order_by(asc(LearningPath.title))
    if active_only:
        q = q.filter(LearningPath.is_active.is_(True))

    items = [_serialize_path(lp, include_steps=include_steps, grouped=grouped) for lp in q.all()]
    return jsonify({"items": items, "count": len(items)})
