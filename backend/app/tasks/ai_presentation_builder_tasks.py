import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.models.presentations import PresentationCreation
from app.services.stages.create.ai_presentation_builder_service import AIPresentationBuilderService
from app.services.presentation_storage_service import (
    save_presentation_stage1,
    upload_presentation_image_to_azure,
    upload_pptx_to_azure,
    download_image_from_url
)
import traceback
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)


@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_presentation_content_task(
    self,
    user_id: str,
    file_id: Optional[str],
    progress_id: str,
    options: dict
):
    """
    Celery task for Stage 1: Generate presentation slide content with ChatGPT.

    Args:
        user_id: ID of the user requesting presentation
        file_id: File ID (if source is file/vault)
        progress_id: Progress tracking ID
        options: Configuration dict with source_type, text_prompt, total_slides, theme
    """
    from flask import current_app as flask_app

    with flask_app.app_context():
        task_id = self.request.id

        try:
            log.info(f"[PresentationBuilderTask] Starting Stage 1 for user {user_id}")

            # Get options
            source_type = options.get('source_type', 'text')
            text_prompt = options.get('text_prompt', '')
            total_slides = options.get('total_slides', 10)
            theme = options.get('theme', 'professional_blue')

            # Update progress to in_progress
            progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
            if progress:
                progress.status = 'in_progress'
                progress.percentage = 10
                db.session.commit()

            # Initialize service
            presentation_service = AIPresentationBuilderService()

            # Get source content
            source_content = text_prompt
            source_file = None

            if source_type in ['file', 'vault'] and file_id:
                log.info(f"[PresentationBuilderTask] Fetching file {file_id}")
                from app.models.files import UploadedFile
                source_file = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()

                if not source_file:
                    raise ValueError(f"File not found: {file_id}")

                # Extract content from file
                source_content = presentation_service._extract_content_from_file(source_file)
                log.info(f"[PresentationBuilderTask] Extracted {len(source_content)} characters from file")

            if progress:
                progress.percentage = 20
                db.session.commit()

            # Generate presentation content
            log.info(f"[PresentationBuilderTask] Generating {total_slides} slides with ChatGPT")
            content_result = presentation_service.generate_presentation_content(
                source_type=source_type,
                source_content=source_content,
                total_slides=total_slides,
                theme=theme,
                source_file=source_file
            )

            if not content_result.get('success'):
                raise Exception(content_result.get('error', 'Failed to generate presentation content'))

            if progress:
                progress.percentage = 70
                db.session.commit()

            # Save to database (Stage 1)
            log.info(f"[PresentationBuilderTask] Saving presentation to database")
            presentation_data = {
                'title': content_result['title'],
                'source_type': source_type,
                'source_file_id': file_id,
                'source_text_preview': text_prompt[:500] if source_type == 'text' else None,
                'theme': theme,
                'generation_options': {
                    'total_slides': total_slides,
                    'source_type': source_type
                },
                'source_info': {
                    'source_name': source_file.original_file_name if source_file else 'Text Prompt',
                    'source_type': source_type
                },
                'ai_metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'model_used': 'gpt-4',
                    'task_id': task_id
                }
            }

            save_result = save_presentation_stage1(
                user_id=user_id,
                presentation_data=presentation_data,
                slides_data=content_result['slides']
            )

            if not save_result.get('success'):
                raise Exception(save_result.get('error', 'Failed to save presentation'))

            presentation_id = save_result['presentation_id']
            log.info(f"[PresentationBuilderTask] Saved presentation {presentation_id}")

            if progress:
                progress.percentage = 100
                progress.status = 'completed'
                progress.result_data = {
                    'presentation_id': presentation_id,
                    'title': content_result['title'],
                    'total_slides': len(content_result['slides']),
                    'stage': 1
                }
                progress.completed_at = datetime.utcnow()
                db.session.commit()

            log.info(f"[PresentationBuilderTask] Stage 1 completed for presentation {presentation_id}")

            return {
                'success': True,
                'presentation_id': presentation_id,
                'title': content_result['title'],
                'total_slides': len(content_result['slides']),
                'stage': 1
            }

        except Exception as e:
            error_msg = f"Error in presentation content generation: {str(e)}"
            log.error(f"[PresentationBuilderTask] {error_msg}")
            log.error(traceback.format_exc())

            # Update progress to failed
            try:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'failed'
                    progress.error_message = error_msg
                    db.session.commit()
            except Exception as commit_error:
                log.error(f"Failed to update progress on error: {str(commit_error)}")

            raise


