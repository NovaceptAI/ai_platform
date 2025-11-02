"""
Infographic Creator Tasks
Handles asynchronous infographic generation and processing
"""
import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.create.infographic_creator_service import InfographicCreatorService
import traceback
from datetime import datetime
import time
import random
import json

log = logging.getLogger(__name__)

def get_file_analysis_data(file_id):
    """Helper function to get file analysis data from database"""
    # This would normally query the database for file analysis results
    # For now, returning mock data that matches expected structure
    return {
        'file_id': file_id,
        'file_name': f'document_{file_id}.pdf',
        'content': f'Sample content for file {file_id}',
        'analysis_results': {
            'total_pages': random.randint(5, 50),
            'word_count': random.randint(1000, 10000),
            'main_topics': ['Topic 1', 'Topic 2', 'Topic 3'],
            'key_insights': ['Insight A', 'Insight B', 'Insight C']
        }
    }

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_infographic_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to generate infographics from uploaded files.
    
    Args:
        user_id: ID of the user requesting infographic generation
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        options: Optional configuration for infographic generation
    """
    # Create a new session for this task
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[InfographicGeneratorTask] Starting infographic generation for user {user_id}, files: {file_ids}")
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.current_step = 'Initializing infographic generation'
                    progress.progress_percentage = 10
                    db.session.commit()
            
            # Initialize service
            infographic_service = InfographicCreatorService()
            
            all_infographics = []
            total_files = len(file_ids)
            
            # Default options
            if options is None:
                options = {}
            
            template_style = options.get('template_style', 'modern')
            color_scheme = options.get('color_scheme', 'blue_gradient')
            include_charts = options.get('include_charts', True)
            size = options.get('size', 'A4')
            sections = options.get('sections', ['overview', 'key_points', 'statistics', 'conclusion'])
            
            for i, file_id in enumerate(file_ids):
                try:
                    log.info(f"[InfographicGeneratorTask] Processing file {file_id} ({i+1}/{total_files})")
                    
                    # Update progress
                    if progress:
                        progress.current_step = f'Generating infographic for file {i+1}/{total_files}'
                        progress.progress_percentage = 20 + (60 * i // total_files)
                        db.session.commit()
                    
                    # Get file data from database
                    file_data = get_file_analysis_data(file_id)
                    
                    if not file_data:
                        log.warning(f"[InfographicGeneratorTask] No analysis data found for file {file_id}")
                        continue
                    
                    # Generate infographic for this file
                    infographic_result = infographic_service.generate_infographic(file_data, options)
                    
                    # Add file identification
                    infographic_result['file_id'] = file_id
                    infographic_result['file_name'] = file_data.get('file_name', f'File {file_id}')
                    infographic_result['user_id'] = user_id
                    infographic_result['task_id'] = task_id
                    infographic_result['created_at'] = datetime.utcnow().isoformat()
                    
                    all_infographics.append(infographic_result)
                    
                    log.info(f"[InfographicGeneratorTask] Successfully generated infographic for file {file_id}")
                    
                except Exception as file_error:
                    log.error(f"[InfographicGeneratorTask] Error processing file {file_id}: {str(file_error)}")
                    log.error(traceback.format_exc())
                    
                    # Add error info but continue with other files
                    error_result = {
                        'file_id': file_id,
                        'error': str(file_error),
                        'status': 'failed'
                    }
                    all_infographics.append(error_result)
            
            # Final result compilation
            final_result = {
                'task_id': task_id,
                'user_id': user_id,
                'total_files': total_files,
                'successful_infographics': len([r for r in all_infographics if 'error' not in r]),
                'failed_infographics': len([r for r in all_infographics if 'error' in r]),
                'infographics': all_infographics,
                'options_used': options,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.current_step = 'Infographic generation completed'
                progress.progress_percentage = 100
                progress.result = final_result
                db.session.commit()
            
            log.info(f"[InfographicGeneratorTask] Completed infographic generation for user {user_id}")
            return final_result
            
        except Exception as e:
            log.error(f"[InfographicGeneratorTask] Task failed: {str(e)}")
            log.error(traceback.format_exc())
            
            # Update progress to failed
            if progress:
                progress.status = 'failed'
                progress.current_step = f'Error: {str(e)}'
                progress.error_message = str(e)
                db.session.commit()
            
            raise


@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_infographic_template(self, user_id: str, template_id: str, file_ids: list, progress_id: str = None, customizations: dict = None):
    """
    Process a specific infographic template with file content
    
    Args:
        user_id: ID of the user
        template_id: ID of the template to use
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        customizations: Template customizations
    """
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[InfographicTemplateTask] Processing template {template_id} for user {user_id}")
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.current_step = 'Loading template'
                    progress.progress_percentage = 10
                    db.session.commit()
            
            # Initialize service
            infographic_service = InfographicCreatorService()
            
            # Process template
            template_result = infographic_service.process_template(
                template_id=template_id,
                file_ids=file_ids,
                customizations=customizations
            )
            
            # Final result
            final_result = {
                'task_id': task_id,
                'user_id': user_id,
                'template_id': template_id,
                'file_ids': file_ids,
                'customizations': customizations,
                'result': template_result,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.current_step = 'Template processing completed'
                progress.progress_percentage = 100
                progress.result = final_result
                db.session.commit()
            
            log.info(f"[InfographicTemplateTask] Completed template {template_id} for user {user_id}")
            return final_result
            
        except Exception as e:
            log.error(f"[InfographicTemplateTask] Task failed: {str(e)}")
            log.error(traceback.format_exc())
            
            if progress:
                progress.status = 'failed'
                progress.current_step = f'Error: {str(e)}'
                progress.error_message = str(e)
                db.session.commit()
            
            raise


@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def export_infographic_task(self, user_id: str, infographic_id: str, export_format: str, progress_id: str = None, options: dict = None):
    """
    Export infographic to specified format
    
    Args:
        user_id: ID of the user
        infographic_id: ID of the infographic to export
        export_format: Export format (PNG, PDF, SVG, JPG)
        progress_id: Progress tracking ID
        options: Export options (resolution, quality, etc.)
    """
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[InfographicExportTask] Exporting infographic {infographic_id} to {export_format}")
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.current_step = f'Initializing {export_format} export'
                    progress.progress_percentage = 10
                    db.session.commit()
            
            # Initialize service
            infographic_service = InfographicCreatorService()
            
            # Export infographic
            export_result = infographic_service.export_infographic(
                infographic_id=infographic_id,
                export_format=export_format,
                options=options
            )
            
            # Final result
            final_result = {
                'task_id': task_id,
                'user_id': user_id,
                'infographic_id': infographic_id,
                'export_format': export_format,
                'options': options,
                'result': export_result,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.current_step = f'Export to {export_format} completed'
                progress.progress_percentage = 100
                progress.result = final_result
                db.session.commit()
            
            log.info(f"[InfographicExportTask] Completed export {infographic_id} to {export_format}")
            return final_result
            
        except Exception as e:
            log.error(f"[InfographicExportTask] Task failed: {str(e)}")
            log.error(traceback.format_exc())
            
            if progress:
                progress.status = 'failed'
                progress.current_step = f'Error: {str(e)}'
                progress.error_message = str(e)
                db.session.commit()
            
            raise
