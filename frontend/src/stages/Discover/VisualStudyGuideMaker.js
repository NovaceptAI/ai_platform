import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown'; // For rich text rendering
import './VisualStudyGuideMaker.css';
import config from '../../config';

function VisualStudyGuideMaker() {
    const [method, setMethod] = useState('category'); // State to manage the input method
    const [category, setCategory] = useState('');
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [studyGuide, setStudyGuide] = useState(null); // State to store the generated study guide
    const [error, setError] = useState(null); // State to handle errors

    const generateStudyGuide = async () => {
        let response;
        try {
            if (method === 'category') {
                // Category-based study guide generation
                response = await fetch(`${config.API_BASE_URL}/study_guide/generate_visual_study_guide`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method, category }),
                });
            } else if (method === 'text') {
                // Text-based study guide generation
                response = await fetch(`${config.API_BASE_URL}/study_guide/generate_visual_study_guide`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method, text }),
                });
            } else if (method === 'document') {
                // Document-based study guide generation
                const formData = new FormData();
                formData.append('file', file);

                response = await fetch(`${config.API_BASE_URL}/study_guide/generate_visual_study_guide`, {
                    method: 'POST',
                    body: formData,
                });
            }

            const result = await response.json();
            if (response.ok) {
                setStudyGuide(result); // Store the generated study guide
            } else {
                setError(result.error || 'Failed to generate the study guide.');
            }
        } catch (error) {
            console.error('Failed to fetch:', error);
            setError('Failed to fetch study guide. Please try again.');
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null); // Clear any previous errors
        setStudyGuide(null); // Clear any previous study guide
        generateStudyGuide();
    };

    const handleRestart = () => {
        setMethod('category');
        setCategory('');
        setText('');
        setFile(null);
        setStudyGuide(null);
        setError(null);
    };

    return (
        <div className="visual-study-guide-maker">
            {!studyGuide ? (
                <div>
                    <h1>Visual Study Guide Maker</h1>
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="method">Input Method:</label>
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
                                    placeholder="Enter the text to base the study guide on"
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

                        <button type="submit">Generate Study Guide</button>
                    </form>
                    {error && <p className="error">{error}</p>}
                </div>
            ) : (
                <div className="study-guide-screen">
                    <h2>Generated Study Guide</h2>
                    {studyGuide.topics.map((topic, index) => (
                        <div key={index} className="study-guide-topic">
                            <h3>{topic.name}</h3>
                            <p><strong>Study Method:</strong> {topic.study_method}</p>
                            <p><strong>Time:</strong> {topic.time} minutes</p>
                            <p><strong>Order:</strong> {topic.order}</p>
                        </div>
                    ))}
                    <button onClick={handleRestart}>Generate Another Study Guide</button>
                </div>
            )}
        </div>
    );
}

export default VisualStudyGuideMaker;