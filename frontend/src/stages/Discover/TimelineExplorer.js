import React, { useState, useEffect } from 'react';
import './TimelineExplorer.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

function TimelineExplorer() {
    const [method, setMethod] = useState('category');
    const [category, setCategory] = useState('');
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedVaultFile, setSelectedVaultFile] = useState('');
    const [uploading, setUploading] = useState(false);
    const [timeline, setTimeline] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchVaultFiles();
    }, []);

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            setVaultFiles(response.data.files || []);
        } catch (err) {
            console.error('Failed to fetch vault files:', err);
            setError('Failed to load vault files.');
        }
    };

    const handleFileUpload = async (e) => {
        const selectedFile = e.target.files[0];
        if (!selectedFile) return;

        setUploading(true);
        const formData = new FormData();
        formData.append('file', selectedFile);

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

    const generateTimeline = async () => {
        try {
            let result;

            if (method === 'category' || method === 'text') {
                const body =
                    method === 'category'
                        ? JSON.stringify({ method, category })
                        : JSON.stringify({ method, text });

                const response = await fetch(`${config.API_BASE_URL}/timeline_explorer/generate_timeline`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body,
                });

                result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Failed to generate the timeline.');
                }
            } else if (method === 'document') {
                if (selectedVaultFile) {
                    // Use file from vault — AXIOS
                    const axiosResponse = await axiosInstance.post('/timeline_explorer/generate_timeline', {
                        method: 'document',
                        fromVault: true,
                        filename: selectedVaultFile,
                    });
                    result = axiosResponse.data;
                } else if (file) {
                    // Use uploaded file — FETCH
                    const formData = new FormData();
                    formData.append('file', file);

                    const response = await fetch(`${config.API_BASE_URL}/timeline_explorer/generate_timeline`, {
                        method: 'POST',
                        body: formData,
                    });

                    result = await response.json();

                    if (!response.ok) {
                        throw new Error(result.error || 'Failed to generate the timeline.');
                    }
                } else {
                    throw new Error('No file selected or uploaded.');
                }
            }

            setTimeline(result);
        } catch (err) {
            console.error('Failed to fetch:', err);
            setError(err.message || 'Failed to fetch timeline. Please try again.');
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null);
        setTimeline(null);
        generateTimeline();
    };

    const handleRestart = () => {
        setMethod('category');
        setCategory('');
        setText('');
        setFile(null);
        setSelectedVaultFile('');
        setTimeline(null);
        setError(null);
    };

    return (
        <div className="timeline-explorer">
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
                                <p style={{ fontSize: '0.85rem', color: '#777', marginTop: '4px' }}>
                                    Note: AI-generated events are based on information available up to <strong>August 2023</strong>.
                                </p>
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
                                    disabled={uploading}
                                />

                                <label htmlFor="vaultSelect" style={{ display: 'block', marginTop: '10px' }}>
                                    Or select from Knowledge Vault:
                                    <select
                                        id="vaultSelect"
                                        value={selectedVaultFile}
                                        onChange={(e) => setSelectedVaultFile(e.target.value)}
                                    >
                                        <option value="">-- Select a file --</option>
                                        {vaultFiles.map((vf, idx) => (
                                            <option key={idx} value={vf.name}>{vf.name}</option>
                                        ))}
                                    </select>
                                </label>
                                {uploading && <p className="loading">Uploading file...</p>}
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
                        {timeline.map((event, index) => (
                            <li key={index} className="timeline-event">
                                <h3>{event[0]}: {event[1]}</h3>
                                <p>{event[2]}</p>
                            </li>
                        ))}
                    </ul>
                    <button onClick={handleRestart}>Generate Another Timeline</button>
                </div>
            )}
        </div>
    );
}

export default TimelineExplorer;