from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import UUID
from datetime import datetime
from app.db import db
from app.models.research import ResearchProject, ProjectFile, ResearchSession, BrowserSearch, ScrapeSource, SessionNote
from app.models.files import UploadedFile, FilePage
from app.models.status import Progress
from app.tasks.live_research_tasks import browser_search_task, scraper_task, synthesize_notes_task
import os
import json

live_research_bp = Blueprint('live_research', __name__, url_prefix='/api/research')

@live_research_bp.post('/projects')
@jwt_required()
def create_project():
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}
    if 'title' not in data:
        return jsonify({'error': 'title required'}), 400
    proj = ResearchProject(user_id=user_id, title=data['title'], topic=data.get('topic'), description=data.get('description'), vault_folder=data.get('vault_folder'))
    db.session.add(proj)
    db.session.commit()
    return jsonify({'id': str(proj.id)}), 201

@live_research_bp.get('/projects')
@jwt_required()
def list_projects():
    user_id = UUID(get_jwt_identity())
    projs = db.session.query(ResearchProject).filter_by(user_id=user_id).order_by(ResearchProject.created_at.desc()).all()
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

@live_research_bp.get('/projects/<uuid:project_id>/sessions/active')
@jwt_required()
def get_or_create_session(project_id):
    """Get existing active session or create new one"""
    user_id = UUID(get_jwt_identity())

    # Check for existing active session
    existing = db.session.query(ResearchSession).filter_by(
        project_id=project_id,
        user_id=user_id,
        active=True
    ).order_by(ResearchSession.started_at.desc()).first()

    if existing:
        return jsonify({
            'session_id': str(existing.id),
            'project_id': str(existing.project_id),
            'active': existing.active,
            'started_at': existing.started_at.isoformat() if existing.started_at else None,
            'is_new': False,
            'meta': existing.meta or {}
        })

    # Create new session
    from app.services.live_research_service import LiveResearchService
    svc = LiveResearchService(session=db.session)
    rs = svc.start_session(user_id, project_id)
    return jsonify({
        'session_id': str(rs.id),
        'project_id': str(rs.project_id),
        'active': rs.active,
        'started_at': rs.started_at.isoformat() if rs.started_at else None,
        'is_new': True
    }), 201

@live_research_bp.post('/projects/<uuid:project_id>/sessions/start')
@jwt_required()
def start_new_session(project_id):
    """Force start a new session (ends active ones)"""
    user_id = UUID(get_jwt_identity())

    # End existing active sessions
    active_sessions = db.session.query(ResearchSession).filter_by(
        project_id=project_id,
        user_id=user_id,
        active=True
    ).all()

    for s in active_sessions:
        s.active = False
        s.ended_at = datetime.utcnow()

    # Create new session
    from app.services.live_research_service import LiveResearchService
    svc = LiveResearchService(session=db.session)
    rs = svc.start_session(user_id, project_id)
    return jsonify({
        'session_id': str(rs.id),
        'project_id': str(rs.project_id),
        'active': rs.active,
        'started_at': rs.started_at.isoformat() if rs.started_at else None
    }), 201

@live_research_bp.get('/sessions/<uuid:session_id>/messages')
@jwt_required()
def get_session_messages(session_id):
    """Get chat messages for a session (max 20 most recent)"""
    messages = db.session.query(SessionNote).filter(
        SessionNote.session_id == session_id,
        SessionNote.note_type.in_(['user', 'assistant'])
    ).order_by(SessionNote.created_at.asc()).limit(20).all()

    return jsonify([{
        'id': str(msg.id),
        'role': msg.note_type,  # 'user' or 'assistant'
        'content': msg.content,
        'timestamp': msg.created_at.isoformat() if msg.created_at else None
    } for msg in messages])

