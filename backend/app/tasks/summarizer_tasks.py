# from app.main import celery_app
from celery import shared_task
from app.services.stages.discover.summarizer_service import Summarizer
from app.db import db
from app.models import FilePage, Progress
from app.models.files import FileTimestamp, UploadedFile
from celery.utils.log import get_task_logger
from celery import states, group
from celery.exceptions import Ignore
from math import ceil
from uuid import UUID, uuid4
from app.utils.file_utils import detect_file_type, extract_text_from_audio, extract_text_from_video, chunk_audio_segments_by_limits, extract_text_by_pages, extract_text_from_image, extract_text_from_presentation, extract_text_from_spreadsheet, analyze_image_content
import os
import gc

logger = get_task_logger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

@shared_task(bind=True, max_retries=3, default_retry_delay=30, acks_late=True, 
              soft_time_limit=1800, time_limit=2400)  # 30 min soft, 40 min hard limit
def process_audio_video_file(self, file_path, file_id, progress_id):
    """
    Process audio/video files asynchronously with memory optimization:
    1. Extract audio/video and transcribe (with chunking for large files)
    2. Chunk into pages with time/word limits
    3. Create FilePage and FileTimestamp records
    4. Kick off summarization tasks
    """
    import gc
    
    session = db.session()
    
    # Monitor memory usage if psutil is available
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        initial_memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Task started with {initial_memory_mb:.1f}MB memory usage")
    else:
        logger.info("Task started (memory monitoring unavailable)")
    
    try:
        # Update progress
        progress = session.query(Progress).get(progress_id)
        if progress:
            progress.status = "processing_media"
            session.commit()
        
        # Get file record
        uploaded_file = session.query(UploadedFile).get(file_id)
        if not uploaded_file:
            raise ValueError(f"File {file_id} not found in database")
        
        # Check file size before processing
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"Starting audio/video processing for file {file_id} ({file_size_mb:.1f}MB)")
        
        # Detect file type and extract content
        file_type = detect_file_type(file_path)
        
        # Memory checkpoint
        if PSUTIL_AVAILABLE:
            current_memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Memory before transcription: {current_memory_mb:.1f}MB")
        
        if file_type == "audio":
            transcription_data = extract_text_from_audio(file_path)
        elif file_type == "video":
            transcription_data = extract_text_from_video(file_path)
        else:
            raise ValueError(f"Expected audio/video file, got {file_type}")
        
        # Force garbage collection after transcription
        gc.collect()
        
        # Memory checkpoint
        if PSUTIL_AVAILABLE:
            current_memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Memory after transcription: {current_memory_mb:.1f}MB")
        
        # Get original segments from transcription
        original_segments = transcription_data['segments']
        logger.info(f"Extracted {len(original_segments)} segments from {file_type} file")
        
        # Check if this was chunked processing
        if 'total_chunks_processed' in transcription_data:
            logger.info(f"Large file processed in {transcription_data['total_chunks_processed']} chunks")
        
        # Chunk segments into pages based on time/word limits
        page_chunks = chunk_audio_segments_by_limits(original_segments)
        logger.info(f"Created {len(page_chunks)} page chunks")
        
        # Update file record
        uploaded_file.total_pages = len(page_chunks)
        uploaded_file.status = "transcribed"
        session.commit()
        
        # Create FilePage and FileTimestamp records
        new_page_ids = []
        for i, chunk in enumerate(page_chunks, start=1):
            # Create FilePage with combined text from chunk
            file_page = FilePage(
                id=uuid4(),
                file_id=uploaded_file.id,
                page_number=i,
                page_text=chunk['text'].strip()
            )
            session.add(file_page)
            session.flush()  # Get the page ID
            
            # Create FileTimestamp records for each original segment in this chunk
            for segment in chunk['segments']:
                timestamp_record = FileTimestamp(
                    id=uuid4(),
                    file_id=uploaded_file.id,
                    page_id=file_page.id,
                    sequence_number=segment['sequence'],
                    start_time=segment['start'],
                    end_time=segment['end'],
                    start_seconds=segment['start_seconds'],
                    end_seconds=segment['end_seconds'],
                    duration=segment['duration'],
                    original_text=segment['text']
                )
                session.add(timestamp_record)
            
            new_page_ids.append(str(file_page.id))
        
        session.commit()
        logger.info(f"Created {len(new_page_ids)} pages and timestamp records")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update progress
        if progress:
            progress.status = "ready_for_summarization"
            session.commit()
        
        # Now kick off summarization tasks
        chunk_size = 5
        page_chunks_for_summary = [new_page_ids[i:i+chunk_size] for i in range(0, len(new_page_ids), chunk_size)]
        
        for idx, chunk in enumerate(page_chunks_for_summary):
            summarize_page_batch.apply_async(
                args=[chunk, progress_id], 
                countdown=idx * 5  # Stagger by 5 seconds
            )
        
        logger.info(f"Scheduled {len(page_chunks_for_summary)} summarization batches")
        
        return {
            "file_id": str(file_id),
            "pages_created": len(new_page_ids),
            "summarization_batches": len(page_chunks_for_summary),
            "status": "summarization_started"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Audio/video processing failed for file {file_id}: {e}")
        
        # Update progress to failed
        try:
            progress = session.query(Progress).get(progress_id)
            if progress:
                progress.status = "failed"
                progress.error_message = str(e)
                session.commit()
        except Exception:
            pass
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            countdown = min(300, 30 * (2 ** self.request.retries))  # Max 5 minutes
            logger.info(f"Retrying audio/video processing in {countdown}s")
            raise self.retry(exc=e, countdown=countdown)
        
        raise
    finally:
        session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10, acks_late=True)
