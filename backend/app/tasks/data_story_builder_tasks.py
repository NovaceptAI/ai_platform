# app/tasks/data_story_builder_tasks.py
"""
Data Story Builder Celery Tasks

Background tasks for generating data stories:
- Stage 1: Profile dataset + Generate AI insights
- Stage 2: Generate visualizations + Export PDF/HTML
"""

import logging
import uuid
from datetime import datetime
from io import BytesIO
import pandas as pd
from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.db import db
from app.models.status import Progress
from app.models.data_stories import DataStoryCreation
from app.models.files import UploadedFile
from app.services.stages.create.data_story_builder_service import DataStoryBuilderService
from app.services.data_story_storage_service import DataStoryStorageService

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="data_story_builder.stage_1")
def generate_data_story_stage_1(self, progress_id, user_id, file_id, title):
    """
    Stage 1: Profile dataset and generate AI insights.

    Args:
        progress_id: Progress tracking ID
        user_id: User's ID
        file_id: Uploaded file ID (CSV/Excel)
        title: Story title

    Returns:
        dict: Result data with data_story_id
    """
    logger.info(f"[Stage 1] Starting data story generation for user {user_id}, file {file_id}")

    progress = None

    try:
        # Get progress record
        progress = Progress.query.get(progress_id)
        if not progress:
            logger.error(f"Progress record not found: {progress_id}")
            return {"status": "failed", "error": "Progress record not found"}

        # Update progress
        progress.status = "in_progress"
        progress.percentage = 10
        db.session.commit()
        logger.info(f"[Stage 1] Progress updated: 10%")

        # Get uploaded file
        uploaded_file = UploadedFile.query.get(file_id)
        if not uploaded_file:
            raise ValueError(f"File not found: {file_id}")

        # Check file type
        filename = uploaded_file.original_file_name.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            raise ValueError("Only CSV and Excel files are supported")

        logger.info(f"[Stage 1] Loading file: {uploaded_file.original_file_name}")

        # Download file from Azure
        file_bytes = _download_file_from_azure(uploaded_file.file_path)

        # Load into pandas
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(file_bytes))
        else:
            df = pd.read_excel(BytesIO(file_bytes))

        logger.info(f"[Stage 1] Loaded dataset: {len(df)} rows, {len(df.columns)} columns")

        # Update progress
        progress.percentage = 20
        db.session.commit()

        # Initialize services
        data_service = DataStoryBuilderService()
        storage_service = DataStoryStorageService()

        # Profile dataset
        logger.info(f"[Stage 1] Profiling dataset...")
        data_profile = data_service.profile_dataset(df, uploaded_file.original_file_name)

        # Update progress
        progress.percentage = 40
        db.session.commit()

        # Generate AI insights
        logger.info(f"[Stage 1] Generating AI insights...")
        insights_data = data_service.generate_insights(df, data_profile)

        # Update progress
        progress.percentage = 70
        db.session.commit()

        # Create DataStoryCreation record
        story_id = uuid.uuid4()
        azure_folder_path = storage_service.get_folder_path(user_id, str(story_id))

        data_story = DataStoryCreation(
            id=story_id,
            user_id=user_id,
            title=title,
            dataset_name=uploaded_file.original_file_name,
            source_type='vault',
            source_file_id=file_id,
            current_stage=1,
            azure_folder_path=azure_folder_path,
            data_profile=data_profile,
            insights_data=insights_data,
            story_metadata={
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "processing_time": "N/A",
                "ai_model_used": "gpt-4",
                "stage_1_completed_at": datetime.utcnow().isoformat()
            }
        )

        db.session.add(data_story)
        db.session.commit()

        logger.info(f"[Stage 1] Created data story record: {story_id}")

        # Upload data file to Azure for reference
        logger.info(f"[Stage 1] Uploading data file to Azure...")
        storage_service.upload_data_file(user_id, str(story_id), file_bytes, uploaded_file.original_file_name)

        # Generate thumbnail (first suggested chart if available)
        thumbnail_url = None
        if data_profile.get('suggested_charts'):
            try:
                first_chart = data_profile['suggested_charts'][0]
                chart_bytes = data_service.generate_chart(df, first_chart)
                thumbnail_url = storage_service.upload_thumbnail(user_id, str(story_id), chart_bytes.read())
                data_story.thumbnail_url = thumbnail_url
                db.session.commit()
                logger.info(f"[Stage 1] Generated thumbnail")
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail: {str(e)}")

        # Complete progress
        progress.status = "completed"
        progress.percentage = 100
        progress.result_data = {
            "data_story_id": str(story_id),
            "stage": 1,
            "insights_count": len(insights_data.get('key_insights', [])),
            "suggested_charts_count": len(data_profile.get('suggested_charts', []))
        }
        progress.completed_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"[Stage 1] Completed successfully: {story_id}")

        return {
            "status": "completed",
            "data_story_id": str(story_id)
        }

    except Exception as e:
        logger.error(f"[Stage 1] Error: {str(e)}", exc_info=True)

        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            try:
                db.session.commit()
            except SQLAlchemyError as db_error:
                logger.error(f"Failed to update progress: {str(db_error)}")
                db.session.rollback()

        return {
            "status": "failed",
            "error": str(e)
        }


