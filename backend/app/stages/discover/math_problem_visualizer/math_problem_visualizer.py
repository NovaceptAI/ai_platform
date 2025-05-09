from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
import sympy as sp
import matplotlib.pyplot as plt
import io
import base64

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
math_visualizer_bp = Blueprint('math_visualizer', __name__)
UPLOAD_FOLDER = '/tmp'

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to save and encode plots
def save_plot_as_base64(fig):
    """Saves a Matplotlib figure as a base64-encoded string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    base64_image = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return f"data:image/png;base64,{base64_image}"

# Function to solve and visualize math problems
def solve_and_visualize_math_problem(problem):
    """Parses, solves, and visualizes a math problem."""
    try:
        # Parse the problem
        expr = sp.sympify(problem)
        solution = sp.solve(expr)

        # Generate visualization
        fig, ax = plt.subplots()
        sp.plot(expr, show=False, ax=ax)
        ax.set_title(f"Visualization of: {problem}")
        ax.grid(True)

        # Save the plot as a base64 string
        visualization = save_plot_as_base64(fig)
        plt.close(fig)

        # Return the solution and visualization
        return {
            "solution": [str(s) for s in solution],
            "visualization": visualization
        }
    except Exception as e:
        logger.error(f"Error solving or visualizing math problem: {str(e)}")
        raise ValueError("Invalid math problem or unsupported format.")

# Route for visualizing math problems
@math_visualizer_bp.route('/visualize_math_problem', methods=['POST'])
def visualize_math_problem():
    try:
        if 'application/json' in request.content_type:
            # Handle text-based input
            data = request.get_json()
            problem = data.get('problem')
            if not problem:
                return jsonify({"error": "Math problem is required"}), 400

            # Solve and visualize the problem
            result = solve_and_visualize_math_problem(problem)
            return jsonify(result)

        elif 'multipart/form-data' in request.content_type:
            # Handle image-based input (future implementation)
            return jsonify({"error": "Image-based input is not yet supported"}), 501

        else:
            return jsonify({"error": "Unsupported Content-Type"}), 415

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error visualizing math problem: {str(e)}")
        return jsonify({"error": str(e)}), 500