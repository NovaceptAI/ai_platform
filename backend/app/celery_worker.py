# app/celery_worker.py
from app.main import celery_app  # Uses the already-initialized celery from Flask context
app = celery_app  # Optional: for CLI command

# Ensure task modules are imported so Celery registers them
import app.tasks.summarizer_tasks  # noqa: F401
import app.tasks.segmenter_tasks  # noqa: F401
import app.tasks.timeline_explorer_tasks  # noqa: F401
import app.tasks.topic_modeller_tasks  # noqa: F401
import app.tasks.quiz_creator_tasks  # noqa: F401
import app.tasks.creative_prompts_tasks  # noqa: F401
import app.tasks.sentiment_tasks  # noqa: F401
import app.tasks.math_visualizer_tasks  # noqa: F401
import app.tasks.visual_guide_tasks  # noqa: F401
import app.tasks.doc_analysis_tasks  # noqa: F401
import app.tasks.chrono_tasks  # noqa: F401
import app.tasks.web_scraper_tasks  # noqa: F401