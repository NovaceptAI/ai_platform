import openai
import os
import docx
import PyPDF2
import logging

# Set up the OpenAI API key
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_document(file_path):
    """Reads the content of a .docx or .pdf file and returns the text."""
    logger.info("Reading document from file path: %s", file_path)
    try:
        if file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            text = '\n'.join(full_text)
        elif file_path.endswith('.pdf'):
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                full_text = []
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    full_text.append(page.extract_text())
                text = '\n'.join(full_text)
        else:
            logger.error("Unsupported document format for file: %s", file_path)
            raise ValueError("Unsupported document format")
        logger.info("Successfully read document from file path: %s", file_path)
        return text
    except Exception as e:
        logger.exception("Error reading document from file path: %s", file_path)
        raise e

def extract_topics_and_keywords_from_file(file_path):
    """Extracts topics and keywords from a .docx or .pdf file."""
    logger.info("Extracting topics and keywords from file: %s", file_path)
    try:
        document_text = read_document(file_path)  # Read the document content
        result = extract_topics_and_keywords(document_text)  # Use the existing function
        logger.info("Successfully extracted topics and keywords from file: %s", file_path)
        return result
    except Exception as e:
        logger.exception("Error extracting topics and keywords from file: %s", file_path)
        raise e

def extract_topics_and_keywords(document_text):
    logger.info("Extracting topics and keywords from document text.")
    try:
        response_topics = openai.ChatCompletion.create(
            engine="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a topic extraction assistant."},
                {"role": "user", "content": f"Extract the main topics from the following text:\n\n{document_text}"}
            ],
            max_tokens=150,
            temperature=0.5,
        )
        topics = response_topics.choices[0].message["content"].strip()
        logger.info("Successfully extracted topics.")

        response_keywords = openai.ChatCompletion.create(
            engine="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a keyword extraction assistant."},
                {"role": "user", "content": f"Extract the keywords from the following text:\n\n{document_text}"}
            ],
            max_tokens=50,
            temperature=0.5,
        )
        keywords = response_keywords.choices[0].message["content"].strip()
        logger.info("Successfully extracted keywords.")

        return {"topics": topics, "keywords": keywords}
    except Exception as e:
        logger.exception("Error extracting topics and keywords from document text.")
        raise e

def cluster_documents(documents):
    logger.info("Clustering documents.")
    try:
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
        logger.info("Successfully clustered documents.")
        return clusters
    except Exception as e:
        logger.exception("Error clustering documents.")
        raise e

def visualize_topics(document_text):
    logger.info("Visualizing topics.")
    try:
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
        logger.info("Successfully visualized topics.")
        return visualization
    except Exception as e:
        logger.exception("Error visualizing topics.")
        raise e

def summarize_topics(document_text):
    logger.info("Summarizing topics.")
    try:
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
        logger.info("Successfully summarized topics.")
        return summary
    except Exception as e:
        logger.exception("Error summarizing topics.")
        raise e

def named_entity_recognition(document_text):
    logger.info("Performing named entity recognition.")
    try:
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
        logger.info("Successfully performed named entity recognition.")
        return entities
    except Exception as e:
        logger.exception("Error performing named entity recognition.")
        raise e

def sentiment_analysis(document_text):
    logger.info("Performing sentiment analysis.")
    try:
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
        logger.info("Successfully performed sentiment analysis.")
        return sentiment
    except Exception as e:
        logger.exception("Error performing sentiment analysis.")
        raise e

def analyze_topic_trends(documents):
    logger.info("Analyzing topic trends.")
    try:
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
        logger.info("Successfully analyzed topic trends.")
        return trends
    except Exception as e:
        logger.exception("Error analyzing topic trends.")
        raise e