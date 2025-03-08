from flask import Flask
from chrono_ai.chrono_ai_routes import chrono_ai_bp
from ai_quiz_creator.quiz_creator_routes import quiz_creator_bp
from digital_debate.digital_debate_routes import digital_debate_bp

app = Flask(__name__)
app.register_blueprint(chrono_ai_bp, url_prefix='/chrono_ai')
app.register_blueprint(quiz_creator_bp, url_prefix='/quiz_creator')
app.register_blueprint(digital_debate_bp, url_prefix='/digital_debate')

@app.route('/')
def home():
    return "Welcome to the Flask app!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)