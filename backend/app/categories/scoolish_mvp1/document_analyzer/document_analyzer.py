import openai
import os
import json

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def extract_topics(document_text):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a topic extraction assistant."},
            {"role": "user", "content": f"Extract the main topics from the following text:\n\n{document_text}"}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    topics = response.choices[0].message["content"].strip()
    return topics

def analyze_document(file_path):
    print(f"Analyzing document at: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            document_text = file.read()
        print("Document read with UTF-8 encoding.")
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            document_text = file.read()
        print("Document read with Latin-1 encoding.")

    print(f"Document text: {document_text[:500]}...")  # Print the first 500 characters of the document text

    topics = extract_topics(document_text)
    print(f"Extracted topics: {topics}")

    return {"document_title": os.path.basename(file_path), "topics": topics.split('\n')}

def analyze_text(text):
    print("Analyzing text data.")
    
    topics = extract_topics(text)
    print(f"Extracted topics: {topics}")

    return {"document_title": "Text Analysis", "topics": topics.split('\n')}