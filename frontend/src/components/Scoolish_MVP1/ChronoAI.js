import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown'; // Import react-markdown for rich text rendering
import './ChronoAI.css';
import config from '../../config.js'; // Adjust the import path as needed

function ChronoAI() {
    const [documentText, setDocumentText] = useState('');
    const [file, setFile] = useState(null);
    const [events, setEvents] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleTextChange = (e) => {
        setDocumentText(e.target.value);
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleAnalyzeText = async (e) => {
        e.preventDefault();
        setError('');
        setEvents(null);
        setLoading(true);

        try {
            const response = await fetch(`${config.API_BASE_URL}/chrono_ai/extract_chronology_from_text`, {
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
            setError('An error occurred while analyzing the text.');
        } finally {
            setLoading(false);
        }
    };

    const handleAnalyzeFile = async (e) => {
        e.preventDefault();
        setError('');
        setEvents(null);
        setLoading(true);

        if (!file) {
            setError('No file selected. Please upload a file.');
            setLoading(false);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${config.API_BASE_URL}/chrono_ai/extract_chronology_from_file`, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();
            if (response.ok) {
                setEvents(data.events);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while analyzing the file.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chrono-ai">
            <h1>Chrono AI</h1>
            <form onSubmit={handleAnalyzeText}>
                <textarea
                    value={documentText}
                    onChange={handleTextChange}
                    placeholder="Enter document text"
                />
                <button type="submit" disabled={loading}>
                    {loading ? 'Analyzing...' : 'Analyze Text'}
                </button>
            </form>
            <form onSubmit={handleAnalyzeFile}>
                <input type="file" onChange={handleFileChange} />
                <button type="submit" disabled={loading}>
                    {loading ? 'Analyzing...' : 'Analyze File'}
                </button>
            </form>
            {error && <p className="error">{error}</p>}
            {events && (
                <div className="events">
                    <h2>Analyzed Events</h2>
                    {/* Render events as rich text using ReactMarkdown */}
                    <ReactMarkdown>{events}</ReactMarkdown>
                </div>
            )}
        </div>
    );
}

export default ChronoAI;