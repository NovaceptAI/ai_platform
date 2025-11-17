import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.create.story_to_comics_converter_service import StoryToComicsConverterService
from app.services.comic_storage_service import persist_comic_to_azure
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_comic_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to create comic strips from stories.

    Args:
        user_id: ID of the user requesting comic creation
        file_ids: List of file IDs to process (can be empty for text source)
        progress_id: Progress tracking ID
        options: Configuration for comic creation including source_type and text_prompt
    """
    # Create a new session for this task
    from flask import current_app as flask_app

    with flask_app.app_context():
        task_id = self.request.id

        try:
            log.info(f"[StoryToComicsTask] Starting comic creation for user {user_id}")

            # Get options with defaults
            source_type = options.get('source_type', 'file') if options else 'file'
            text_prompt = options.get('text_prompt', '') if options else ''
            num_panels = options.get('num_panels', 6) if options else 6
            image_style = options.get('image_style', 'vivid') if options else 'vivid'
            image_size = '1792x1024'  # Landscape format for comic panels
            generate_images = options.get('generate_images', True) if options else True

            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.percentage = 10
                    db.session.commit()

            # Initialize service
            comic_service = StoryToComicsConverterService()

            all_comics = []

            # Process based on source type
            if source_type == 'text':
                # Process text prompt
                try:
                    log.info(f"[StoryToComicsTask] Processing text prompt")

                    if progress:
                        progress.percentage = 20
                        db.session.commit()

                    # Convert text to comic
                    comic_result = comic_service.convert_story_to_comic(
                        source_type='text',
                        source_content=text_prompt,
                        num_panels=num_panels,
                        style=image_style
                    )

                    # Generate comic panel images if requested
                    panels = []
                    if generate_images and comic_result.get('comic_data'):
                        try:
                            log.info(f"[StoryToComicsTask] Generating {num_panels} comic panel images...")

                            if progress:
                                progress.percentage = 40
                                db.session.commit()

                            panels = comic_service.generate_comic_images(
                                comic_data=comic_result['comic_data'],
                                style=image_style,
                                size=image_size
                            )

                            log.info(f"[StoryToComicsTask] Generated {len(panels)} comic panel images")
                        except Exception as img_error:
                            log.error(f"[StoryToComicsTask] Error generating images: {str(img_error)}")
                            # Continue even if image generation fails

                    all_comics.append({
                        'source_type': 'text',
                        'source_name': 'User Text Prompt',
                        'comic_data': comic_result['comic_data'],
                        'panels': panels,
                        'metadata': comic_result['metadata']
                    })

                    log.info(f"[StoryToComicsTask] Successfully created comic from text prompt")

                except Exception as e:
                    log.error(f"[StoryToComicsTask] Error processing text prompt: {str(e)}")
                    all_comics.append({
                        'source_type': 'text',
                        'error': str(e)
                    })

            else:  # file or vault source
                total_files = len(file_ids)

                for i, file_id in enumerate(file_ids):
                    try:
                        log.info(f"[StoryToComicsTask] Processing file {file_id} ({i+1}/{total_files})")

                        # Update progress
                        if progress:
                            progress.percentage = 20 + (60 * i // total_files)
                            db.session.commit()

                        # Get file from database
                        from app.models.files import UploadedFile
                        file_obj = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()

                        if not file_obj:
                            log.warning(f"[StoryToComicsTask] File {file_id} not found")
                            continue

                        # Convert file content to comic
                        comic_result = comic_service.convert_story_to_comic(
                            source_type=source_type,
                            source_content='',  # Will extract from file
                            num_panels=num_panels,
                            style=image_style,
                            source_file=file_obj
                        )

                        # Generate comic panel images if requested
                        panels = []
                        if generate_images and comic_result.get('comic_data'):
                            try:
                                log.info(f"[StoryToComicsTask] Generating {num_panels} comic panel images...")

                                if progress:
                                    progress.percentage = 20 + (50 * i // total_files)
                                    db.session.commit()

                                panels = comic_service.generate_comic_images(
                                    comic_data=comic_result['comic_data'],
                                    style=image_style,
                                    size=image_size
                                )

                                log.info(f"[StoryToComicsTask] Generated {len(panels)} comic panel images")
                            except Exception as img_error:
                                log.error(f"[StoryToComicsTask] Error generating images: {str(img_error)}")
                                # Continue even if image generation fails

                        all_comics.append({
                            'file_id': file_id,
                            'source_type': source_type,
                            'source_name': file_obj.original_file_name,
                            'comic_data': comic_result['comic_data'],
                            'panels': panels,
                            'metadata': comic_result['metadata']
                        })

                        log.info(f"[StoryToComicsTask] Successfully created comic from {file_obj.original_file_name}")

                    except Exception as e:
                        log.error(f"[StoryToComicsTask] Error processing file {file_id}: {str(e)}")
                        all_comics.append({
                            'file_id': file_id,
                            'source_type': source_type,
                            'error': str(e)
                        })
                        continue

            # Persist comics to Azure storage and database
            persisted_comics = []
            if progress:
                progress.percentage = 85
                db.session.commit()

            for comic in all_comics:
                # Only persist successful comics with panels
                if 'panels' not in comic or not comic['panels'] or 'error' in comic:
                    log.warning(f"[StoryToComicsTask] Skipping persistence for comic without panels or with errors")
                    continue

                try:
                    log.info(f"[StoryToComicsTask] Persisting comic to Azure: {comic.get('source_name', 'Unknown')}")

                    # Prepare comic metadata for persistence
                    comic_metadata = {
                        'title': comic['comic_data'].get('title', 'Untitled Comic'),
                        'source_type': comic.get('source_type', source_type),
                        'source_file_id': comic.get('file_id'),
                        'source_text_preview': text_prompt[:200] if source_type == 'text' else None,
                        'style': image_style,
                        'generation_options': {
                            'num_panels': num_panels,
                            'image_style': image_style,
                            'source_type': source_type
                        },
                        'source_info': {
                            'source_name': comic.get('source_name', 'Unknown'),
                            'source_type': source_type
                        },
                        'ai_metadata': comic.get('metadata', {})
                    }

                    # Persist to Azure and create database record
                    persistence_result = persist_comic_to_azure(
                        user_id=user_id,
                        comic_data=comic_metadata,
                        panels_with_dalle_urls=comic['panels']
                    )

                    if persistence_result.get('success'):
                        log.info(f"[StoryToComicsTask] Successfully persisted comic {persistence_result['comic_id']}")
                        persisted_comics.append({
                            'comic_id': persistence_result['comic_id'],
                            'source_name': comic.get('source_name'),
                            'panels_persisted': persistence_result.get('panels_persisted', 0),
                            'thumbnail_url': persistence_result.get('thumbnail_url')
                        })
                    else:
                        log.error(f"[StoryToComicsTask] Failed to persist comic: {persistence_result.get('error')}")

                except Exception as persist_error:
                    log.error(f"[StoryToComicsTask] Error persisting comic: {str(persist_error)}")
                    log.error(traceback.format_exc())
                    continue

            # Create final result
            result = {
                'comics': all_comics,
                'total_comics': len(all_comics),
                'successful_comics': len([c for c in all_comics if 'comic_data' in c]),
                'persisted_comics': persisted_comics,
                'total_persisted': len(persisted_comics),
                'metadata': {
                    'source_type': source_type,
                    'num_panels': num_panels,
                    'image_style': image_style,
                    'generated_at': datetime.now().isoformat()
                }
            }

            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.percentage = 100
                progress.result_data = result
                progress.completed_at = datetime.utcnow()
                db.session.commit()

            log.info(f"[StoryToComicsTask] Successfully completed comic creation for user {user_id}")
            log.info(f"[StoryToComicsTask] Persisted {len(persisted_comics)} comics to gallery")
            return result

        except Exception as e:
            error_msg = f"Error in comic creation: {str(e)}"
            log.error(f"[StoryToComicsTask] {error_msg}")
            log.error(traceback.format_exc())

            # Update progress to failed
            if progress_id:
                try:
                    progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                    if progress:
                        progress.status = 'failed'
                        progress.error_message = error_msg
                        db.session.commit()
                except Exception as commit_error:
                    log.error(f"Failed to update progress on error: {str(commit_error)}")

            # Re-raise the exception so Celery knows the task failed
            raise
