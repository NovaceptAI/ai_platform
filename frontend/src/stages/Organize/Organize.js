// src/stages/Organize/OrganizeHome.js
import React from 'react';
import { Link } from 'react-router-dom';
import { FaChalkboardTeacher, FaCalendarCheck, FaClipboardList, FaMusic, FaHeadphones } from 'react-icons/fa';
import '../../stages/StagesHome.css';

const organizeTools = [
  { name: 'Mindful Study Planner', path: '/mindful_study_planner', icon: <FaCalendarCheck />, colorClass: 'card-purple' },
  { name: 'AI Lesson Plan Designer', path: '/ai_lesson_plan_designer', icon: <FaClipboardList />, colorClass: 'card-pink' },
  { name: 'Mood-Based Study Music Generator', path: '/mood_study_music', icon: <FaMusic />, colorClass: 'card-teal' },
  { name: 'Music to Study By', path: '/music_to_study_by', icon: <FaHeadphones />, colorClass: 'card-green' },
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