import React, { useState, useMemo } from 'react';
import './StoryVisualizer.css';
import config from '../../config.js'; // Adjust the import path as needed

// A hardcoded list of classes and stories for the dropdowns
const CATEGORY_DATA = {
    'Class 8 ICSE Literature': [
        'The Kabuliwala',
        'After Twenty Years',
        'My Lost Dollar',
        'The Tiger in the Tunnel',
        "Ranji's Wonderful Bat"
    ],
    'Class 10 CBSE Literature': [
        'A Letter to God',
        'Nelson Mandela: Long Walk to Freedom',
        'The Diary of a Young Girl',
        'The Hundred Dresses'
    ],
    'International Literature': [
        'The Tell-Tale Heart',
        'The Gift of the Magi',
        'The Last Leaf'
    ]
};

function StoryVisualizer() {
    // New state for input method
    const [method, setMethod] = useState('category'); // 'category' | 'text' | 'document'
    const [category, setCategory] = useState('');
    const [story, setStory] = useState('');
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);

    const [visualization, setVisualization] = useState(null);
    const [steps, setSteps] = useState([]);
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const handleContentChange = (e) => {
        setText(e.target.value);
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const canSubmit = useMemo(() => {
        if (submitting) return false;
        if (method === 'category') return category && story;
        if (method === 'text') return text.trim().length > 10;
        if (method === 'document') return !!file;
        return false;
    }, [submitting, method, category, story, text, file]);

    const handleCreateStory = async (e) => {
            e.preventDefault();
            if (!canSubmit) return;

            setSubmitting(true);
            setError('');
            setVisualization(null);

            try {
                let response;
                let payload;

                if (method === 'category') {
                    const combinedText = `${category} - ${story}`;
                    payload = { method: 'text', content: combinedText };
                } else if (method === 'text') {
                    // Corrected payload to use the 'text' state variable
                    payload = { method: 'text', content: text };
                } else if (method === 'document') {
                    const formData = new FormData();
                    formData.append('method', 'document');
                    formData.append('file', file);

                    response = await fetch(`${config.API_BASE_URL}/story_visualizer/create_story_visualization`, {
                        method: 'POST',
                        body: formData,
                    });
                }

                if (method !== 'document') {
                    response = await fetch(`${config.API_BASE_URL}/story_visualizer/create_story_visualization`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                }

                const data = await response.json();
                if (response.ok) {
                    setVisualization(data);
                } else {
                    setError(data.error);
                }
            } catch (err) {
                setError('An error occurred while creating the story visualization.');
            } finally {
                setSubmitting(false);
            }
        };

    const fetchHowItWorks = async () => {
        try {
            const response = await fetch(`${config.API_BASE_URL}/story_visualizer/how_it_works`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();
            if (response.ok) {
                setSteps(data.steps);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while fetching the steps.');
        }
    };

    return (
        <div className="story-visualizer">
            <h1>Story Visualizer</h1>

            <div className="vsg-seg">
                <button type="button" className={`seg-btn ${method === 'category' ? 'active' : ''}`} onClick={() => setMethod('category')}>
                    Category
                </button>
                <button type="button" className={`seg-btn ${method === 'text' ? 'active' : ''}`} onClick={() => setMethod('text')}>
                    Paste Text
                </button>
                <button type="button" className={`seg-btn ${method === 'document' ? 'active' : ''}`} onClick={() => setMethod('document')}>
                    Upload File
                </button>
            </div>

            <form onSubmit={handleCreateStory}>
                {method === 'category' && (
                    <div className="vsg-field">
                        <label className="vsg-label">Choose a Class</label>
                        <select className="vsg-select" value={category} onChange={(e) => {
                            setCategory(e.target.value);
                            setStory('');
                        }}>
                            <option value="">Select a class...</option>
                            {Object.keys(CATEGORY_DATA).map(className => (
                                <option key={className} value={className}>{className}</option>
                            ))}
                        </select>
                        {category && (
                            <>
                                <label className="vsg-label" style={{marginTop: '16px'}}>Choose a Story</label>
                                <select className="vsg-select" value={story} onChange={(e) => setStory(e.target.value)}>
                                    <option value="">Select a story...</option>
                                    {CATEGORY_DATA[category].map(storyName => (
                                        <option key={storyName} value={storyName}>{storyName}</option>
                                    ))}
                                </select>
                            </>
                        )}
                    </div>
                )}
                {method === 'text' && (
                    <div className="vsg-field">
                        <label className="vsg-label">Paste Text</label>
                        <textarea
                            value={text} // Changed from {content} to {text}
                            onChange={handleContentChange}
                            placeholder="Enter content to visualize"
                        />
                    </div>
                )}
                {method === 'document' && (
                    <div className="vsg-field">
                        <label className="vsg-label">Upload a Document</label>
                        <input type="file" onChange={handleFileChange} />
                    </div>
                )}

                <button type="submit" disabled={!canSubmit}>
                    {submitting ? 'Creating...' : 'Create Story Visualization'}
                </button>
            </form>
            {error && <p className="error">{error}</p>}
            {visualization && (
                <div className="visualization">
                    <h2>Story Visualization</h2>
                    <pre>{JSON.stringify(visualization, null, 2)}</pre>
                </div>
            )}
            <button onClick={fetchHowItWorks}>How It Works</button>
            {steps.length > 0 && (
                <div className="how-it-works">
                    <h2>How It Works</h2>
                    <ol>
                        {steps.map((step, index) => (
                            <li key={index}>{step}</li>
                        ))}
                    </ol>
                </div>
            )}
        </div>
    );
}

export default StoryVisualizer;
