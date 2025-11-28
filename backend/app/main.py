# app/main.py
from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import timedelta
import os
import jwt as pyjwt

# from app import make_flask_app
from app.db import db
from app import make_celery 
from app import models  # ensure models are imported before create_all
from app.logging_setup import configure_logging
from app.services.logging_service import log_endpoint
from flask_jwt_extended import JWTManager

load_dotenv()


def register_blueprints(flask_app: Flask) -> None:
    """Import and register all blueprints. Imported inside function to avoid circulars."""
    # Auth
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.onboarding import onboarding_bp

    # Upload
    from app.routes.upload import upload_bp
    from app.routes.file_prerequisites import file_prerequisites_bp

    # Discover Stage
    from app.routes.stages.discover.summarizer_routes import summarizer_bp
    from app.routes.stages.discover.summarizer_batch_routes import summ_batch_bp
    from app.routes.stages.discover.modeller_routes import modeller_bp
    from app.routes.stages.discover.chrono_routes import chrono_bp
    from app.routes.stages.discover.sentiment_routes import sentiment_bp
    from app.routes.stages.discover.segmenter_routes import segmenter_bp
    from app.routes.stages.discover.visual_guide_routes import vsg_bp
    from app.routes.stages.discover.timeline_explorer_routes import timeline_explorer_bp
    from app.routes.stages.discover.evidence_extractor_routes import evidence_extractor_bp
    from app.routes.stages.discover.readability_routes import readability_bp
    from app.routes.stages.discover.comparison_routes import comparison_bp
    from app.routes.stages.discover.explore_document_routes import explore_document_bp

    # Organize Stage
    from app.routes.organize_routes import organize_bp

    # Create Stage
    from app.routes.stages.create.creative_prompts_routes import creative_prompts_bp
    from app.routes.stages.create.essay_generator_routes import essay_generator_bp
    from app.routes.stages.create.infographic_creator_routes import infographic_creator_bp
    from app.routes.stages.create.report_builder_routes import report_builder_bp
    from app.routes.stages.create.story_visualizer_routes import story_visualizer_bp
    from app.routes.stages.create.ai_3d_model_builder_routes import ai_3d_model_builder_bp
    from app.routes.stages.create.story_to_comics_converter_routes import story_to_comics_bp
    from app.routes.stages.create.interactive_comic_strip_builder_routes import interactive_comic_strip_builder_bp
    from app.routes.stages.create.ai_presentation_builder_routes import ai_presentation_builder_bp
    from app.routes.stages.create.ai_art_creator_for_kids_routes import ai_art_creator_for_kids_bp
    from app.routes.stages.create.data_story_builder_routes import data_story_builder_bp
    from app.routes.stages.create.learn_by_drawing_routes import learn_by_drawing_bp

    # Document Analysis
    from app.routes.doc_analysis_routes import doc_bp

    # Knowledge Data Stage
    from app.routes.stages.knowledge_data.timeline_builder_routes import timeline_builder_bp

    # Master Stage
    from app.routes.stages.master.quiz_creator_routes import quiz_creator_bp
    from app.routes.stages.master.flashcards_routes import flashcards_bp
    from app.routes.stages.master.homework_helper_routes import homework_helper_bp
    from app.routes.stages.master.math_visualizer_routes import math_visualizer_bp
    from app.routes.stages.master.visual_study_guide_routes import visual_study_guide_bp
    from app.routes.stages.master.language_lab_routes import language_lab_bp
    from app.routes.stages.master.code_playground_routes import code_playground_bp
    from app.routes.stages.master.stem_challenge_routes import stem_challenge_bp
    from app.routes.stages.master.ethical_ai_tutor_routes import ethical_ai_tutor_bp
    from app.routes.stages.master.science_lab_routes import science_lab_bp

    # Collaborate Stage
    from app.routes.stages.collaborate.debate_routes import debate_bp
    from app.routes.stages.collaborate.mind_map_routes import mind_map_bp
    from app.routes.group_discussion_routes import group_discussion_bp
    from app.routes.peer_review_routes import peer_review_bp
    from app.routes.project_manager_routes import project_manager_bp

    # MVP Tools
    from app.routes.tool_progress import tool_progress_bp
   

    # Learning Paths
    from app.routes.learning_paths_routes import learning_paths_bp

    # Progress Routes
    from app.routes.progress_routes import progress_bp
    from app.routes.web_scraper_routes import web_bp

    # Register
    flask_app.register_blueprint(auth_bp, url_prefix='/api/auth')
    flask_app.register_blueprint(user_bp, url_prefix='/api/users')
    flask_app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')

    flask_app.register_blueprint(upload_bp, url_prefix='/api/upload')
    flask_app.register_blueprint(file_prerequisites_bp, url_prefix='/api/files')

    flask_app.register_blueprint(summarizer_bp, url_prefix='/api/summarizer')
    flask_app.register_blueprint(summ_batch_bp, url_prefix='/api/batch_summarizer')
    flask_app.register_blueprint(modeller_bp, url_prefix='/api/modeller')
    flask_app.register_blueprint(chrono_bp, url_prefix='/api/chronology')
    flask_app.register_blueprint(sentiment_bp, url_prefix='/api/sentiment')
    flask_app.register_blueprint(segmenter_bp, url_prefix='/api/segmenter')
    flask_app.register_blueprint(vsg_bp, url_prefix='/api/study_guide')
    flask_app.register_blueprint(math_visualizer_bp, url_prefix='/api/master/math_visualizer')
    flask_app.register_blueprint(timeline_explorer_bp, url_prefix='/api/timeline_explorer')
    flask_app.register_blueprint(evidence_extractor_bp, url_prefix='/api/stages/discover/evidence_extractor')
    flask_app.register_blueprint(readability_bp, url_prefix='/api/stages/discover/readability')
    flask_app.register_blueprint(comparison_bp, url_prefix='/api/stages/discover/comparison')
    flask_app.register_blueprint(explore_document_bp, url_prefix='/api/discover/explore_document')

    # Organize Stage
    flask_app.register_blueprint(organize_bp, url_prefix='/api/organize')

    flask_app.register_blueprint(creative_prompts_bp, url_prefix='/api/creative_prompts')
    flask_app.register_blueprint(essay_generator_bp, url_prefix='/api/create/essay_generator')
    flask_app.register_blueprint(infographic_creator_bp, url_prefix='/api/create/infographic_creator')
    flask_app.register_blueprint(report_builder_bp, url_prefix='/api/create/report_builder')
    flask_app.register_blueprint(story_visualizer_bp, url_prefix='/api/create/story_visualizer')
    flask_app.register_blueprint(story_to_comics_bp, url_prefix='/api/create/story_to_comics')
    flask_app.register_blueprint(doc_bp, url_prefix='/api/doc_analysis')

    flask_app.register_blueprint(quiz_creator_bp, url_prefix='/api/master/quiz_creator')
    flask_app.register_blueprint(flashcards_bp, url_prefix='/api/master/flashcards')
    flask_app.register_blueprint(homework_helper_bp, url_prefix='/api/master/homework_helper')
    flask_app.register_blueprint(visual_study_guide_bp, url_prefix='/api/master/visual_study_guide')
    flask_app.register_blueprint(language_lab_bp, url_prefix='/api/master/language_lab')
    flask_app.register_blueprint(code_playground_bp, url_prefix='/api/master/code_playground')
    flask_app.register_blueprint(stem_challenge_bp, url_prefix='/api/master/stem_challenge')
    flask_app.register_blueprint(ethical_ai_tutor_bp, url_prefix='/api/master/ethical_ai_tutor')
    flask_app.register_blueprint(science_lab_bp, url_prefix='/api/master/science_lab')

    # Collaborate Stage
    flask_app.register_blueprint(debate_bp, url_prefix='/api/stages/collaborate/debate')
    flask_app.register_blueprint(mind_map_bp, url_prefix='/api/stages/collaborate/mind_map')
    flask_app.register_blueprint(group_discussion_bp)
    flask_app.register_blueprint(peer_review_bp)
    flask_app.register_blueprint(project_manager_bp)

    # flask_app.register_blueprint(story_bp, url_prefix='/api/story_visualizer')
    # flask_app.register_blueprint(document_analyzer_bp, url_prefix='/api/document_analyzer')
    flask_app.register_blueprint(tool_progress_bp, url_prefix='/api/tools')
    flask_app.register_blueprint(ai_3d_model_builder_bp, url_prefix='/api/stages/create/ai_3d_model_builder')
    flask_app.register_blueprint(interactive_comic_strip_builder_bp, url_prefix='/api/interactive-comic-strip-builder')
    flask_app.register_blueprint(ai_presentation_builder_bp, url_prefix='/api/ai_presentation_builder')
    flask_app.register_blueprint(ai_art_creator_for_kids_bp, url_prefix='/api/ai_art_creator_for_kids')
    flask_app.register_blueprint(data_story_builder_bp, url_prefix='/api/data_story_builder')
    flask_app.register_blueprint(learn_by_drawing_bp, url_prefix='/api/learn_by_drawing')
    flask_app.register_blueprint(timeline_builder_bp, url_prefix='/api/timeline_builder')

    flask_app.register_blueprint(learning_paths_bp, url_prefix='/api/learning_paths')

    flask_app.register_blueprint(progress_bp, url_prefix='/api/progress')
    flask_app.register_blueprint(web_bp, url_prefix='/api/web')


