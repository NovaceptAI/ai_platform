"""
Learn by Drawing Celery Tasks

Async tasks for analyzing student drawings.
"""

import logging
import base64
from celery import current_app
from app.db import db
from app.models.learning_drawings import LearningDrawing
from app.services.stages.create.learn_by_drawing_service import LearnByDrawingService
from app.services.learning_drawing_storage_service import upload_drawing_to_azure

logger = logging.getLogger(__name__)


@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_drawing_task(self, user_id: str, progress_id: str, options: dict):
    """
    Analyze a student drawing with AI.

    Args:
        user_id: User ID
        progress_id: Progress tracking ID
        options: {
            'image_data': base64 encoded PNG,
            'topic': 'water_cycle',
            'age_group': '8-10',
            'title': 'My Water Cycle Drawing',
            'canvas_width': 800,
            'canvas_height': 600
        }
    """

    # Initialize service
    drawing_service = LearnByDrawingService()

    try:
        # Update progress: Starting
        self.update_state(
            task_id=self.request.id,
            state='PROGRESS',
            meta={'progress': 10, 'status': 'Preparing drawing...', 'progress_id': progress_id}
        )

        # Extract options
        image_data = options.get('image_data')
        topic = options.get('topic', 'water_cycle')
        age_group = options.get('age_group', '8-10')
        title = options.get('title', 'My Drawing')
        canvas_width = options.get('canvas_width', 800)
        canvas_height = options.get('canvas_height', 600)

        # Decode base64 image
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)

        logger.info(f"[DrawingTask] Starting analysis for user {user_id}, topic: {topic}")

        # Create database record (draft)
        drawing = LearningDrawing(
            user_id=user_id,
            title=title,
            topic=topic,
            age_group=age_group,
            drawing_image_url='',  # Will be filled after upload
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            completion_status='analyzing'
        )
        db.session.add(drawing)
        db.session.commit()

        drawing_id = str(drawing.id)

        # Update progress: Uploading
        self.update_state(
            task_id=self.request.id,
            state='PROGRESS',
            meta={'progress': 20, 'status': 'Uploading drawing...', 'progress_id': progress_id}
        )

        # Upload to Azure
        drawing_url = upload_drawing_to_azure(user_id, drawing_id, image_bytes)
        drawing.drawing_image_url = drawing_url
        db.session.commit()

        # Update progress: Analyzing with Azure CV
        self.update_state(
            task_id=self.request.id,
            state='PROGRESS',
            meta={'progress': 40, 'status': 'Detecting objects...', 'progress_id': progress_id}
        )

        # Analyze with AI
        analysis_result = drawing_service.analyze_drawing(
            image_bytes=image_bytes,
            topic=topic,
            age_group=age_group
        )

        # Update progress: Generating feedback
        self.update_state(
            task_id=self.request.id,
            state='PROGRESS',
            meta={'progress': 80, 'status': 'Generating educational feedback...', 'progress_id': progress_id}
        )

        # Update drawing with results
        drawing.detected_objects = analysis_result.get('detected_objects', [])
        drawing.recognized_concepts = analysis_result.get('recognized_concepts', [])
        drawing.topic_match = analysis_result.get('topic_match')
        drawing.confidence_score = analysis_result.get('confidence_score', 0.0)
        drawing.feedback_text = analysis_result.get('feedback_text', '')
        drawing.accuracy_score = analysis_result.get('accuracy_score', 0)
        drawing.suggestions = analysis_result.get('suggestions', [])
        drawing.fun_fact = analysis_result.get('fun_fact', '')
        drawing.azure_cv_tags = analysis_result.get('azure_cv_tags', [])
        drawing.azure_cv_description = analysis_result.get('azure_cv_description', '')
        drawing.azure_cv_confidence = analysis_result.get('azure_cv_confidence', 0.0)
        drawing.completion_status = 'analyzed'

        # Check for badges
        total_drawings = LearningDrawing.get_user_drawings_count(user_id)
        topics_summary = LearningDrawing.get_user_topics_summary(user_id)
        badges = drawing_service.check_badges(
            drawing_count=total_drawings,
            topic=topic,
            accuracy_score=drawing.accuracy_score,
            user_topics_summary=topics_summary
        )
        drawing.badges_earned = badges

        db.session.commit()

        logger.info(f"[DrawingTask] Analysis complete for drawing {drawing_id}, score: {drawing.accuracy_score}/10")

        # Return result
        return {
            'drawing': drawing.to_dict(),
            'badges': badges,
            'progress_id': progress_id
        }

    except Exception as e:
        logger.error(f"[DrawingTask] Error: {str(e)}")

        # Update drawing status to error if it exists
        if 'drawing' in locals():
            drawing.completion_status = 'error'
            db.session.commit()

        # Retry on failure
        try:
            self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            return {
                'error': str(e),
                'progress_id': progress_id
            }


@current_app.task
def cleanup_old_drawings_task(days_old: int = 90):
    """
    Cleanup old drawings from database and Azure storage.

    Args:
        days_old: Delete drawings older than this many days
    """
    from datetime import datetime, timedelta
    from app.services.learning_drawing_storage_service import delete_drawing_from_azure

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        old_drawings = LearningDrawing.query.filter(
            LearningDrawing.created_at < cutoff_date
        ).all()

        logger.info(f"[Cleanup] Found {len(old_drawings)} drawings older than {days_old} days")

        deleted_count = 0
        for drawing in old_drawings:
            try:
                # Delete from Azure
                delete_drawing_from_azure(drawing.drawing_image_url)

                # Delete from database
                db.session.delete(drawing)
                deleted_count += 1

            except Exception as e:
                logger.error(f"[Cleanup] Error deleting drawing {drawing.id}: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"[Cleanup] Deleted {deleted_count} old drawings")

        return {'deleted_count': deleted_count}

    except Exception as e:
        logger.error(f"[Cleanup] Error: {str(e)}")
        return {'error': str(e)}
