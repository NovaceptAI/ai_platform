import React, { useState } from 'react';
import './Segmenter.css';
import config from '../../config.js'; // Adjust the import path as needed

function Segmenter() {
    const [documentText, setDocumentText] = useState('');
    const [file, setFile] = useState(null);
    const [result, setResult] = useState('');
    const [error, setError] = useState('');

    const handleTextChange = (e) => {
        setDocumentText(e.target.value);
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleSubmit = async (e, endpoint) => {
        e.preventDefault();
        setError('');
        setResult('');

        try {
            let response;
            if (file) {
                const formData = new FormData();
                formData.append('file', file);

                response = await fetch(`${config.API_BASE_URL}/segmenter${endpoint}`, {
                    method: 'POST',
                    body: formData,
                });
            } else {
                response = await fetch(`${config.API_BASE_URL}/segmenter${endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ document_text: documentText }),
                });
            }

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
        <div className="segmenter">
            <h1>Document Segmenter</h1>
            <textarea
                value={documentText}
                onChange={handleTextChange}
                placeholder="Enter document text"
            />
            <input type="file" onChange={handleFileChange} />
            <div className="buttons">
                <button onClick={(e) => handleSubmit(e, '/segment_document')}>Segment Document</button>
                <button onClick={(e) => handleSubmit(e, '/extract_keywords')}>Extract Keywords</button>
                <button onClick={(e) => handleSubmit(e, '/summarize_document')}>Summarize Document</button>
                <button onClick={(e) => handleSubmit(e, '/named_entity_recognition')}>Named Entity Recognition</button>
                <button onClick={(e) => handleSubmit(e, '/sentiment_analysis')}>Sentiment Analysis</button>
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

export default Segmenter;