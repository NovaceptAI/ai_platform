import requests
import re
import logging
import os
import json
import time
import traceback
import tempfile
from collections import Counter

logger = logging.getLogger(__name__)

# Complete list of supported languages by LemonFox AI
SUPPORTED_LANGUAGES = {
    'english', 'chinese', 'german', 'spanish', 'russian', 'korean', 'french', 'japanese', 
    'portuguese', 'turkish', 'polish', 'catalan', 'dutch', 'arabic', 'swedish', 'italian', 
    'indonesian', 'hindi', 'finnish', 'vietnamese', 'hebrew', 'ukrainian', 'greek', 'malay', 
    'czech', 'romanian', 'danish', 'hungarian', 'tamil', 'norwegian', 'thai', 'urdu', 
    'croatian', 'bulgarian', 'lithuanian', 'latin', 'maori', 'malayalam', 'welsh', 'slovak', 
    'telugu', 'persian', 'latvian', 'bengali', 'serbian', 'azerbaijani', 'slovenian', 
    'kannada', 'estonian', 'macedonian', 'breton', 'basque', 'icelandic', 'armenian', 
    'nepali', 'mongolian', 'bosnian', 'kazakh', 'albanian', 'swahili', 'galician', 'marathi', 
    'punjabi', 'sinhala', 'khmer', 'shona', 'yoruba', 'somali', 'afrikaans', 'occitan', 
    'georgian', 'belarusian', 'tajik', 'sindhi', 'gujarati', 'amharic', 'yiddish', 'lao', 
    'uzbek', 'faroese', 'haitian creole', 'pashto', 'turkmen', 'nynorsk', 'maltese', 
    'sanskrit', 'luxembourgish', 'myanmar', 'tibetan', 'tagalog', 'malagasy', 'assamese', 
    'tatar', 'hawaiian', 'lingala', 'hausa', 'bashkir', 'javanese', 'sundanese', 'cantonese', 
    'burmese', 'valencian', 'flemish', 'haitian', 'letzeburgesch', 'pushto', 'panjabi', 
    'moldavian', 'moldovan', 'sinhalese', 'castilian', 'mandarin'
}

# Language aliases (some languages have multiple names)
LANGUAGE_ALIASES = {
    'mandarin': 'chinese',
    'cantonese': 'chinese', 
    'castilian': 'spanish',
    'valencian': 'catalan',
    'flemish': 'dutch',
    'panjabi': 'punjabi',
    'pushto': 'pashto',
    'sinhalese': 'sinhala',
    'moldavian': 'romanian',
    'moldovan': 'romanian',
    'letzeburgesch': 'luxembourgish'
}

def normalize_language(language):
    """Normalize language name to primary variant"""
    language = language.lower().strip()
    return LANGUAGE_ALIASES.get(language, language)

