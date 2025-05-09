from flask import Blueprint, request, jsonify
from .math_problem_visualizer import solve_and_visualize_math_problem
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
math_problem_visualiser_bp = Blueprint('math_problem_visualiser', __name__)

# Route for visualizing math problems
@math_problem_visualiser_bp.route('/visualize_math_problem', methods=['POST'])
def visualize_math_problem():
    """
    Handles requests from the frontend to visualize math problems.
    Accepts JSON input with a math problem and returns the solution and visualization.
    """
    try:
        # Check if the request is JSON
        if 'application/json' in request.content_type:
            data = request.get_json()

            # Extract the math problem from the request
            problem = data.get('problem')
            if not problem:
                return jsonify({"error": "Math problem is required"}), 400

            # Solve and visualize the math problem
            logger.info(f"Received math problem: {problem}")
            result = solve_and_visualize_math_problem(problem)

            # Return the solution and visualization to the frontend
            return jsonify({
                "solution": result["solution"],
                "visualization": result["visualization"]
            }), 200

        else:
            return jsonify({"error": "Unsupported Content-Type. Please send JSON data."}), 415

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error visualizing math problem: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500