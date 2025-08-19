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
    """Generates the most minimal prompt: just return a raw list of lists."""
    base_prompt = (
        "List key historical events from this {type}.\n"
        "Only output a list like:\n"
        "[\"YYYY-MM-DD\", \"Title\", \"Description\"]\n\n"
        "{label}:\n{context}"
    )
    label = "Category" if context_type == "category" else "Text"
    return base_prompt.format(type=context_type, label=label, context=context)

def call_openai_chat_completion(prompt, max_tokens=1000):
    """Calls the OpenAI Chat Completion API with the given prompt and returns the content."""
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4o",  # Replace with your actual deployment name
            messages=[
                {"role": "system", "content": "You are a timeline generator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )

        # Extract the generated content
        content = response['choices'][0]['message']['content'].strip()

        try:
            # Try parsing as a single JSON array
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON decode failed: {e}")
            logger.debug(f"Attempting line-by-line fix. Raw content:\n{content}")

            # Try to parse multiple JSON arrays line by line
            try:
                lines = content.strip().splitlines()
                parsed = [json.loads(line.strip()) for line in lines if line.strip()]
                return parsed
            except Exception as inner_e:
                logger.exception("Failed to parse even line-by-line")
                raise inner_e

    except Exception as e:
        logger.exception("Exception while calling OpenAI ChatCompletion")
        raise

def fix_malformed_json(content):
    """Attempts to fix common JSON issues in the response."""
    import re
    # Convert single quotes to double quotes
    content = content.replace("'", '"')
    # Remove trailing commas
    content = re.sub(r",\s*([\]}])", r"\1", content)
    # Escape unescaped double quotes inside strings
    content = re.sub(r'(?<!\\)"(?![:,}\]])', r'\"', content)
    return content

def generate_timeline_from_category(category):
    """Generates a timeline based on the given category."""
    logger.info(f"Generating timeline for category: {category}")
    prompt = generate_prompt('category', category)
    raw_timeline = call_openai_chat_completion(prompt)
    # timeline = format_timeline(raw_timeline)
    return raw_timeline

def generate_timeline_from_document(file_path):
    """Generates a timeline based on the content of a document."""
    logger.info(f"Generating timeline from document: {file_path}")
    text = extract_text_from_document(file_path)
    prompt = generate_prompt('text', text)
    raw_timeline = call_openai_chat_completion(prompt)
    # timeline = format_timeline(raw_timeline)
    return raw_timeline

def generate_timeline_from_text(text):
    """Generates a timeline based on the given text."""
    logger.info("Generating timeline from provided text")
    prompt = generate_prompt('text', text)
    return call_openai_chat_completion(prompt)

def format_timeline(raw_events):
    """Convert list of lists into structured event objects."""
    if not isinstance(raw_events, list):
        logger.error("Expected a list of events but got: {}".format(type(raw_events)))
        raise ValueError("Invalid response format from OpenAI API")
    return {
        "events": [
            {
                "date": item[0],
                "title": item[1],
                "description": item[2],
                "media": None  # You can add logic for media later
            } for item in raw_events
        ]
    }