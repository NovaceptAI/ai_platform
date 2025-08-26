// src/pages/LearningPath.js
import React from 'react';
import './LearningPath.css';
import { useNavigate } from 'react-router-dom';

const learningPaths = [
  {
    id: 'LP1',
    title: 'Curious Explorer',
    icon: '🔍',
    description: 'For first-time users, students, and casual learners.',
    tools: ['Summarizer', 'Quiz Creator', 'Homework Helper', 'Study Guide'],
    estimatedTime: '15–20 min',
  },
  {
    id: 'LP2',
    title: 'Academic Researcher',
    icon: '📚',
    description: 'For graduate students and researchers.',
    tools: ['Summarizer', 'Entity Resolution', 'Topic Modelling', 'Chronology', 'Document Analyzer', 'Report Export'],
    estimatedTime: '30–40 min',
  },
  {
    id: 'LP3',
    title: 'Startup Thinker',
    icon: '🚀',
    description: 'For entrepreneurs and innovators.',
    tools: ['Summarizer', 'Segments', 'Clustering', 'Similarity', 'Concept Map', 'Presentation Builder'],
    estimatedTime: '25–35 min',
  }
];

export default function LearningPath() {
  const navigate = useNavigate();
  const goTo = (id) => navigate(`/learning-path/${id}`);

  return (
    <div className="lp-container">
      <h1 className="lp-title">📚 Choose Your Learning Path</h1>
      <p className="lp-subtitle">
        Scoolish guides you through powerful tools based on your goals. Pick a path to begin.
      </p>

      <div className="lp-grid">
        {learningPaths.map((lp) => (
          <div key={lp.id} className="lp-card">
            <div className="lp-header">
              <span className="lp-icon">{lp.icon}</span>
              <h2>{lp.title}</h2>
            </div>
            <p className="lp-description">{lp.description}</p>
            <div className="lp-tools">
              {lp.tools.map((tool, idx) => (
                <span key={idx} className="lp-tool-chip">{tool}</span>
              ))}
            </div>
            <p className="lp-time">🕒 {lp.estimatedTime}</p>
            <div className="lp-actions">
              <button className="lp-button" onClick={() => goTo(lp.id)}>View Path</button>
              <button className="lp-button primary" onClick={() => goTo(lp.id)}>Start / Resume</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
