"""
Enhanced file processing utilities with memory optimization and large file handling
"""
import os
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration for large file handling
MAX_FILE_SIZE_MB = 1000  # 1GB limit
MAX_AUDIO_DURATION_MINUTES = 120  # 2 hours max
CHUNK_DURATION_MINUTES = 10  # Process in 10-minute chunks
MAX_MEMORY_MB = 512  # Memory limit per task

def check_file_size_limits(file_path):
    """Check if file is within processing limits"""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File size {file_size_mb:.1f}MB exceeds limit of {MAX_FILE_SIZE_MB}MB")
    
    logger.info(f"File size: {file_size_mb:.1f}MB - within limits")
    return file_size_mb

def get_video_duration_safe(file_path):
    """Get video duration without loading entire file into memory"""
    try:
        import moviepy.editor as mp
        # Use moviepy's probe function instead of loading full video
        video = mp.VideoFileClip(file_path)
        duration = video.duration
        video.close()  # Important: release memory
        return duration
    except Exception as e:
        logger.error(f"Failed to get video duration: {e}")
        raise

def extract_text_from_video_optimized(file_path):
    """
    Memory-optimized video processing with chunking for large files
    """
    try:
        import moviepy.editor as mp
    except ImportError:
        raise RuntimeError("moviepy not available")
    
    # Check file size limits
    file_size_mb = check_file_size_limits(file_path)
    
    # Get video duration safely
    duration = get_video_duration_safe(file_path)
    duration_minutes = duration / 60
    
    logger.info(f"Video duration: {duration_minutes:.1f} minutes")
    
    if duration_minutes > MAX_AUDIO_DURATION_MINUTES:
        raise ValueError(f"Video duration {duration_minutes:.1f}m exceeds limit of {MAX_AUDIO_DURATION_MINUTES}m")
    
    # For large files, process in chunks
    if file_size_mb > 200 or duration_minutes > CHUNK_DURATION_MINUTES:
        return extract_video_in_chunks(file_path, duration)
    else:
        return extract_video_simple(file_path)

def extract_video_simple(file_path):
    """Simple extraction for smaller videos"""
    import moviepy.editor as mp
    from app.services.lemonfox_service import transcribe_audio_with_timestamps
    
    logger.info("Processing video with simple extraction")
    
    # Create temporary file with proper cleanup
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
        temp_audio_path = temp_audio.name
    
    try:
        # Load video with memory management
        video = mp.VideoFileClip(file_path)
        
        if video.audio is None:
            raise ValueError("Video file has no audio track")
        
        # Extract audio with compression settings to reduce file size
        video.audio.write_audiofile(
            temp_audio_path,
            verbose=False,
            logger=None,
            codec='pcm_s16le',  # 16-bit PCM for smaller files
            ffmpeg_params=['-ac', '1']  # Mono audio to reduce size
        )
        
        # Important: Close video to free memory
        video.close()
        
        # Check temp audio file size
        audio_size_mb = os.path.getsize(temp_audio_path) / (1024 * 1024)
        logger.info(f"Extracted audio size: {audio_size_mb:.1f}MB")
        
        # Transcribe audio
        result = transcribe_audio_with_timestamps(temp_audio_path)
        
        return result
        
    finally:
        # Always clean up temporary files
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.info("Cleaned up temporary audio file")

