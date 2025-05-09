import React from 'react';
import { Link } from 'react-router-dom';
import './Create.css'; // Common CSS for all stage homepages

const createTools = [
    { name: 'Story Visualizer', path: '/story_visualizer' },
    { name: 'Timeline Builder', path: '/timeline_builder' },
];

function Create() {
    return (
        <div className="stage-home">
            <h1>Create Tools</h1>
            <div className="tool-cards">
                {createTools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Create;