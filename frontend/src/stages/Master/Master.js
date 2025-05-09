import React from 'react';
import { Link } from 'react-router-dom';
import '../../stages/StagesHome.css'; // Common CSS for all stage homepages

const masterTools = [
    { name: 'Quiz Creator', path: '/quiz_creator' },
    { name: 'Homework Helper', path: '/homework_helper' },
];

function MasterHome() {
    return (
        <div className="stage-home">
            <h1>Master Tools</h1>
            <div className="tool-cards">
                {masterTools.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default MasterHome;