import React, { useState } from 'react';
import './StoryVisualizer.css';
import config from '../../config.js'; // Adjust the import path as needed

function StoryVisualizer() {
    const [content, setContent] = useState('');
    const [visualization, setVisualization] = useState(null);
    const [steps, setSteps] = useState([]);
    const [error, setError] = useState('');

    const handleContentChange = (e) => {
        setContent(e.target.value);
    };

    const handleCreateStory = async (e) => {
        e.preventDefault();
        setError('');
        setVisualization(null);

        try {
            const response = await fetch(`${config.API_BASE_URL}/story_visualizer/create_story_visualization`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content }),
            });

            const data = await response.json();
            if (response.ok) {
                setVisualization(data);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while creating the story visualization.');
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
            <form onSubmit={handleCreateStory}>
                <textarea
                    value={content}
                    onChange={handleContentChange}
                    placeholder="Enter content to visualize"
                />
                <button type="submit">Create Story Visualization</button>
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