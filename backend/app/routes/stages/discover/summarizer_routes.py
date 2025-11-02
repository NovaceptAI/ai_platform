from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.stages.discover.summarizer_service import Summarizer
from app.tasks.summarizer_tasks import summarize_page_batch, process_audio_video_file, process_document_file, process_image_file, process_presentation_file, process_spreadsheet_file
import os
import logging
import tempfile
from app.routes.upload import download_blob_to_tmp
from app.db import db
from app.models import FilePage, UploadedFile, Progress
from app.models.files import FileTimestamp
from uuid import uuid4
from app.utils.file_utils import extract_text_by_pages, detect_file_type, extract_text_from_audio, extract_text_from_video, chunk_audio_segments_by_limits
from math import ceil
from app.models import Progress


# Configure logger
logger = logging.getLogger(__name__)
# logger.info("This is a log message from a blueprint.")

summarizer_bp = Blueprint('summarizer', __name__)
# Create an instance of the Summarizer class
summarizer = Summarizer()

@summarizer_bp.route('/summarize_text', methods=['POST'])
def summarize_text_route():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        logger.info("No text provided in the request")
        return jsonify({"error": "No text provided"}), 400

    logger.info("Received text for summarization")
    summary_data = summarizer._summarize_text(text)
    logger.info("Text summarization completed successfully")
    return jsonify(summary_data)


@summarizer_bp.route('/summarize_file', methods=['POST'])
def summarize_file_route():
    try:
        # 1. Extract file
        if request.is_json:
            data = request.get_json()
            filename = data.get('filename')
            logger.info(f"Received filename: {filename}")
            from_vault = data.get('fromVault', False)
            if not filename or not from_vault:
                return jsonify({"error": "Missing filename or vault flag"}), 400
            file_path = download_blob_to_tmp(filename)

        elif 'file' in request.files:
            file = request.files['file']
            file_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(file_path)

        else:
            return jsonify({"error": "No valid file provided"}), 400


        # 2. DB lookup
        uploaded_file = db.session.query(UploadedFile).filter_by(stored_file_name=filename).first()
        if not uploaded_file:
            return jsonify({"error": "Uploaded file not found in DB"}), 404

        # 3. Create progress tracker
        progress = Progress(
            id=uuid4(),
            user_id=uploaded_file.user_id,
            file_id=uploaded_file.id,
            status='queued',
            tool='summarizer',
        )
        db.session.add(progress)
        db.session.commit()

        existing_pages = db.session.query(FilePage).filter_by(file_id=uploaded_file.id).all()

        if existing_pages:
            # File already processed, just run summarization
            progress.status = 'in_progress'
            db.session.commit()
            
            processed_pages = existing_pages
            for chunk in chunk_list(existing_pages, 5):
                valid_ids = [str(p.id) for p in chunk if p.page_text and not p.page_summary]
                if valid_ids:
                    summarize_page_batch.delay(valid_ids, str(progress.id))

        else:
            # New file - delegate processing to Celery
            file_type = detect_file_type(file_path)
            
            if file_type in ["audio", "video"]:
                # Delegate audio/video processing to Celery
                progress.status = 'processing_media'
                db.session.commit()
                
                task_result = process_audio_video_file.delay(
                    file_path, 
                    str(uploaded_file.id), 
                    str(progress.id)
                )
                
                return jsonify({
                    "message": "Audio/video file queued for processing",
                    "file_id": str(uploaded_file.id),
                    "progress_id": str(progress.id),
                    "task_id": task_result.id,
                    "estimated_time": "2-5 minutes for transcription + summarization"
                })
                
            elif file_type == "document":
                # Delegate document processing to Celery  
                progress.status = 'processing_document'
                db.session.commit()
                
                task_result = process_document_file.delay(
                    file_path,
                    str(uploaded_file.id),
                    str(progress.id)
                )
                
                return jsonify({
                    "message": "Document file queued for processing", 
                    "file_id": str(uploaded_file.id),
                    "progress_id": str(progress.id),
                    "task_id": task_result.id,
                    "estimated_time": "30 seconds to 2 minutes"
                })
                
            elif file_type == "image":
                # Delegate image processing to Celery
                progress.status = 'processing_image'
                db.session.commit()
                
                task_result = process_image_file.delay(
                    file_path,
                    str(uploaded_file.id),
                    str(progress.id)
                )
                
                return jsonify({
                    "message": "Image file queued for processing", 
                    "file_id": str(uploaded_file.id),
                    "progress_id": str(progress.id),
                    "task_id": task_result.id,
                    "estimated_time": "30 seconds to 1 minute"
                })
                
            elif file_type == "presentation":
                # Delegate PowerPoint processing to Celery
                progress.status = 'processing_presentation'
                db.session.commit()
                
                task_result = process_presentation_file.delay(
                    file_path,
                    str(uploaded_file.id),
                    str(progress.id)
                )
                
                return jsonify({
                    "message": "Presentation file queued for processing", 
                    "file_id": str(uploaded_file.id),
                    "progress_id": str(progress.id),
                    "task_id": task_result.id,
                    "estimated_time": "30 seconds to 1 minute"
                })
                
            elif file_type == "spreadsheet":
                # Delegate Excel processing to Celery
                progress.status = 'processing_spreadsheet'
                db.session.commit()
                
                task_result = process_spreadsheet_file.delay(
                    file_path,
                    str(uploaded_file.id),
                    str(progress.id)
                )
                
                return jsonify({
                    "message": "Spreadsheet file queued for processing", 
                    "file_id": str(uploaded_file.id),
                    "progress_id": str(progress.id),
                    "task_id": task_result.id,
                    "estimated_time": "30 seconds to 1 minute"
                })
                
            else:
                return jsonify({"error": f"Unsupported file type: {file_type}"}), 400

        # This is only reached for existing files (re-summarization)
        return jsonify({
            "message": f"Re-processing {len(processed_pages)} existing pages in background",
            "file_id": str(uploaded_file.id),
            "progress_id": str(progress.id)
        })

    except Exception as e:
        db.session.rollback()
        logger.exception("Summarization route failed")
        return jsonify({"error": "Internal server error"}), 500



