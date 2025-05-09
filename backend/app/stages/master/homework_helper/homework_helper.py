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

def generate_prompt(context_type, context, question):
    """Generates a dynamic prompt for answering homework questions."""
    if context_type == 'category':
        return (
            f"Answer the following question based on the given category. "
            "Provide a detailed and accurate response:\n\n"
            f"Category:\n{context}\n\n"
            f"Question:\n{question}"
        )
    elif context_type == 'text':
        return (
            f"Answer the following question based on the given text. "
            "Provide a detailed and accurate response:\n\n"
            f"Text:\n{context}\n\n"
            f"Question:\n{question}"
        )
    else:
        raise ValueError("Invalid context type for prompt generation")

def call_openai_chat_completion(prompt, max_tokens=1000):
    """Calls the OpenAI Chat Completion API with the given prompt."""
    try:
        response = openai.ChatCompletion.create(
            engine="gpt-4o",  # Replace with your actual deployment name
            messages=[
                {"role": "system", "content": "You are a homework helper."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        raise

def answer_question_from_category(category, question):
    """Answers a question based on the given category."""
    logger.info(f"Answering question from category: {category}")
    prompt = generate_prompt('category', category, question)
    return call_openai_chat_completion(prompt)

def answer_question_from_document(file_path, question):
    """Answers a question based on the content of a document."""
    logger.info(f"Answering question from document: {file_path}")
    text = extract_text_from_document(file_path)
    prompt = generate_prompt('text', text, question)
    return call_openai_chat_completion(prompt)

def answer_question_from_text(text, question):
    """Answers a question based on the given text."""
    logger.info("Answering question from provided text")
    prompt = generate_prompt('text', text, question)
    return call_openai_chat_completion(prompt)