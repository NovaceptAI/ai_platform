"""
AI 3D Model Builder Celery Tasks

Background tasks for AI-powered 3D model generation.
Handles async generation with progress tracking and file storage.
"""

import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.create.ai_3d_model_builder_service import AI3DModelBuilderService
from app.services.three_d_model_storage_service import save_3d_model_to_azure
import traceback
from datetime import datetime

log = logging.getLogger(__name__)


@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_3d_model_task(self, user_id: str, progress_id: str, options: dict):
    """
    Celery task to generate 3D models from text prompts.

    Args:
        user_id: ID of the user requesting model generation
        progress_id: Progress tracking ID
        options: Configuration dict with prompt_text, complexity_level, style, title

    Progress stages:
    - 10%: Analyzing prompt
    - 30%: Generating 3D geometry with AI
    - 50%: Creating mesh and textures
    - 70%: Rendering preview images
    - 85%: Converting to export formats
    - 100%: Uploading to Azure and saving to DB
    """
    from flask import current_app as flask_app

    with flask_app.app_context():
        task_id = self.request.id

        try:
            log.info(f"[AI3DModelBuilderTask] Starting 3D model generation for user {user_id}")

            # Get options
            prompt_text = options.get('prompt_text')
            complexity_level = options.get('complexity_level', 'simple')
            style = options.get('style', 'realistic')
            title = options.get('title', 'My 3D Model')

            # Update progress to in_progress
            progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
            if progress:
                progress.status = 'in_progress'
                progress.percentage = 10
                db.session.commit()

            # Initialize service
            model_service = AI3DModelBuilderService()

            # Step 1: Analyze prompt (10%)
            log.info(f"[AI3DModelBuilderTask] Analyzing prompt: {prompt_text}")

            if progress:
                progress.percentage = 10
                db.session.commit()

            prompt_analysis = model_service.analyze_3d_prompt(
                prompt_text=prompt_text,
                complexity=complexity_level
            )

            log.info(f"[AI3DModelBuilderTask] Prompt analysis: {prompt_analysis}")

            # Step 2: Generate 3D geometry (30%)
            log.info(f"[AI3DModelBuilderTask] Generating 3D geometry")

            if progress:
                progress.percentage = 30
                db.session.commit()

            geometry_result = model_service.generate_3d_geometry(
                prompt=prompt_text,
                object_type=prompt_analysis.get('object_type', 'object'),
                complexity=complexity_level,
                style=style
            )

            log.info(f"[AI3DModelBuilderTask] Generated geometry with {geometry_result.get('shape_count', 0)} shapes")

            # Step 3: Create mesh and apply materials (50%)
            log.info(f"[AI3DModelBuilderTask] Creating mesh and applying materials")

            if progress:
                progress.percentage = 50
                db.session.commit()

            mesh_data = model_service.create_mesh_from_geometry(
                geometry=geometry_result['geometry'],
                style=style
            )

            log.info(f"[AI3DModelBuilderTask] Created mesh: {mesh_data['metadata']['vertex_count']} vertices, {mesh_data['metadata']['face_count']} faces")

            # Step 4: Render preview images (70%)
            log.info(f"[AI3DModelBuilderTask] Rendering preview images")

            if progress:
                progress.percentage = 70
                db.session.commit()

            preview_images = model_service.render_preview_images(
                mesh_data=mesh_data,
                angles=['front', 'side', 'top', 'perspective']
            )

            log.info(f"[AI3DModelBuilderTask] Rendered {len(preview_images)} preview images")

            # Step 5: Export to multiple formats (85%)
            log.info(f"[AI3DModelBuilderTask] Exporting to file formats")

            if progress:
                progress.percentage = 85
                db.session.commit()

            export_files = model_service.export_3d_model(
                mesh_data=mesh_data,
                formats=['glb', 'obj', 'stl']
            )

            log.info(f"[AI3DModelBuilderTask] Exported to {len(export_files)} formats")

            # Step 6: Save to Azure and database (100%)
            log.info(f"[AI3DModelBuilderTask] Saving to Azure and database")

            if progress:
                progress.percentage = 90
                db.session.commit()

            # Prepare model metadata
            model_data = {
                'title': title,
                'prompt_text': prompt_text,
                'complexity_level': complexity_level,
                'style': style,
                'category': prompt_analysis.get('category'),
                'object_type': prompt_analysis.get('object_type'),
                'generation_metadata': {
                    'prompt_analysis': prompt_analysis,
                    'generation_time': datetime.utcnow().isoformat(),
                    'task_id': task_id,
                    'service_version': '1.0',
                    'stage': 1
                }
            }

            # Save to Azure and create database record
            save_result = save_3d_model_to_azure(
                user_id=user_id,
                model_data=model_data,
                export_files=export_files,
                preview_images=preview_images,
                mesh_metadata=mesh_data['metadata']
            )

            if not save_result.get('success'):
                raise Exception(save_result.get('error', 'Failed to save 3D model'))

            model_id = save_result['model_id']
            log.info(f"[AI3DModelBuilderTask] Successfully saved 3D model {model_id}")

            # Create final result
            result = {
                'model_id': model_id,
                'title': title,
                'vertex_count': mesh_data['metadata']['vertex_count'],
                'face_count': mesh_data['metadata']['face_count'],
                'formats_available': list(export_files.keys()),
                'preview_count': len(preview_images),
                'thumbnail_url': save_result.get('thumbnail_url'),
                'category': prompt_analysis.get('category'),
                'object_type': prompt_analysis.get('object_type')
            }

            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.percentage = 100
                progress.result_data = result
                progress.completed_at = datetime.utcnow()
                db.session.commit()

            log.info(f"[AI3DModelBuilderTask] Successfully completed 3D model generation for user {user_id}")
            return result

        except Exception as e:
            error_msg = f"Error in 3D model generation: {str(e)}"
            log.error(f"[AI3DModelBuilderTask] {error_msg}")
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

            # Re-raise the exception so Celery knows the task failed
            raise
