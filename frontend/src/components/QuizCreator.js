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

const QUESTION_COUNTS = [1, 30, 50, 70, 100];

function QuizCreator() {
    const [category, setCategory] = useState('');
    const [numQuestions, setNumQuestions] = useState(1);
    const [quiz, setQuiz] = useState(null);
    const [file, setFile] = useState(null);
    const [method, setMethod] = useState('category'); // State to manage the quiz generation method

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

    const analyzeDocumentAndGenerateQuiz = async () => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('num_questions', numQuestions);

        const response = await fetch(`${config.API_BASE_URL}/quiz_creator/analyze_document_and_generate_quiz`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (response.ok) {
            setQuiz(JSON.parse(result.quiz).quiz);
        } else {
            setQuiz(`Error: ${result.error}`);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (method === 'category') {
            generateQuiz();
        } else if (method === 'document') {
            analyzeDocumentAndGenerateQuiz();
        }
    };

    const handleRestart = () => {
        setQuiz(null);
        setCategory('');
        setNumQuestions(1);
        setFile(null);
        setMethod('category');
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
                </div>
            ) : (
                <QuizScreen quiz={quiz} onRestart={handleRestart} />
            )}
        </div>
    );
}

export default QuizCreator;