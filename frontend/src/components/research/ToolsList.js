import React from 'react';

const ToolsList = ({ onSelectTool }) => {
  const tools = [
    {
      id: 'flashcards',
      name: 'Flashcards',
      icon: '🃏',
      stage: 'Master',
      description: 'Generate interactive flashcards for spaced repetition learning',
      color: '#4CAF50',
      available: true
    },
    {
      id: 'presentation',
      name: 'AI Presentation',
      icon: '📊',
      stage: 'Create',
      description: 'Create beautiful presentations with AI-generated content',
      color: '#2196F3',
      available: true
    },
    {
      id: 'summarizer',
      name: 'Summarizer',
      icon: '📝',
      stage: 'Discover',
      description: 'Generate concise summaries of research documents',
      color: '#FF9800',
      available: false
    },
    {
      id: 'timeline',
      name: 'Timeline Explorer',
      icon: '⏳',
      stage: 'Discover',
      description: 'Create interactive timelines from historical content',
      color: '#9C27B0',
      available: false
    },
    {
      id: 'topic_model',
      name: 'Topic Modeler',
      icon: '🏷️',
      stage: 'Discover',
      description: 'Extract and visualize key topics from documents',
      color: '#00BCD4',
      available: false
    },
    {
      id: 'visual_guide',
      name: 'Visual Study Guide',
      icon: '🎨',
      stage: 'Master',
      description: 'Create visual diagrams and concept maps',
      color: '#E91E63',
      available: false
    },
    {
      id: 'evidence',
      name: 'Evidence Extractor',
      icon: '🔍',
      stage: 'Master',
      description: 'Extract and organize evidence for arguments',
      color: '#795548',
      available: false
    }
  ];

  return (
    <div className="tools-list">
      <div className="tools-intro">
        <p>Generate study materials and presentations from your research documents</p>
      </div>

      <div className="tools-grid">
        {tools.map(tool => (
          <button
            key={tool.id}
            className={`tool-card ${!tool.available ? 'tool-card-disabled' : ''}`}
            onClick={() => tool.available && onSelectTool(tool.id)}
            style={{ '--tool-color': tool.color }}
            disabled={!tool.available}
          >
            <div className="tool-card-header">
              <span className="tool-card-icon">{tool.icon}</span>
              <span className="tool-card-stage">{tool.stage}</span>
            </div>
            <h4 className="tool-card-name">{tool.name}</h4>
            <p className="tool-card-description">{tool.description}</p>
            {!tool.available && (
              <div className="coming-soon-badge">Coming Soon</div>
            )}
          </button>
        ))}
      </div>

      <div className="tools-hint">
        <p>💡 Select documents in the left panel before generating</p>
      </div>
    </div>
  );
};

export default ToolsList;
