import React, { useState } from 'react';
import './QuizCreator.css';
import config from '../config';
import QuizScreen from './QuizScreen';

const QUIZ_CATEGORIES = [
    "Sports", "Recent News", "Elections", "History", "Science", "Technology",
    "Movies", "Music", "Geography", "Politics", "Business", "Health",
    "Environment", "Space", "Literature", "Art", "Mythology", "Psychology",
    "Food & Drink", "General Knowledge"
];

const QUESTION_COUNTS = [10, 30, 50, 70, 100];

function QuizCreator() {
    const [category, setCategory] = useState('');
    const [numQuestions, setNumQuestions] = useState(10);
    const [quiz, setQuiz] = useState(null);

    const generateQuiz = async () => {
        const response = await fetch(`${config.API_BASE_URL}/quiz_creator/generate_quiz`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ categories: [category], num_questions: numQuestions })
        });

        const result = await response.json();
        if (response.ok) {
            setQuiz(JSON.parse(result.quiz).quiz);
        } else {
            setQuiz(`Error: ${result.error}`);
        }
    };

    return (
        <div className="quiz-creator">
            {!quiz ? (
                <div>
                    <h1>Quiz Creator</h1>
                    <form onSubmit={(e) => { e.preventDefault(); generateQuiz(); }}>
                        <label htmlFor="category">Category:</label>
                        <select
                            id="category"
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            required
                        >
                            <option value="">Select a category</option>
                            {QUIZ_CATEGORIES.map((cat) => (
                                <option key={cat} value={cat}>{cat}</option>
                            ))}
                        </select>
                        <label htmlFor="numQuestions">Number of Questions:</label>
                        <select
                            id="numQuestions"
                            value={numQuestions}
                            onChange={(e) => setNumQuestions(parseInt(e.target.value))}
                            required
                        >
                            {QUESTION_COUNTS.map((count) => (
                                <option key={count} value={count}>{count}</option>
                            ))}
                        </select>
                        <button type="submit">Generate Quiz</button>
                    </form>
                </div>
            ) : (
                <QuizScreen quiz={quiz} />
            )}
        </div>
    );
}

export default QuizCreator;