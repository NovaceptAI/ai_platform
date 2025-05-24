import React, { useState, useEffect } from 'react';
import './MathProblemVisualizer.css';
import config from '../../config';
import FileUploader from '../../components/FileUploader';
import axiosInstance from '../../utils/axiosInstance';

function MathProblemVisualizer() {
    const [expression, setExpression] = useState('');
    const [visualization, setVisualization] = useState(null);
    const [solution, setSolution] = useState('');
    const [steps, setSteps] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState('');

    const resetAll = () => {
        setExpression('');
        setVisualization(null);
        setSolution('');
        setSteps([]);
        setError(null);
        setSelectedFile('');
    };

    const preprocessInput = (input) => input.replace(/\^/g, '**');

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            setVaultFiles(response.data.files || []);
        } catch (err) {
            console.error('Failed to fetch vault files:', err);
            setError('Could not fetch files from vault.');
        }
    };

    const handleVaultFileSelect = async (filename) => {
        setSelectedFile(filename);
    };

    const handleUploadComplete = async ({ stored_as }) => {
        setSelectedFile(stored_as);
        await handleVaultFileSelect(stored_as);
    };

    const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setVisualization(null);
    setLoading(true);

    try {
        const requestBody = selectedFile
            ? { filename: selectedFile, fromVault: true }
            : { problem: preprocessInput(expression) };

        const response = await fetch(
            `${config.API_BASE_URL}/math_problem_visualizer/visualize_math_problem`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            }
        );

        const result = await response.json();

        if (response.ok) {
            setSolution(result.solution);
            setSteps(result.steps || []);
            setVisualization(result.visualization);
        } else {
            setError(result.error || 'Failed to visualize the math expression.');
        }
        } catch (err) {
            console.error('Failed to fetch:', err);
            setError('An unexpected error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchVaultFiles();
    }, []);

    return (
        <div className="math-problem-visualizer">
            {!visualization ? (
                <>
                    <h1>Math Expression Plotter</h1>

                    {/* EXPRESSION INPUT */}
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="expression">Enter a Math Expression:</label>
                        <textarea
                            id="expression"
                            value={expression}
                            onChange={(e) => setExpression(e.target.value)}
                            placeholder="e.g., x^2 - 4"
                            required
                        />
                        <button type="submit" disabled={loading}>
                            {loading ? 'Plotting...' : 'Plot'}
                        </button>
                    </form>

                    {/* FILE FORM */}
                    <form onSubmit={handleSubmit} style={{ marginTop: '30px' }}>
                        <label style={{ display: 'block', marginTop: '20px' }}>
                            Upload File:
                            <FileUploader onUploadComplete={handleUploadComplete} />
                        </label>

                        <label style={{ display: 'block', marginTop: '10px' }}>
                            Or Select from Knowledge Vault:
                            <select
                                className="w-full border p-2 rounded"
                                value={selectedFile}
                                onChange={(e) => handleVaultFileSelect(e.target.value)}
                            >
                                <option value="">-- Select a file --</option>
                                {vaultFiles.map((vf, idx) => (
                                    <option key={idx} value={vf.name}>{vf.name}</option>
                                ))}
                            </select>
                        </label>

                        <button type="submit" className="submit-button" style={{ marginTop: '10px' }} disabled={loading}>
                            {loading ? 'Loading...' : 'Plot from File'}
                        </button>
                    </form>

                    {error && <p className="error">{error}</p>}
                </>
            ) : (
                <div className="visualization-screen">
                    <h2>Visualization</h2>
                    {visualization ? (
                        <img
                            src={visualization}
                            alt="Math Expression Visualization"
                            className="visualization-image"
                        />
                    ) : (
                        <p>No plot available.</p>
                    )}

                    {steps.length > 0 && (
                        <div className="solution-steps">
                            <h2>Solution Steps</h2>
                            {steps.map((step, index) => (
                                <p key={index}>{step}</p>
                            ))}
                        </div>
                    )}

                    <button onClick={resetAll}>Plot Another Expression</button>
                </div>
            )}
        </div>
    );
}

export default MathProblemVisualizer;