def process_document_file(self, file_path, file_id, progress_id):
    """
    Process document files (PDF, DOCX, TXT) asynchronously.
    This maintains consistency with audio/video processing flow.
    """
    session = db.session()
    
    try:
        # Update progress
        progress = session.query(Progress).get(progress_id)
        if progress:
            progress.status = "processing_document"
            session.commit()
        
        # Get file record
        uploaded_file = session.query(UploadedFile).get(file_id)
        if not uploaded_file:
            raise ValueError(f"File {file_id} not found in database")
        
        logger.info(f"Starting document processing for file {file_id}")
        
        # Extract text by pages
        pages = extract_text_by_pages(file_path)
        pages = [p for p in pages if p.strip()]  # Skip empty
        
        # Update file record
        uploaded_file.total_pages = len(pages)
        uploaded_file.status = "processed"
        session.commit()
        
        # Create FilePage records
        new_page_ids = []
        for i, page_text in enumerate(pages, start=1):
            file_page = FilePage(
                id=uuid4(),
                file_id=uploaded_file.id,
                page_number=i,
                page_text=page_text
            )
            session.add(file_page)
            session.flush()
            new_page_ids.append(str(file_page.id))
        
        session.commit()
        logger.info(f"Created {len(new_page_ids)} pages for document")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update progress
        if progress:
            progress.status = "ready_for_summarization"
            session.commit()
        
        # Kick off summarization tasks
        chunk_size = 5
        page_chunks = [new_page_ids[i:i+chunk_size] for i in range(0, len(new_page_ids), chunk_size)]
        
        for idx, chunk in enumerate(page_chunks):
            summarize_page_batch.apply_async(
                args=[chunk, progress_id], 
                countdown=idx * 2  # Stagger by 2 seconds
            )
        
        logger.info(f"Scheduled {len(page_chunks)} summarization batches")
        
        return {
            "file_id": str(file_id),
            "pages_created": len(new_page_ids),
            "summarization_batches": len(page_chunks),
            "status": "summarization_started"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Document processing failed for file {file_id}: {e}")
        
        # Update progress to failed
        try:
            progress = session.query(Progress).get(progress_id)
            if progress:
                progress.status = "failed"
                progress.error_message = str(e)
                session.commit()
        except Exception:
            pass
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if self.request.retries < self.max_retries:
            countdown = min(60, 10 * (2 ** self.request.retries))
            logger.info(f"Retrying document processing in {countdown}s")
            raise self.retry(exc=e, countdown=countdown)
        
        raise
    finally:
        session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10, acks_late=True)