def create_app() -> Flask:
    app = Flask(__name__)

    # Core config
    SECRET_KEY = os.getenv('JWT_SECRET', 'your_secret_key')
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET', 'dev_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL', "postgresql://novacept:password@172.178.120.199:5432/scoolish")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'pool_pre_ping': True,  # Verify connections before using them
        'max_overflow': 20,
    }
    app.config["JWT_SECRET_KEY"] = SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"

    # Init extensions
    db.init_app(app)
    JWTManager(app)
    configure_logging(app)
    
    # Initialize WebSocket support for collaboration
    from app.services.websocket_service import init_socketio
    socketio = init_socketio(app)

    app.logger.info("Flask application has started successfully!")

    # CORS
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": [
                    "http://172.178.120.199:3000",
                    "http://127.0.0.1:3000",
                    "http://172.178.120.199:3000",
                    "https://scoolish.com"
                ]
            }
        }
    )

    # Ensure tables (dev)
    if os.getenv("AUTO_CREATE_DB", "true").lower() == "true":
        try:
            with app.app_context():
                db.create_all()
                app.logger.info("Database tables ensured via create_all()")
        except Exception as _e:
            app.logger.warning(f"DB create_all skipped or failed: {_e}")

    # Blueprints
    register_blueprints(app)

    # Default route
    @app.route('/')
    def home():
        return os.getenv("AZURE_OPENAI_API_KEY", "API key not found")

    # Request logging
    @app.before_request
    def log_all_requests():
        username = 'anonymous'
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            try:
                payload = pyjwt.decode(token, os.getenv('JWT_SECRET', 'your_secret_key'), algorithms=["HS256"])
                username = payload.get('username', 'anonymous')
            except pyjwt.ExpiredSignatureError:
                app.logger.warning("JWT expired")
            except pyjwt.InvalidTokenError:
                app.logger.warning("Invalid JWT")

        log_endpoint(
            username=username,
            endpoint=request.path,
            method=request.method,
            ip_address=request.remote_addr
        )

    return app, socketio


# WSGI entrypoint
flask_app, socketio_app = create_app()

if __name__ == '__main__':
    socketio_app.run(flask_app, host='0.0.0.0', port=8000, debug=True)
