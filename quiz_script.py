import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Azure OpenAI API credentials
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

def generate_mcq_question(category):
    """Generates a multiple-choice question with 4 options from Azure OpenAI API."""
    prompt = (
        f"Generate a multiple-choice question in the {category} category. "
        "The question should be challenging but fair, and include four answer choices, "
        "with one correct answer and three plausible incorrect answers. Format the output as:\n"
        "Question: <text>\nA) <option1>\nB) <option2>\nC) <option3>\nD) <option4>\nAnswer: <correct option letter>"
    )

    response = openai.ChatCompletion.create(
        engine="gpt-4o",  # Replace with your actual deployment name
        messages=[{"role": "system", "content": "You are a quiz question generator."},
                  {"role": "user", "content": prompt}],
        max_tokens=150
    )

    output = response["choices"][0]["message"]["content"]
    lines = output.strip().split("\n")

    question = lines[0].replace("Question: ", "").strip()
    options = {line[0]: line[3:].strip() for line in lines[1:5]}
    correct_answer = lines[5].replace("Answer: ", "").strip()

    return {
        "question": question,
        "options": options,
        "correct_answer": correct_answer
    }

# Example usage
category = "Science"
mcq = generate_mcq_question(category)
print("Generated MCQ:", mcq)