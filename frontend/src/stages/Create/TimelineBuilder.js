import React, { useState } from 'react';
import './TimelineBuilder.css';
import config from '../../config';

function TimelineBuilder() {
    const [method, setMethod] = useState('category'); // State to manage the input method
    const [category, setCategory] = useState('');
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [timeline, setTimeline] = useState(null); // State to store the generated timeline
    const [error, setError] = useState(null); // State to handle errors

    const generateTimeline = async () => {
        let response;
        try {
            if (method === 'category') {
                // Category-based timeline generation
                response = await fetch(`${config.API_BASE_URL}/timeline_builder/generate_timeline`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method, category }),
                });
            } else if (method === 'text') {
                // Text-based timeline generation
                response = await fetch(`${config.API_BASE_URL}/timeline_builder/generate_timeline`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method, text }),
                });
            } else if (method === 'document') {
                // Document-based timeline generation
                const formData = new FormData();
                formData.append('file', file);

                response = await fetch(`${config.API_BASE_URL}/timeline_builder/generate_timeline`, {
                    method: 'POST',
                    body: formData,
                });
            }

            const result = await response.json();
            if (response.ok) {
                setTimeline(result); // Store the generated timeline
            } else {
                setError(result.error || 'Failed to generate the timeline.');
            }
        } catch (error) {
            console.error('Failed to fetch:', error);
            setError('Failed to fetch timeline. Please try again.');
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null); // Clear any previous errors
        setTimeline(null); // Clear any previous timeline
        generateTimeline();
    };

    const handleRestart = () => {
        setMethod('category');
        setCategory('');
        setText('');
        setFile(null);
        setTimeline(null);
        setError(null);
    };

    return (
        <div className="timeline-builder">
            {!timeline ? (
                <div>
                    <h1>Historical Timeline Builder</h1>
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
                                    placeholder="Enter a category (e.g., World War II)"
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
                                    placeholder="Enter the text to base the timeline on"
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

                        <button type="submit">Generate Timeline</button>
                    </form>
                    {error && <p className="error">{error}</p>}
                </div>
            ) : (
                <div className="timeline-screen">
                    <h2>Generated Timeline</h2>
                    <ul>
                        {timeline.events.map((event, index) => (
                            <li key={index} className="timeline-event">
                                <h3>{event.date}: {event.title}</h3>
                                <p>{event.description}</p>
                                {event.media && (
                                    <img src={event.media} alt={event.title} className="timeline-media" />
                                )}
                            </li>
                        ))}
                    </ul>
                    <button onClick={handleRestart}>Generate Another Timeline</button>
                </div>
            )}
        </div>
    );
}

export default TimelineBuilder;