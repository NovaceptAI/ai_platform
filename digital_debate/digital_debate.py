import openai
import random
import json
import os
# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

# List of predefined debate topics
DEBATE_TOPICS = [
    "Climate Change", "Artificial Intelligence", "Space Exploration", "Education System",
    "Healthcare", "Economic Policies", "Social Media Impact", "Privacy and Security",
    "Renewable Energy", "Globalization"
]

def create_debate(topic=None):
    """Creates a debate from a chosen topic or added topic."""
    if topic is None:
        topic = random.choice(DEBATE_TOPICS)
    
    prompt = (
        f"Create a debate on the topic: {topic}. "
        "Provide arguments for and against the topic. Format the output as:\n"
        "For: <arguments for the topic>\n"
        "Against: <arguments against the topic>"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a debate generator."},
                  {"role": "user", "content": prompt}],
        max_tokens=300
    )

    output = response["choices"][0]["message"]["content"]
    lines = output.strip().split("\n")

    for_arguments = lines[0].replace("For: ", "").strip()
    against_arguments = lines[1].replace("Against: ", "").strip()

    return {
        "topic": topic,
        "for_arguments": for_arguments,
        "against_arguments": against_arguments
    }

def score_debate(for_student_score, against_student_score):
    """Scores the debate for the For Student and Against Student."""
    if not (0 <= for_student_score <= 100) or not (0 <= against_student_score <= 100):
        raise ValueError("Scores must be between 0 and 100")

    result = "Draw"
    if for_student_score > against_student_score:
        result = "For Student Wins"
    elif against_student_score > for_student_score:
        result = "Against Student Wins"

    return {
        "for_student_score": for_student_score,
        "against_student_score": against_student_score,
        "result": result
    }

# Example Usage:
# debate = create_debate("Artificial Intelligence")
# print(debate)
# score = score_debate(85, 90)
# print(score)