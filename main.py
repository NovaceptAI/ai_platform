from flask import Flask
from flask_cors import CORS
from chrono_ai.chrono_ai_routes import chrono_ai_bp
from ai_quiz_creator.quiz_creator_routes import quiz_creator_bp
from digital_debate.digital_debate_routes import digital_debate_bp
from story_visualizer.story_routes import story_bp
from summarizer.summarizer_routes import summarizer_bp
from segmenter.segmenter_routes import segmenter_bp
from topic_modeller.modeller_routes import modeller_bp
from document_analyzer.document_analyzer_routes import document_analyzer_bp

import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os
# Load environment variables from .env file
load_dotenv()

# Temporary check: print environment variables to verify
# print("AZURE_OPENAI_API_KEY:", os.getenv("AZURE_OPENAI_API_KEY"), flush=True)
# print("AZURE_OPENAI_API_BASE:", os.getenv("AZURE_OPENAI_API_BASE"))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
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


# Configure logging
if not app.debug:
    # Create a file handler object
    file_handler = RotatingFileHandler('/home/azureuser/ai_platform/logs/flask_error.log', maxBytes=10240, backupCount=10)
    file_handler.setLevel(logging.ERROR)
    
    # Create a logging format
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    file_handler.setFormatter(formatter)
    
    # Add the file handler to the app's logger
    app.logger.addHandler(file_handler)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)