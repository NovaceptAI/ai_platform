from flask import Flask
from flask_cors import CORS
import os
from logging.handlers import RotatingFileHandler
import logging
from dotenv import load_dotenv

from routes.auth import auth_bp
from categories.scoolish_mvp1.chrono_ai.chrono_ai_routes import chrono_ai_bp
from categories.scoolish_mvp1.ai_quiz_creator.quiz_creator_routes import quiz_creator_bp
from categories.scoolish_mvp1.digital_debate.digital_debate_routes import digital_debate_bp
from categories.scoolish_mvp1.story_visualizer.story_routes import story_bp
from categories.scoolish_mvp1.summarizer.summarizer_routes import summarizer_bp
from categories.scoolish_mvp1.segmenter.segmenter_routes import segmenter_bp
from categories.scoolish_mvp1.topic_modeller.modeller_routes import modeller_bp
from categories.scoolish_mvp1.document_analyzer.document_analyzer_routes import document_analyzer_bp


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
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(chrono_ai_bp, url_prefix='/chrono_ai')
app.register_blueprint(quiz_creator_bp, url_prefix='/quiz_creator')
app.register_blueprint(digital_debate_bp, url_prefix='/digital_debate')
app.register_blueprint(story_bp, url_prefix='/story_visualizer')
app.register_blueprint(summarizer_bp, url_prefix='/summarizer')
app.register_blueprint(segmenter_bp, url_prefix='/segmenter')
app.register_blueprint(modeller_bp, url_prefix='/modeller')
app.register_blueprint(document_analyzer_bp, url_prefix='/document_analyzer')

@app.route('/')
def home():
    return os.getenv("AZURE_OPENAI_API_KEY")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
    