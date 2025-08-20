// src/stages/Collaborate/CollaborateHome.js
import React from 'react';
import { Link } from 'react-router-dom';
import { FaComments, FaProjectDiagram } from 'react-icons/fa';
import '../../stages/StagesHome.css';

const collaborateTools = [
  { name: 'Digital Debate Platform', path: '/digital_debate', icon: <FaComments />, colorClass: 'card-blue' },
  { name: 'Collaborative Mind Mapping', path: '/collaborative_mind_mapping', icon: <FaProjectDiagram />, colorClass: 'card-amber' },
];

function CollaborateHome() {
  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🤝 Collaborate</h1>
        <p className="stage-subtitle">Work together in real time to explore ideas and build better outcomes.</p>
      </header>

      <div className="stage-grid">
        {collaborateTools.map((tool) => (
          <div key={tool.name} className={`stage-card ${tool.colorClass}`}>
            <div className="card-top">
              <span className="card-icon">{tool.icon}</span>
              <h3 className="card-title" title={tool.name}>{tool.name}</h3>
            </div>
            <div className="card-actions">
              <Link to={tool.path} className="try-btn">Try Now →</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default CollaborateHome;