def process_image_file(self, file_path, file_id, progress_id):
    """
    Process image files (JPG, PNG, GIF, BMP, TIFF) asynchronously.
    Uses AWS Textract OCR to extract text from images.
    """
    session = db.session()
    
    try:
        # Update progress
        progress = session.query(Progress).get(progress_id)
        if progress:
            progress.status = "processing_image"
            session.commit()
        
        # Get file record
        uploaded_file = session.query(UploadedFile).get(file_id)
        if not uploaded_file:
            raise ValueError(f"File {file_id} not found in database")
        
        logger.info(f"Starting image processing for file {file_id}")
        
        # Extract text from image using OCR
        try:
            text_chunks = extract_text_from_image(file_path)
        except Exception as e:
            # If OCR fails or no text found, create a fallback message
            error_msg = str(e).lower()
            if "no text detected" in error_msg or "no data found" in error_msg:
                text_chunks = ["No data found in the image"]
                logger.info(f"No text detected in image {file_id}")
            else:
                logger.error(f"OCR failed for image {file_id}: {e}")
                text_chunks = ["No data found - OCR processing failed"]
        
        # Filter out empty chunks and check for meaningful text
        text_chunks = [chunk for chunk in text_chunks if chunk.strip()]
        
        # Check if we only have "no data found" messages or empty results
        has_meaningful_text = any(
            chunk for chunk in text_chunks 
            if chunk.strip() and not any(phrase in chunk.lower() for phrase in [
                "no data found", "no text detected", "ocr processing failed"
            ])
        )
        
        # If no meaningful text found, analyze image content
        if not has_meaningful_text:
            logger.info(f"No meaningful text found in image {file_id}, performing image analysis")
            # Create a temporary copy for analysis since extract_text_from_image deletes the original
            import shutil
            temp_analysis_path = f"{file_path}_analysis"
            try:
                # Check if original file still exists, if not skip analysis
                if os.path.exists(file_path):
                    shutil.copy2(file_path, temp_analysis_path)
                    image_analysis = analyze_image_content(temp_analysis_path)
                    text_chunks = [image_analysis]
                else:
                    text_chunks = ["This image contains no text. Please upload an image containing text for document processing."]
            except Exception as analysis_error:
                logger.warning(f"Image analysis failed for {file_id}: {analysis_error}")
                text_chunks = ["This image contains no text. Please upload an image containing text for document processing."]
            finally:
                # Clean up analysis temp file
                if os.path.exists(temp_analysis_path):
                    os.remove(temp_analysis_path)
        
        # Final fallback if still no chunks
        if not text_chunks:
            text_chunks = ["No data found in the image"]
        
        # Update file record
        uploaded_file.total_pages = len(text_chunks)
        uploaded_file.status = "processed"
        session.commit()
        
        # Create FilePage records
        new_page_ids = []
        for i, text_content in enumerate(text_chunks, start=1):
            file_page = FilePage(
                id=uuid4(),
                file_id=uploaded_file.id,
                page_number=i,
                page_text=text_content
            )
            session.add(file_page)
            session.flush()
            new_page_ids.append(str(file_page.id))
        
        session.commit()
        logger.info(f"Created {len(new_page_ids)} pages for image")
        
        # Clean up temporary file (note: extract_text_from_image already deletes it)
        # but check if it still exists just in case
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update progress
        if progress:
            progress.status = "ready_for_summarization"
            session.commit()
        
        # Kick off summarization tasks (images typically have fewer chunks)
        chunk_size = 3  # Smaller chunks for images since they typically have less text
        page_chunks = [new_page_ids[i:i+chunk_size] for i in range(0, len(new_page_ids), chunk_size)]
        
        for idx, chunk in enumerate(page_chunks):
            summarize_page_batch.apply_async(
                args=[chunk, progress_id], 
                countdown=idx * 1  # Stagger by 1 second for images
            )
        
        logger.info(f"Scheduled {len(page_chunks)} summarization batches for image")
        
        return {
            "file_id": str(file_id),
            "pages_created": len(new_page_ids),
            "summarization_batches": len(page_chunks),
            "status": "summarization_started",
            "text_detected": len(text_chunks) > 0 and text_chunks[0] != "No data found in the image"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Image processing failed for file {file_id}: {e}")
        
        # Update progress to failed
        try:
            progress = session.query(Progress).get(progress_id)
            if progress:
                progress.status = "failed"
                progress.error_message = str(e)
                session.commit()
        except Exception:
            pass
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if self.request.retries < self.max_retries:
            countdown = min(60, 10 * (2 ** self.request.retries))
            logger.info(f"Retrying image processing in {countdown}s")
            raise self.retry(exc=e, countdown=countdown)
        
        raise
    finally:
        session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10, acks_late=True)
