from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
import logging
import os
import jwt as pyjwt
from app import make_celery
from flask_jwt_extended import JWTManager
from datetime import timedelta
# Initialize .env variables
load_dotenv()

# Import app services and database
from app.db import db
from app.services.logging_service import log_endpoint

# Flask App Initialization
app = Flask(__name__)
SECRET_KEY = os.getenv('JWT_SECRET', 'your_secret_key')  # Use the same secret key for encoding and decoding JWTs

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://novacept:password@localhost:5432/scoolish"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = SECRET_KEY  # required
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  # optional
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
db.init_app(app)

# Celery Configuration
celery_app = make_celery(app)

# JWT Configuration
jwt = JWTManager(app)

# Centralized logging configuration
from app.logging_setup import configure_logging
configure_logging(app)

# Log startup
app.logger.info("Flask application has started successfully!")

# Enable CORS for all domains and all routes
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})

# Import Blueprints
# Auth
from app.routes.auth import auth_bp

# Upload
from app.routes.upload import upload_bp

# Discover Stage
from app.stages.discover.summarizer.summarizer_routes import summarizer_bp
from app.routes.stages.discover.summarizer_batch_routes import summ_batch_bp
# from app.stages.discover.segmenter.segmenter_routes import segmenter_bp
# from app.stages.discover.interactive_timeline_explorer.timeline_explorer_routes import timeline_explorer_bp
# from app.stages.discover.visual_study_guide.study_guide_routes import study_guide_bp
from app.stages.discover.math_problem_visualizer.math_problem_visualizer_routes import math_problem_visualiser_bp
from app.stages.discover.topic_modeller.modeller_routes import modeller_bp
from app.routes.stages.discover.chrono_routes import chrono_bp
from app.routes.stages.discover.sentiment_routes import sentiment_bp
from app.routes.stages.discover.segmenter_routes import segmenter_bp
from app.routes.stages.discover.visual_guide_routes import vsg_bp
from app.routes.stages.discover.math_visualizer_routes import math_visualizer_bp
from app.routes.stages.discover.timeline_explorer_routes import timeline_explorer_bp

# Create Stage
from app.routes.stages.create.creative_prompts_routes import creative_prompts_bp

# Document Analysis
from app.routes.doc_analysis_routes import doc_bp

# Master Stage
from app.routes.stages.master.quiz_creator_routes import quiz_creator_bp
from app.stages.master.homework_helper.homework_helper_routes import homework_helper_bp

# Collaborate Stage
from app.stages.collaborate.digital_debate.digital_debate_routes import digital_debate_bp

# MVP Tools

from app.ai_tools.story_visualizer.story_routes import story_bp
from app.ai_tools.document_analyzer.document_analyzer_routes import document_analyzer_bp

# Progress Routes
from app.routes.progress_routes import progress_bp


# Register Blueprints
# Auth
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Upload
app.register_blueprint(upload_bp, url_prefix='/api/upload')

# Discover Stage
app.register_blueprint(summarizer_bp, url_prefix='/api/summarizer')
app.register_blueprint(summ_batch_bp, url_prefix='/api/batch_summarizer')
app.register_blueprint(modeller_bp, url_prefix='/api/modeller')
app.register_blueprint(chrono_bp, url_prefix='/api/chronology')
app.register_blueprint(sentiment_bp, url_prefix='/api/sentiment')
app.register_blueprint(segmenter_bp, url_prefix='/api/segmenter')
app.register_blueprint(vsg_bp, url_prefix='/api/study_guide')
app.register_blueprint(math_visualizer_bp, url_prefix='/api/math_visualizer')
app.register_blueprint(timeline_explorer_bp, url_prefix='/api/timeline_explorer')

# Create Stage
app.register_blueprint(creative_prompts_bp, url_prefix='/api/creative_prompts')

# Document Analysis
app.register_blueprint(doc_bp, url_prefix='/api/doc_analysis')

# Master Stage
app.register_blueprint(quiz_creator_bp, url_prefix='/api/quiz_creator')
app.register_blueprint(homework_helper_bp, url_prefix='/api/homework_helper')

# Collaborate Stage
app.register_blueprint(digital_debate_bp, url_prefix='/api/digital_debate')

# MVP Tools
app.register_blueprint(story_bp, url_prefix='/api/story_visualizer')
app.register_blueprint(document_analyzer_bp, url_prefix='/api/document_analyzer')

# Progress Routes
app.register_blueprint(progress_bp, url_prefix='/api/progress')


# Default route (temporary)
@app.route('/')
def home():
    return os.getenv("AZURE_OPENAI_API_KEY", "API key not found")

# Log all requests (excluding static files)
@app.before_request
def log_all_requests():
    username = 'anonymous'
    auth_header = request.headers.get('Authorization')

    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(" ")[1]
        try:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
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

# Run App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)