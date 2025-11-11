# app/celery_worker.py
from app.main import create_app
from app import make_celery

# Build Flask app, then Celery bound to its context
flask_app, socketio_app = create_app()
celery_app = make_celery(flask_app)

# Celery CLI target
app = celery_app

# Import task modules AFTER celery_app exists so @shared_task decorators register
import app.tasks.summarizer_tasks              # noqa: F401
import app.tasks.segmenter_tasks               # noqa: F401
import app.tasks.timeline_explorer_tasks       # noqa: F401
import app.tasks.topic_modeller_tasks          # noqa: F401
import app.tasks.quiz_creator_tasks            # noqa: F401
import app.tasks.creative_prompts_tasks        # noqa: F401
import app.tasks.sentiment_tasks               # noqa: F401
import app.tasks.math_visualizer_tasks         # noqa: F401
import app.tasks.visual_guide_tasks            # noqa: F401
import app.tasks.doc_analysis_tasks            # noqa: F401
import app.tasks.chrono_tasks                  # noqa: F401
import app.tasks.web_scraper_tasks             # noqa: F401
import app.tasks.three_d_model_builder_task    # noqa: F401
import app.tasks.story_to_comics_converter_tasks # noqa: F401
import app.tasks.interactive_comic_strip_builder_task # noqa: F401
import app.tasks.ai_presentation_builder_tasks  # noqa: F401
import app.tasks.ai_art_creator_for_kids_task  # noqa: F401
import app.tasks.data_story_builder_task       # noqa: F401
import app.tasks.learn_by_drawing_tasks        # noqa: F401
import app.tasks.timeline_builder_tasks        # noqa: F401
import app.tasks.learning_paths_stage_tasks    # noqa: F401
import app.tasks.learning_paths_tasks          # noqa: F401
import app.tasks.clustering_tasks              # noqa: F401