@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def finalize_presentation_task(
    self,
    user_id: str,
    progress_id: str,
    options: dict
):
    """
    Celery task for Stage 2: Generate DALL-E images and create PPTX file.

    Args:
        user_id: ID of the user
        progress_id: Progress tracking ID
        options: Configuration dict with presentation_id, image_style, slides_for_images
    """
    from flask import current_app as flask_app

    with flask_app.app_context():
        task_id = self.request.id

        try:
            log.info(f"[PresentationBuilderTask] Starting Stage 2 for user {user_id}")

            # Get options
            presentation_id = options.get('presentation_id')
            image_style = options.get('image_style', 'professional')
            slides_for_images = options.get('slides_for_images', [])

            # Update progress to in_progress
            progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
            if progress:
                progress.status = 'in_progress'
                progress.percentage = 10
                db.session.commit()

            # Get presentation from database
            log.info(f"[PresentationBuilderTask] Fetching presentation {presentation_id}")
            presentation = PresentationCreation.query.filter_by(
                id=presentation_id,
                user_id=user_id
            ).first()

            if not presentation:
                raise ValueError(f"Presentation not found: {presentation_id}")

            # Initialize service
            presentation_service = AIPresentationBuilderService()

            # Get slides data
            slides_data = presentation.slides_data
            if not isinstance(slides_data, list):
                raise ValueError("Invalid slides_data format")

            # Mark which slides should have images
            for slide in slides_data:
                slide_number = slide.get('slide_number', 0)
                slide['user_wants_image'] = slide_number in slides_for_images

            if progress:
                progress.percentage = 20
                db.session.commit()

            # Generate DALL-E images for selected slides
            images_generated = 0
            if slides_for_images:
                log.info(f"[PresentationBuilderTask] Generating images for {len(slides_for_images)} slides")
                slides_data = presentation_service.generate_images_for_slides(
                    slides_data=slides_data,
                    image_style=image_style
                )
                images_generated = sum(1 for s in slides_data if s.get('dalle_image_url'))
                log.info(f"[PresentationBuilderTask] Generated {images_generated} images")

            if progress:
                progress.percentage = 60
                db.session.commit()

            # Download images from DALL-E and upload to Azure
            log.info(f"[PresentationBuilderTask] Uploading images to Azure")
            for slide in slides_data:
                if slide.get('dalle_image_url'):
                    try:
                        # Download from DALL-E
                        image_bytes = download_image_from_url(slide['dalle_image_url'])
                        if image_bytes:
                            # Upload to Azure
                            azure_url = upload_presentation_image_to_azure(
                                user_id=user_id,
                                presentation_id=presentation_id,
                                slide_number=slide['slide_number'],
                                image_bytes=image_bytes,
                                compress=True
                            )
                            if azure_url:
                                slide['azure_image_url'] = azure_url
                                log.info(f"[PresentationBuilderTask] Uploaded slide {slide['slide_number']} image to Azure")
                    except Exception as img_error:
                        log.error(f"[PresentationBuilderTask] Error uploading image for slide {slide['slide_number']}: {str(img_error)}")

            if progress:
                progress.percentage = 75
                db.session.commit()

            # Create PowerPoint file
            log.info(f"[PresentationBuilderTask] Creating PowerPoint file")
            pptx_bytes = presentation_service.create_powerpoint(
                slides_data=slides_data,
                theme=presentation.theme,
                title=presentation.title
            )

            # Upload PPTX to Azure
            log.info(f"[PresentationBuilderTask] Uploading PPTX to Azure")
            pptx_url = upload_pptx_to_azure(
                user_id=user_id,
                presentation_id=presentation_id,
                pptx_bytes=pptx_bytes
            )

            if not pptx_url:
                raise Exception("Failed to upload PPTX to Azure")

            if progress:
                progress.percentage = 90
                db.session.commit()

            # Update presentation in database
            log.info(f"[PresentationBuilderTask] Updating presentation in database")
            presentation.slides_data = slides_data
            presentation.image_style = image_style
            presentation.pptx_url = pptx_url

            # Set thumbnail to first slide with image, or first slide
            thumbnail_url = None
            for slide in slides_data:
                if slide.get('azure_image_url'):
                    thumbnail_url = slide['azure_image_url']
                    break
            presentation.thumbnail_url = thumbnail_url

            # Collect preview images (all slide images)
            preview_images = []
            for slide in slides_data:
                if slide.get('azure_image_url'):
                    preview_images.append({
                        'slide_number': slide['slide_number'],
                        'url': slide['azure_image_url']
                    })
            presentation.preview_images = preview_images

            # Update metadata
            if not presentation.presentation_metadata:
                presentation.presentation_metadata = {}
            presentation.presentation_metadata['stage'] = 2
            presentation.presentation_metadata['finalized_at'] = datetime.utcnow().isoformat()
            presentation.presentation_metadata['images_generated'] = images_generated
            presentation.presentation_metadata['finalize_task_id'] = task_id

            db.session.commit()
            log.info(f"[PresentationBuilderTask] Successfully updated presentation {presentation_id}")

            # Update progress to completed
            if progress:
                progress.percentage = 100
                progress.status = 'completed'
                progress.result_data = {
                    'presentation_id': presentation_id,
                    'title': presentation.title,
                    'total_slides': presentation.total_slides,
                    'images_generated': images_generated,
                    'pptx_url': pptx_url,
                    'thumbnail_url': thumbnail_url,
                    'stage': 2
                }
                progress.completed_at = datetime.utcnow()
                db.session.commit()

            log.info(f"[PresentationBuilderTask] Stage 2 completed for presentation {presentation_id}")

            return {
                'success': True,
                'presentation_id': presentation_id,
                'title': presentation.title,
                'total_slides': presentation.total_slides,
                'images_generated': images_generated,
                'pptx_url': pptx_url,
                'stage': 2
            }

        except Exception as e:
            error_msg = f"Error in presentation finalization: {str(e)}"
            log.error(f"[PresentationBuilderTask] {error_msg}")
            log.error(traceback.format_exc())

            # Update progress to failed
            try:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'failed'
                    progress.error_message = error_msg
                    db.session.commit()
            except Exception as commit_error:
                log.error(f"Failed to update progress on error: {str(commit_error)}")

            raise
