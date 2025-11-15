import React from 'react';
import { Link } from 'react-router-dom';
import '../../stages/StagesHome.css';
import { FaHighlighter, FaCut, FaSitemap, FaChalkboardTeacher, FaSuperscript, FaStream, FaBook } from 'react-icons/fa';

const discoverTools = [
  { name: 'Summarizer', path: '/summarizer', icon: <FaHighlighter />, colorClass: 'card-blue' },
  { name: 'Evidence Extractor', path: '/evidence_extractor', icon: <FaChalkboardTeacher />, colorClass: 'card-pink' },
  { name: 'Readability & Style', path: '/readability_analyzer', icon: <FaBook />, colorClass: 'card-green' },
];

function Discover() {
  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🔎 Discover</h1>
        <p className="stage-subtitle">Explore tools that help you extract, structure, and understand information faster.</p>
      </header>

      <div className="stage-grid">
        {discoverTools.map((tool) => (
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

export default Discover;