from flask import Blueprint, request, jsonify
from uuid import uuid4
from app.db import db
from app.models import Progress, UploadedFile
from sqlalchemy import or_


def _resolve_file_id(filename: str, user_id: str = None):
    if not filename:
        return None
    q = db.session.query(UploadedFile.id)
    conds = []
    if hasattr(UploadedFile, 'stored_file_name'):
        conds.append(UploadedFile.stored_file_name == filename)
    if hasattr(UploadedFile, 'original_file_name'):
        conds.append(UploadedFile.original_file_name == filename)
    if hasattr(UploadedFile, 'filename'):
        conds.append(UploadedFile.filename == filename)
    if not conds:
        return None
    if user_id and hasattr(UploadedFile, 'user_id'):
        row = q.filter(or_(*conds), UploadedFile.user_id == user_id).first()
    else:
        row = q.filter(or_(*conds)).first()
    return str(row[0]) if row else None


def _make_dummy_blueprint(tool_name: str, url_prefix: str):
    bp = Blueprint(tool_name, __name__)

    @bp.route('/start', methods=['POST'])
    def start():
        data = request.get_json(force=True, silent=True) or {}
        file_id = data.get('file_id') or data.get('filename') or data.get('stored_name')
        user_id = data.get('user_id')

        # Resolve filename to file_id if needed
        if file_id and len(str(file_id)) < 36:
            maybe = _resolve_file_id(str(file_id), user_id=user_id)
            file_id = maybe or None
        if not file_id:
            return jsonify({'error': 'file_id or filename required'}), 400

        prog_id = uuid4()
        p = Progress(
            id=prog_id,
            file_id=file_id,
            user_id=user_id,
            tool=tool_name,
            status='done',
            percentage=100
        )
        db.session.add(p)
        db.session.commit()
        return jsonify({'message': f'{tool_name} is under development', 'progress_id': str(prog_id), 'file_id': str(file_id)}), 202

    @bp.route('/progress/<uuid:progress_id>', methods=['GET'])
    def progress(progress_id):
        p = db.session.query(Progress).get(progress_id)
        if not p:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'progress_id': str(p.id),
            'file_id': str(p.file_id),
            'tool': p.tool,
            'status': p.status,
            'percentage': p.percentage or 0
        })

    @bp.route('/results', methods=['GET'])
    def results():
        return jsonify({'message': f'{tool_name} tool is still under development.'})

    bp.url_prefix = url_prefix
    return bp


# Create blueprints for each dummy tool
clustering_bp = _make_dummy_blueprint('clustering', '/api/clustering')
similarity_bp = _make_dummy_blueprint('similarity', '/api/similarity')
report_export_bp = _make_dummy_blueprint('report_export', '/api/report_export')