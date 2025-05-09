import React from 'react';
import { Link } from 'react-router-dom';
import '../../stages/StagesHome.css'; // Common CSS for all stage homepages

const collaborateTools = [
    { name: 'Digital Debate Platform', path: '/digital_debate' },
];

function CollaborateHome() {
    return (
        <div className="stage-home">
            <h1>Collaborate Tools</h1>
            <div className="tool-cards">
                {collaborateTools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default CollaborateHome;