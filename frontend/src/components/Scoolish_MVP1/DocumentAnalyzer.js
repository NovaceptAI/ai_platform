import React, { useState } from 'react';
import './DocumentAnalyzer.css';
import Tree from 'react-d3-tree';
import config from '../../config';

function DocumentAnalyzer() {
    const [file, setFile] = useState(null);
    const [text, setText] = useState('');
    const [analysis, setAnalysis] = useState(null);
    const [error, setError] = useState('');

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleTextChange = (e) => {
        setText(e.target.value);
    };

    const handleAnalyze = async (e) => {
        e.preventDefault();
        setError('');
        setAnalysis(null);

        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        } else {
            formData.append('text', text);
        }

        try {
            const response = await fetch(`${config.API_BASE_URL}/document_analyzer/analyze`, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();
            console.log('Response data:', data); // Debugging: Log the response data
            if (response.ok) {
                const treeData = {
                    name: data.document_title || 'Document',
                    children: data.topics.map((topic) => ({
                        name: topic || 'Untitled Topic',
                    })),
                };
                console.log('Generated tree data:', treeData); // Debugging: Log the generated tree data
                setAnalysis(treeData);
            } else {
                setError(data.error);
            }
        } catch (err) {
            console.error('Error:', err); // Debugging: Log any errors
            setError('An error occurred while analyzing the document.');
        }
    };

    return (
        <div className="document-analyzer">
            <h1>Document Analyzer</h1>
            <form onSubmit={handleAnalyze}>
                <input type="file" onChange={handleFileChange} />
                <textarea
                    value={text}
                    onChange={handleTextChange}
                    placeholder="Or enter text here"
                    rows="10"
                    style={{ marginTop: '10px', padding: '10px', fontSize: '16px' }}
                />
                <button type="submit">Analyze Document</button>
            </form>
            {error && <p className="error">{error}</p>}
            {analysis && (
                <div className="tree-container" style={{ height: '500px', width: '100%' }}>
                    <Tree
                        data={[analysis]}
                        orientation="vertical"
                        translate={{ x: 400, y: 50 }}
                        pathFunc="diagonal"
                        styles={{
                            nodes: {
                                node: {
                                    circle: { fill: '#007bff' },
                                    name: { stroke: '#0056b3', fill: '#ffffff' },
                                    attributes: { stroke: '#cccccc', fill: '#cccccc' },
                                },
                                leafNode: {
                                    circle: { fill: '#007bff' },
                                    name: { stroke: '#0056b3', fill: '#ffffff' },
                                    attributes: { stroke: '#cccccc', fill: '#cccccc' },
                                },
                            },
                            links: {
                                stroke: '#cccccc',
                                strokeWidth: 2,
                            },
                        }}
                    />
                </div>
            )}
        </div>
    );
}

export default DocumentAnalyzer;