import React from 'react';
import { Link } from 'react-router-dom';
import '../../stages/StagesHome.css';
import { FaHighlighter, FaCut, FaSitemap, FaChalkboardTeacher, FaSuperscript, FaStream } from 'react-icons/fa';

const discoverTools = [
  { name: 'Summarizer', path: '/summarizer', icon: <FaHighlighter />, colorClass: 'card-blue' },
  { name: 'Segmenter', path: '/segmenter', icon: <FaCut />, colorClass: 'card-amber' },
  { name: 'Topic Modeller', path: '/topic_modeller', icon: <FaSitemap />, colorClass: 'card-purple' },
  { name: 'Visual Study Guide Maker', path: '/visual_study_guide_maker', icon: <FaChalkboardTeacher />, colorClass: 'card-pink' },
  { name: 'Math Problem Visualizer', path: '/math_problem_visualizer', icon: <FaSuperscript />, colorClass: 'card-teal' },
  { name: 'Timeline Explorer', path: '/timeline_explorer', icon: <FaStream />, colorClass: 'card-green' },
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