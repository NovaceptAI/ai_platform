import openai

# Azure OpenAI API Configuration
openai.api_type = "azure"
openai.api_base = "https://scoolish-openai.openai.azure.com/"
openai.api_version = "2023-05-15"
openai.api_key = "66gxh1j4bZGbQ7RIyjOipoGM69TSsMw3EQ8fA0XD1JlgnTxn8gcCJQQJ99BCACYeBjFXJ3w3AAABACOGwOWK"

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