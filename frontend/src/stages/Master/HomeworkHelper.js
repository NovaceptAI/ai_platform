import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown'; // Import React Markdown
import './HomeworkHelper.css';
import config from '../../config';

function HomeworkHelper() {
    const [method, setMethod] = useState('category'); // State to manage the question answering method
    const [category, setCategory] = useState('');
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState(null);
    const [error, setError] = useState(null);

    const getAnswer = async () => {
        let response;
        try {
            if (method === 'category') {
                // Category-based question answering
                response = await fetch(`${config.API_BASE_URL}/homework_helper/answer_question`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method, category, question }),
                });
            } else if (method === 'text') {
                // Text-based question answering
                response = await fetch(`${config.API_BASE_URL}/homework_helper/answer_question`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method, text, question }),
                });
            } else if (method === 'document') {
                // Document-based question answering
                const formData = new FormData();
                formData.append('file', file);
                formData.append('question', question);

                response = await fetch(`${config.API_BASE_URL}/homework_helper/answer_question`, {
                    method: 'POST',
                    body: formData,
                });
            }

            const result = await response.json();
            if (response.ok) {
                setAnswer(result.answer);
            } else {
                setError(result.error || 'Failed to get an answer.');
            }
        } catch (error) {
            console.error('Failed to fetch:', error);
            setError('Failed to fetch answer. Please try again.');
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null); // Clear any previous errors
        setAnswer(null); // Clear any previous answers
        getAnswer();
    };

    const handleRestart = () => {
        setMethod('category');
        setCategory('');
        setText('');
        setFile(null);
        setQuestion('');
        setAnswer(null);
        setError(null);
    };

    return (
        <div className="homework-helper">
            {!answer ? (
                <div>
                    <h1>Homework Helper</h1>
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="method">Question Answering Method:</label>
                        <select
                            id="method"
                            value={method}
                            onChange={(e) => setMethod(e.target.value)}
                            required
                        >
                            <option value="category">By Category</option>
                            <option value="text">By Text</option>
                            <option value="document">By Document</option>
                        </select>

                        {method === 'category' && (
                            <>
                                <label htmlFor="category">Category:</label>
                                <input
                                    type="text"
                                    id="category"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    placeholder="Enter a category (e.g., Physics)"
                                    required
                                />
                            </>
                        )}

                        {method === 'text' && (
                            <>
                                <label htmlFor="text">Text:</label>
                                <textarea
                                    id="text"
                                    value={text}
                                    onChange={(e) => setText(e.target.value)}
                                    placeholder="Enter the text to base the answer on"
                                    required
                                />
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

                        <label htmlFor="question">Question:</label>
                        <textarea
                            id="question"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="Enter your question"
                            required
                        />

                        <button type="submit">Get Answer</button>
                    </form>
                    {error && <p className="error">{error}</p>}
                </div>
            ) : (
                <div className="answer-screen">
                    <h2>Answer</h2>
                    {/* Render the answer as rich text using ReactMarkdown */}
                    <ReactMarkdown>{answer}</ReactMarkdown>
                    <button onClick={handleRestart}>Ask Another Question</button>
                </div>
            )}
        </div>
    );
}

export default HomeworkHelper;