import os
import openai
import tempfile
import requests

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = "https://scoolish-openai.openai.azure.com/"
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def call_openai_api(prompt):
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150
    )
    return response.choices[0].message["content"].strip()

def generate_image(prompt, n=4):
    url = "https://scoolish-openai.openai.azure.com/openai/deployments/dall-e-3/images/generations?api-version=2024-02-01"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }
    data = {
        "prompt": prompt,
        "n": n,
        "size": "1024x1024"
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    image_urls = [data['url'] for data in response.json()['data']]
    return image_urls

def save_images(image_urls):
    tmp_dir = tempfile.mkdtemp()
    image_paths = []
    for i, url in enumerate(image_urls):
        image_path = os.path.join(tmp_dir, f"image_{i+1}.png")
        with open(image_path, 'wb') as f:
            f.write(requests.get(url).content)
        image_paths.append(image_path)
    return image_paths

def ai_assisted_story_structuring(content):
    structuring_prompt = f"Organize the following content into a clear, engaging storyline:\n\n{content}"
    structured_story = call_openai_api(structuring_prompt)
    
    # Generate images based on the structured story
    image_prompt = f"Create images based on the following story:\n\n{structured_story}"
    image_urls = generate_image(image_prompt)
    
    # Save images to a temporary folder
    image_paths = save_images(image_urls)
    
    return structured_story, image_paths

def dynamic_visual_elements():
    # Placeholder for actual implementation of dynamic visual elements
    return "Interactive timelines, concept maps, and data-driven storytelling visuals."

def customizable_story_templates():
    # Placeholder for actual implementation of customizable story templates
    return "A variety of professionally designed templates tailored for different storytelling needs."

def collaborative_editing_sharing():
    # Placeholder for actual implementation of collaborative editing and sharing
    return "Real-time collaborative editing and sharing across platforms."

def create_story_visualization(content):
    structured_story, image_paths = ai_assisted_story_structuring(content)
    visual_elements = dynamic_visual_elements()
    templates = customizable_story_templates()
    collaboration = collaborative_editing_sharing()
    
    return {
        "structured_story": structured_story,
        "image_paths": image_paths,
        "visual_elements": visual_elements,
        "templates": templates,
        "collaboration": collaboration
    }

def how_it_works():
    return [
        "Step 1: Input Your Content - Upload text, images, or data sets to start crafting your story.",
        "Step 2: AI-Powered Structuring - The tool automatically organizes content into a compelling narrative structure.",
        "Step 3: Customize & Enhance - Add interactive visuals, adjust layouts, and refine story flow to match your vision.",
        "Step 4: Share & Present - Export your story as an interactive web experience, presentation, or downloadable report."
    ]

# Example usage
# if __name__ == "__main__":
#     prompt = "A futuristic cityscape with flying cars and neon lights"
#     image_urls = generate_image(prompt)
#     print(f"Generated image URLs: {image_urls}")