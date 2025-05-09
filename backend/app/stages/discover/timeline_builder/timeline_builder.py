import os
import openai
import json
import docx
import PyPDF2
import logging

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

# Configure logging
logger = logging.getLogger(__name__)

def extract_text_from_document(file_path):
    """Extracts text from a document based on its file type."""
    if file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return '\n'.join(full_text)
    elif file_path.endswith('.pdf'):
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = [page.extract_text() for page in reader.pages]
        return '\n'.join(full_text)
    else:
        raise ValueError("Unsupported document format")

def generate_prompt(context_type, context):
    """Generates a dynamic prompt for creating a historical timeline."""
    if context_type == 'category':
        return (
            f"Create a historical timeline for the following category. "
            "Extract key events, provide their dates, titles, and descriptions, "
            "and arrange them in chronological order. Format the output as JSON with the following structure:\n\n"
            "{\n"
            "  'events': [\n"
            "    {\n"
            "      'date': '<YYYY-MM-DD>',\n"
            "      'title': '<event_title>',\n"
            "      'description': '<event_description>',\n"
            "      'media': '<optional_media_url>'\n"
            "    },\n"
            "    ...\n"
            "  ]\n"
            "}\n\n"
            f"Category:\n{context}"
        )
    elif context_type == 'text':
        return (
            f"Create a historical timeline based on the following text. "
            "Extract key events, provide their dates, titles, and descriptions, "
            "and arrange them in chronological order. Format the output as JSON with the following structure:\n\n"
            "{\n"
            "  'events': [\n"
            "    {\n"
            "      'date': '<YYYY-MM-DD>',\n"
            "      'title': '<event_title>',\n"
            "      'description': '<event_description>',\n"
            "      'media': '<optional_media_url>'\n"
            "    },\n"
            "    ...\n"
            "  ]\n"
            "}\n\n"
            f"Text:\n{context}"
        )
    else:
        raise ValueError("Invalid context type for prompt generation")

def call_openai_chat_completion(prompt, max_tokens=1500):
    """Calls the OpenAI Chat Completion API with the given prompt."""
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4o",  # Replace with your actual deployment name
            messages=[
                {"role": "system", "content": "You are a timeline generator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        logger.info(f"Raw OpenAI API response: {response}")  # Log the raw response

        # Extract the content from the response
        content = response["choices"][0]["message"]["content"].strip()

        # Remove triple backticks if present
        if content.startswith("```json"):
            content = content[7:]  # Remove the opening ```json
        if content.endswith("```"):
            content = content[:-3]  # Remove the closing ```

        # Parse the cleaned JSON content
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
        logger.error(f"Raw response content: {response['choices'][0]['message']['content']}")
        raise
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise

def generate_timeline_from_category(category):
    """Generates a timeline based on the given category."""
    logger.info(f"Generating timeline for category: {category}")
    prompt = generate_prompt('category', category)
    return call_openai_chat_completion(prompt)

def generate_timeline_from_document(file_path):
    """Generates a timeline based on the content of a document."""
    logger.info(f"Generating timeline from document: {file_path}")
    text = extract_text_from_document(file_path)
    prompt = generate_prompt('text', text)
    return call_openai_chat_completion(prompt)

def generate_timeline_from_text(text):
    """Generates a timeline based on the given text."""
    logger.info("Generating timeline from provided text")
    prompt = generate_prompt('text', text)
    return call_openai_chat_completion(prompt)