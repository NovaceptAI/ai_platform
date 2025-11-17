"""
Timeline Builder Celery Tasks

Handles async processing for timeline generation, document parsing,
and timeline enhancement.
"""

import os
import logging
import tempfile
from celery import shared_task
from app.db import db
from app.models.historical_timelines import HistoricalTimeline
from app.services.stages.knowledge_data.timeline_builder_service import TimelineBuilderService
from app.services.timeline_storage_service import (
    upload_timeline_document,
    export_timeline_json
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='timeline_builder.generate_from_text')
def generate_timeline_from_text_task(
    self,
    user_id: str,
    timeline_id: str,
    input_text: str,
    category: str = None,
    time_period: str = None,
    enhance: bool = True
):
    """
    Generate timeline from text input (async).

    Args:
        user_id: User ID
        timeline_id: Timeline ID
        input_text: Text to analyze
        category: Optional category
        time_period: Optional time period
        enhance: Whether to enhance with research
    """
    try:
        logger.info(f"[TimelineTask] Starting timeline generation from text for {timeline_id}")

        # Initialize service
        service = TimelineBuilderService()

        # Get timeline from database
        timeline = HistoricalTimeline.query.filter_by(
            id=timeline_id,
            user_id=user_id
        ).first()

        if not timeline:
            logger.error(f"[TimelineTask] Timeline {timeline_id} not found")
            return {'success': False, 'error': 'Timeline not found'}

        # Extract timeline from text
        extraction_result = service.extract_timeline_from_text(input_text, category, time_period)

        if not extraction_result.get('success'):
            logger.error(f"[TimelineTask] Extraction failed: {extraction_result.get('error')}")
            return extraction_result

        timeline_data = extraction_result['timeline_data']

        # STAGE 1: Basic extraction only (enhancement disabled for now)
        # TODO: Add Stage 2 enhancement in separate endpoint/task
        # if enhance:
        #     logger.info("[TimelineTask] Enhancing timeline with research")
        #     enhancement_result = service.enhance_timeline_with_research(timeline_data)
        #     if enhancement_result.get('success'):
        #         timeline_data = enhancement_result['timeline_data']

        # STAGE 1: Skip relationship analysis for now (causes parsing errors)
        # TODO: Add relationship analysis in Stage 2
        # logger.info("[TimelineTask] Analyzing event relationships")
        # timeline_data['events'] = service.analyze_timeline_relationships(timeline_data.get('events', []))

        # Validate data
        validation_result = service.validate_timeline_data(timeline_data)
        if validation_result.get('success'):
            timeline_data = validation_result['timeline_data']

        # Generate visualization config
        viz_config = service.generate_timeline_visualization_config(timeline_data)

        # Update timeline in database
        timeline.title = timeline_data.get('title', 'Untitled Timeline')
        timeline.description = timeline_data.get('description')
        timeline.time_period = timeline_data.get('time_period')
        timeline.events = timeline_data.get('events', [])
        timeline.total_events = len(timeline_data.get('events', []))
        timeline.date_range_start = timeline_data.get('date_range_start')
        timeline.date_range_end = timeline_data.get('date_range_end')
        timeline.key_themes = timeline_data.get('key_themes', [])
        timeline.key_figures = timeline_data.get('key_figures', [])
        timeline.visualization_type = viz_config.get('visualization_type', 'linear')
        timeline.color_scheme = viz_config.get('color_scheme', 'default')
        timeline.display_options = viz_config.get('display_options', {})
        timeline.ai_model_used = extraction_result.get('model_used', 'gpt-4-turbo-preview')
        timeline.confidence_score = timeline_data.get('confidence_score', 0)

        db.session.commit()

        logger.info(f"[TimelineTask] Timeline {timeline_id} generated successfully with {timeline.total_events} events")

        return {
            'success': True,
            'timeline_id': timeline_id,
            'total_events': timeline.total_events,
            'timeline_data': timeline.to_dict()
        }

    except Exception as e:
        logger.error(f"[TimelineTask] Error generating timeline: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(bind=True, name='timeline_builder.generate_from_document')
def generate_timeline_from_document_task(
    self,
    user_id: str,
    timeline_id: str,
    document_bytes: bytes,
    filename: str,
    category: str = None,
    time_period: str = None,
    enhance: bool = True
):
    """
    Generate timeline from document (async).

    Args:
        user_id: User ID
        timeline_id: Timeline ID
        document_bytes: Document bytes
        filename: Original filename
        category: Optional category
        time_period: Optional time period
        enhance: Whether to enhance with research
    """
    try:
        logger.info(f"[TimelineTask] Starting timeline generation from document for {timeline_id}")

        # Initialize service
        service = TimelineBuilderService()

        # Get timeline from database
        timeline = HistoricalTimeline.query.filter_by(
            id=timeline_id,
            user_id=user_id
        ).first()

        if not timeline:
            logger.error(f"[TimelineTask] Timeline {timeline_id} not found")
            return {'success': False, 'error': 'Timeline not found'}

        # Save document to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(document_bytes)
            temp_path = temp_file.name

        try:
            # Upload document to Azure
            logger.info("[TimelineTask] Uploading document to Azure")
            document_url = upload_timeline_document(user_id, timeline_id, document_bytes, filename)
            timeline.document_url = document_url

            # Extract timeline from document
            extraction_result = service.extract_timeline_from_document(temp_path, category, time_period)

            if not extraction_result.get('success'):
                logger.error(f"[TimelineTask] Extraction failed: {extraction_result.get('error')}")
                return extraction_result

            timeline_data = extraction_result['timeline_data']

            # STAGE 1: Basic extraction only (enhancement disabled for now)
            # TODO: Add Stage 2 enhancement in separate endpoint/task
            # if enhance:
            #     logger.info("[TimelineTask] Enhancing timeline with research")
            #     enhancement_result = service.enhance_timeline_with_research(timeline_data)
            #     if enhancement_result.get('success'):
            #         timeline_data = enhancement_result['timeline_data']

            # STAGE 1: Skip relationship analysis for now (causes parsing errors)
            # TODO: Add relationship analysis in Stage 2
            # logger.info("[TimelineTask] Analyzing event relationships")
            # timeline_data['events'] = service.analyze_timeline_relationships(timeline_data.get('events', []))

            # Validate data
            validation_result = service.validate_timeline_data(timeline_data)
            if validation_result.get('success'):
                timeline_data = validation_result['timeline_data']

            # Generate visualization config
            viz_config = service.generate_timeline_visualization_config(timeline_data)

            # Update timeline in database
            timeline.title = timeline_data.get('title', 'Untitled Timeline')
            timeline.description = timeline_data.get('description')
            timeline.time_period = timeline_data.get('time_period')
            timeline.events = timeline_data.get('events', [])
            timeline.total_events = len(timeline_data.get('events', []))
            timeline.date_range_start = timeline_data.get('date_range_start')
            timeline.date_range_end = timeline_data.get('date_range_end')
            timeline.key_themes = timeline_data.get('key_themes', [])
            timeline.key_figures = timeline_data.get('key_figures', [])
            timeline.visualization_type = viz_config.get('visualization_type', 'linear')
            timeline.color_scheme = viz_config.get('color_scheme', 'default')
            timeline.display_options = viz_config.get('display_options', {})
            timeline.ai_model_used = extraction_result.get('model_used', 'gpt-4-turbo-preview')
            timeline.confidence_score = timeline_data.get('confidence_score', 0)

            db.session.commit()

            logger.info(f"[TimelineTask] Timeline {timeline_id} generated successfully with {timeline.total_events} events")

            return {
                'success': True,
                'timeline_id': timeline_id,
                'total_events': timeline.total_events,
                'document_url': document_url,
                'timeline_data': timeline.to_dict()
            }

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        logger.error(f"[TimelineTask] Error generating timeline from document: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(bind=True, name='timeline_builder.export_timeline')
def export_timeline_task(
    self,
    user_id: str,
    timeline_id: str,
    export_format: str = 'json'
):
    """
    Export timeline to various formats (async).

    Args:
        user_id: User ID
        timeline_id: Timeline ID
        export_format: Export format (json, csv, pdf)
    """
    try:
        logger.info(f"[TimelineTask] Exporting timeline {timeline_id} as {export_format}")

        # Get timeline from database
        timeline = HistoricalTimeline.query.filter_by(
            id=timeline_id,
            user_id=user_id
        ).first()

        if not timeline:
            logger.error(f"[TimelineTask] Timeline {timeline_id} not found")
            return {'success': False, 'error': 'Timeline not found'}

        if export_format == 'json':
            # Export as JSON
            timeline_dict = timeline.to_dict()
            export_url = export_timeline_json(user_id, timeline_id, timeline_dict)

            logger.info(f"[TimelineTask] Timeline exported successfully: {export_url}")

            return {
                'success': True,
                'export_url': export_url,
                'format': 'json'
            }

        else:
            return {
                'success': False,
                'error': f'Unsupported export format: {export_format}'
            }

    except Exception as e:
        logger.error(f"[TimelineTask] Error exporting timeline: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(bind=True, name='timeline_builder.enhance_existing_timeline')
def enhance_existing_timeline_task(
    self,
    user_id: str,
    timeline_id: str
):
    """
    Enhance existing timeline with additional research (async).

    Args:
        user_id: User ID
        timeline_id: Timeline ID
    """
    try:
        logger.info(f"[TimelineTask] Enhancing timeline {timeline_id}")

        # Get timeline from database
        timeline = HistoricalTimeline.query.filter_by(
            id=timeline_id,
            user_id=user_id
        ).first()

        if not timeline:
            logger.error(f"[TimelineTask] Timeline {timeline_id} not found")
            return {'success': False, 'error': 'Timeline not found'}

        # Build timeline data
        timeline_data = {
            'title': timeline.title,
            'description': timeline.description,
            'events': timeline.events,
            'key_themes': timeline.key_themes,
            'key_figures': timeline.key_figures
        }

        # Enhance with research
        enhancement_result = enhance_timeline_with_research(timeline_data)

        if not enhancement_result.get('success'):
            return enhancement_result

        enhanced_data = enhancement_result['timeline_data']

        # Analyze relationships
        enhanced_data['events'] = analyze_timeline_relationships(enhanced_data.get('events', []))

        # Update timeline
        timeline.events = enhanced_data.get('events', [])
        timeline.key_themes = enhanced_data.get('key_themes', timeline.key_themes)
        timeline.key_figures = enhanced_data.get('key_figures', timeline.key_figures)
        timeline.total_events = len(enhanced_data.get('events', []))

        db.session.commit()

        logger.info(f"[TimelineTask] Timeline {timeline_id} enhanced successfully")

        return {
            'success': True,
            'timeline_id': timeline_id,
            'timeline_data': timeline.to_dict()
        }

    except Exception as e:
        logger.error(f"[TimelineTask] Error enhancing timeline: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }
