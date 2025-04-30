import os
import tempfile
import requests
import json 
import openai
from dotenv import load_dotenv
# Azure OpenAI API configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = "https://scoolish-openai.openai.azure.com"
API_VERSION = "2024-02-01"

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

# if not AZURE_OPENAI_API_KEY:
#     raise ValueError("AZURE_OPENAI_API_KEY environment variable is not set.")

def generate_image(prompt, n=1):
    """
    Generates images using DALL-E 3 via Azure OpenAI.

    Args:
        prompt (str): The text prompt for generating images.
        n (int): The number of images to generate.

    Returns:
        list: A list of URLs for the generated images.
    """
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/dall-e-3/images/generations?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_OPENAI_API_KEY}"
    }
    payload = {
        "prompt": prompt,
        "n": n,
        "size": "1024x1024"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        image_urls = [item['url'] for item in data.get('data', [])]
        return image_urls
    except requests.exceptions.RequestException as e:
        print(f"Error generating images: {e}")
        raise

def save_images(image_urls):
    """
    Saves images from URLs to a temporary directory.

    Args:
        image_urls (list): List of image URLs.

    Returns:
        list: A list of file paths for the saved images.
    """
    tmp_dir = tempfile.mkdtemp()
    image_paths = []
    for i, url in enumerate(image_urls):
        image_path = os.path.join(tmp_dir, f"image_{i+1}.png")
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(image_path, 'wb') as f:
                f.write(response.content)
            image_paths.append(image_path)
        except Exception as e:
            print(f"Error saving image {url}: {e}")
            raise
    return image_paths

def ai_assisted_story_structuring(content):
    """
    Generates a structured story and associated images based on the content.

    Args:
        content (str): The input content for the story.

    Returns:
        tuple: A tuple containing the structured story and image paths.
    """
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/gpt-4o/chat/completions?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_OPENAI_API_KEY}"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Organize the following content into a clear, engaging storyline:\n\n{content}"}
        ],
        "max_tokens": 500
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        structured_story = response.json()["choices"][0]["message"]["content"].strip()

        # Generate images based on the structured story
        image_prompt = f"Create images based on the following story:\n\n{structured_story}"
        image_urls = generate_image(image_prompt, n=4)

        # Save images to a temporary folder
        image_paths = save_images(image_urls)

        return structured_story, image_paths
    except requests.exceptions.RequestException as e:
        print(f"Error in AI-assisted story structuring: {e}")
        raise

def create_story_visualization(content):
    """
    Creates a story visualization with structured content and images.

    Args:
        content (str): The input content for the story.

    Returns:
        dict: A dictionary containing the structured story, image paths, and additional elements.
    """
    structured_story, image_paths = ai_assisted_story_structuring(content)
    return {
        "structured_story": structured_story,
        "image_paths": image_paths,
        "visual_elements": "Interactive timelines, concept maps, and data-driven storytelling visuals.",
        "templates": "A variety of professionally designed templates tailored for different storytelling needs.",
        "collaboration": "Real-time collaborative editing and sharing across platforms."
    }

# Example usage
# if __name__ == "__main__":
#     content = "Once upon a time, a girl lived in a small village with her pets."
#     try:
#         visualization = create_story_visualization(content)
#         print("Structured Story:")
#         print(visualization["structured_story"])
#         print("\nGenerated Image Paths:")
#         print(visualization["image_paths"])
#     except Exception as e:
#         print(f"Failed to create story visualization: {e}")