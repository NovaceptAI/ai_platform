import React, { useState } from 'react';
import './TopicModeller.css';
import config from '../../config.js'; // Adjust the import path as needed

function TopicModeller() {
    const [documentText, setDocumentText] = useState('');
    const [documents, setDocuments] = useState([]);
    const [result, setResult] = useState('');
    const [error, setError] = useState('');

    const handleTextChange = (e) => {
        setDocumentText(e.target.value);
    };

    const handleDocumentsChange = (e) => {
        const files = e.target.files;
        const fileReaders = [];
        const fileContents = [];

        for (let i = 0; i < files.length; i++) {
            const fileReader = new FileReader();
            fileReaders.push(fileReader);

            fileReader.onload = (event) => {
                fileContents.push(event.target.result);
                if (fileContents.length === files.length) {
                    setDocuments(fileContents);
                }
            };

            fileReader.readAsText(files[i]);
        }
    };

    const handleSubmit = async (e, endpoint) => {
        e.preventDefault();
        setError('');
        setResult('');

        const payload = endpoint === '/cluster_documents' || endpoint === '/analyze_topic_trends'
            ? { documents }
            : { document_text: documentText };

        try {
            const response = await fetch(`${config.API_BASE_URL}/modeller${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            if (response.ok) {
                setResult(data);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while processing the document.');
        }
    };

    return (
        <div className="topic-modeller">
            <h1>Topic Modeller</h1>
            <textarea
                value={documentText}
                onChange={handleTextChange}
                placeholder="Enter document text"
            />
            <input type="file" multiple onChange={handleDocumentsChange} />
            <div className="buttons">
                <button onClick={(e) => handleSubmit(e, '/extract_topics')}>Extract Topics</button>
                <button onClick={(e) => handleSubmit(e, '/extract_keywords')}>Extract Keywords</button>
                <button onClick={(e) => handleSubmit(e, '/cluster_documents')}>Cluster Documents</button>
                <button onClick={(e) => handleSubmit(e, '/visualize_topics')}>Visualize Topics</button>
                <button onClick={(e) => handleSubmit(e, '/summarize_topics')}>Summarize Topics</button>
                <button onClick={(e) => handleSubmit(e, '/named_entity_recognition')}>Named Entity Recognition</button>
                <button onClick={(e) => handleSubmit(e, '/sentiment_analysis')}>Sentiment Analysis</button>
                <button onClick={(e) => handleSubmit(e, '/analyze_topic_trends')}>Analyze Topic Trends</button>
            </div>
            {error && <p className="error">{error}</p>}
            {result && (
                <div className="result">
                    <h2>Result</h2>
                    <pre>{JSON.stringify(result, null, 2)}</pre>
                </div>
            )}
        </div>
    );
}

export default TopicModeller;