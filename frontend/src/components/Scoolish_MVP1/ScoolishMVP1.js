import React from 'react';
import { Link } from 'react-router-dom';
import './ScoolishMVP1.css';

const scoolishMVP1Tools = [
    { name: 'Summarizer & Segmenter', path: '/ai_summarizer' },
    { name: 'AI Quiz Creator', path: '/quiz_creator' },
    { name: 'AI Topic Modelling', path: '/ai_topic_modelling' },
    { name: 'Story Visualizer', path: '/story_visualizer' },
    { name: 'AI Chronology', path: '/chrono_ai' },
    { name: 'Digital Debate Platform', path: '/digital_debate' },
    { name: 'Document Analyzer', path: '/document_analyzer' },
];

function ScoolishMVP1() {
    return (
        <div className="scoolish-mvp-1">
            <h1>Scoolish MVP 1</h1>
            <div className="tool-cards">
                {scoolishMVP1Tools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default ScoolishMVP1;