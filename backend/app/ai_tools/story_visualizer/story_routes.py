from flask import Blueprint, request, jsonify
from .story_visualizer import create_story_visualization    #, how_it_works

story_bp = Blueprint('story_visualizer', __name__)

@story_bp.route('/create_story_visualization', methods=['POST'])
def create_story_visualization_route():
    data = request.get_json()
    content = data.get('content', '')
    if not content:
        return jsonify({"error": "No content provided"}), 400

    visualization = create_story_visualization(content)
    return jsonify(visualization)

def how_it_works():
    """
    Returns a list of steps explaining how the story visualizer works.
    """
    return [
        "Write your story in the provided text box.",
        "Submit your story to the Story Visualizer.",
        "The system analyzes your story and generates relevant images for key scenes.",
        "View and download the visualized story with images.",
        "This tool helps you turn your written story into a visual experience using AI-generated images."
    ]

@story_bp.route('/how_it_works', methods=['GET'])
def how_it_works_route():
    steps = how_it_works()
    return jsonify({"steps": steps})