@live_research_bp.put('/sessions/<uuid:session_id>/meta')
@jwt_required()
def update_session_meta(session_id):
    """Update session metadata (e.g., selected files)"""
    from sqlalchemy.orm.attributes import flag_modified

    s = db.session.get(ResearchSession, session_id)
    if not s:
        return jsonify({'error': 'Session not found'}), 404

    data = request.get_json() or {}
    # Update or merge meta
    if s.meta is None:
        s.meta = {}
    s.meta.update(data)

    # Flag the column as modified so SQLAlchemy knows to update it
    flag_modified(s, 'meta')

    db.session.commit()
    return jsonify({'ok': True, 'meta': s.meta})

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
    note_type = data.get('note_type', 'text')

    note = SessionNote(
        session_id=session_id,
        note_type=note_type,
        content=data.get('content', ''),
        meta=data.get('meta', {})
    )
    db.session.add(note)

    # If this is a chat message (user or assistant), keep only last 50 messages (increased from 20)
    if note_type in ['user', 'assistant']:
        # Get all chat messages for this session, ordered by creation time
        chat_messages = db.session.query(SessionNote).filter(
            SessionNote.session_id == session_id,
            SessionNote.note_type.in_(['user', 'assistant'])
        ).order_by(SessionNote.created_at.desc()).all()

        # If we have more than 50, delete the oldest ones
        if len(chat_messages) >= 50:
            # Keep newest 49 (plus the one we're adding = 50 total)
            messages_to_delete = chat_messages[49:]
            for msg in messages_to_delete:
                db.session.delete(msg)

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

# New endpoints for Research Workspace

