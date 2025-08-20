import os
import json
import logging
from app.services.lemonfox_service import transcribe_audio
import openai

from app.utils.file_utils import (
    detect_file_type,
    extract_text_from_document,
    extract_text_from_audio,
    extract_text_from_video
)

from app.services.openai_key_manager import key_manager

logger = logging.getLogger(__name__)

# We’ll set api_key/base per-instance (or per-call) via rotation:
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = "2023-03-15-preview"  # keep your current version

class Summarizer:
    def __init__(self, openai_engine="gpt-4.1"):
        self.openai_engine = openai_engine
        # grab credentials for this batch instance
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        logger.info(f"[Summarizer] Using Azure OpenAI credential slot #{idx} ({openai.api_base})")

    def _summarize_file(self, file_path):
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
        chunks = extract_text_from_document(file_path)  # returns chunks
        summaries, tags, entities = [], [], []

        for chunk in chunks:
            summaries.append(self._summarize_text(chunk))
            tags.append(self._tag_segment(chunk))
            entities.append(self._extract_entities(chunk))

        toc = self._generate_toc(chunks)
        return {
            "toc": toc,
            "segments": chunks,
            "tags": tags,
            "entities": entities,
            "summary": summaries
        }

    def _summarize_audio(self, file_path):
        transcribed_text = extract_text_from_audio(file_path)
        segments = self._segment_text(transcribed_text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {"toc": toc, "segments": segments, "tags": tags, "entities": entities, "summary": summaries}

    def _summarize_video(self, file_path):
        transcribed_text = extract_text_from_video(file_path)
        segments = self._segment_text(transcribed_text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {"toc": toc, "segments": segments, "tags": tags, "entities": entities, "summary": summaries}

    def _summarize_text(self, text):
        if not text or not text.strip():
            return ""

        # If you want to be extra-safe against long-lived instances hitting limits,
        # you can rotate before each API call (uncomment next line).
        # self._use_new_credentials()

        try:
            prompt = f"Summarize the following text in a concise manner:\n\n{text}"
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a document summarizer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5,
                timeout=20
            )
            return resp["choices"][0]["message"]["content"].strip()

        except openai.error.RateLimitError as e:
            # (Optional) rotate credentials and re-raise; the Celery task will retry
            logger.warning(f"Rate limit encountered, rotating credentials and retrying via Celery: {e}")
            self._use_new_credentials()
            raise

        except openai.error.OpenAIError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected summarization error: {str(e)}")

    def _segment_text(self, text):
        return text.split('\n\n')

    def _generate_toc(self, segments):
        return [f"Section {i+1}: {segment[:30]}..." for i, segment in enumerate(segments)]

    def _tag_segments(self, segments):
        tags = []
        for segment in segments:
            tags.append(self._tag_segment(segment))
        return tags

    def _tag_segment(self, segment):
        resp = openai.ChatCompletion.create(
            engine=self.openai_engine,
            messages=[
                {"role": "system", "content": "You are a keyword extraction assistant."},
                {"role": "user", "content": f"Assign tags to the following text:\n\n{segment}"}
            ],
            max_tokens=50
        )
        return resp["choices"][0]["message"]["content"].strip()

    def _extract_named_entities(self, segments):
        return [self._extract_entities(s) for s in segments]

    def _extract_entities(self, segment):
        prompt = (
            "Extract named entities (e.g., people, organizations, locations) from the following text. "
            "Format the output as a list of entities in JSON format:\n\n"
            f"Text:\n{segment}"
        )
        resp = openai.ChatCompletion.create(
            engine=self.openai_engine,
            messages=[
                {"role": "system", "content": "You are a named entity recognition assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        try:
            return json.loads(resp["choices"][0]["message"]["content"].strip())
        except json.JSONDecodeError:
            return []