def process_presentation_file(self, file_path, file_id, progress_id):
    """
    Process PowerPoint presentation files (.pptx) asynchronously.
    Extracts text from slides and shapes.
    """
    session = db.session()
    
    try:
        # Update progress
        progress = session.query(Progress).get(progress_id)
        if progress:
            progress.status = "processing_presentation"
            session.commit()
        
        # Get file record
        uploaded_file = session.query(UploadedFile).get(file_id)
        if not uploaded_file:
            raise ValueError(f"File {file_id} not found in database")
        
        logger.info(f"Starting presentation processing for file {file_id}")
        
        # Extract text from presentation
        try:
            text_chunks = extract_text_from_presentation(file_path)
        except Exception as e:
            # If extraction fails, create a fallback message
            logger.error(f"Presentation extraction failed for file {file_id}: {e}")
            text_chunks = ["No data found - presentation processing failed"]
        
        # Filter out empty chunks
        text_chunks = [chunk for chunk in text_chunks if chunk.strip()]
        
        # If no valid chunks, use fallback
        if not text_chunks:
            text_chunks = ["No data found in the presentation"]
        
        # Update file record
        uploaded_file.total_pages = len(text_chunks)
        uploaded_file.status = "processed"
        session.commit()
        
        # Create FilePage records
        new_page_ids = []
        for i, text_content in enumerate(text_chunks, start=1):
            file_page = FilePage(
                id=uuid4(),
                file_id=uploaded_file.id,
                page_number=i,
                page_text=text_content
            )
            session.add(file_page)
            session.flush()
            new_page_ids.append(str(file_page.id))
        
        session.commit()
        logger.info(f"Created {len(new_page_ids)} pages for presentation")
        
        # Clean up temporary file (note: extract_text_from_presentation already deletes it)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update progress
        if progress:
            progress.status = "ready_for_summarization"
            session.commit()
        
        # Kick off summarization tasks
        chunk_size = 3  # Smaller chunks for presentations
        page_chunks = [new_page_ids[i:i+chunk_size] for i in range(0, len(new_page_ids), chunk_size)]
        
        for idx, chunk in enumerate(page_chunks):
            summarize_page_batch.apply_async(
                args=[chunk, progress_id], 
                countdown=idx * 1  # Stagger by 1 second
            )
        
        logger.info(f"Scheduled {len(page_chunks)} summarization batches for presentation")
        
        return {
            "file_id": str(file_id),
            "pages_created": len(new_page_ids),
            "summarization_batches": len(page_chunks),
            "status": "summarization_started"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Presentation processing failed for file {file_id}: {e}")
        
        # Update progress to failed
        try:
            progress = session.query(Progress).get(progress_id)
            if progress:
                progress.status = "failed"
                progress.error_message = str(e)
                session.commit()
        except Exception:
            pass
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if self.request.retries < self.max_retries:
            countdown = min(60, 10 * (2 ** self.request.retries))
            logger.info(f"Retrying presentation processing in {countdown}s")
            raise self.retry(exc=e, countdown=countdown)
        
        raise
    finally:
        session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10, acks_late=True)
