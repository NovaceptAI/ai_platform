import openai
import os

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def segment_document(document_text):
    """Segments the document into sections, paragraphs, and sentences."""
    prompt = (
        "Segment the following document into sections, paragraphs, and sentences. "
        "Format the output as:\n"
        "Section 1:\n<paragraph1>\n<paragraph2>\n...\n"
        "Section 2:\n<paragraph1>\n<paragraph2>\n...\n\n"
        f"Document:\n{document_text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a document segmenter."},
                  {"role": "user", "content": prompt}],
        max_tokens=1000
    )

    output = response["choices"][0]["message"]["content"]
    return output

def extract_keywords(document_text):
    """Extracts keywords from the document."""
    prompt = (
        "Extract the main keywords from the following document. "
        "Format the output as a list of keywords:\n\n"
        f"Document:\n{document_text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a keyword extractor."},
                  {"role": "user", "content": prompt}],
        max_tokens=150
    )

    output = response["choices"][0]["message"]["content"]
    return output.strip().split("\n")

def summarize_document(document_text):
    """Summarizes the document."""
    prompt = (
        "Summarize the following document in a concise manner:\n\n"
        f"Document:\n{document_text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a document summarizer."},
                  {"role": "user", "content": prompt}],
        max_tokens=300
    )

    output = response["choices"][0]["message"]["content"]
    return output.strip()

def named_entity_recognition(document_text):
    """Performs named entity recognition (NER) on the document."""
    prompt = (
        "Identify and extract named entities (e.g., people, organizations, locations) from the following document. "
        "Format the output as a list of entities:\n\n"
        f"Document:\n{document_text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a named entity recognizer."},
                  {"role": "user", "content": prompt}],
        max_tokens=200
    )

    output = response["choices"][0]["message"]["content"]
    return output.strip().split("\n")

def sentiment_analysis(document_text):
    """Analyzes the sentiment of the document."""
    prompt = (
        "Analyze the sentiment (positive, negative, neutral) of the following document. "
        "Format the output as:\n"
        "Sentiment: <sentiment>\n\n"
        f"Document:\n{document_text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a sentiment analyzer."},
                  {"role": "user", "content": prompt}],
        max_tokens=100
    )

    output = response["choices"][0]["message"]["content"]
    return output.strip()