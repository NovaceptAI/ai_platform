from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
import logging
import os, jwt

# Initialize .env variables
load_dotenv()

# Import app services and database
from db import db
from services.logging_service import log_endpoint

# Flask App Initialization
app = Flask(__name__)
SECRET_KEY = os.getenv('JWT_SECRET', 'your_secret_key')  # Use the same secret key for encoding and decoding JWTs
# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/scoolish'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Logging Configuration
log_file = '/home/azureuser/ai_platform/backend/app/logs/app.log'
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)

# Attach handler to app and root logger
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

# Log startup
app.logger.info("Flask application has started successfully!")

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Register Blueprints

# Auth
from routes.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

# Upload
from routes.upload import upload_bp
app.register_blueprint(upload_bp, url_prefix='/upload')

# Discover Stage
from stages.discover.summarizer.summarizer_routes import summarizer_bp
from stages.discover.segmenter.segmenter_routes import segmenter_bp
from stages.discover.interactive_timeline_explorer.timeline_explorer_routes import timeline_explorer_bp
from stages.discover.visual_study_guide.study_guide_routes import study_guide_bp
from stages.discover.math_problem_visualizer.math_problem_visualizer_routes import math_problem_visualiser_bp
from stages.discover.topic_modeller.modeller_routes import modeller_bp

app.register_blueprint(summarizer_bp, url_prefix='/summarizer')
app.register_blueprint(segmenter_bp, url_prefix='/segmenter')
app.register_blueprint(timeline_explorer_bp, url_prefix='/timeline_explorer')
app.register_blueprint(study_guide_bp, url_prefix='/study_guide')
app.register_blueprint(math_problem_visualiser_bp, url_prefix='/math_problem_visualizer')
app.register_blueprint(modeller_bp, url_prefix='/modeller')

# Master Stage
from stages.master.ai_quiz_creator.quiz_creator_routes import quiz_creator_bp
from stages.master.homework_helper.homework_helper_routes import homework_helper_bp

app.register_blueprint(quiz_creator_bp, url_prefix='/quiz_creator')
app.register_blueprint(homework_helper_bp, url_prefix='/homework_helper')

# Collaborate Stage
from stages.collaborate.digital_debate.digital_debate_routes import digital_debate_bp
app.register_blueprint(digital_debate_bp, url_prefix='/digital_debate')

# MVP Tools
from ai_tools.chrono_ai.chrono_ai_routes import chrono_ai_bp
from ai_tools.story_visualizer.story_routes import story_bp
from ai_tools.document_analyzer.document_analyzer_routes import document_analyzer_bp

app.register_blueprint(chrono_ai_bp, url_prefix='/chrono_ai')
app.register_blueprint(story_bp, url_prefix='/story_visualizer')
app.register_blueprint(document_analyzer_bp, url_prefix='/document_analyzer')

# Create tables inside the app context
with app.app_context():
    db.create_all()
    print("✅ Tables created successfully.")

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
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            username = payload.get('username', 'anonymous')
        except jwt.ExpiredSignatureError:
            app.logger.warning("JWT expired")
        except jwt.InvalidTokenError:
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