import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown'; // Import react-markdown
import './TopicModeller.css';
import config from '../../config.js'; // Adjust the import path as needed

function TopicModeller() {
    const [file, setFile] = useState(null); // Single file state
    const [topics, setTopics] = useState(''); // Separate state for topics
    const [keywords, setKeywords] = useState(''); // Separate state for keywords
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false); // Loading state

    const handleFileChange = (e) => {
        setFile(e.target.files[0]); // Set the selected file
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setTopics('');
        setKeywords('');
        setLoading(true); // Start loading

        if (!file) {
            setError('No file selected. Please upload a file.');
            setLoading(false); // Stop loading
            return;
        }

        const formData = new FormData();
        formData.append('file', file); // Append the single file to FormData

        try {
            const response = await fetch(`${config.API_BASE_URL}/modeller/extract_topics_keywords`, {
                method: 'POST',
                body: formData, // Send FormData directly
            });

            const data = await response.json();
            if (response.ok) {
                setTopics(data.topics); // Set topics
                setKeywords(data.keywords); // Set keywords
            } else {
                setError(data.error || 'An error occurred while processing the request.');
            }
        } catch (err) {
            console.error('Error:', err); // Log the error for debugging
            setError('An error occurred while processing the document.');
        } finally {
            setLoading(false); // Stop loading
        }
    };

    return (
        <div className="topic-modeller">
            <h1>Topic Modeller</h1>
            <input type="file" onChange={handleFileChange} /> {/* Single file input */}
            <div className="buttons">
                <button onClick={handleSubmit} disabled={loading}>
                    {loading ? 'Processing...' : 'Extract Topics and Keywords'}
                </button>
            </div>
            {loading && <div className="loading-bar">Loading...</div>} {/* Loading bar */}
            {error && <p className="error">{error}</p>}
            {topics && (
                <div className="result">
                    <h2>Topics</h2>
                    <ReactMarkdown>{topics}</ReactMarkdown> {/* Render topics as rich text */}
                </div>
            )}
            {keywords && (
                <div className="result">
                    <h2>Keywords</h2>
                    <ReactMarkdown>{keywords}</ReactMarkdown> {/* Render keywords as rich text */}
                </div>
            )}
        </div>
    );
}

export default TopicModeller;