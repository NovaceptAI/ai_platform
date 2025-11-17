import logging
from celery import current_app
from app.db import db
from app.models.status import Progress
from app.services.stages.create.report_builder_service import ReportBuilderService
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

@current_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report_task(self, user_id: str, file_ids: list, progress_id: str = None, options: dict = None):
    """
    Celery task to generate structured research reports from uploaded files.
    
    Args:
        user_id: ID of the user requesting report generation
        file_ids: List of file IDs to process
        progress_id: Progress tracking ID
        options: Optional configuration for report generation
    """
    # Create a new session for this task
    from flask import current_app as flask_app
    
    with flask_app.app_context():
        task_id = self.request.id
        
        try:
            log.info(f"[ReportBuilderTask] Starting report generation for user {user_id}, files: {file_ids}")
            
            # Get options with defaults
            report_type = options.get('report_type', 'research') if options else 'research'
            format_style = options.get('format_style', 'academic') if options else 'academic'
            length = options.get('length', 'medium') if options else 'medium'
            include_citations = options.get('include_citations', True) if options else True
            
            # Update progress to in_progress
            progress = None
            if progress_id:
                progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                if progress:
                    progress.status = 'in_progress'
                    progress.current_step = 'Initializing report generation'
                    progress.progress_percentage = 10
                    db.session.commit()
            
            # Initialize service
            report_service = ReportBuilderService()
            
            all_reports = []
            total_files = len(file_ids)
            
            for i, file_id in enumerate(file_ids):
                try:
                    log.info(f"[ReportBuilderTask] Processing file {file_id} ({i+1}/{total_files})")
                    
                    # Update progress
                    if progress:
                        progress.current_step = f'Generating report for file {i+1}/{total_files}'
                        progress.progress_percentage = 20 + (60 * i // total_files)
                        db.session.commit()
                    
                    # Get file from database
                    from app.models.files import UploadedFile
                    file_obj = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
                    
                    if not file_obj:
                        log.warning(f"[ReportBuilderTask] File {file_id} not found")
                        continue
                    
                    # Generate report
                    report_result = report_service.generate_report(
                        file=file_obj,
                        report_type=report_type,
                        format_style=format_style,
                        length=length,
                        include_citations=include_citations
                    )
                    
                    all_reports.append({
                        'file_id': file_id,
                        'filename': file_obj.filename,
                        'report': report_result
                    })
                    
                    log.info(f"[ReportBuilderTask] Successfully generated report for {file_obj.filename}")
                    
                except Exception as e:
                    log.error(f"[ReportBuilderTask] Error processing file {file_id}: {str(e)}")
                    all_reports.append({
                        'file_id': file_id,
                        'error': str(e)
                    })
                    continue
            
            # Create consolidated result if multiple files
            if len(all_reports) > 1:
                # Update progress
                if progress:
                    progress.current_step = 'Consolidating reports'
                    progress.progress_percentage = 90
                    db.session.commit()
                
                consolidated_report = consolidate_reports(all_reports, report_type, format_style)
                
                result = {
                    'consolidated_report': consolidated_report,
                    'individual_reports': all_reports,
                    'files_processed': len(file_ids),
                    'successful_reports': len([r for r in all_reports if 'report' in r]),
                    'report_metadata': {
                        'report_type': report_type,
                        'format_style': format_style,
                        'length': length,
                        'include_citations': include_citations
                    }
                }
            else:
                # Single file result
                result = {
                    'report': all_reports[0] if all_reports else None,
                    'report_metadata': {
                        'report_type': report_type,
                        'format_style': format_style,
                        'length': length,
                        'include_citations': include_citations
                    }
                }
            
            # Update progress to completed
            if progress:
                progress.status = 'completed'
                progress.current_step = 'Report generation completed'
                progress.progress_percentage = 100
                progress.result = result
                progress.completed_at = datetime.utcnow()
                db.session.commit()
            
            log.info(f"[ReportBuilderTask] Successfully completed report generation for user {user_id}")
            return result
            
        except Exception as e:
            error_msg = f"Error in report generation: {str(e)}"
            log.error(f"[ReportBuilderTask] {error_msg}")
            log.error(traceback.format_exc())
            
            # Update progress to failed
            if progress_id:
                try:
                    progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
                    if progress:
                        progress.status = 'failed'
                        progress.current_step = 'Report generation failed'
                        progress.error_message = error_msg
                        db.session.commit()
                except Exception as commit_error:
                    log.error(f"Failed to update progress on error: {str(commit_error)}")
            
            # Re-raise the exception so Celery knows the task failed
            raise


def consolidate_reports(individual_reports, report_type, format_style):
    """
    Consolidate multiple reports into a unified document.
    
    Args:
        individual_reports: List of individual report results
        report_type: Type of report
        format_style: Formatting style
        
    Returns:
        Consolidated report dictionary
    """
    try:
        # Filter successful reports
        successful_reports = [r for r in individual_reports if 'report' in r and r['report']]
        
        if not successful_reports:
            return {
                'error': 'No successful reports to consolidate',
                'report_content': create_error_report(),
                'metadata': create_default_metadata(report_type, format_style)
            }
        
        # Collect sections from all reports
        all_sections = {}
        combined_metadata = []
        total_word_count = 0
        
        for report_data in successful_reports:
            report = report_data.get('report', {})
            filename = report_data.get('filename', 'Unknown')
            
            # Extract sections from each report
            report_content = report.get('report_content', {})
            sections = report_content.get('sections', {})
            
            # Combine similar sections
            for section_key, section_data in sections.items():
                if section_key not in all_sections:
                    all_sections[section_key] = {
                        'title': section_data.get('title', section_key.replace('_', ' ').title()),
                        'combined_content': [],
                        'source_files': [],
                        'section_type': section_data.get('section_type', 'content')
                    }
                
                all_sections[section_key]['combined_content'].append({
                    'source_file': filename,
                    'content': section_data.get('content', ''),
                    'word_count': section_data.get('word_count', 0)
                })
                all_sections[section_key]['source_files'].append(filename)
            
            # Collect metadata
            metadata = report.get('metadata', {})
            combined_metadata.append({
                'filename': filename,
                'metadata': metadata
            })
            
            # Add to total word count
            sections_summary = report.get('sections_summary', {})
            total_word_count += sections_summary.get('word_count_estimate', 0)
        
        # Create consolidated report structure
        consolidated_content = create_consolidated_content(all_sections, report_type, format_style)
        
        # Create consolidated metadata
        consolidated_metadata = create_consolidated_metadata(
            combined_metadata, report_type, format_style, len(successful_reports)
        )
        
        return {
            'report_content': consolidated_content,
            'individual_sources': [r['filename'] for r in successful_reports],
            'metadata': consolidated_metadata,
            'consolidation_summary': {
                'source_files': len(successful_reports),
                'total_sections': len(all_sections),
                'estimated_word_count': total_word_count,
                'report_type': report_type,
                'format_style': format_style
            }
        }
        
    except Exception as e:
        log.error(f"Error consolidating reports: {str(e)}")
        return {
            'error': f'Consolidation failed: {str(e)}',
            'report_content': create_error_report(),
            'metadata': create_default_metadata(report_type, format_style)
        }


def create_consolidated_content(all_sections, report_type, format_style):
    """Create consolidated report content from multiple sources."""
    
    consolidated_sections = {}
    
    # Define section priority order
    section_priority = {
        'executive_summary': 1,
        'abstract': 1,
        'introduction': 2,
        'main_section_1': 3,
        'main_section_2': 4,
        'main_section_3': 5,
        'analysis': 6,
        'conclusions': 7,
        'references': 8,
        'appendices': 9
    }
    
    # Sort sections by priority
    sorted_sections = sorted(all_sections.items(), 
                           key=lambda x: section_priority.get(x[0], 99))
    
    for section_key, section_data in sorted_sections:
        # Combine content from multiple sources
        combined_text = ""
        source_attribution = []
        
        for content_item in section_data['combined_content']:
            source_file = content_item['source_file']
            content = content_item['content']
            
            if content:
                combined_text += f"\n\n### From {source_file}:\n{content}"
                source_attribution.append(source_file)
        
        # Create consolidated section
        consolidated_sections[section_key] = {
            'title': section_data['title'],
            'content': combined_text.strip(),
            'source_files': list(set(source_attribution)),
            'section_type': section_data['section_type'],
            'word_count': len(combined_text.split())
        }
    
    return {
        'title': f"Consolidated {report_type.title()} Report",
        'subtitle': f"Multi-Source Analysis - {format_style.title()} Format",
        'generation_date': datetime.now().strftime("%B %d, %Y"),
        'sections': consolidated_sections,
        'document_type': 'consolidated_report'
    }


def create_consolidated_metadata(combined_metadata, report_type, format_style, source_count):
    """Create metadata for consolidated report."""
    
    return {
        'consolidation_info': {
            'source_files': source_count,
            'report_type': report_type,
            'format_style': format_style,
            'consolidated_at': datetime.now().isoformat(),
            'consolidation_method': 'section_based_merge'
        },
        'source_metadata': combined_metadata,
        'quality_indicators': {
            'multi_source_analysis': True,
            'comprehensive_coverage': source_count > 1,
            'professional_formatting': True,
            'structured_sections': True
        }
    }


def create_error_report():
    """Create a basic error report structure."""
    return {
        'title': 'Report Generation Error',
        'sections': {
            'error_summary': {
                'title': 'Error Summary',
                'content': 'Unable to generate report from provided sources.',
                'section_type': 'error'
            }
        }
    }


def create_default_metadata(report_type, format_style):
    """Create default metadata for error cases."""
    return {
        'generation_info': {
            'report_type': report_type,
            'format_style': format_style,
            'status': 'error',
            'generated_at': datetime.now().isoformat()
        },
        'error': True
    }
