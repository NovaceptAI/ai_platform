// src/stages/Create/Create.js
import React from 'react';
import { Link } from 'react-router-dom';
import { 
  FaLightbulb, 
  FaImages, 
  FaFilm, 
  FaProjectDiagram, 
  FaChalkboardTeacher, 
  FaPaintBrush, 
  FaCube, 
  FaChartArea, 
  FaPencilRuler, 
  FaHistory 
} from 'react-icons/fa';
import '../../stages/StagesHome.css';

const createTools = [
  { name: 'Creative Writing Prompts', path: '/creative_writing_prompts', icon: <FaLightbulb />, colorClass: 'card-purple' },
  { name: 'Story Visualizer', path: '/story_visualizer', icon: <FaImages />, colorClass: 'card-pink' },
  { name: 'Story to Comics Converter', path: '/story_to_comics', icon: <FaFilm />, colorClass: 'card-teal' },
  { name: 'Interactive Comic Strip Builder', path: '/interactive_comic_strip_builder', icon: <FaProjectDiagram />, colorClass: 'card-green' },
  { name: 'AI Presentation Builder', path: '/ai_presentation_builder', icon: <FaChalkboardTeacher />, colorClass: 'card-amber' },
  { name: 'AI Art Creator for Kids', path: '/ai_art_creator_for_kids', icon: <FaPaintBrush />, colorClass: 'card-blue' },
  { name: '3D Model Builder', path: '/three_d_model_builder', icon: <FaCube />, colorClass: 'card-teal' },
  { name: 'Data Story Builder', path: '/data_story_builder', icon: <FaChartArea />, colorClass: 'card-amber' },
  { name: 'Learn by Drawing', path: '/learn_by_drawing', icon: <FaPencilRuler />, colorClass: 'card-green' },
  { name: 'Historical Timeline Builder', path: '/historical_timeline_builder', icon: <FaHistory />, colorClass: 'card-purple' },
];

function Create() {
  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🎨 Create</h1>
        <p className="stage-subtitle">Turn ideas into visuals, stories, presentations, and interactive experiences.</p>
      </header>

      <div className="stage-grid">
        {createTools.map((tool) => (
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

export default Create;