@shared_task(bind=True, name="data_story_builder.stage_2")
def generate_data_story_stage_2(self, progress_id, user_id, data_story_id, selected_charts):
    """
    Stage 2: Generate visualizations and export PDF/HTML.

    Args:
        progress_id: Progress tracking ID
        user_id: User's ID
        data_story_id: DataStoryCreation ID
        selected_charts: List of chart configurations to generate

    Returns:
        dict: Result data with export URLs
    """
    logger.info(f"[Stage 2] Starting visualization generation for story {data_story_id}")

    progress = None

    try:
        # Get progress record
        progress = Progress.query.get(progress_id)
        if not progress:
            logger.error(f"Progress record not found: {progress_id}")
            return {"status": "failed", "error": "Progress record not found"}

        # Update progress
        progress.status = "in_progress"
        progress.percentage = 10
        db.session.commit()

        # Get data story
        data_story = DataStoryCreation.query.get(data_story_id)
        if not data_story:
            raise ValueError(f"Data story not found: {data_story_id}")

        if data_story.user_id != user_id:
            raise ValueError("Unauthorized access to data story")

        # Get original file
        if not data_story.source_file_id:
            raise ValueError("Source file not found")

        uploaded_file = UploadedFile.query.get(data_story.source_file_id)
        if not uploaded_file:
            raise ValueError("Source file no longer exists")

        # Load data
        logger.info(f"[Stage 2] Loading dataset...")
        file_bytes = _download_file_from_azure(uploaded_file.file_path)
        
        filename = uploaded_file.original_file_name.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(file_bytes))
        else:
            df = pd.read_excel(BytesIO(file_bytes))

        # Update progress
        progress.percentage = 20
        db.session.commit()

        # Initialize services
        data_service = DataStoryBuilderService()
        storage_service = DataStoryStorageService()

        # Generate charts
        visualizations = []
        total_charts = len(selected_charts)

        for idx, chart_config in enumerate(selected_charts):
            logger.info(f"[Stage 2] Generating chart {idx + 1}/{total_charts}: {chart_config.get('title')}")

            try:
                # Generate chart
                chart_bytes = data_service.generate_chart(df, chart_config)

                # Upload to Azure
                chart_id = f"chart_{idx + 1}"
                chart_url = storage_service.upload_chart(
                    user_id, 
                    data_story_id, 
                    chart_id, 
                    chart_bytes.read()
                )

                # Add to visualizations
                visualizations.append({
                    "id": chart_id,
                    "chart_type": chart_config['chart_type'],
                    "title": chart_config.get('title', 'Chart'),
                    "chart_url": chart_url,
                    "chart_config": chart_config
                })

                # Update progress
                progress_percent = 20 + int((idx + 1) / total_charts * 50)
                progress.percentage = progress_percent
                db.session.commit()

            except Exception as e:
                logger.error(f"Failed to generate chart {idx + 1}: {str(e)}")
                # Continue with other charts

        # Update data story with visualizations
        data_story.visualizations = visualizations
        data_story.current_stage = 2
        db.session.commit()

        logger.info(f"[Stage 2] Generated {len(visualizations)} charts")

        # Update progress
        progress.percentage = 80
        db.session.commit()

        # TODO: Generate PDF export (optional for MVP)
        # pdf_bytes = _generate_pdf(data_story, df)
        # pdf_url = storage_service.upload_pdf(user_id, data_story_id, pdf_bytes)
        # data_story.pdf_url = pdf_url

        # TODO: Generate HTML export (optional for MVP)
        # html_content = _generate_html(data_story)
        # html_url = storage_service.upload_html(user_id, data_story_id, html_content)
        # data_story.html_url = html_url

        # Mark as completed
        data_story.completed_at = datetime.utcnow()
        data_story.story_metadata['charts_generated'] = len(visualizations)
        data_story.story_metadata['stage_2_completed_at'] = datetime.utcnow().isoformat()
        db.session.commit()

        # Complete progress
        progress.status = "completed"
        progress.percentage = 100
        progress.result_data = {
            "data_story_id": data_story_id,
            "stage": 2,
            "charts_generated": len(visualizations),
            "pdf_url": data_story.pdf_url,
            "html_url": data_story.html_url
        }
        progress.completed_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"[Stage 2] Completed successfully: {data_story_id}")

        return {
            "status": "completed",
            "data_story_id": data_story_id,
            "charts_generated": len(visualizations)
        }

    except Exception as e:
        logger.error(f"[Stage 2] Error: {str(e)}", exc_info=True)

        if progress:
            progress.status = "failed"
            progress.error_message = str(e)
            try:
                db.session.commit()
            except SQLAlchemyError as db_error:
                logger.error(f"Failed to update progress: {str(db_error)}")
                db.session.rollback()

        return {
            "status": "failed",
            "error": str(e)
        }


def _download_file_from_azure(blob_path):
    """
    Download file from Azure Blob Storage.
    
    TODO: Implement based on your storage setup.
    This is a placeholder that should integrate with your existing file storage.
    """
    # Placeholder implementation
    from app.services.data_story_storage_service import DataStoryStorageService
    storage = DataStoryStorageService()
    
    blob_client = storage.container_client.get_blob_client(blob_path)
    return blob_client.download_blob().readall()
