// src/stages/Organize/OrganizeHome.js
import React from 'react';
import { Link } from 'react-router-dom';
import { FaLayerGroup, FaFolderOpen, FaProjectDiagram, FaEye, FaTags } from 'react-icons/fa';
import '../../stages/StagesHome.css';

const organizeTools = [
  { name: 'Clusters', path: '/clusters', icon: <FaLayerGroup />, colorClass: 'card-purple' },
  { name: 'Collections', path: '/collections', icon: <FaFolderOpen />, colorClass: 'card-pink' },
  { name: 'Concept Graphs', path: '/concept_graphs', icon: <FaProjectDiagram />, colorClass: 'card-teal' },
  { name: 'Saved Views', path: '/saved_views', icon: <FaEye />, colorClass: 'card-green' },
  { name: 'Tags Routes', path: '/tags_routes', icon: <FaTags />, colorClass: 'card-blue' },
];

function OrganizeHome() {
  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🗂️ Organize</h1>
        <p className="stage-subtitle">Arrange plans, study materials, and routines to make learning effortless.</p>
      </header>

      <div className="stage-grid">
        {organizeTools.map((tool) => (
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

export default OrganizeHome;