import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.create.story_visualizer_service import StoryVisualizerService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_visualizer_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to create document visualizations from uploaded files.

    This task analyzes document content and generates visual representations
    (diagrams, illustrations, infographics) of the actual content.

    Args:
        user_id: ID of the user requesting visualization
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        options: Optional configuration for visualization
    """
    # Create a new session for this task
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[DocumentVisualizerTask] Starting visualization for user {user_id}, files: {file_ids}")

            # Get options with defaults
            audience_level = options.get('audience_level', 'general') if options else 'general'

            # Image generation options
            num_scenes = options.get('num_scenes', 5) if options else 5
            image_style = options.get('image_style', 'vivid') if options else 'vivid'
            image_size = options.get('image_size', '1024x1024') if options else '1024x1024'
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
            story_service = StoryVisualizerService()
            
            all_stories = []
            total_files = len(file_ids)
            
            for i, file_id in enumerate(file_ids):
                try:
                    log.info(f"[DocumentVisualizerTask] Processing file {file_id} ({i+1}/{total_files})")

                    # Update progress
                    if progress:
                        progress.percentage = 20 + (60 * i // total_files)
                        db.session.commit()

                    # Get file from database
                    from app.models.files import UploadedFile
                    file_obj = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()

                    if not file_obj:
                        log.warning(f"[DocumentVisualizerTask] File {file_id} not found")
                        continue

                    # Analyze document for visualization
                    story_result = story_service.create_story(
                        file=file_obj,
                        audience_level=audience_level
                    )
                    
                    # Generate visualization images if requested
                    scene_images = []
                    if generate_images and story_result.get('story_content'):
                        try:
                            log.info(f"[DocumentVisualizerTask] Generating {num_scenes} visualization images...")
                            # Update progress
                            if progress:
                                progress.percentage = 20 + (50 * i // total_files)
                                db.session.commit()

                            scene_images = story_service.generate_scene_images(
                                story_content=story_result['story_content'],
                                num_scenes=num_scenes,
                                style=image_style,
                                size=image_size
                            )

                            log.info(f"[DocumentVisualizerTask] Generated {len(scene_images)} visualization images")
                        except Exception as img_error:
                            log.error(f"[DocumentVisualizerTask] Error generating images: {str(img_error)}")
                            # Continue even if image generation fails

                    all_stories.append({
                        'file_id': file_id,
                        'filename': file_obj.original_file_name,
                        'story': story_result,
                        'scene_images': scene_images
                    })

                    log.info(f"[DocumentVisualizerTask] Successfully analyzed {file_obj.original_file_name}")

                except Exception as e:
                    log.error(f"[DocumentVisualizerTask] Error processing file {file_id}: {str(e)}")
                    all_stories.append({
                        'file_id': file_id,
                        'error': str(e)
                    })
                    continue
            
            # Create consolidated result if multiple files
            if len(all_stories) > 1:
                # Update progress
                if progress:
                    progress.percentage = 90
                    db.session.commit()
                
                consolidated_story = consolidate_stories(all_stories, audience_level)
                
                result = {
                    'consolidated_story': consolidated_story,
                    'individual_stories': all_stories,
                    'files_processed': len(file_ids),
                    'successful_stories': len([s for s in all_stories if 'story' in s]),
                    'story_metadata': {
                        'audience_level': audience_level,
                        'visualization_type': 'document_visualization'
                    }
                }
            else:
                # Single file result
                story_data = all_stories[0] if all_stories else None
                scene_images = story_data.get('scene_images', []) if story_data else []
                
                result = {
                    'story': story_data,
                    'scene_images': scene_images,  # Extract scene_images to top level
                    'story_metadata': {
                        'audience_level': audience_level,
                        'visualization_type': 'document_visualization'
                    }
                }
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.percentage = 100
                progress.result_data = result
                progress.completed_at = datetime.utcnow()
                db.session.commit()
            
            log.info(f"[DocumentVisualizerTask] Successfully completed visualization for user {user_id}")
            return result

        except Exception as e:
            error_msg = f"Error in document visualization: {str(e)}"
            log.error(f"[DocumentVisualizerTask] {error_msg}")
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


def consolidate_stories(individual_stories, audience_level):
    """
    Consolidate multiple document visualizations into a unified result.

    Args:
        individual_stories: List of individual visualization results
        audience_level: Target audience level

    Returns:
        Consolidated visualization dictionary
    """
    try:
        # Filter successful stories
        successful_stories = [s for s in individual_stories if 'story' in s and s['story']]
        
        if not successful_stories:
            return {
                'error': 'No successful visualizations to consolidate',
                'story_content': create_error_story(),
                'metadata': create_default_story_metadata(audience_level)
            }
        
        # Collect story elements from all stories
        consolidated_sections = {}
        all_characters = []
        all_settings = []
        combined_learning_objectives = []
        total_reading_time = 0
        
        for story_data in successful_stories:
            story = story_data.get('story', {})
            filename = story_data.get('filename', 'Unknown')
            
            # Extract story sections
            story_content = story.get('story_content', {})
            story_sections = story_content.get('story_sections', {})
            
            # Combine sections
            for section_key, section_data in story_sections.items():
                if section_key not in consolidated_sections:
                    consolidated_sections[section_key] = {
                        'title': section_data.get('title', section_key.replace('_', ' ').title()),
                        'combined_content': [],
                        'source_files': [],
                        'purpose': section_data.get('purpose', 'narrative')
                    }
                
                consolidated_sections[section_key]['combined_content'].append({
                    'source_file': filename,
                    'content': section_data.get('content', ''),
                    'word_count': section_data.get('word_count', 0)
                })
                consolidated_sections[section_key]['source_files'].append(filename)
            
            # Collect other elements
            story_summary = story.get('story_summary', {})
            estimated_time = story_summary.get('estimated_reading_time', '0 minutes')
            # Simple time extraction (could be more sophisticated)
            if 'minute' in estimated_time:
                try:
                    minutes = int(estimated_time.split()[0])
                    total_reading_time += minutes
                except:
                    total_reading_time += 5  # default fallback
        
        # Create consolidated structure
        consolidated_content = create_consolidated_story_content(
            consolidated_sections, audience_level
        )

        # Create consolidated metadata
        consolidated_metadata = create_consolidated_story_metadata(
            successful_stories, audience_level, len(successful_stories)
        )

        return {
            'story_content': consolidated_content,
            'individual_sources': [s['filename'] for s in successful_stories],
            'metadata': consolidated_metadata,
            'consolidation_summary': {
                'source_files': len(successful_stories),
                'total_sections': len(consolidated_sections),
                'estimated_reading_time': f"{total_reading_time} minutes",
                'visualization_type': 'document_visualization',
                'audience_level': audience_level
            }
        }

    except Exception as e:
        log.error(f"Error consolidating visualizations: {str(e)}")
        return {
            'error': f'Consolidation failed: {str(e)}',
            'story_content': create_error_story(),
            'metadata': create_default_story_metadata(audience_level)
        }


def create_consolidated_story_content(consolidated_sections, audience_level):
    """Create consolidated visualization content from multiple sources."""
    
    # Define section priority order for storytelling
    section_priority = {
        'opening': 1,
        'characters': 2,
        'setting': 3,
        'main_narrative': 4,
        'climax': 5,
        'resolution': 6,
        'learning_objectives': 7,
        'creative_elements': 8
    }
    
    # Sort sections by storytelling priority
    sorted_sections = sorted(consolidated_sections.items(), 
                           key=lambda x: section_priority.get(x[0], 99))
    
    consolidated_story_sections = {}
    
    for section_key, section_data in sorted_sections:
        # Create a unified narrative from multiple sources
        if section_key == 'main_narrative' and 'sections' in section_data.get('combined_content', [{}])[0]:
            # Handle narrative arc specially
            consolidated_story_sections[section_key] = create_unified_narrative_arc(section_data)
        else:
            # Combine other sections
            combined_text = ""
            source_attribution = []
            
            for content_item in section_data['combined_content']:
                source_file = content_item['source_file']
                content = content_item['content']
                
                if content:
                    # Add smooth transitions between sources
                    if combined_text:
                        combined_text += f"\n\n*Continuing our story...*\n\n{content}"
                    else:
                        combined_text = content
                    source_attribution.append(source_file)
            
            consolidated_story_sections[section_key] = {
                'title': section_data['title'],
                'content': combined_text.strip(),
                'source_files': list(set(source_attribution)),
                'purpose': section_data['purpose'],
                'word_count': len(combined_text.split())
            }
    
    return {
        'title': f"Consolidated Document Visualization Collection",
        'subtitle': f"Multi-Source Visual Representations for {audience_level.title()} Audience",
        'story_type': f"consolidated_visualization",
        'audience_level': audience_level,
        'creation_date': datetime.now().strftime("%B %d, %Y"),
        'story_sections': consolidated_story_sections,
        'consolidation_note': "This combines visualizations from multiple source documents."
    }


def create_unified_narrative_arc(narrative_section_data):
    """Create a unified narrative arc from multiple story arcs."""
    
    all_chapters = []
    
    for content_item in narrative_section_data['combined_content']:
        content = content_item['content']
        source_file = content_item['source_file']
        
        # If this is a narrative arc with sections, extract them
        if 'sections' in content:
            sections = content['sections']
            for section in sections:
                all_chapters.append({
                    'title': f"{section.get('title', 'Chapter')} (from {source_file})",
                    'content': section.get('content', ''),
                    'theme': section.get('theme', 'story_development'),
                    'source_file': source_file,
                    'word_count': section.get('word_count', 0)
                })
    
    return {
        'title': 'Unified Story Journey',
        'sections': all_chapters,
        'purpose': 'consolidated_narrative',
        'total_chapters': len(all_chapters),
        'total_word_count': sum(chapter['word_count'] for chapter in all_chapters)
    }


def create_consolidated_story_metadata(successful_stories, audience_level, source_count):
    """Create metadata for consolidated visualizations."""

    return {
        'consolidation_info': {
            'source_files': source_count,
            'visualization_type': 'document_visualization',
            'audience_level': audience_level,
            'consolidated_at': datetime.now().isoformat(),
            'consolidation_method': 'visualization_merge'
        },
        'source_stories': [
            {
                'filename': story['filename'],
                'metadata': story['story'].get('metadata', {})
            } for story in successful_stories
        ],
        'educational_value': {
            'multi_source_learning': True,
            'visual_engagement': 'high',
            'comprehensive_coverage': source_count > 1,
            'factual_accuracy': 'high'
        }
    }


def create_error_story():
    """Create a basic error story structure."""
    return {
        'title': 'Story Creation Error',
        'story_sections': {
            'error_message': {
                'title': 'Unable to Create Story',
                'content': 'We encountered an issue while creating your story. Please try again with different content.',
                'purpose': 'error_notification'
            }
        }
    }


def create_default_story_metadata(audience_level):
    """Create default metadata for error cases."""
    return {
        'story_configuration': {
            'visualization_type': 'document_visualization',
            'audience_level': audience_level,
            'status': 'error',
            'generated_at': datetime.now().isoformat()
        },
        'error': True
    }
