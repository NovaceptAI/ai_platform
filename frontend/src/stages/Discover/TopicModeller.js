import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './TopicModeller.css';
import config from '../../config.js';
import axiosInstance from '../../utils/axiosInstance'; // Use your configured axios instance

function TopicModeller() {
    const [file, setFile] = useState(null);
    const [vaultFiles, setVaultFiles] = useState([]); // Vault file list
    const [selectedVaultFile, setSelectedVaultFile] = useState(''); // Selected file from vault
    const [topics, setTopics] = useState('');
    const [keywords, setKeywords] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // Fetch Knowledge Vault files on mount
    useEffect(() => {
        const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            setVaultFiles(response.data.files || []);
        } catch (err) {
            setError('Failed to fetch vault files.');
        }
    };
        fetchVaultFiles();
    }, []);

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
        setSelectedVaultFile(''); // Clear vault selection if direct upload
    };

    const handleVaultSelection = (e) => {
        setSelectedVaultFile(e.target.value);
        setFile(null); // Clear file input if vault file is chosen
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setTopics('');
        setKeywords('');
        setLoading(true);

        try {
            let response;

            if (selectedVaultFile) {
                response = await axiosInstance.post('/modeller/extract_topics_keywords', {
                    fromVault: true,
                    filename: selectedVaultFile,
                });
            } else if (file) {
                const formData = new FormData();
                formData.append('file', file);
                response = await fetch(`${config.API_BASE_URL}/modeller/extract_topics_keywords`, {
                    method: 'POST',
                    body: formData,
                });
                response = await response.json();
            } else {
                setError('No file selected. Please upload a file or choose from the Knowledge Vault.');
                setLoading(false);
                return;
            }

            if (response?.data) {
                setTopics(response.data.topics);
                setKeywords(response.data.keywords);
            } else if (response?.topics && response?.keywords) {
                setTopics(response.topics);
                setKeywords(response.keywords);
            } else {
                setError(response?.error || 'Failed to extract topics and keywords.');
            }
        } catch (err) {
            console.error('Error:', err);
            setError('An error occurred while processing the document.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="topic-modeller">
            <h1>Topic Modeller</h1>

            <label>Upload File:</label>
            <input type="file" onChange={handleFileChange} />

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

            <div className="buttons">
                <button onClick={handleSubmit} disabled={loading}>
                    {loading ? 'Processing...' : 'Extract Topics and Keywords'}
                </button>
            </div>

            {loading && <div className="loading-bar">Loading...</div>}
            {error && <p className="error">{error}</p>}

            {topics && (
                <div className="result">
                    <h2>Topics</h2>
                    <ReactMarkdown>{topics}</ReactMarkdown>
                </div>
            )}
            {keywords && (
                <div className="result">
                    <h2>Keywords</h2>
                    <ReactMarkdown>{keywords}</ReactMarkdown>
                </div>
            )}
        </div>
    );
}

export default TopicModeller;