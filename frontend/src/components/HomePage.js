import React from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

const tools = [
    { name: 'AI Summarizer', path: '/ai_summarizer' },
    { name: 'AI Quiz Creator', path: '/quiz_creator' },
    { name: 'AI Segmenter', path: '/ai_segmenter' },
    { name: 'AI Chronology', path: '/ai_chrono' },
    { name: 'AI Story Visualizer', path: '/ai_story_visualizer' },
    { name: 'AI Topic Modeller', path: '/ai_topic_modeller' },
    { name: 'AI Translator', path: '/ai_translator' },
    { name: 'AI Transcription', path: '/ai_transcription' },
    { name: 'AI Image Talker', path: '/ai_image_talker' },
    { name: 'AI Infographic Maker', path: '/ai_infographic_maker' },
    { name: 'AI Digital Debater', path: '/ai_digital_debate' },
];

function HomePage() {
    return (
        <div className="home-page">
            <h1>Welcome to the AI Tools Platform</h1>
            <div className="tool-cards">
                {tools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h2>{tool.name}</h2>
                        <Link to={tool.path}>Go to {tool.name}</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default HomePage;