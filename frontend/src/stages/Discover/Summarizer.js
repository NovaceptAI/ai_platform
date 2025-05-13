import React, { useState } from 'react';
import './Summarizer.css';
// import config from '../../config.js';
import axiosInstance from '../../utils/axiosInstance';

function RichTextDisplay({ title, content }) {
    return (
        <div className="rich-text-display">
            <h2>{title}</h2>
            <div className="content">
                {Array.isArray(content) ? (
                    <ul>
                        {content.map((item, index) => (
                            <li key={index}>{item}</li>
                        ))}
                    </ul>
                ) : (
                    <p>{content}</p>
                )}
            </div>
        </div>
    );
}

function Summarizer() {
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [summary, setSummary] = useState('');
    const [segments, setSegments] = useState([]);
    const [toc, setToc] = useState([]);
    const [tags, setTags] = useState([]);
    const [exportedData, setExportedData] = useState('');
    const [error, setError] = useState('');
    const [view, setView] = useState('summary');
    const [entities, setEntities] = useState([]);
    const [loading, setLoading] = useState(false);

    const handleTextChange = (e) => setText(e.target.value);
    const handleFileChange = (e) => setFile(e.target.files[0]);

    const handleTextSubmit = async (e) => {
        e.preventDefault();
        resetOutputStates();
        setLoading(true);

        try {
            const response = await axiosInstance.post('/summarizer/summarize_text', { text });
            const data = response.data;

            setSummary(data.summary);
            setSegments(data.segments);
            setToc(data.toc);
            setTags(data.tags);
            setEntities(data.entities);
        } catch (err) {
            setError(err.response?.data?.error || 'An error occurred while summarizing the text.');
        } finally {
            setLoading(false);
        }
    };

    const handleFileSubmit = async (e) => {
        e.preventDefault();
        resetOutputStates();
        setLoading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axiosInstance.post('/summarizer/summarize_file', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            const data = response.data;

            setSummary(data.summary);
            setSegments(data.segments);
            setToc(data.toc);
            setTags(data.tags);
            setEntities(data.entities);
        } catch (err) {
            setError(err.response?.data?.error || 'An error occurred while summarizing the file.');
        } finally {
            setLoading(false);
        }
    };

    const handleExportSubmit = async (e, format) => {
        e.preventDefault();
        setError('');
        setExportedData('');
        setLoading(true);

        try {
            const response = await axiosInstance.post('/summarizer/export_segments', {
                segments,
                format,
            });

            setExportedData(response.data.exported_data);
        } catch (err) {
            setError(err.response?.data?.error || 'An error occurred while exporting the segments.');
        } finally {
            setLoading(false);
        }
    };

    const resetOutputStates = () => {
        setError('');
        setSummary('');
        setSegments([]);
        setToc([]);
        setTags([]);
        setEntities([]);
        setExportedData('');
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
            {loading && <p className="loading">Loading...</p>} {/* Loader */}
            {error && <p className="error">{error}</p>}
            <div className="view-options">
                <button onClick={() => setView('summary')} className="view-button">Show Summary</button>
                <button onClick={() => setView('toc')} className="view-button">Show Table of Contents</button>
                <button onClick={() => setView('tags')} className="view-button">Show Tags</button>
                <button onClick={() => setView('segments')} className="view-button">Show Segments</button>
                <button onClick={() => setView('entities')} className="view-button">Show Named Entities</button>
            </div>
            {!loading && view === 'summary' && summary && (
                <RichTextDisplay title="Summary" content={summary} />
            )}
            {!loading && view === 'toc' && toc.length > 0 && (
                <RichTextDisplay title="Table of Contents" content={toc} />
            )}
            {!loading && view === 'tags' && tags.length > 0 && (
                <RichTextDisplay title="Tags" content={tags} />
            )}
            {!loading && view === 'segments' && segments.length > 0 && (
                <div className="segments">
                    <h2>Segments</h2>
                    <div className="segments-container">
                        {segments.map((segment, index) => (
                            <RichTextDisplay key={index} title={`Segment ${index + 1}`} content={segment} />
                        ))}
                    </div>
                </div>
            )}
            {!loading && view === 'entities' && entities?.length > 0 && (
                <div className="entities">
                    <h2>Named Entities</h2>
                    <div className="entities-container">
                        {entities.map((entityList, index) => (
                            <RichTextDisplay
                                key={index}
                                title={`Segment ${index + 1}`}
                                content={entityList.map(entity => `${entity.type}: ${entity.name}`)}
                            />
                        ))}
                    </div>
                </div>
            )}
            {!loading && segments.length > 0 && (
                <div className="export">
                    <h2>Export Segments</h2>
                    <button disabled onClick={(e) => handleExportSubmit(e, 'json')} className="export-button">Export as JSON</button>
                    <button disabled onClick={(e) => handleExportSubmit(e, 'csv')} className="export-button">Export as CSV</button>
                </div>
            )}
            {!loading && exportedData && (
                <div className="exported-data">
                    <h2>Exported Data</h2>
                    <pre>{JSON.stringify(exportedData, null, 2)}</pre>
                </div>
            )}
        </div>
    );
}

export default Summarizer;