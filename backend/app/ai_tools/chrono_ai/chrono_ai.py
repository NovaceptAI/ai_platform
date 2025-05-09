import openai
import os
import docx
import PyPDF2

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def read_document(file_path):
    """
    Reads text from a document file (.txt, .docx, .pdf).

    Args:
        file_path (str): The path to the document file.

    Returns:
        str: The extracted text from the document.
    """
    if file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    elif file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    elif file_path.endswith('.pdf'):
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return '\n'.join([page.extract_text() for page in reader.pages])
    else:
        raise ValueError("Unsupported file format. Please provide a .txt, .docx, or .pdf file.")

def analyze_document(document_text):
    """
    Analyzes the document text and returns all events in chronological order.

    Args:
        document_text (str): The text content of the document.

    Returns:
        str: The extracted events in chronological order.
    """
    prompt = (
        "Analyze the following document and extract all events that include dates. "
        "If dates are found, return the events in chronological order as a numbered list (e.g., 1. Event 1, 2. Event 2). "
        "If no dates are found, return exactly this message: 'No Dates Found'. "
        "Do not include any additional text or explanations.\n\n"
        f"Document:\n{document_text}"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are an event analyzer."},
                  {"role": "user", "content": prompt}],
        max_tokens=500
    )

    output = response["choices"][0]["message"]["content"]
    return output

def analyze_file(file_path):
    """
    Reads a document file and analyzes its content for chronological events.

    Args:
        file_path (str): The path to the document file.

    Returns:
        str: The extracted events in chronological order.
    """
    try:
        document_text = read_document(file_path)
        return analyze_document(document_text)
    except Exception as e:
        print(f"Error analyzing file: {e}")
        raise

# Example usage
if __name__ == "__main__":
    file_path = "example.docx"  # Replace with the path to your document file
    try:
        events = analyze_file(file_path)
        print("Extracted Events in Chronological Order:")
        print(events)
    except Exception as e:
        print(f"Failed to analyze the document: {e}")