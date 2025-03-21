import openai
import os

# Set up the OpenAI API key
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

def extract_keywords(document_text):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a keyword extraction assistant."},
            {"role": "user", "content": f"Extract the keywords from the following text:\n\n{document_text}"}
        ],
        max_tokens=50,
        temperature=0.5,
    )
    keywords = response.choices[0].message["content"].strip()
    return keywords

def cluster_documents(documents):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a document clustering assistant."},
            {"role": "user", "content": f"Cluster the following documents based on their topics:\n\n{documents}"}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    clusters = response.choices[0].message["content"].strip()
    return clusters

def visualize_topics(document_text):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a topic visualization assistant."},
            {"role": "user", "content": f"Visualize the topics in the following text:\n\n{document_text}"}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    visualization = response.choices[0].message["content"].strip()
    return visualization

def summarize_topics(document_text):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a topic summarization assistant."},
            {"role": "user", "content": f"Summarize the main topics in the following text:\n\n{document_text}"}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    summary = response.choices[0].message["content"].strip()
    return summary

def named_entity_recognition(document_text):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a named entity recognition assistant."},
            {"role": "user", "content": f"Identify and classify the named entities in the following text:\n\n{document_text}"}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    entities = response.choices[0].message["content"].strip()
    return entities

def sentiment_analysis(document_text):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a sentiment analysis assistant."},
            {"role": "user", "content": f"Analyze the sentiment of the following text:\n\n{document_text}"}
        ],
        max_tokens=50,
        temperature=0.5,
    )
    sentiment = response.choices[0].message["content"].strip()
    return sentiment

def analyze_topic_trends(documents):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a topic trend analysis assistant."},
            {"role": "user", "content": f"Analyze the topic trends in the following documents:\n\n{documents}"}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    trends = response.choices[0].message["content"].strip()
    return trends