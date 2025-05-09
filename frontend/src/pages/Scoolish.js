import React from 'react';
import { Link } from 'react-router-dom';
import './Scoolish.css';

const scoolish = [
    { name: 'Discover', path: '/discover' },
    { name: 'Organize', path: '/organize' },
    { name: 'Master', path: '/master' },
    { name: 'Create', path: '/create' },
    { name: 'Collaborate', path: '/collaborate' },
    { name: 'Support', path: '/support' },
    { name: 'Vault', path: '/vault' },
];

function Scoolish() {
    return (
        <div className="scoolish-mvp-1">
            <h1>Scoolish</h1>
            <div className="tool-cards">
                {scoolish.map((tool) => (
                    <div key={tool.name} className="tool-card">
                        <h3>{tool.name}</h3>
                        <Link to={tool.path}>Try Now</Link>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Scoolish;