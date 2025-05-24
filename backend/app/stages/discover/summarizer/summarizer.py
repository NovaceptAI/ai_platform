import os
import json
import logging
from pydub import AudioSegment
import moviepy.editor as mp
# import docx
# import PyPDF2
from services.lemonfox_service import transcribe_audio
import openai

from utils.file_utils import (
    detect_file_type,
    extract_text_from_document,
    extract_text_from_audio,
    extract_text_from_video
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

class Summarizer:
    def __init__(self, openai_engine="gpt-4.1"):
        self.openai_engine = openai_engine

    def _summarize_file(self, file_path):
        """Summarizes the file based on its type."""
        try:
            file_type = detect_file_type(file_path)
            if file_type == "document":
                return self._summarize_document(file_path)
            elif file_type == "audio":
                return self._summarize_audio(file_path)
            elif file_type == "video":
                return self._summarize_video(file_path)
            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            logger.error(f"Error summarizing file: {e}")
            raise


    def _summarize_document(self, file_path):
        """Summarizes a document file."""
        text = extract_text_from_document(file_path)
        segments = self._segment_text(text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {
            "toc": toc,
            "segments": segments,
            "tags": tags,
            "entities": entities,
            "summary": summaries
        }
    

    def _summarize_audio(self, file_path):
        """Summarizes an audio file."""
        transcribed_text = extract_text_from_audio(file_path)
        segments = self._segment_text(transcribed_text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {
            "toc": toc,
            "segments": segments,
            "tags": tags,
            "entities": entities,
            "summary": summaries
        }
        

    def _summarize_video(self, file_path):
        """Summarizes a video file."""
        transcribed_text = extract_text_from_video(file_path)
        segments = self._segment_text(transcribed_text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {
            "toc": toc,
            "segments": segments,
            "tags": tags,
            "entities": entities,
            "summary": summaries
        }
        

    def _summarize_text(self, text):
        """Summarizes text using OpenAI."""
        prompt = f"Summarize the following text in a concise manner:\n\n{text}"
        response = openai.ChatCompletion.create(
            engine=self.openai_engine,
            messages=[
                {"role": "system", "content": "You are a document summarizer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        return response["choices"][0]["message"]["content"].strip()

    def _segment_text(self, text):
        """Segments text into paragraphs."""
        return text.split('\n\n')

    def _generate_toc(self, segments):
        """Generates a table of contents from text segments."""
        return [f"Section {i+1}: {segment[:30]}..." for i, segment in enumerate(segments)]

    def _tag_segments(self, segments):
        """Tags each segment with relevant keywords."""
        tags = []
        for segment in segments:
            response = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a keyword extraction assistant."},
                    {"role": "user", "content": f"Assign tags to the following text:\n\n{segment}"}
                ],
                max_tokens=50
            )
            tags.append(response["choices"][0]["message"]["content"].strip())
        return tags

    def _extract_named_entities(self, segments):
        """Extracts named entities from text segments."""
        entities = []
        for segment in segments:
            prompt = (
                "Extract named entities (e.g., people, organizations, locations) from the following text. "
                "Format the output as a list of entities in JSON format:\n\n"
                f"Text:\n{segment}"
            )
            response = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a named entity recognition assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )
            try:
                entities.append(json.loads(response["choices"][0]["message"]["content"].strip()))
            except json.JSONDecodeError:
                entities.append([])  # Fallback to an empty list if parsing fails
        return entities