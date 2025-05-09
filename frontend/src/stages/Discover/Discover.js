import React from 'react';
import { Link } from 'react-router-dom';
import '../../stages/StagesHome.css'; // Common CSS for all stage homepages

const discoverTools = [
    { name: 'Summarizer', path: '/summarizer' },
    { name: 'Segmenter', path: '/segmenter' },
    { name: 'Topic Modeller', path: '/topic_modeller' },
    { name: 'Visual Study Guide Maker', path: '/visual_study_guide_maker' },
    { name: 'Math Problem Visualizer', path: '/math_problem_visualizer' },
];

function Discover() {
    return (
        <div className="stage-home">
            <h1>Discover Tools</h1>
            <div className="tool-cards">
                {discoverTools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Discover;