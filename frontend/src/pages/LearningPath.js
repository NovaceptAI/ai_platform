// src/pages/LearningPath.js
import React, { useEffect, useState } from 'react';
import './LearningPath.css';
import axiosInstance from '../utils/axiosInstance';

const learningPaths = [
  {
    id: 'LP1',
    title: 'Curious Explorer',
    icon: '🔍',
    description: 'For first-time users, students, and casual learners.',
    tools: ['Summarizer', 'Learn by Drawing', 'Homework Helper', 'Quiz Creator', 'Comics Converter'],
    estimatedTime: '15–20 min',
  },
  {
    id: 'LP2',
    title: 'Academic Researcher',
    icon: '📚',
    description: 'For graduate students and researchers.',
    tools: ['Summarizer', 'Entity Resolution', 'Topic Modelling', 'Clustering', 'Chronology', 'Similarity', 'Mind Mapping'],
    estimatedTime: '30–40 min',
  },
  {
    id: 'LP3',
    title: 'Startup Thinker',
    icon: '🚀',
    description: 'For entrepreneurs and innovators.',
    tools: ['Summarizer', 'Sentiment Analyser', 'Clustering', 'Entity Resolution', 'Topic Modelling', 'Debate Platform', '3D Model Builder'],
    estimatedTime: '25–35 min',
  }
];

export default function LearningPath() {
  const [progress, setProgress] = useState({});

  useEffect(() => {
    // Optional: Fetch progress from backend
    // axiosInstance.get('/progress/all_paths').then(res => setProgress(res.data));
  }, []);

  const handleButtonMouseMove = (event) => {
    const target = event.currentTarget;
    const rect = target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    target.style.setProperty('--x', `${x}px`);
    target.style.setProperty('--y', `${y}px`);
  };

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
              <button className="lp-button" onMouseMove={handleButtonMouseMove}>View Path</button>
              <button className="lp-button primary" onMouseMove={handleButtonMouseMove}>Start / Resume</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
