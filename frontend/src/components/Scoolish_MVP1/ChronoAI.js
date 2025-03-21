import React, { useState } from 'react';
import './ChronoAI.css';
import config from '../../config.js'; // Adjust the import path as needed

function ChronoAI() {
    const [documentText, setDocumentText] = useState('');
    const [events, setEvents] = useState(null);
    const [error, setError] = useState('');

    const handleTextChange = (e) => {
        setDocumentText(e.target.value);
    };

    const handleAnalyze = async (e) => {
        e.preventDefault();
        setError('');
        setEvents(null);

        try {
            const response = await fetch(`${config.API_BASE_URL}/chrono_ai/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ document_text: documentText }),
            });

            const data = await response.json();
            if (response.ok) {
                setEvents(data.events);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while analyzing the document.');
        }
    };

    return (
        <div className="chrono-ai">
            <h1>Chrono AI</h1>
            <form onSubmit={handleAnalyze}>
                <textarea
                    value={documentText}
                    onChange={handleTextChange}
                    placeholder="Enter document text"
                />
                <button type="submit">Analyze Document</button>
            </form>
            {error && <p className="error">{error}</p>}
            {events && (
                <div className="events">
                    <h2>Analyzed Events</h2>
                    <pre>{JSON.stringify(events, null, 2)}</pre>
                </div>
            )}
        </div>
    );
}

export default ChronoAI;