import React, { useState } from 'react';
import './QuizCreator.css';
import config from '../../config';
import QuizScreen from './QuizScreen';

const QUIZ_CATEGORIES = [
    "Sports", "Recent News", "Elections", "History", "Science", "Technology",
    "Movies", "Music", "Geography", "Politics", "Business", "Health",
    "Environment", "Space", "Literature", "Art", "Mythology", "Psychology",
    "Food & Drink", "General Knowledge"
];

const QUESTION_COUNTS = [1, 2, 3, 4 , 5, 10, 30, 50, 70, 100];

function QuizCreator() {
    const [category, setCategory] = useState('');
    const [numQuestions, setNumQuestions] = useState(1);
    const [quiz, setQuiz] = useState(null);
    const [file, setFile] = useState(null);
    const [method, setMethod] = useState('category'); // State to manage the quiz generation method
    const [error, setError] = useState(null); // State to handle errors

    const generateQuiz = async () => {
        let response;
        try {
            if (method === 'category') {
                response = await fetch(`${config.API_BASE_URL}/quiz_creator/generate_quiz`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ method, category, num_questions: numQuestions })
                });
            } else if (method === 'document') {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('num_questions', numQuestions);
                formData.append('method', method);

                response = await fetch(`${config.API_BASE_URL}/quiz_creator/generate_quiz`, {
                    method: 'POST',
                    body: formData
                });
            }

            const result = await response.json();
            if (response.ok) {
                // Ensure the quiz data is properly parsed
                if (Array.isArray(result)) {
                    setQuiz(result);
                } else {
                    setError('Invalid quiz data received from the server.');
                }
            } else {
                setError(result.error || 'Failed to generate quiz.');
            }
        } catch (error) {
            console.error('Failed to fetch:', error);
            setError('Failed to fetch quiz data. Please try again.');
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null); // Clear any previous errors
        generateQuiz();
    };

    const handleRestart = () => {
        setQuiz(null);
        setCategory('');
        setNumQuestions(1);
        setFile(null);
        setMethod('category');
        setError(null); // Clear any errors
    };

    return (
        <div className="quiz-creator">
            {!quiz ? (
                <div>
                    <h1>Quiz Creator</h1>
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="method">Quiz Generation Method:</label>
                        <select
                            id="method"
                            value={method}
                            onChange={(e) => setMethod(e.target.value)}
                            required
                        >
                            <option value="category">By Category</option>
                            <option value="document">By Document</option>
                        </select>

                        {method === 'category' && (
                            <>
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
                            </>
                        )}

                        {method === 'document' && (
                            <>
                                <label htmlFor="file">Upload Document:</label>
                                <input
                                    type="file"
                                    id="file"
                                    onChange={(e) => setFile(e.target.files[0])}
                                    required
                                />
                            </>
                        )}

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
                    {error && <p className="error">{error}</p>}
                </div>
            ) : (
                <QuizScreen quiz={quiz} onRestart={handleRestart} />
            )}
        </div>
    );
}

export default QuizCreator;