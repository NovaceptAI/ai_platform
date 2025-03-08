import os
import openai
from pydub import AudioSegment
import moviepy.editor as mp
import docx
import PyPDF2
from .services.lemonfox_service import transcribe_audio

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def summarize_text(text):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Summarize the following text:\n\n{text}",
        max_tokens=150
    )
    return response.choices[0].text.strip()

def summarize_document(file_path):
    if file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return summarize_text('\n'.join(full_text))
    elif file_path.endswith('.pdf'):
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfFileReader(file)
            full_text = []
            for page_num in range(reader.numPages):
                page = reader.getPage(page_num)
                full_text.append(page.extract_text())
            return summarize_text('\n'.join(full_text))
    else:
        raise ValueError("Unsupported document format")

def summarize_audio(file_path):
    audio = AudioSegment.from_file(file_path)
    audio.export("temp.wav", format="wav")
    transcribed_text = transcribe_audio("temp.wav")
    os.remove("temp.wav")
    return summarize_text(transcribed_text)

def summarize_video(file_path):
    video = mp.VideoFileClip(file_path)
    audio_path = "temp_audio.wav"
    video.audio.write_audiofile(audio_path)
    summary = summarize_audio(audio_path)
    os.remove(audio_path)
    return summary

def summarize_file(file_path):
    if file_path.endswith(('.docx', '.pdf')):
        return summarize_document(file_path)
    elif file_path.endswith(('.mp3', '.wav')):
        return summarize_audio(file_path)
    elif file_path.endswith(('.mp4', '.avi')):
        return summarize_video(file_path)
    else:
        raise ValueError("Unsupported file format")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python summarizer.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    summary = summarize_file(file_path)
    print("Summary:")
    print(summary)