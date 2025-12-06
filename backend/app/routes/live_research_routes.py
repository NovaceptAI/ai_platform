from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import UUID
from datetime import datetime
from app.db import db
from app.models.research import ResearchProject, ProjectFile, ResearchSession, BrowserSearch, ScrapeSource, SessionNote, ResearchArtifact
from app.models.files import UploadedFile, FilePage
from app.models.status import Progress
from app.tasks.live_research_tasks import browser_search_task, scraper_task, synthesize_notes_task
from app.services.research_artifacts_service import ResearchArtifactsService
from app.services.presentation_storage_service import delete_presentation
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
    """Get chat messages for a session (max 50 most recent, in chronological order)"""
    # Get the 50 most recent messages, then reverse to chronological order
    messages = db.session.query(SessionNote).filter(
        SessionNote.session_id == session_id,
        SessionNote.note_type.in_(['user', 'assistant'])
    ).order_by(SessionNote.created_at.desc()).limit(50).all()
    
    # Reverse to get chronological order (oldest first)
    messages = list(reversed(messages))

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
    research_mode = data.get('research_mode', 'strict')  # 'strict' or 'flexible'

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

        # System prompt based on research mode
        if context_parts:
            if research_mode == 'flexible':
                system_prompt = f"""You are a research assistant helping analyze these documents:

Document Context ({total_pages_loaded} pages loaded):
{context}

Response Guidelines:
1. PRIMARILY answer from the documents above - they are your main source
2. When documents contain relevant information: Use ONLY document content
3. When helpful for context or understanding: You may supplement with general knowledge
4. ALWAYS clearly distinguish between sources:
   • "According to your documents: ..."
   • "For additional context (general knowledge): ..."
   • "The documents don't cover this, but generally: ..."
5. Stay relevant to the research topic and documents

You may use general knowledge to:
- Explain concepts mentioned in documents
- Provide comparative context (e.g., laws in other countries)
- Define technical terms
- Answer follow-up questions that expand on document topics

But always prioritize and cite the documents when they contain relevant information."""
            else:  # strict mode
                system_prompt = f"""You are a research assistant specialized in analyzing the provided documents.

STRICT RULES:
1. ONLY answer questions about the content in the documents provided below
2. If the user asks about anything NOT in these documents, politely decline and redirect them to ask about the documents
3. Use conversation history to maintain context, but ALWAYS base your answers on the documents
4. If you don't find relevant information in the documents, say so explicitly
5. Never use external knowledge or make assumptions beyond what's in the documents

Document Context ({total_pages_loaded} pages loaded):
{context}

Remember: Your role is to help analyze THESE SPECIFIC DOCUMENTS, nothing else."""
        else:
            system_prompt = """You are a research assistant. 

IMPORTANT: The user has not selected any documents yet. Politely ask them to select documents from the left panel (\"Sources\") before you can assist with their research.

Do not answer general knowledge questions. Your purpose is to help users analyze their selected documents."""

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
            'research_mode': research_mode,
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


# ============================================================================
# Research Artifacts - Flashcards & Presentations
# ============================================================================

