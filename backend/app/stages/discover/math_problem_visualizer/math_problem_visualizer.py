from flask import Blueprint, request, jsonify
import os
import logging
import sympy as sp
import numpy as np
# from sympy.plotting import plot
import matplotlib.pyplot as plt
import io
import base64
import openai

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
math_visualizer_bp = Blueprint('math_visualizer', __name__)
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Utility to save matplotlib figure to base64 string
def save_plot_as_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    base64_img = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{base64_img}"

# Function to parse, solve and visualize
def solve_and_visualize_math_problem(problem):
    try:
        steps = []
        # Detect and parse equations
        if '=' in problem:
            lhs, rhs = problem.split('=')
            lhs_expr = sp.sympify(lhs.strip())
            rhs_expr = sp.sympify(rhs.strip())
            equation = sp.Eq(lhs_expr, rhs_expr)
            steps.append(f"Parsed equation: {sp.pretty(equation)}")
        else:
            lhs_expr = sp.sympify(problem)
            rhs_expr = None
            equation = lhs_expr
            steps.append(f"Parsed expression: {sp.pretty(equation)}")

        # Solve the equation
        symbol_list = equation.free_symbols
        if not symbol_list:
            raise ValueError("No variables found in the expression.")
        variable = list(symbol_list)[0]
        solution = sp.solve(equation, variable)
        steps.append(f"Detected variable: {variable}")

        # Plot only if univariate
        visualization = None
        if len(symbol_list) == 1:
            try:
                x_vals = np.linspace(-10, 10, 400)
                f_lhs = sp.lambdify(variable, lhs_expr, modules=["numpy"])

                if rhs_expr:
                    f_rhs = sp.lambdify(variable, rhs_expr, modules=["numpy"])
                    y_vals = f_lhs(x_vals) - f_rhs(x_vals)
                    label = f'{lhs.strip()} - ({rhs.strip()})'
                else:
                    y_vals = f_lhs(x_vals)
                    label = f'{lhs_expr}'

                fig, ax = plt.subplots()
                ax.plot(x_vals, y_vals, label=label)
                ax.axhline(0, color='gray', linewidth=0.5)
                ax.axvline(0, color='gray', linewidth=0.5)
                ax.set_title(f"Plot of: {problem}")
                ax.set_xlabel(str(variable))
                ax.set_ylabel("y")
                ax.legend()

                visualization = save_plot_as_base64(fig)
                plt.close(fig)

            except Exception as plot_err:
                logger.warning(f"Plotting failed: {plot_err}")
                visualization = None

        gpt_steps = get_solution_steps_with_gpt(problem)

        return {
            "solution": [str(s) for s in solution],
            "steps": gpt_steps,
            "visualization": visualization or "Plot not available"
        }

    except Exception as e:
        logger.error(f"Error solving or visualizing math problem: {str(e)}")
        raise ValueError("Invalid math problem or unsupported format.")
    

def get_solution_steps_with_gpt(problem):
    """Use GPT to generate human-readable steps for solving the problem."""
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4o",
            messages=[
                        {
                            "role": "system",
                            "content": "You are a math tutor. Respond only with numbered step-by-step instructions to solve the given equation. Do not include introductions, summaries, or extra text. Just output the steps."
                        },
                        {
                            "role": "user",
                            "content": f"Solve the equation step-by-step: {problem}"
                        }
                    ],
            max_tokens=500,
            temperature=0.3,
            timeout=10  # seconds
        )
        content = response["choices"][0]["message"]["content"].strip()
        return content.split("\n")
    except Exception as e:
        logger.warning(f"GPT step generation failed: {e}")
        return ["(GPT explanation unavailable. Try again.)"]
