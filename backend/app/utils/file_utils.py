import os
import docx
import PyPDF2
from pydub import AudioSegment
import moviepy.editor as mp
from services.lemonfox_service import transcribe_audio
from services.whisper_service import translate_audio_with_azure_whisper

# transcriber = AzureWhisperTranscriber()

def detect_file_type(file_path):
    """Detects the file type based on its extension."""
    if file_path.endswith(('.docx', '.pdf', '.txt')):
        return "document"
    elif file_path.endswith(('.mp3', '.wav', '.m4a')):
        return "audio"
    elif file_path.endswith(('.mp4', '.avi', '.mov')):
        return "video"
    else:
        raise ValueError("Unsupported file format")

def extract_text_from_document(file_path):
    """Extracts text from a document file."""
    if file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])

    elif file_path.endswith('.pdf'):
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return '\n'.join([page.extract_text() or "" for page in reader.pages])

    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    else:
        raise ValueError("Unsupported document format")

def extract_text_from_audio(file_path):
    """Extracts and transcribes audio to text."""
    # temp_audio_path = "temp_audio.wav"
    # audio = AudioSegment.from_file(file_path)
    # audio.export(temp_audio_path, format="wav")
    try:
        return translate_audio_with_azure_whisper(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def extract_text_from_video(file_path):
    """Extracts audio from video and transcribes it to text."""
    temp_audio_path = "temp_audio.wav"
    video = mp.VideoFileClip(file_path)
    video.audio.write_audiofile(temp_audio_path)
    try:
        return translate_audio_with_azure_whisper(temp_audio_path)
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)