@live_research_bp.post('/chat')
@jwt_required()
def research_chat():
    """
    AI Chat endpoint for research workspace
    Accepts a message and returns AI-generated response based on project context
    Supports 'azure' (default) and 'chatgpt' modes
    """
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}

    project_id = data.get('project_id')
    message = data.get('message', '')
    selected_file_ids = data.get('selected_file_ids', [])
    mode = data.get('mode', 'azure')  # 'azure' or 'chatgpt'

    if not project_id or not message:
        return jsonify({'error': 'project_id and message required'}), 400

    try:
        # Get project
        project = db.session.get(ResearchProject, UUID(project_id))
        if not project or project.user_id != user_id:
            return jsonify({'error': 'Project not found or unauthorized'}), 404

        # Get active session to load conversation history
        active_session = db.session.query(ResearchSession).filter_by(
            project_id=UUID(project_id),
            user_id=user_id,
            active=True
        ).order_by(ResearchSession.started_at.desc()).first()

        # Load recent conversation history (last 10 exchanges = 20 messages)
        conversation_history = []
        if active_session:
            recent_messages = db.session.query(SessionNote).filter(
                SessionNote.session_id == active_session.id,
                SessionNote.note_type.in_(['user', 'assistant'])
            ).order_by(SessionNote.created_at.desc()).limit(20).all()
            
            # Reverse to chronological order
            conversation_history = [
                {"role": msg.note_type, "content": msg.content}
                for msg in reversed(recent_messages)
            ]

        # Gather context from selected files (min: whatever available, max: 5 pages)
        context_parts = []
        total_pages_loaded = 0

        if selected_file_ids:
            for file_id in selected_file_ids:
                try:
                    uploaded_file = db.session.get(UploadedFile, UUID(file_id))
                    if uploaded_file and uploaded_file.user_id == str(user_id):
                        # Get file pages/content (all available, max 5)
                        pages = db.session.query(FilePage).filter_by(
                            file_id=uploaded_file.id
                        ).order_by(FilePage.page_number).limit(5).all()

                        if pages:
                            file_context = f"\n--- Document: {uploaded_file.original_file_name} ---\n"
                            for page in pages:
                                if page.page_text:
                                    # Use full page text (not truncated)
                                    file_context += f"\n[Page {page.page_number}]\n{page.page_text}\n"
                                    total_pages_loaded += 1
                            context_parts.append(file_context)
                        elif uploaded_file.overall_summary:
                            # Fallback to summary if no pages
                            context_parts.append(
                                f"\n--- Summary of {uploaded_file.original_file_name} ---\n"
                                f"{uploaded_file.overall_summary}\n"
                            )
                except Exception as e:
                    print(f"Error loading file {file_id}: {e}")

        # Build prompt for AI with conversation context
        context = "\n".join(context_parts) if context_parts else "No document context provided."

        system_prompt = """You are a helpful research assistant. Provide detailed, accurate answers based on the document context and conversation history provided.

IMPORTANT: You have access to the full conversation history. Reference previous questions and answers when relevant. Build on the ongoing discussion naturally."""

        # Build messages array for chat completion
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if available
        if conversation_history:
            # Include context in first user message if we have history
            first_message_with_context = f"""Project: {project.title}
Topic: {project.topic or 'General Research'}

Document Context ({total_pages_loaded} pages loaded):
{context}

[Continuing our conversation...]
{conversation_history[0]['content']}"""
            
            messages.append({"role": "user", "content": first_message_with_context})
            
            # Add rest of conversation history
            messages.extend(conversation_history[1:])
        else:
            # First message in conversation - include full context
            context_message = f"""Project: {project.title}
Topic: {project.topic or 'General Research'}

Document Context ({total_pages_loaded} pages loaded):
{context}"""
            messages.append({"role": "user", "content": context_message})
        
        # Add current user message
        messages.append({"role": "user", "content": message})

        # Call AI based on mode
        try:
            import openai

            if mode == 'chatgpt':
                # Direct OpenAI (ChatGPT) mode
                openai.api_type = "open_ai"
                openai.api_base = "https://api.openai.com/v1"
                openai.api_key = os.getenv("OPENAI_API_KEY")
                openai.api_version = None

                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )

                ai_response = response.choices[0].message.content
                response_mode = "ChatGPT Direct"

            else:
                # Azure OpenAI mode (default)
                from app.services.openai_key_manager import key_manager

                # Get next available Azure endpoint
                api_key, api_base, index = key_manager.get_next()

                if not api_key or not api_base:
                    raise ValueError("No valid Azure OpenAI endpoints configured")

                # Configure openai for Azure (v0.28 style)
                openai.api_type = "azure"
                openai.api_base = api_base
                openai.api_key = api_key
                openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")

                deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

                response = openai.ChatCompletion.create(
                    engine=deployment,
                    messages=messages,  # Use the full conversation history
                    temperature=0.7,
                    max_tokens=2000
                )

                ai_response = response.choices[0].message.content
                response_mode = f"Azure OpenAI (endpoint #{index})"

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"OpenAI API error: {e}")
            print(f"Full traceback: {error_detail}")

            return jsonify({
                'error': f'AI API error: {str(e)}',
                'details': error_detail if os.getenv('DEBUG') == 'True' else None
            }), 500

        return jsonify({
            'response': ai_response,
            'timestamp': datetime.utcnow().isoformat(),
            'mode': response_mode,
            'context_loaded': {
                'files': len(selected_file_ids),
                'pages': total_pages_loaded,
                'conversation_messages': len(conversation_history)
            }
        })

    except Exception as e:
        import traceback
        print(f"Chat error: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to process chat request: {str(e)}'}), 500


@live_research_bp.get('/vault/files/<uuid:file_id>/content')
@jwt_required()
def get_file_content(file_id):
    """
    Retrieve file content for document viewer
    """
    user_id = get_jwt_identity()

    try:
        uploaded_file = db.session.get(UploadedFile, file_id)

        if not uploaded_file or uploaded_file.user_id != user_id:
            return jsonify({'error': 'File not found or unauthorized'}), 404

        # Get all pages for the file
        pages = db.session.query(FilePage).filter_by(file_id=file_id).order_by(FilePage.page_number).all()

        if pages:
            # Concatenate all page text
            content = "\n\n".join([
                f"--- Page {p.page_number} ---\n{p.page_text}"
                for p in pages if p.page_text
            ])
        else:
            # Fallback to summary if no pages
            content = uploaded_file.overall_summary or "No content available for this file."

        return jsonify({
            'content': content,
            'file_name': uploaded_file.original_file_name,
            'file_type': uploaded_file.file_type,
            'pages': len(pages)
        })

    except Exception as e:
        print(f"File content retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve file content'}), 500


@live_research_bp.get('/events/stream')
@jwt_required()
def event_stream():
    """
    Server-Sent Events endpoint for real-time knowledge monitoring
    """
    def generate():
        # This is a placeholder for SSE implementation
        # In production, you would:
        # 1. Subscribe to Redis pub/sub for project events
        # 2. Listen to Celery task updates
        # 3. Stream real-time analysis results

        yield f"data: {json.dumps({'type': 'connected', 'message': 'Knowledge monitor connected'})}\n\n"

        # Example: Send periodic updates (replace with actual event stream)
        import time
        for i in range(5):
            time.sleep(2)
            event = {
                'type': 'update',
                'timestamp': datetime.utcnow().isoformat(),
                'message': f'Monitoring research activities... ({i+1}/5)'
            }
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
