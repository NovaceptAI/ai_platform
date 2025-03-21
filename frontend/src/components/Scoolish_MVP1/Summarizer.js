import React, { useState } from 'react';
import './Summarizer.css';
import config from '../../config.js';

function Summarizer() {
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [summary, setSummary] = useState('');
    const [segments, setSegments] = useState([]);
    const [toc, setToc] = useState([]);
    const [tags, setTags] = useState([]);
    const [exportedData, setExportedData] = useState('');
    const [error, setError] = useState('');
    const [view, setView] = useState('summary'); // State to manage the view

    const handleTextChange = (e) => {
        setText(e.target.value);
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleTextSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSummary('');
        setSegments([]);
        setToc([]);
        setTags([]);

        try {
            const response = await fetch(`${config.API_BASE_URL}/summarizer/summarize_text`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();
            if (response.ok) {
                setSummary(data.summary);
                setSegments(data.segments);
                setToc(data.toc);
                setTags(data.tags);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while summarizing the text.');
        }
    };

    const handleFileSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSummary('');
        setSegments([]);
        setToc([]);
        setTags([]);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${config.API_BASE_URL}/summarizer/summarize_file`, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();
            if (response.ok) {
                setSummary(data.summary);
                setSegments(data.segments);
                setToc(data.toc);
                setTags(data.tags);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while summarizing the file.');
        }
    };

    const handleExportSubmit = async (e, format) => {
        e.preventDefault();
        setError('');
        setExportedData('');

        try {
            const response = await fetch(`${config.API_BASE_URL}/summarizer/export_segments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ segments, format }),
            });

            const data = await response.json();
            if (response.ok) {
                setExportedData(data.exported_data);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while exporting the segments.');
        }
    };

    return (
        <div className="summarizer">
            <h1>Summarizer</h1>
            <form onSubmit={handleTextSubmit}>
                <textarea
                    value={text}
                    onChange={handleTextChange}
                    placeholder="Enter text to summarize"
                    rows="10"
                    style={{ marginTop: '10px', padding: '10px', fontSize: '16px', width: '100%', height: '200px', borderRadius: '8px', border: '1px solid #ccc', boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)' }}
                />
                <button type="submit" className="submit-button">Summarize Text</button>
            </form>
            <form onSubmit={handleFileSubmit}>
                <input type="file" onChange={handleFileChange} className="file-input" />
                <button type="submit" className="submit-button">Summarize File</button>
            </form>
            {error && <p className="error">{error}</p>}
            <div className="view-options">
                <button onClick={() => setView('summary')} className="view-button">Show Summary</button>
                <button onClick={() => setView('toc')} className="view-button">Show Table of Contents</button>
                <button onClick={() => setView('tags')} className="view-button">Show Tags</button>
                <button onClick={() => setView('segments')} className="view-button">Show Segments</button>
            </div>
            {view === 'summary' && summary && (
                <div className="summary">
                    <h2>Summary</h2>
                    <p>{summary}</p>
                </div>
            )}
            {view === 'toc' && toc.length > 0 && (
                <div className="toc">
                    <h2>Table of Contents</h2>
                    <ul>
                        {toc.map((item, index) => (
                            <li key={index}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}
            {view === 'tags' && tags.length > 0 && (
                <div className="tags">
                    <h2>Tags</h2>
                    <ul>
                        {tags.map((tag, index) => (
                            <li key={index}>{tag}</li>
                        ))}
                    </ul>
                </div>
            )}
            {view === 'segments' && segments.length > 0 && (
                <div className="segments">
                    <h2>Segments</h2>
                    <div className="segments-container">
                        {segments.map((segment, index) => (
                            <div key={index} className="segment">
                                <h3>Segment {index + 1}</h3>
                                <p>{segment}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
            {segments.length > 0 && (
                <div className="export">
                    <h2>Export Segments</h2>
                    <button onClick={(e) => handleExportSubmit(e, 'json')} className="export-button">Export as JSON</button>
                    <button onClick={(e) => handleExportSubmit(e, 'csv')} className="export-button">Export as CSV</button>
                </div>
            )}
            {exportedData && (
                <div className="exported-data">
                    <h2>Exported Data</h2>
                    <pre>{JSON.stringify(exportedData, null, 2)}</pre>
                </div>
            )}
        </div>
    );
}

export default Summarizer;