def detect_audio_language_segments(temp_audio_path, chunk_duration=30):
    """
    Detect language by analyzing multiple segments of the audio.
    Returns language distribution and confidence scores.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        logger.warning("[LemonFox] pydub not available for segment analysis. Using full file detection.")
        return detect_audio_language_simple(temp_audio_path)
    
    logger.info(f"[LemonFox] Analyzing audio segments for language detection: {temp_audio_path}")
    
    # Load audio and get duration
    audio = AudioSegment.from_file(temp_audio_path)
    duration_seconds = len(audio) / 1000
    
    # If audio is short, just analyze the whole thing
    if duration_seconds <= chunk_duration:
        return detect_audio_language_simple(temp_audio_path)
    
    # Analyze multiple segments throughout the audio
    num_segments = min(5, int(duration_seconds / chunk_duration))  # Max 5 segments
    segment_duration_ms = int((duration_seconds * 1000) / num_segments)
    
    language_detections = []
    
    for i in range(num_segments):
        start_ms = i * segment_duration_ms
        end_ms = min(start_ms + (chunk_duration * 1000), len(audio))
        
        # Extract segment
        segment = audio[start_ms:end_ms]
        
        # Save segment to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_segment:
            temp_segment_path = temp_segment.name
        
        try:
            segment.export(temp_segment_path, format="wav")
            
            # Detect language for this segment
            detection_result = detect_audio_language_simple(temp_segment_path)
            if detection_result:
                language_detections.append(detection_result)
                
            logger.info(f"[LemonFox] Segment {i+1}/{num_segments}: {detection_result}")
            
        finally:
            if os.path.exists(temp_segment_path):
                os.remove(temp_segment_path)
    
    # Analyze results
    if not language_detections:
        logger.warning("[LemonFox] No language detections from segments. Using English fallback.")
        return {'primary_language': 'english', 'confidence': 0.5, 'languages': {'english': 1.0}}
    
    # Count language occurrences
    language_counts = Counter()
    total_confidence = 0
    
    for detection in language_detections:
        lang = detection.get('primary_language', 'english')
        conf = detection.get('confidence', 0.5)
        language_counts[lang] += conf
        total_confidence += conf
    
    # Normalize to get percentages
    language_percentages = {}
    for lang, count in language_counts.items():
        language_percentages[lang] = count / total_confidence if total_confidence > 0 else 0
    
    # Determine primary language
    primary_language = language_counts.most_common(1)[0][0] if language_counts else 'english'
    primary_confidence = language_percentages.get(primary_language, 0.5)
    
    result = {
        'primary_language': primary_language,
        'confidence': primary_confidence,
        'languages': language_percentages,
        'is_multilingual': len(language_counts) > 1 and max(language_percentages.values()) < 0.8
    }
    
    logger.info(f"[LemonFox] Language analysis result: {result}")
    return result

def detect_audio_language_simple(temp_audio_path):
    """
    Simple language detection using LemonFox API.
    """
    url = "https://api.lemonfox.ai/v1/audio/language-detection"
    headers = {
        "Authorization": "Bearer rk61hEoE7P1WYvymUqCsIicLySY4KUYj"
    }
    
    try:
        file_size = os.path.getsize(temp_audio_path) if os.path.exists(temp_audio_path) else 0
        logger.info(f"[LemonFox] Detecting language for: {temp_audio_path} (size: {file_size} bytes)")
        
        with open(temp_audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            response = requests.post(url, headers=headers, files=files, timeout=120)
        
        logger.info(f"[LemonFox] Language detection response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                detected_language = normalize_language(result.get('language', 'english'))
                confidence = float(result.get('confidence', 0.5))
                
                # Validate detected language
                if detected_language not in SUPPORTED_LANGUAGES:
                    logger.warning(f"[LemonFox] Unsupported language detected: {detected_language}. Using English fallback.")
                    detected_language = 'english'
                    confidence = 0.5
                
                logger.info(f"[LemonFox] Detected language: {detected_language} (confidence: {confidence:.2f})")
                
                return {
                    'primary_language': detected_language,
                    'confidence': confidence,
                    'languages': {detected_language: 1.0}
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"[LemonFox] Failed to parse language detection response: {e}")
                
        else:
            logger.warning(f"[LemonFox] Language detection failed [{response.status_code}]: {response.text}")
            
    except Exception as e:
        logger.warning(f"[LemonFox] Language detection error: {e}")
    
    # Fallback to English
    return {
        'primary_language': 'english',
        'confidence': 0.5,
        'languages': {'english': 1.0}
    }

def transcribe_multiingual_audio(temp_audio_path, language_info):
    """
    Handle multilingual transcription based on language analysis.
    """
    primary_language = language_info['primary_language']
    is_multilingual = language_info.get('is_multilingual', False)
    confidence = language_info.get('confidence', 0.5)
    
    logger.info(f"[LemonFox] Transcribing audio - Primary: {primary_language}, Multilingual: {is_multilingual}, Confidence: {confidence:.2f}")
    
    # Strategy 1: High confidence in single language
    if confidence > 0.7 and not is_multilingual:
        logger.info(f"[LemonFox] High confidence single language transcription: {primary_language}")
        srt_content, used_language = transcribe_audio_single_language(temp_audio_path, primary_language)
        return {
            'srt_content': srt_content,
            'primary_language': used_language,
            'transcription_strategy': 'primary_language',
            'language_analysis': language_info
        }
    
    # Strategy 2: Multilingual or low confidence - try primary language first
    elif is_multilingual or confidence < 0.7:
        logger.info(f"[LemonFox] Multilingual/uncertain content detected. Trying multiple approaches.")
        
        # Try primary language first
        try:
            srt_content, used_language = transcribe_audio_single_language(temp_audio_path, primary_language)
            return {
                'srt_content': srt_content,
                'primary_language': used_language,
                'transcription_strategy': 'primary_language',
                'language_analysis': language_info
            }
        except Exception as e:
            logger.warning(f"[LemonFox] Primary language ({primary_language}) transcription failed: {e}")
        
        # Fallback to auto-detect mode (no language specified)
        try:
            logger.info("[LemonFox] Trying auto-detect mode for multilingual content")
            srt_content, used_language = transcribe_audio_single_language(temp_audio_path, 'auto')
            return {
                'srt_content': srt_content,
                'primary_language': used_language,
                'transcription_strategy': 'auto_detect',
                'language_analysis': language_info
            }
        except Exception as e:
            logger.warning(f"[LemonFox] Auto-detect transcription failed: {e}")
        
        # Final fallback to English
        logger.info("[LemonFox] Final fallback to English transcription")
        srt_content, used_language = transcribe_audio_single_language(temp_audio_path, 'english')
        return {
            'srt_content': srt_content,
            'primary_language': used_language,
            'transcription_strategy': 'english_fallback',
            'language_analysis': language_info
        }
    
    # Strategy 3: Default single language
    else:
        logger.info(f"[LemonFox] Standard single language transcription: {primary_language}")
        srt_content, used_language = transcribe_audio_single_language(temp_audio_path, primary_language)
        return {
            'srt_content': srt_content,
            'primary_language': used_language,
            'transcription_strategy': 'single_language',
            'language_analysis': language_info
        }

def transcribe_audio_single_language(temp_audio_path, language):
    """
    Transcribe audio in a single specified language.
    """
    url = "https://api.lemonfox.ai/v1/audio/transcriptions"
    headers = {
        "Authorization": "Bearer rk61hEoE7P1WYvymUqCsIicLySY4KUYj"
    }
    
    # Handle special cases
    if language == 'auto':
        # Don't specify language - let LemonFox auto-detect
        data = {"response_format": "srt"}
        logger.info("[LemonFox] Using auto-detection mode")
    else:
        # Validate language
        normalized_lang = normalize_language(language)
        if normalized_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"[LemonFox] Unsupported language: {language}. Using English.")
            normalized_lang = 'english'
        
        data = {
            "language": normalized_lang,
            "response_format": "srt"
        }
        logger.info(f"[LemonFox] Using specified language: {normalized_lang}")
    
    # Log file info
    file_size = os.path.getsize(temp_audio_path) if os.path.exists(temp_audio_path) else 0
    logger.info(f"[LemonFox] Transcribing audio file: {temp_audio_path} (size: {file_size} bytes)")
    
    try:
        with open(temp_audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            logger.info(f"[LemonFox] Sending request to {url}")
            response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
        
        logger.info(f"[LemonFox] Response status: {response.status_code}")
        logger.info(f"[LemonFox] Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            srt_content = response.text
            logger.info(f"[LemonFox] Received SRT content length: {len(srt_content)} characters")
            logger.info(f"[LemonFox] First 500 chars of SRT: {srt_content[:500]}")
            return srt_content, language
        else:
            error_msg = f"Transcription failed [{response.status_code}]: {response.text}"
            logger.error(f"[LemonFox] {error_msg}")
            raise Exception(error_msg)
    except Exception as e:
        logger.error(f"[LemonFox] Exception during transcription: {e}")
        raise

def transcribe_audio(temp_audio_path, language=None):
    """
    Enhanced transcribe function with automatic language detection.
    """
    # If no language specified, perform language analysis
    if language is None:
        logger.info("[LemonFox] No language specified. Performing language analysis...")
        language_info = detect_audio_language_segments(temp_audio_path)
        return transcribe_multiingual_audio(temp_audio_path, language_info)
    else:
        # Use specified language directly
        logger.info(f"[LemonFox] Using specified language: {language}")
        srt_content, used_language = transcribe_audio_single_language(temp_audio_path, language)
        return srt_content, used_language

def transcribe_audio_with_timestamps(temp_audio_path, language=None):
    """
    Enhanced transcription with automatic language detection and multilingual support.
    """
    logger.info(f"[LemonFox] Starting enhanced transcription for: {temp_audio_path}")
    
    # Get transcription result
    if language is None:
        # Perform language analysis and multilingual transcription
        language_info = detect_audio_language_segments(temp_audio_path)
        transcription_result = transcribe_multiingual_audio(temp_audio_path, language_info)
        
        srt_content = transcription_result['srt_content']
        detected_language = transcription_result.get('primary_language', 'english')
        language_analysis = transcription_result.get('language_analysis', {})
        transcription_strategy = transcription_result.get('transcription_strategy', 'unknown')
        
    else:
        # Use specified language
        srt_content, detected_language = transcribe_audio(temp_audio_path, language)
        language_analysis = {'primary_language': language, 'confidence': 1.0, 'languages': {language: 1.0}}
        transcription_strategy = 'user_specified'
    
    logger.info(f"[LemonFox] Parsing SRT content for language: {detected_language}")
    logger.info(f"[LemonFox] Transcription strategy used: {transcription_strategy}")
    
    # Parse SRT content
    segments = parse_srt_content(srt_content)
    logger.info(f"[LemonFox] Parsed {len(segments)} segments from SRT")
    
    # Add language information to each segment
    for segment in segments:
        segment['detected_language'] = detected_language
        segment['language_confidence'] = language_analysis.get('confidence', 0.5)
    
    full_text = " ".join([segment['text'] for segment in segments])
    logger.info(f"[LemonFox] Generated full text with {len(full_text)} characters")
    
    result = {
        'segments': segments,
        'full_text': full_text,
        'srt_content': srt_content,
        'detected_language': detected_language,
        'language_analysis': language_analysis,
        'transcription_strategy': transcription_strategy,
        'is_multilingual': language_analysis.get('is_multilingual', False)
    }
    
    # Log first few segments for debugging
    if segments:
        logger.info(f"[LemonFox] First segment: {segments[0]}")
        if len(segments) > 1:
            logger.info(f"[LemonFox] Last segment: {segments[-1]}")
    
    # Log language summary
    if language_analysis.get('is_multilingual'):
        languages = language_analysis.get('languages', {})
        lang_summary = ", ".join([f"{lang}: {pct:.1%}" for lang, pct in languages.items()])
        logger.info(f"[LemonFox] Multilingual content detected: {lang_summary}")
    
    return result

def parse_srt_content(srt_content):
    """
    Parses SRT content and extracts segments with timestamps.
    Returns: list of dicts with 'start', 'end', 'text', 'start_seconds', 'end_seconds'
    """
    logger.info(f"[LemonFox] Parsing SRT content with {len(srt_content)} characters")
    segments = []
    
    if not srt_content.strip():
        logger.warning("[LemonFox] Empty SRT content received")
        return segments
    
    # Handle quoted content and escaped newlines from LemonFox API
    cleaned_content = srt_content.strip()
    
    # Remove quotes if the content is wrapped in quotes
    if cleaned_content.startswith('"') and cleaned_content.endswith('"'):
        cleaned_content = cleaned_content[1:-1]
        logger.info("[LemonFox] Removed surrounding quotes from SRT content")
    
    # Replace escaped newlines with actual newlines
    if '\\n' in cleaned_content:
        cleaned_content = cleaned_content.replace('\\n', '\n')
        logger.info("[LemonFox] Converted escaped newlines to actual newlines")
    
    logger.info(f"[LemonFox] Cleaned content first 300 chars: {cleaned_content[:300]}")
    
    # Split by double newlines to get individual subtitle blocks
    blocks = re.split(r'\n\s*\n', cleaned_content.strip())
    logger.info(f"[LemonFox] Found {len(blocks)} SRT blocks")
    
    for i, block in enumerate(blocks):
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            logger.warning(f"[LemonFox] Block {i} has insufficient lines: {len(lines)}")
            continue
            
        # First line is sequence number
        sequence = lines[0].strip()
        
        # Second line contains timestamps
        timestamp_line = lines[1].strip()
        timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
        
        if not timestamp_match:
            logger.warning(f"[LemonFox] Block {i} has invalid timestamp format: {timestamp_line}")
            continue
            
        start_time = timestamp_match.group(1)
        end_time = timestamp_match.group(2)
        
        # Remaining lines are the text content
        text = ' '.join(lines[2:]).strip()
        
        # Convert timestamps to seconds for easier processing
        start_seconds = timestamp_to_seconds(start_time)
        end_seconds = timestamp_to_seconds(end_time)
        
        segment = {
            'sequence': int(sequence) if sequence.isdigit() else len(segments) + 1,
            'start': start_time,
            'end': end_time,
            'start_seconds': start_seconds,
            'end_seconds': end_seconds,
            'text': text,
            'duration': end_seconds - start_seconds
        }
        segments.append(segment)
        
        # Log first few segments for debugging
        if i < 3:
            logger.info(f"[LemonFox] Segment {i}: {segment}")
    
    logger.info(f"[LemonFox] Successfully parsed {len(segments)} segments")
    return segments

def timestamp_to_seconds(timestamp):
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds"""
    # Remove comma and convert to standard format
    timestamp = timestamp.replace(',', '.')
    
    # Split into parts
    parts = timestamp.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_and_ms = float(parts[2])
    
    total_seconds = hours * 3600 + minutes * 60 + seconds_and_ms
    return total_seconds      