@summarizer_bp.route('/export_segments', methods=['POST'])
def export_segments_route():
    data = request.get_json()
    segments = data.get('segments', [])
    format = data.get('format', 'json')
    
    if not segments:
        logger.info("No segments provided in the request")
        return jsonify({"error": "No segments provided"}), 400

    logger.info(f"Exporting segments in {format} format")
    try:
        exported_data = summarizer._export_segments(segments, format)
        logger.info("Segments exported successfully")
    except ValueError as e:
        logger.error(f"Error during segment export: {e}")
        return jsonify({"error": str(e)}), 400

    return jsonify({"exported_data": exported_data})


# @summarizer_bp.route('/progress/<file_id>', methods=['GET'])
# def summarization_progress(file_id):
#     try:
#         uploaded_file = db.session.query(UploadedFile).filter_by(id=file_id).first()
#         if not uploaded_file:
#             return jsonify({"error": "File not found"}), 404

#         total_pages = uploaded_file.total_pages or 0
#         summarized_count = db.session.query(FilePage).filter(
#             FilePage.file_id == file_id,
#             FilePage.page_summary.isnot(None)
#         ).count()

#         return jsonify({
#             "file_id": str(file_id),
#             "total_pages": total_pages,
#             "pages_summarized": summarized_count,
#             "percentage": int((summarized_count / total_pages) * 100) if total_pages else 0
#         })

#     except Exception as e:
#         logger.exception("Error fetching progress")
#         return jsonify({"error": "Internal server error"}), 500


