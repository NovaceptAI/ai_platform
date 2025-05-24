import React, { useState, useEffect } from 'react';
import './Summarizer.css';
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
    const [selectedVaultFile, setSelectedVaultFile] = useState('');
    const [vaultFiles, setVaultFiles] = useState([]);
    const [summary, setSummary] = useState('');
    const [segments, setSegments] = useState([]);
    const [toc, setToc] = useState([]);
    const [tags, setTags] = useState([]);
    const [entities, setEntities] = useState([]);
    const [exportedData, setExportedData] = useState('');
    const [error, setError] = useState('');
    const [view, setView] = useState('summary');
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);

    useEffect(() => {
        fetchVaultFiles();
    }, []);

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            setVaultFiles(response.data.files || []);
        } catch (err) {
            setError('Failed to fetch vault files.');
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

        try {
            if (selectedVaultFile) {
                const summarizerResponse = await axiosInstance.post('/summarizer/summarize_file', {
                    filename: selectedVaultFile,
                    fromVault: true,
                });

                const data = summarizerResponse.data;
                setSummary(data.summary);
                setSegments(data.segments);
                setToc(data.toc);
                setTags(data.tags);
                setEntities(data.entities);
            } else {
                setError('Please select or upload a file.');
            }
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

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        setError('');

        const formData = new FormData();
        formData.append('file', file);

        try {
             const response = await axiosInstance.post('/upload/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
            const storedAs = response.data.stored_as;
            await fetchVaultFiles();
            setSelectedVaultFile(storedAs);
        } catch (err) {
            console.error(err);
            setError('File upload failed.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="summarizer">
            <h1>Summarizer</h1>

            {/* TEXT FORM */}
            <form onSubmit={handleTextSubmit}>
                <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Enter text to summarize"
                    rows="10"
                    style={{
                        marginTop: '10px',
                        padding: '10px',
                        fontSize: '16px',
                        width: '100%',
                        height: '200px',
                        borderRadius: '8px',
                        border: '1px solid #ccc',
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                    }}
                />
                <button type="submit" className="submit-button">Summarize Text</button>
            </form>

            {/* FILE FORM */}
            <form onSubmit={handleFileSubmit}>
                <label style={{ display: 'block', marginTop: '20px' }}>
                    Upload File:
                    <input type="file" onChange={handleFileUpload} disabled={uploading} />
                </label>

                <label style={{ display: 'block', marginTop: '10px' }}>
                    Or Select from Knowledge Vault:
                    <select
                        className="w-full border p-2 rounded"
                        value={selectedVaultFile}
                        onChange={(e) => setSelectedVaultFile(e.target.value)}
                    >
                        <option value="">-- Select a file --</option>
                        {vaultFiles.map((vf, idx) => (
                            <option key={idx} value={vf.name}>{vf.name}</option>
                        ))}
                    </select>
                </label>

                <button type="submit" className="submit-button" style={{ marginTop: '10px' }}>
                    Summarize File
                </button>
            </form>

            {uploading && <p className="loading">Uploading file...</p>}
            {loading && <p className="loading">Loading...</p>}
            {error && <p className="error">{error}</p>}

            {/* VIEW TOGGLE */}
            <div className="view-options">
                <button onClick={() => setView('summary')} className="view-button">Show Summary</button>
                <button onClick={() => setView('toc')} className="view-button">Show Table of Contents</button>
                <button onClick={() => setView('tags')} className="view-button">Show Tags</button>
                <button onClick={() => setView('segments')} className="view-button">Show Segments</button>
                <button onClick={() => setView('entities')} className="view-button">Show Named Entities</button>
            </div>

            {/* OUTPUT DISPLAY */}
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
            {!loading && view === 'entities' && entities.length > 0 && (
                <div className="entities">
                    <h2>Named Entities</h2>
                    <div className="entities-container">
                        {entities.map((entityGroup, index) => (
                            <RichTextDisplay
                                key={index}
                                title={`Segment ${index + 1}`}
                                content={entityGroup.map(entity => `${entity.type}: ${entity.name}`)}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* EXPORT SECTION */}
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