def transcribe_audio_file(file_path, language=None, optimize_large_files=True):
    """Enhanced transcribe audio file with automatic language detection"""
    start_time = time.time()
    logger.info(f"[LemonFox] Starting transcription for: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    # Get file size for optimization decisions
    file_size = get_file_size(file_path)
    
    try:
        # Use multilingual transcription if language not specified or explicitly requested
        if language is None or language == 'auto':
            result = transcribe_multiingual_audio(file_path)
            
            # Extract the SRT content and language from the result
            if isinstance(result, dict):
                srt_content = result.get('srt_content', '')
                detected_language = result.get('primary_language', 'unknown')
                language_info = result.get('language_analysis', {})
                strategy = result.get('transcription_strategy', 'multilingual')
            else:
                # Fallback if result format unexpected
                srt_content = result
                detected_language = 'unknown'
                language_info = {}
                strategy = 'fallback'
            
            logger.info(f"[LemonFox] Multilingual transcription completed in {time.time() - start_time:.2f}s")
            logger.info(f"[LemonFox] Detected language: {detected_language}, Strategy: {strategy}")
            
        else:
            # Use single language transcription
            srt_content, detected_language = transcribe_audio_single_language(file_path, language)
            language_info = {'primary_language': detected_language, 'confidence': 1.0}
            strategy = 'single_language'
            
            logger.info(f"[LemonFox] Single language transcription completed in {time.time() - start_time:.2f}s")
        
        # Parse the SRT content to create pages
        pages = parse_srt_to_pages(srt_content)
        
        logger.info(f"[LemonFox] Created {len(pages)} pages from transcription")
        logger.info(f"[LemonFox] File size: {file_size / (1024*1024):.2f} MB")
        
        return {
            'pages': pages,
            'language': detected_language,
            'file_size': file_size,
            'transcription_time': time.time() - start_time,
            'language_analysis': language_info,
            'transcription_strategy': strategy,
            'total_segments': len(pages)
        }
        
    except Exception as e:
        logger.error(f"[LemonFox] Audio transcription failed for {file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise e


def transcribe_video_file(file_path, language=None, optimize_large_files=True):
    """Enhanced transcribe video file with automatic language detection"""
    start_time = time.time()
    logger.info(f"[LemonFox] Starting video transcription for: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Video file not found: {file_path}")
    
    # Get file size for optimization decisions
    file_size = get_file_size(file_path)
    
    # Extract audio from video first
    temp_audio_path = None
    try:
        temp_audio_path = extract_audio_from_video(file_path)
        
        # Use multilingual transcription if language not specified
        if language is None or language == 'auto':
            result = transcribe_multiingual_audio(temp_audio_path)
            
            # Extract the data from result
            if isinstance(result, dict):
                srt_content = result.get('srt_content', '')
                detected_language = result.get('primary_language', 'unknown')
                language_info = result.get('language_analysis', {})
                strategy = result.get('transcription_strategy', 'multilingual')
            else:
                srt_content = result
                detected_language = 'unknown'
                language_info = {}
                strategy = 'fallback'
            
            logger.info(f"[LemonFox] Video multilingual transcription completed in {time.time() - start_time:.2f}s")
            logger.info(f"[LemonFox] Detected language: {detected_language}, Strategy: {strategy}")
            
        else:
            # Use single language transcription
            srt_content, detected_language = transcribe_audio_single_language(temp_audio_path, language)
            language_info = {'primary_language': detected_language, 'confidence': 1.0}
            strategy = 'single_language'
            
            logger.info(f"[LemonFox] Video single language transcription completed in {time.time() - start_time:.2f}s")
        
        # Parse the SRT content to create pages
        pages = parse_srt_to_pages(srt_content)
        
        logger.info(f"[LemonFox] Created {len(pages)} pages from video transcription")
        logger.info(f"[LemonFox] Video file size: {file_size / (1024*1024):.2f} MB")
        
        return {
            'pages': pages,
            'language': detected_language,
            'file_size': file_size,
            'transcription_time': time.time() - start_time,
            'language_analysis': language_info,
            'transcription_strategy': strategy,
            'total_segments': len(pages)
        }
        
    except Exception as e:
        logger.error(f"[LemonFox] Video transcription failed for {file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise e
    finally:
        # Clean up temporary audio file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
                logger.info(f"[LemonFox] Cleaned up temporary audio file: {temp_audio_path}")
            except Exception as cleanup_error:
                logger.warning(f"[LemonFox] Failed to cleanup temp file: {cleanup_error}")


def get_file_size(file_path):
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def extract_audio_from_video(file_path):
    """Extract audio from video file and return temporary audio file path"""
    try:
        import moviepy.editor as mp
    except ImportError:
        raise RuntimeError("moviepy not available for video processing")
    
    logger.info(f"[LemonFox] Extracting audio from video: {file_path}")
    
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
        
        logger.info(f"[LemonFox] Audio extracted to: {temp_audio_path}")
        return temp_audio_path
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        raise e


def parse_srt_to_pages(srt_content):
    """Parse SRT content into pages for the application"""
    logger.info(f"[LemonFox] Converting SRT content to pages")
    
    # Parse SRT content to get segments
    segments = parse_srt_content(srt_content)
    
    if not segments:
        logger.warning("[LemonFox] No segments found in SRT content")
        return []
    
    # Convert segments to pages format
    pages = []
    for i, segment in enumerate(segments):
        page = {
            'page_number': i + 1,
            'text': segment['text'],
            'start_time': segment['start'],
            'end_time': segment['end'],
            'start_seconds': segment['start_seconds'],
            'end_seconds': segment['end_seconds'],
            'duration': segment['duration'],
            'tokens': len(segment['text'].split())  # Simple token count
        }
        pages.append(page)
    
    logger.info(f"[LemonFox] Created {len(pages)} pages from SRT content")
    return pages      