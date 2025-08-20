// src/stages/Master/MasterHome.js
import React from 'react';
import { Link } from 'react-router-dom';
import {
  FaQuestionCircle,
  FaBookOpen,
  FaSuperscript,
  FaFlask,
  FaLanguage,
  FaCode,
  FaClone,
  FaCogs,
  FaBalanceScale,
} from 'react-icons/fa';
import '../../stages/StagesHome.css';

const masterTools = [
  { name: 'Interactive Quiz Creator', path: '/quiz_creator', icon: <FaQuestionCircle />, colorClass: 'card-blue' },
  { name: 'AI-Powered Homework Helper', path: '/homework_helper', icon: <FaBookOpen />, colorClass: 'card-amber' },
  { name: 'Math Problem Visualizer', path: '/math_problem_visualizer', icon: <FaSuperscript />, colorClass: 'card-teal' },
  { name: 'Virtual Science Lab', path: '/virtual_science_lab', icon: <FaFlask />, colorClass: 'card-green' },
  { name: 'Language Learning Games', path: '/language_learning_games', icon: <FaLanguage />, colorClass: 'card-purple' },
  { name: 'Code Playground for Kids (AI Coding)', path: '/code_playground_kids', icon: <FaCode />, colorClass: 'card-pink' },
  { name: 'Customizable Flashcard Creator', path: '/flashcard_creator', icon: <FaClone />, colorClass: 'card-amber' },
  { name: 'STEM Challenge Generator', path: '/stem_challenge_generator', icon: <FaCogs />, colorClass: 'card-teal' },
  { name: 'Ethical AI Tutor', path: '/ethical_ai_tutor', icon: <FaBalanceScale />, colorClass: 'card-green' },
];

function MasterHome() {
  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🏆 Master</h1>
        <p className="stage-subtitle">Practice, test, and reinforce knowledge until it sticks.</p>
      </header>

      <div className="stage-grid">
        {masterTools.map((tool) => (
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

export default MasterHome;