@live_research_bp.post('/sessions/<uuid:session_id>/flashcards')
@jwt_required()
def generate_flashcards(session_id):
    """
    Generate flashcards from research session documents.
    
    Request Body:
        {
            "file_ids": ["uuid1", "uuid2"],  # Required: list of file UUIDs
            "title": "My Flashcards",         # Required: artifact title
            "options": {                      # Optional: generation options
                "max_cards": 20,
                "difficulty": "medium",
                "include_definitions": true,
                "include_concepts": true,
                "include_facts": true
            }
        }
    
    Returns:
        {
            "artifact_id": "uuid",
            "progress_id": "uuid",
            "status": "pending"
        }
    """
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}
    
    # Validate required fields
    if 'file_ids' not in data or not data['file_ids']:
        return jsonify({'error': 'file_ids required'}), 400
    if 'title' not in data or not data['title']:
        return jsonify({'error': 'title required'}), 400
    
    try:
        service = ResearchArtifactsService()
        result = service.generate_flashcards(
            session_id=str(session_id),
            user_id=str(user_id),
            file_ids=data['file_ids'],
            title=data['title'],
            options=data.get('options')
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to generate flashcards: {str(e)}'}), 500


@live_research_bp.get('/sessions/<uuid:session_id>/flashcards')
@jwt_required()
def list_flashcards(session_id):
    """
    List all flashcard artifacts for a research session.
    
    Returns:
        [
            {
                "id": "uuid",
                "title": "My Flashcards",
                "status": "completed",
                "progress_id": "uuid",
                "created_at": "2025-12-06T...",
                ...
            }
        ]
    """
    user_id = UUID(get_jwt_identity())
    
    try:
        service = ResearchArtifactsService()
        artifacts = service.list_artifacts(
            session_id=str(session_id),
            user_id=str(user_id),
            artifact_type='flashcards'
        )
        return jsonify(artifacts), 200
    except Exception as e:
        return jsonify({'error': f'Failed to list flashcards: {str(e)}'}), 500


@live_research_bp.get('/artifacts/<uuid:artifact_id>')
@jwt_required()
def get_artifact(artifact_id):
    """
    Get artifact by ID (works for both flashcards and presentations).
    
    Returns:
        {
            "id": "uuid",
            "artifact_type": "flashcards",
            "title": "My Flashcards",
            "status": "completed",
            "config_data": {...},
            "result_data": {...},
            "progress_id": "uuid",
            ...
        }
    """
    user_id = UUID(get_jwt_identity())
    
    try:
        service = ResearchArtifactsService()
        artifact = service.get_artifact(
            artifact_id=str(artifact_id),
            user_id=str(user_id)
        )
        
        if not artifact:
            return jsonify({'error': 'Artifact not found'}), 404
        
        return jsonify(artifact), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get artifact: {str(e)}'}), 500


@live_research_bp.get('/artifacts/<uuid:artifact_id>/progress')
@jwt_required()
def get_artifact_progress(artifact_id):
    """
    Get progress for an artifact (flashcards or presentation).
    
    Returns:
        {
            "progress_id": "uuid",
            "status": "in_progress",
            "percentage": 45,
            "message": "Processing...",
            "artifact_status": "processing"
        }
    """
    user_id = UUID(get_jwt_identity())
    
    try:
        service = ResearchArtifactsService()
        artifact = service.get_artifact(
            artifact_id=str(artifact_id),
            user_id=str(user_id)
        )
        
        if not artifact:
            return jsonify({'error': 'Artifact not found'}), 404
        
        # Get progress if available
        progress_data = {
            'artifact_id': str(artifact_id),
            'artifact_status': artifact['status']
        }
        
        if artifact.get('progress_id'):
            progress = db.session.query(Progress).filter(
                Progress.id == artifact['progress_id']
            ).first()
            
            if progress:
                progress_data.update({
                    'progress_id': str(progress.id),
                    'status': progress.status,
                    'percentage': progress.percentage,
                    'error_message': progress.error_message
                })
        
        return jsonify(progress_data), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get progress: {str(e)}'}), 500


@live_research_bp.post('/sessions/<uuid:session_id>/presentations')
@jwt_required()
def generate_presentation(session_id):
    """
    Generate AI presentation from research session documents.
    
    Request Body:
        {
            "file_id": "uuid",                # Optional: source file UUID
            "title": "My Presentation",        # Required: artifact title
            "options": {                       # Required: generation options
                "source_type": "text",         # text|file|vault
                "text_prompt": "...",          # Required if source_type=text
                "total_slides": 10,
                "theme": "professional_blue"
            }
        }
    
    Returns:
        {
            "artifact_id": "uuid",
            "progress_id": "uuid",
            "status": "pending"
        }
    """
    user_id = UUID(get_jwt_identity())
    data = request.get_json() or {}
    
    # Validate required fields
    if 'title' not in data or not data['title']:
        return jsonify({'error': 'title required'}), 400
    if 'options' not in data:
        return jsonify({'error': 'options required'}), 400
    
    try:
        service = ResearchArtifactsService()
        result = service.generate_presentation(
            session_id=str(session_id),
            user_id=str(user_id),
            file_id=data.get('file_id'),
            title=data['title'],
            options=data['options']
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to generate presentation: {str(e)}'}), 500


@live_research_bp.get('/sessions/<uuid:session_id>/presentations')
@jwt_required()
def list_presentations(session_id):
    """
    List all presentation artifacts for a research session.
    
    Returns:
        [
            {
                "id": "uuid",
                "title": "My Presentation",
                "status": "completed",
                "progress_id": "uuid",
                "created_at": "2025-12-06T...",
                ...
            }
        ]
    """
    user_id = UUID(get_jwt_identity())
    
    try:
        service = ResearchArtifactsService()
        artifacts = service.list_artifacts(
            session_id=str(session_id),
            user_id=str(user_id),
            artifact_type='presentation'
        )
        return jsonify(artifacts), 200
    except Exception as e:
        return jsonify({'error': f'Failed to list presentations: {str(e)}'}), 500


@live_research_bp.delete('/artifacts/<uuid:artifact_id>')
@jwt_required()
def delete_artifact(artifact_id):
    """
    Delete an artifact (flashcards or presentation).
    Also deletes associated files from Azure storage if applicable.
    
    Returns:
        {"message": "Artifact deleted successfully"}
    """
    user_id = UUID(get_jwt_identity())
    
    try:
        service = ResearchArtifactsService()
        
        # Get artifact to check ownership and type
        artifact = service.get_artifact(
            artifact_id=str(artifact_id),
            user_id=str(user_id)
        )
        
        if not artifact:
            return jsonify({'error': 'Artifact not found'}), 404
        
        # Delete Azure storage files for presentations
        if artifact['artifact_type'] == 'presentation':
            presentation_id = artifact.get('result_data', {}).get('presentation_id')
            if presentation_id:
                try:
                    # Use the proper delete function that handles both Azure storage and database
                    result = delete_presentation(str(user_id), str(presentation_id))
                    if not result.get('success'):
                        print(f"Warning: Presentation deletion failed: {result.get('error')}")
                except Exception as e:
                    print(f"Error deleting presentation: {e}")
        
        # Delete the artifact record
        artifact_record = db.session.query(ResearchArtifact).filter(
            ResearchArtifact.id == artifact_id
        ).first()
        
        if artifact_record:
            db.session.delete(artifact_record)
            db.session.commit()
        
        return jsonify({'message': 'Artifact deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete artifact: {str(e)}'}), 500