@summarizer_bp.route('/results', methods=['GET'])
@jwt_required()
def summarizer_results():
    """Get summarizer results for a specific file"""
    try:
        file_id = request.args.get('file_id')
        if not file_id:
            return jsonify({"error": "file_id parameter is required"}), 400
            
        user_id = get_jwt_identity()
        
        # Verify file belongs to user
        uploaded_file = db.session.query(UploadedFile).filter(
            UploadedFile.id == file_id,
            UploadedFile.user_id == user_id
        ).first()
        
        if not uploaded_file:
            return jsonify({"error": "File not found"}), 404
            
        # Get summary results
        pages = db.session.query(FilePage).filter_by(file_id=file_id).order_by(FilePage.page_number).all()
        
        if not pages:
            return jsonify({"error": "No summary results found"}), 404
            
        # Format results
        results = {
            "file_id": file_id,
            "file_name": uploaded_file.original_file_name,
            "total_pages": len(pages),
            "summaries": []
        }
        
        for page in pages:
            if page.page_summary:
                results["summaries"].append({
                    "page_number": page.page_number,
                    "summary": page.page_summary,
                    "created_at": page.created_at.isoformat() if page.created_at else None
                })
                
        return jsonify(results), 200
        
    except Exception as e:
        logger.exception("Error fetching summarizer results")
        return jsonify({"error": "Internal server error"}), 500

@summarizer_bp.route('/get_summary/<file_id>', methods=['GET'])
def get_summarized_file(file_id):
    try:
        # Get the uploaded file to check its type
        uploaded_file = db.session.query(UploadedFile).filter_by(id=file_id).first()
        if not uploaded_file:
            return jsonify({"error": "File not found"}), 404

        pages = db.session.query(FilePage).filter_by(file_id=file_id).order_by(FilePage.page_number).all()
        if not pages:
            return jsonify({"error": "No pages found"}), 404

        # Determine if this is audio/video by checking file extension
        file_extension = uploaded_file.original_file_name.split('.')[-1].lower()
        is_audio_video = file_extension in ['mp3', 'wav', 'm4a', 'mp4', 'avi', 'mov']

        response = {
            "file_id": file_id,
            "file_type": "audio_video" if is_audio_video else "document",
            "has_timestamps": is_audio_video,
            "pages": []
        }
        
        for page in pages:
            if page.page_summary:
                page_data = {
                    "page_number": page.page_number,
                    "summary": page.page_summary,
                    "text": page.page_text
                }
                
                # Add timestamp information if this is audio/video
                if is_audio_video:
                    # Get timestamp data for this page
                    timestamps = db.session.query(FileTimestamp).filter_by(
                        page_id=page.id
                    ).order_by(FileTimestamp.sequence_number).all()
                    
                    if timestamps:
                        # Page-level timing (overall start/end for the chunk)
                        page_data.update({
                            "start_time": timestamps[0].start_time,
                            "end_time": timestamps[-1].end_time,
                            "start_seconds": timestamps[0].start_seconds,
                            "end_seconds": timestamps[-1].end_seconds,
                            "total_duration": timestamps[-1].end_seconds - timestamps[0].start_seconds,
                            "segment_count": len(timestamps)
                        })
                
                response["pages"].append(page_data)
        
        return jsonify(response)

    except Exception as e:
        logger.exception("Error fetching summary")
        return jsonify({"error": "Internal server error"}), 500


