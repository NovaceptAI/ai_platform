from flask import Flask
from flask_cors import CORS
import os
from logging.handlers import RotatingFileHandler
import logging
from dotenv import load_dotenv

from routes.auth import auth_bp

# Discover APIs
from stages.discover.summarizer.summarizer_routes import summarizer_bp
from stages.discover.segmenter.segmenter_routes import segmenter_bp
from stages.discover.timeline_builder.timeline_builder_routes import timeline_builder_bp
from stages.discover.visual_study_guide.study_guide_routes import study_guide_bp
from stages.discover.math_problem_visualizer.math_problem_visualizer_routes import math_problem_visualiser_bp
from stages.discover.topic_modeller.modeller_routes import modeller_bp

# Organize APIs


# Master APIs
from stages.master.ai_quiz_creator.quiz_creator_routes import quiz_creator_bp
from stages.master.homework_helper.homework_helper_routes import homework_helper_bp

# Create APIs


# Collaborate APIs
from stages.collaborate.digital_debate.digital_debate_routes import digital_debate_bp

# MVP1
from ai_tools.chrono_ai.chrono_ai_routes import chrono_ai_bp
from ai_tools.story_visualizer.story_routes import story_bp
from ai_tools.document_analyzer.document_analyzer_routes import document_analyzer_bp

# MVP2



# Load environment variables from .env file
load_dotenv()

# Temporary check: print environment variables to verify
# print("AZURE_OPENAI_API_KEY:", os.getenv("AZURE_OPENAI_API_KEY"), flush=True)
# print("AZURE_OPENAI_API_BASE:", os.getenv("AZURE_OPENAI_API_BASE"))

app = Flask(__name__)

# Configure logging
log_file = '/home/azureuser/ai_platform/backend/app/logs/app.log'

# Set up the log handler
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)

# Set up the log format
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)

# Attach handler to app.logger
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Also attach handler to the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

# Log startup message
app.logger.info("Flask application has started successfully!")


# Configure Flask-CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Reguister blueprints

# Login and registration
app.register_blueprint(auth_bp, url_prefix='/auth')

# MVP1
app.register_blueprint(chrono_ai_bp, url_prefix='/chrono_ai')
app.register_blueprint(quiz_creator_bp, url_prefix='/quiz_creator')
app.register_blueprint(digital_debate_bp, url_prefix='/digital_debate')
app.register_blueprint(story_bp, url_prefix='/story_visualizer')
app.register_blueprint(summarizer_bp, url_prefix='/summarizer')
app.register_blueprint(segmenter_bp, url_prefix='/segmenter')
app.register_blueprint(modeller_bp, url_prefix='/modeller')
app.register_blueprint(document_analyzer_bp, url_prefix='/document_analyzer')

# MVP2
app.register_blueprint(homework_helper_bp, url_prefix='/homework_helper')
app.register_blueprint(study_guide_bp, url_prefix='/study_guide')
app.register_blueprint(timeline_builder_bp, url_prefix='/timeline_builder')
app.register_blueprint(math_problem_visualiser_bp, url_prefix='/math_problem_visualizer')

@app.route('/')
def home():
    return os.getenv("AZURE_OPENAI_API_KEY")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
    