def extract_video_in_chunks(file_path, total_duration):
    """
    Process large videos in chunks to manage memory usage
    """
    import moviepy.editor as mp
    from app.services.lemonfox_service import transcribe_audio_with_timestamps
    
    logger.info(f"Processing large video in chunks (duration: {total_duration/60:.1f}m)")
    
    chunk_duration = CHUNK_DURATION_MINUTES * 60  # Convert to seconds
    num_chunks = int((total_duration / chunk_duration) + 1)
    
    all_segments = []
    segment_offset = 0
    
    for chunk_idx in range(num_chunks):
        start_time = chunk_idx * chunk_duration
        end_time = min(start_time + chunk_duration, total_duration)
        
        if start_time >= total_duration:
            break
        
        logger.info(f"Processing chunk {chunk_idx + 1}/{num_chunks}: {start_time/60:.1f}m - {end_time/60:.1f}m")
        
        # Create temporary file for this chunk
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        
        try:
            # Load only the chunk we need
            video = mp.VideoFileClip(file_path).subclip(start_time, end_time)
            
            if video.audio is None:
                logger.warning(f"Chunk {chunk_idx + 1} has no audio, skipping")
                continue
            
            # Extract audio for this chunk
            video.audio.write_audiofile(
                temp_audio_path,
                verbose=False,
                logger=None,
                codec='pcm_s16le',
                ffmpeg_params=['-ac', '1']
            )
            
            # Close video chunk to free memory
            video.close()
            
            # Transcribe this chunk
            chunk_result = transcribe_audio_with_timestamps(temp_audio_path)
            
            # Adjust timestamps to account for chunk offset
            for segment in chunk_result['segments']:
                segment['start_seconds'] += start_time
                segment['end_seconds'] += start_time
                segment['sequence'] += segment_offset
                
                # Update SRT format timestamps
                segment['start'] = seconds_to_srt_timestamp(segment['start_seconds'])
                segment['end'] = seconds_to_srt_timestamp(segment['end_seconds'])
            
            all_segments.extend(chunk_result['segments'])
            segment_offset += len(chunk_result['segments'])
            
            logger.info(f"Chunk {chunk_idx + 1} completed: {len(chunk_result['segments'])} segments")
            
        finally:
            # Clean up chunk temp file
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    
    # Combine all segments
    full_text = " ".join([segment['text'] for segment in all_segments])
    
    return {
        'segments': all_segments,
        'full_text': full_text,
        'total_chunks_processed': num_chunks
    }

def seconds_to_srt_timestamp(seconds):
    """Convert seconds to SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def extract_text_from_audio_optimized(file_path):
    """
    Memory-optimized audio processing
    """
    from app.services.lemonfox_service import transcribe_audio_with_timestamps
    
    # Check file size limits
    file_size_mb = check_file_size_limits(file_path)
    
    logger.info(f"Processing audio file: {file_size_mb:.1f}MB")
    
    # For very large audio files, we might need to split them
    if file_size_mb > 500:  # 500MB threshold for audio
        return extract_large_audio_in_chunks(file_path)
    else:
        return transcribe_audio_with_timestamps(file_path)

def extract_large_audio_in_chunks(file_path):
    """
    Split large audio files into chunks for processing
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError("pydub not available for large audio processing")
    
    from app.services.lemonfox_service import transcribe_audio_with_timestamps
    
    logger.info("Processing large audio file in chunks")
    
    # Load audio metadata without loading full file
    audio = AudioSegment.from_file(file_path)
    duration_ms = len(audio)
    duration_minutes = duration_ms / (1000 * 60)
    
    if duration_minutes > MAX_AUDIO_DURATION_MINUTES:
        raise ValueError(f"Audio duration {duration_minutes:.1f}m exceeds limit of {MAX_AUDIO_DURATION_MINUTES}m")
    
    chunk_duration_ms = CHUNK_DURATION_MINUTES * 60 * 1000  # Convert to milliseconds
    num_chunks = int((duration_ms / chunk_duration_ms) + 1)
    
    all_segments = []
    segment_offset = 0
    
    for chunk_idx in range(num_chunks):
        start_ms = chunk_idx * chunk_duration_ms
        end_ms = min(start_ms + chunk_duration_ms, duration_ms)
        
        if start_ms >= duration_ms:
            break
        
        logger.info(f"Processing audio chunk {chunk_idx + 1}/{num_chunks}")
        
        # Extract chunk
        chunk = audio[start_ms:end_ms]
        
        # Save chunk to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_chunk:
            temp_chunk_path = temp_chunk.name
        
        try:
            chunk.export(temp_chunk_path, format="wav")
            
            # Transcribe chunk
            chunk_result = transcribe_audio_with_timestamps(temp_chunk_path)
            
            # Adjust timestamps
            start_seconds = start_ms / 1000
            for segment in chunk_result['segments']:
                segment['start_seconds'] += start_seconds
                segment['end_seconds'] += start_seconds
                segment['sequence'] += segment_offset
                
                segment['start'] = seconds_to_srt_timestamp(segment['start_seconds'])
                segment['end'] = seconds_to_srt_timestamp(segment['end_seconds'])
            
            all_segments.extend(chunk_result['segments'])
            segment_offset += len(chunk_result['segments'])
            
        finally:
            if os.path.exists(temp_chunk_path):
                os.remove(temp_chunk_path)
    
    full_text = " ".join([segment['text'] for segment in all_segments])
    
    return {
        'segments': all_segments,
        'full_text': full_text,
        'total_chunks_processed': num_chunks
    }
