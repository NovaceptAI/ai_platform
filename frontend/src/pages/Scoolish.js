import React from 'react';
import { Link } from 'react-router-dom';
import './Scoolish.css';

const scoolish = [
    { name: 'Discover', path: '/discover', colorClass: 'card-discover' },
    { name: 'Organize', path: '/organize', colorClass: 'card-organize' },
    { name: 'Master', path: '/master', colorClass: 'card-master' },
    { name: 'Create', path: '/create', colorClass: 'card-create' },
    { name: 'Collaborate', path: '/collaborate', colorClass: 'card-collaborate' },
    { name: 'Support', path: '/support', colorClass: 'card-support' },
    { name: 'Vault', path: '/vault', colorClass: 'card-vault' },
];

function Scoolish() {
    return (
        <div className="scoolish-mvp-1">
            <h1 className="scoolish-title">🚀 Scoolish</h1>
            <p className="scoolish-subtitle">Choose a stage to begin your journey</p>
            <div className="tool-cards">
                {scoolish.map((tool) => (
                    <div key={tool.name} className={`tool-card ${tool.colorClass}`}>
                        <h3>{tool.name}</h3>
                        <Link to={tool.path} className="try-button">Try Now →</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Scoolish;