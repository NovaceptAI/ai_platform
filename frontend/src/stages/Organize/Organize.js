import React from 'react';
import { Link } from 'react-router-dom';
import '../../stages/StagesHome.css'; // Common CSS for all stage homepages

const organizeTools = [
    // { name: 'Digital Debate Platform', path: '/digital_debate' },
];

function OrganizeHome() {
    return (
        <div className="stage-home">
            <h1>Organize Tools</h1>
            <div className="tool-cards">
                {organizeTools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default OrganizeHome;