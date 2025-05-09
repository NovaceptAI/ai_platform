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

def generate_prompt(context_type, context, num_questions):
    """Generates a dynamic prompt for quiz creation."""
    if context_type == 'category':
        return (
            f"Generate {num_questions} multiple-choice questions based on the following category. "
            "Each question should include four answer choices, with one correct answer and three plausible incorrect answers. "
            "Format the output as:\n"
            "Question: <text>\nA) <option1>\nB) <option2>\nC) <option3>\nD) <option4>\nAnswer: <correct option letter>\n\n"
            f"Category:\n{context}"
        )
    elif context_type == 'text':
        return (
            f"Generate {num_questions} multiple-choice questions based on the following text. "
            "Each question should include four answer choices, with one correct answer and three plausible incorrect answers. "
            "Format the output as:\n"
            "Question: <text>\nA) <option1>\nB) <option2>\nC) <option3>\nD) <option4>\nAnswer: <correct option letter>\n\n"
            f"Text:\n{context}"
        )
    else:
        raise ValueError("Invalid context type for prompt generation")

def call_openai_chat_completion(prompt, max_tokens=1000):
    """Calls the OpenAI Chat Completion API with the given prompt."""
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4o",  # Replace with your actual deployment name
            messages=[
                {"role": "system", "content": "You are a quiz creator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise

def generate_quiz_from_category(category, num_questions=5):
    """Generates a quiz from the given category."""
    logger.info(f"Generating quiz for category: {category} with {num_questions} questions")
    prompt = generate_prompt('category', category, num_questions)
    return call_openai_chat_completion(prompt)

def generate_quiz_from_document(file_path, num_questions=5):
    """Generates a quiz from the document based on its file type."""
    logger.info(f"Generating quiz from document: {file_path} with {num_questions} questions")
    text = extract_text_from_document(file_path)
    prompt = generate_prompt('text', text, num_questions)
    return call_openai_chat_completion(prompt)