@summarizer_bp.route('/progress/<progress_id>', methods=['GET'])
def summarization_progress(progress_id):
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress ID not found"}), 404

        uploaded_file = db.session.query(UploadedFile).filter_by(id=progress.file_id).first()
        if not uploaded_file:
            return jsonify({"error": "File not found"}), 404

        total_pages = uploaded_file.total_pages or 0
        summarized_count = db.session.query(FilePage).filter(
            FilePage.file_id == uploaded_file.id,
            FilePage.page_summary.isnot(None)
        ).count()

        # Calculate percentage
        percentage = int((summarized_count / total_pages) * 100) if total_pages else 0

        # ✅ Update percentage and status in the DB if changed
        if progress.percentage != percentage:
            progress.percentage = percentage

        if total_pages > 0 and summarized_count == total_pages and progress.status != "done":
            progress.status = "done"

        db.session.commit()

        return jsonify({
            "progress_id": str(progress.id),
            "file_id": str(uploaded_file.id),
            "status": progress.status,
            "total_pages": total_pages,
            "pages_summarized": summarized_count,
            "percentage": percentage
        })

    except Exception as e:
        logger.exception("Error fetching progress")
        return jsonify({"error": "Internal server error"}), 500

@summarizer_bp.route('/get_transcript/<file_id>', methods=['GET'])
def get_transcript(file_id):
    """Get full transcript with timestamps for audio/video files"""
    try:
        # Check if this is an audio/video file
        uploaded_file = db.session.query(UploadedFile).filter_by(id=file_id).first()
        if not uploaded_file:
            return jsonify({"error": "File not found"}), 404

        file_extension = uploaded_file.original_file_name.split('.')[-1].lower()
        is_audio_video = file_extension in ['mp3', 'wav', 'm4a', 'mp4', 'avi', 'mov']
        
        if not is_audio_video:
            return jsonify({"error": "This file doesn't have timestamp data (not audio/video)"}), 400

        # Get all timestamp records for this file
        timestamps = db.session.query(FileTimestamp).filter_by(
            file_id=file_id
        ).order_by(FileTimestamp.sequence_number).all()
        
        if not timestamps:
            return jsonify({"error": "No timestamp data found"}), 404

        # Get pages for grouping
        pages = db.session.query(FilePage).filter_by(file_id=file_id).order_by(FilePage.page_number).all()

        transcript_segments = []
        page_groups = []
        full_text = ""
        
        # Group timestamps by page
        for page in pages:
            page_timestamps = [t for t in timestamps if t.page_id == page.id]
            
            page_group = {
                "page_number": page.page_number,
                "page_text": page.page_text,
                "start_time": page_timestamps[0].start_time if page_timestamps else None,
                "end_time": page_timestamps[-1].end_time if page_timestamps else None,
                "segments": []
            }
            
            for timestamp in page_timestamps:
                segment = {
                    "sequence": timestamp.sequence_number,
                    "text": timestamp.original_text,
                    "start_time": timestamp.start_time,
                    "end_time": timestamp.end_time,
                    "start_seconds": timestamp.start_seconds,
                    "end_seconds": timestamp.end_seconds,
                    "duration": timestamp.duration
                }
                transcript_segments.append(segment)
                page_group["segments"].append(segment)
                full_text += timestamp.original_text + " "
            
            if page_timestamps:
                page_groups.append(page_group)

        response = {
            "file_id": file_id,
            "file_name": uploaded_file.original_file_name,
            "full_text": full_text.strip(),
            "total_segments": len(transcript_segments),
            "total_pages": len(page_groups),
            "total_duration": max([t.end_seconds for t in timestamps]) if timestamps else 0,
            "segments": transcript_segments,
            "page_groups": page_groups
        }
        
        return jsonify(response)

    except Exception as e:
        logger.exception("Error fetching transcript")
        return jsonify({"error": "Internal server error"}), 500


@summarizer_bp.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a Celery task"""
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'state': task_result.state,
                'status': 'Task is waiting to be processed'
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'state': task_result.state,
                'status': task_result.info.get('status', 'Processing...'),
                'progress': task_result.info
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'state': task_result.state,
                'status': 'Task completed successfully',
                'result': task_result.result
            }
        else:
            # FAILURE or other states
            response = {
                'state': task_result.state,
                'status': str(task_result.info),
                'error': True
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.exception("Error fetching task status")
        return jsonify({"error": "Internal server error"}), 500


def chunk_list(lst, chunk_size):
    """Utility to chunk list into groups of n."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]