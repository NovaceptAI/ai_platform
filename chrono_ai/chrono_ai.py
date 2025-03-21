import openai
import os
# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def analyze_document(document_text):
    """Analyzes the document text and returns all events in chronological order."""
    prompt = (
        "Analyze the following document and extract all events mentioned in it. "
        "Return the events in chronological order. Format the output as:\n"
        "1. <event1>\n2. <event2>\n3. <event3>\n...\n\n"
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