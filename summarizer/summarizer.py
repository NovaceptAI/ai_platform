import os
import openai
from pydub import AudioSegment
import moviepy.editor as mp
import docx
import PyPDF2
import json
import csv
from services.lemonfox_service import transcribe_audio

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def summarize_text(text):
    """Summarizes the document."""
    prompt = (
        "Summarize the following document in a concise manner:\n\n"
        f"Document:\n{text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a document summarizer."},
                  {"role": "user", "content": prompt}],
        max_tokens=300
    )

    output = response["choices"][0]["message"]["content"]
    return output.strip()

def segment_text(text):
    """Segments the text into paragraphs."""
    segments = text.split('\n\n')
    return segments

def generate_toc(segments):
    """Generates a table of contents from the segments."""
    toc = []
    for i, segment in enumerate(segments):
        toc.append(f"Section {i+1}: {segment[:30]}...")
    return toc

def tag_segments(segments):
    """Tags each segment with relevant keywords."""
    tags = []
    for segment in segments:
        response = openai.ChatCompletion.create(
            engine="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a keyword extraction assistant."},
                {"role": "user", "content": f"Assign tags to the following text:\n\n{segment}"}
            ],
            max_tokens=50
        )
        tags.append(response.choices[0].message["content"].strip())
    return tags

def export_segments(segments, format='json'):
    """Exports the segments in the specified format."""
    if format == 'json':
        return json.dumps(segments, indent=2)
    elif format == 'csv':
        output = []
        for i, segment in enumerate(segments):
            output.append([f"Section {i+1}", segment])
        return output
    else:
        raise ValueError("Unsupported export format")

def summarize_document(file_path):
    """Summarizes the document based on its file type."""
    if file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        text = '\n'.join(full_text)
    elif file_path.endswith('.pdf'):
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = []
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                full_text.append(page.extract_text())
            text = '\n'.join(full_text)
    else:
        raise ValueError("Unsupported document format")
    
    segments = segment_text(text)
    toc = generate_toc(segments)
    tags = tag_segments(segments)
    summary = [summarize_text(segment) for segment in segments]
    return {
        "toc": toc,
        "segments": segments,
        "tags": tags,
        "summary": summary
    }

def summarize_audio(file_path):
    """Summarizes the audio file."""
    audio = AudioSegment.from_file(file_path)
    audio.export("temp.wav", format="wav")
    transcribed_text = transcribe_audio("temp.wav")
    os.remove("temp.wav")
    return summarize_text(transcribed_text)

def summarize_video(file_path):
    """Summarizes the video file."""
    video = mp.VideoFileClip(file_path)
    audio_path = "temp_audio.wav"
    video.audio.write_audiofile(audio_path)
    summary = summarize_audio(audio_path)
    os.remove(audio_path)
    return summary

def summarize_file(file_path):
    """Summarizes the file based on its type."""
    if file_path.endswith(('.docx', '.pdf')):
        return summarize_document(file_path)
    elif file_path.endswith(('.mp3', '.wav')):
        return summarize_audio(file_path)
    elif file_path.endswith(('.mp4', '.avi')):
        return summarize_video(file_path)
    else:
        raise ValueError("Unsupported file format")