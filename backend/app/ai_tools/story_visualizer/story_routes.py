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

# @story_bp.route('/how_it_works', methods=['GET'])
# def how_it_works_route():
#     steps = how_it_works()
#     return jsonify({"steps": steps})