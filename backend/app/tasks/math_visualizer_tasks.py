# app/tasks/math_visualizer_task.py
from __future__ import annotations

from celery import shared_task
from app.services.stages.discover.math_visualizer_service import MathVisualizerService, MathVisualizerInput


@shared_task(name="math_visualizer.solve", bind=True, max_retries=2)
def math_visualizer_solve_task(self, payload: dict) -> dict:
    """
    Async solver for text-based problems (and document if you later pass a blob key).
    For file uploads in this baseline, we keep sync in the route (like your other tools).
    """
    try:
        mvs = MathVisualizerService()
        mvi = MathVisualizerInput(
            method=payload.get("method", "text"),
            text=payload.get("text"),
            file_storage=None,  # if you later add blob download, inject a FileStorage-like object
            filename=None,
            difficulty=payload.get("difficulty"),
            level=payload.get("level"),
            show_hints=bool(payload.get("show_hints", True)),
            practice_count=int(payload.get("practice_count", 3)),
            visualize_types=payload.get("visualize_types") or ["graph", "number_line", "geometry"],
        )
        return mvs.solve(mvi)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)