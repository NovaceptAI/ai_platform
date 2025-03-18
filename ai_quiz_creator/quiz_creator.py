import openai
import random
import json
import time

# Azure OpenAI API Configuration
openai.api_type = "azure"
openai.api_base = "https://scoolish-openai.openai.azure.com/"
openai.api_version = "2023-05-15"
openai.api_key = "66gxh1j4bZGbQ7RIyjOipoGM69TSsMw3EQ8fA0XD1JlgnTxn8gcCJQQJ99BCACYeBjFXJ3w3AAABACOGwOWK"

# List of predefined quiz categories
QUIZ_CATEGORIES = [
    "Sports", "Recent News", "Elections", "History", "Science", "Technology",
    "Movies", "Music", "Geography", "Politics", "Business", "Health",
    "Environment", "Space", "Literature", "Art", "Mythology", "Psychology",
    "Food & Drink", "General Knowledge"
]

def generate_mcq_question(category):
    """Generates a multiple-choice question with 4 options from Azure OpenAI API."""
    prompt = (
        f"Generate a multiple-choice question in the {category} category. "
        "The question should be challenging but fair, and include four answer choices, "
        "with one correct answer and three plausible incorrect answers. Format the output as:\n"
        "Question: <text>\nA) <option1>\nB) <option2>\nC) <option3>\nD) <option4>\nAnswer: <correct option letter>"
    )

    retries = 3
    for attempt in range(retries):
        try:
            response = openai.ChatCompletion.create(
                engine="gpt-4o",  # Replace with your actual deployment name
                messages=[{"role": "system", "content": "You are a quiz question generator."},
                          {"role": "user", "content": prompt}],
                max_tokens=150
            )
            break
        except openai.error.RateLimitError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

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

def generate_quiz(categories, num_questions):
    """Generates a quiz with the specified categories and number of questions."""
    if not all(cat in QUIZ_CATEGORIES for cat in categories):
        raise ValueError("Invalid category selected!")

    if num_questions not in [10, 30, 50, 70, 100]:
        raise ValueError("Invalid number of questions!")

    quiz = []
    for _ in range(num_questions):
        category = random.choice(categories)
        quiz.append(generate_mcq_question(category))

    return json.dumps({"quiz": quiz}, indent=4)

# Example Usage:
# categories = ["Sports", "Recent News"]
# num_questions = 20
# quiz_json = generate_quiz(categories, num_questions)
# print(quiz_json)