def process_spreadsheet_file(self, file_path, file_id, progress_id):
    """
    Process Excel spreadsheet files (.xlsx, .xls) asynchronously.
    Extracts text from worksheets and cells.
    """
    session = db.session()
    
    try:
        # Update progress
        progress = session.query(Progress).get(progress_id)
        if progress:
            progress.status = "processing_spreadsheet"
            session.commit()
        
        # Get file record
        uploaded_file = session.query(UploadedFile).get(file_id)
        if not uploaded_file:
            raise ValueError(f"File {file_id} not found in database")
        
        logger.info(f"Starting spreadsheet processing for file {file_id}")
        
        # Extract text from spreadsheet
        try:
            text_chunks = extract_text_from_spreadsheet(file_path)
        except Exception as e:
            # If extraction fails, create a fallback message
            logger.error(f"Spreadsheet extraction failed for file {file_id}: {e}")
            text_chunks = ["No data found - spreadsheet processing failed"]
        
        # Filter out empty chunks
        text_chunks = [chunk for chunk in text_chunks if chunk.strip()]
        
        # If no valid chunks, use fallback
        if not text_chunks:
            text_chunks = ["No data found in the spreadsheet"]
        
        # Update file record
        uploaded_file.total_pages = len(text_chunks)
        uploaded_file.status = "processed"
        session.commit()
        
        # Create FilePage records
        new_page_ids = []
        for i, text_content in enumerate(text_chunks, start=1):
            file_page = FilePage(
                id=uuid4(),
                file_id=uploaded_file.id,
                page_number=i,
                page_text=text_content
            )
            session.add(file_page)
            session.flush()
            new_page_ids.append(str(file_page.id))
        
        session.commit()
        logger.info(f"Created {len(new_page_ids)} pages for spreadsheet")
        
        # Clean up temporary file (note: extract_text_from_spreadsheet already deletes it)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update progress
        if progress:
            progress.status = "ready_for_summarization"
            session.commit()
        
        # Kick off summarization tasks
        chunk_size = 4  # Moderate chunks for spreadsheets
        page_chunks = [new_page_ids[i:i+chunk_size] for i in range(0, len(new_page_ids), chunk_size)]
        
        for idx, chunk in enumerate(page_chunks):
            summarize_page_batch.apply_async(
                args=[chunk, progress_id], 
                countdown=idx * 1  # Stagger by 1 second
            )
        
        logger.info(f"Scheduled {len(page_chunks)} summarization batches for spreadsheet")
        
        return {
            "file_id": str(file_id),
            "pages_created": len(new_page_ids),
            "summarization_batches": len(page_chunks),
            "status": "summarization_started"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Spreadsheet processing failed for file {file_id}: {e}")
        
        # Update progress to failed
        try:
            progress = session.query(Progress).get(progress_id)
            if progress:
                progress.status = "failed"
                progress.error_message = str(e)
                session.commit()
        except Exception:
            pass
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if self.request.retries < self.max_retries:
            countdown = min(60, 10 * (2 ** self.request.retries))
            logger.info(f"Retrying spreadsheet processing in {countdown}s")
            raise self.retry(exc=e, countdown=countdown)
        
        raise
    finally:
        session.close()


CHUNK_SIZE = 8            # tune for your page size & rate limits
STAGGER_SECONDS = 10      # gentle ramp to avoid bursts
logger = get_task_logger(__name__)

# Tip: You can also configure autoretry at the decorator level for specific exceptions
@shared_task(bind=True, max_retries=5, default_retry_delay=10, acks_late=True)
def summarize_page_batch(self, page_ids, progress_id=None):
    """
    Summarize a batch of pages.
    Rotation: Each task instantiates Summarizer(), which selects the next Azure key/base.
    Retries: on RateLimitError or transient errors, Celery retry kicks in with backoff.
    """
    session = db.session()
    summarizer = Summarizer()

    try:
        pages = session.query(FilePage).filter(FilePage.id.in_(page_ids)).all()
        if not pages:
            logger.warning("No pages found for batch.")
            self.update_state(state=states.SUCCESS, meta={"message": "Empty batch"})
            return

        file_id = pages[0].file_id

        for page in pages:
            if page.page_summary:
                logger.info(f"Page {page.id} already summarized. Skipping.")
                continue

            try:
                summary = summarizer._summarize_text(page.page_text)
                page.page_summary = summary
                session.add(page)
                
            except Exception as inner_e:
                logger.error(f"Failed to summarize page {page.id}. Error: {inner_e}")
                
                # Check if this is a content filter error
                if "content_filter" in str(inner_e).lower() or "content management policy" in str(inner_e).lower():
                    logger.warning(f"Content filter error for page {page.id}. Using fallback summary.")
                    # Create a safe fallback summary
                    fallback_summary = f"Content Summary: This page contains text that could not be processed through AI summarization due to content filtering policies. The page appears to contain {len(page.page_text.split())} words. [Automated fallback summary]"
                    page.page_summary = fallback_summary
                    session.add(page)
                    continue
                
                # For other errors, use exponential backoff with jitter
                countdown = min(300, 40 * (2 ** self.request.retries))  # Cap at 5 minutes
                logger.error(f"Retrying page batch in {countdown}s. Retry {self.request.retries + 1}/{self.max_retries}")
                session.rollback()
                raise self.retry(exc=inner_e, countdown=countdown)

        session.commit()

        # Update progress (idempotent)
        total_pages = session.query(FilePage).filter_by(file_id=file_id).count()
        summarized_pages = session.query(FilePage).filter(
            FilePage.file_id == file_id, FilePage.page_summary.isnot(None)
        ).count()
        percent = int((summarized_pages / total_pages) * 100) if total_pages else 0

        progress_record = None
        if progress_id:
            try:
                # Prefer the exact per-batch row
                progress_record = session.get(Progress, UUID(progress_id))
            except Exception:
                progress_record = session.query(Progress).get(progress_id)
        # Fallback for legacy runs (if no progress_id was supplied)
        if not progress_record:
            progress_record = session.query(Progress).filter_by(file_id=file_id).first()
        if progress_record:
            dirty = False
            if progress_record.percentage != percent:
                progress_record.percentage = percent
                dirty = True
            if percent == 100 and progress_record.status != "completed":
                progress_record.status = "completed"
                dirty = True
            if dirty:
                session.add(progress_record)
                session.commit()
            logger.info(f"Progress for file {file_id} updated to {percent}%")

        return {"file_id": file_id, "percent": percent}

    except Exception as e:
        session.rollback()
        logger.error(f"Batch summarization failed: {e}")
        
        # Check if this is a content filter error and handle gracefully
        if "content_filter" in str(e).lower() or "content management policy" in str(e).lower():
            logger.warning(f"Content filter error in batch. Marking pages with fallback summaries.")
            
            # Try to mark remaining pages with fallback summaries
            try:
                for page_id in page_ids:
                    page = session.query(FilePage).get(page_id)
                    if page and not page.page_summary:
                        fallback_summary = f"Content Summary: This page contains text that could not be processed through AI summarization due to content filtering policies. [Automated fallback - Page {page.page_number}]"
                        page.page_summary = fallback_summary
                        session.add(page)
                session.commit()
                logger.info(f"Applied fallback summaries to content-filtered pages")
                return {"file_id": file_id, "status": "completed_with_fallback", "reason": "content_filter"}
            except Exception as fallback_error:
                logger.error(f"Failed to apply fallback summaries: {fallback_error}")
        
        # Re-raise for Celery's retry; if out of retries, mark as failure
        if self.request.retries >= self.max_retries:
            logger.error(f"Max retries ({self.max_retries}) exceeded for batch summarization")
            self.update_state(state=states.FAILURE, meta={"exc": str(e), "retries": self.request.retries})
            raise
        
        # Calculate retry delay with exponential backoff
        countdown = min(300, 40 * (2 ** self.request.retries))
        logger.info(f"Retrying batch in {countdown}s (attempt {self.request.retries + 1}/{self.max_retries})")
        raise self.retry(exc=e, countdown=countdown)
    finally:
        session.close()


@shared_task(bind=True, acks_late=True)
def summarize_file_kickoff(self, file_id: str, progress_id: str):
    """
    Fan-out a file's pages into multiple summarize_page_batch tasks.
    Uses small countdown offsets to avoid rate-limit spikes.
    """
    session = db.session()
    try:
        # 1) Collect all page IDs for this file
        page_ids = [
            pid for (pid,) in session.query(FilePage.id)
                                     .filter(FilePage.file_id == file_id)
                                     .order_by(FilePage.page_number.asc())
                                     .all()
        ]
        if not page_ids:
            # empty file: mark progress completed
            prog = session.query(Progress).get(progress_id)
            if prog:
                prog.percentage = 100
                prog.status = "completed"
                session.add(prog); session.commit()
            return {"file_id": file_id, "percent": 100, "message": "No pages"}

        # 2) Slice into batches
        chunks = [page_ids[i:i+CHUNK_SIZE] for i in range(0, len(page_ids), CHUNK_SIZE)]

        # 3) Schedule batches with light staggering
        for idx, chunk in enumerate(chunks):
            summarize_page_batch.apply_async(args=[chunk, progress_id], countdown=idx * STAGGER_SECONDS)

        # Option A (simple): rely on each page-batch to update Progress (you already do this).
        # Option B (optional): schedule a lightweight polling/finisher to flip 'completed'
        # after the last batch should have finished. Often not needed because your per-batch
        # task already computes Progress percentage.

        return {"file_id": file_id, "scheduled_batches": len(chunks)}

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()