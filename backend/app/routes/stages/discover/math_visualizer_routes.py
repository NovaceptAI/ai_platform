# app/routes/math_visualizer_routes.py
from __future__ import annotations

import traceback
from flask import Blueprint, request, jsonify
from celery.result import AsyncResult

from app.services.stages.discover.math_visualizer_service import MathVisualizerService, MathVisualizerInput
from app.tasks.math_visualizer_tasks import math_visualizer_solve_task

math_visualizer_bp = Blueprint("math_visualizer", __name__, url_prefix="/math_visualizer")


@math_visualizer_bp.route("/solve", methods=["POST"])
def solve_math_problem():
    """
    Accepts:
      JSON:
        {
          "method": "text",
          "text": "Solve 2x+3=11",
          "difficulty": "beginner|intermediate|advanced",
          "level": "school|college|olympiad",
          "show_hints": true,
          "practice_count": 3,
          "visualize_types": ["graph","number_line","geometry","flowchart"]
        }

      Multipart form-data:
        method=document
        file=<file>
        difficulty=...
        level=...
        show_hints=true|false
        practice_count=...
        visualize_types=comma,separated

    Query:
      ?async=true -> enqueue Celery (only for method=text in this baseline)
    """
    try:
        use_async = str(request.args.get("async", "false")).lower() == "true"
        svc = MathVisualizerService()

        # JSON flow
        if request.content_type and "application/json" in request.content_type:
            data = request.get_json(silent=True) or {}
            method = (data.get("method") or "text").strip().lower()

            # Async only for text mode by default
            if use_async and method == "text":
                task = math_visualizer_solve_task.delay({
                    "method": "text",
                    "text": data.get("text"),
                    "difficulty": data.get("difficulty"),
                    "level": data.get("level"),
                    "show_hints": data.get("show_hints", True),
                    "practice_count": data.get("practice_count", 3),
                    "visualize_types": data.get("visualize_types"),
                })
                return jsonify({"task_id": task.id}), 202

            # Sync path
            mvi = MathVisualizerInput(
                method=method,
                text=data.get("text"),
                difficulty=data.get("difficulty"),
                level=data.get("level"),
                show_hints=bool(data.get("show_hints", True)),
                practice_count=int(data.get("practice_count", 3)),
                visualize_types=data.get("visualize_types"),
            )
            result = svc.solve(mvi)
            return jsonify(result), 200

        # Multipart (document)
        if request.content_type and "multipart/form-data" in request.content_type:
            method = (request.form.get("method") or "document").strip().lower()
            file = request.files.get("file")

            visualize_types = request.form.get("visualize_types")
            if visualize_types:
                visualize_types = [v.strip() for v in visualize_types.split(",") if v.strip()]
            else:
                visualize_types = None

            mvi = MathVisualizerInput(
                method=method,
                file_storage=file,
                filename=file.filename if file else None,
                difficulty=request.form.get("difficulty"),
                level=request.form.get("level"),
                show_hints=str(request.form.get("show_hints", "true")).lower() == "true",
                practice_count=int(request.form.get("practice_count", 3)),
                visualize_types=visualize_types,
            )
            result = svc.solve(mvi)
            return jsonify(result), 200

        return jsonify({"error": "Unsupported content type. Send JSON or multipart/form-data."}), 400

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Failed to solve the math problem."}), 500


@math_visualizer_bp.route("/status/<task_id>", methods=["GET"])
def math_visualizer_status(task_id: str):
    res = AsyncResult(task_id)
    if not res:
        return jsonify({"error": "Task not found"}), 404
    if res.successful():
        return jsonify({"status": "SUCCESS", "result": res.result}), 200
    if res.failed():
        return jsonify({"status": "FAILURE", "error": str(res.result)}), 200
    return jsonify({"status": res.status}), 200