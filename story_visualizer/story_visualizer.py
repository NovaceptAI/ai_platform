import os
import openai

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def call_openai_api(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

def ai_assisted_story_structuring(content):
    structuring_prompt = f"Organize the following content into a clear, engaging storyline:\n\n{content}"
    structured_story = call_openai_api(structuring_prompt)
    return structured_story

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
    structured_story = ai_assisted_story_structuring(content)
    visual_elements = dynamic_visual_elements()
    templates = customizable_story_templates()
    collaboration = collaborative_editing_sharing()
    
    return {
        "structured_story": structured_story,
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
