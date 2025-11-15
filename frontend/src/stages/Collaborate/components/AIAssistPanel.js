// frontend/src/stages/Collaborate/components/AIAssistPanel.js
import React, { useState } from 'react';
import { FaTimes, FaLightbulb, FaLink, FaFileAlt, FaRobot } from 'react-icons/fa';
import axiosInstance from '../../../utils/axiosInstance';

const AIAssistPanel = ({ mindMapId, nodes, onNodeExpand, onClose }) => {
  const [activeFeature, setActiveFeature] = useState('expand'); // 'expand', 'connections', 'summary'
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleExpandNode = async () => {
    if (!selectedNodeId) {
      setError('Please select a node to expand');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/ai/expand`, {
        node_id: selectedNodeId,
      });

      setSuggestions(response.data.suggestions || []);
    } catch (err) {
      setError('Failed to generate suggestions');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestConnections = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/ai/suggest_connections`);
      setSuggestions(response.data.connections || []);
    } catch (err) {
      setError('Failed to suggest connections');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/ai/summarize`, {
        node_id: selectedNodeId || null,
      });

      setSummary(response.data.summary || '');
    } catch (err) {
      setError('Failed to generate summary');
    } finally {
      setLoading(false);
    }
  };

  const handleApplySuggestion = async (suggestion) => {
    if (activeFeature === 'expand') {
      // Create child node
      try {
        const selectedNode = nodes.find((n) => n.id === selectedNodeId);
        if (!selectedNode) return;

        const response = await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/nodes`, {
          type: 'text',
          content: suggestion,
          title: suggestion,
          position_x: selectedNode.position.x + 200,
          position_y: selectedNode.position.y + Math.random() * 100,
          color: selectedNode.data.color || '#667eea',
          shape: 'rectangle',
        });

        const newNode = response.data.node;

        // Create connection from parent to child
        await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/connections`, {
          source_id: selectedNodeId,
          target_id: newNode.id,
          line_type: 'curved',
          line_color: '#9ca3af',
        });

        // Notify parent component
        if (onNodeExpand) {
          onNodeExpand(selectedNodeId, [suggestion]);
        }

        alert('Node created successfully!');
      } catch (err) {
        alert('Failed to create node');
      }
    } else if (activeFeature === 'connections') {
      // Create suggested connection
      try {
        await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/connections`, {
          source_id: suggestion.source_id,
          target_id: suggestion.target_id,
          label: suggestion.label,
          line_type: 'curved',
          line_color: '#feca57',
        });

        alert('Connection created successfully!');
      } catch (err) {
        alert('Failed to create connection');
      }
    }
  };

  return (
    <div className="ai-assist-panel">
      <div className="panel-header">
        <h3><FaRobot /> AI Assistant</h3>
        <button onClick={onClose} className="close-btn">
          <FaTimes />
        </button>
      </div>

      {/* Feature Selection */}
      <div className="ai-features">
        <button
          onClick={() => setActiveFeature('expand')}
          className={`feature-btn ${activeFeature === 'expand' ? 'active' : ''}`}
        >
          <FaLightbulb /> Expand Node
        </button>
        <button
          onClick={() => setActiveFeature('connections')}
          className={`feature-btn ${activeFeature === 'connections' ? 'active' : ''}`}
        >
          <FaLink /> Suggest Connections
        </button>
        <button
          onClick={() => setActiveFeature('summary')}
          className={`feature-btn ${activeFeature === 'summary' ? 'active' : ''}`}
        >
          <FaFileAlt /> Summarize
        </button>
      </div>

      <div className="panel-content">
        {/* Expand Node Feature */}
        {activeFeature === 'expand' && (
          <div className="ai-feature-content">
            <h4>Expand a Node</h4>
            <p className="feature-description">
              Select a node and AI will suggest related subtopics or child ideas.
            </p>

            <select
              value={selectedNodeId}
              onChange={(e) => setSelectedNodeId(e.target.value)}
              className="node-selector"
            >
              <option value="">Select a node...</option>
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.data.label || node.data.content}
                </option>
              ))}
            </select>

            <button
              onClick={handleExpandNode}
              className="btn-primary"
              disabled={loading || !selectedNodeId}
            >
              {loading ? 'Generating...' : 'Generate Suggestions'}
            </button>

            {error && <div className="error-message">{error}</div>}

            {suggestions.length > 0 && (
              <div className="suggestions-list">
                <h5>Suggested Subtopics:</h5>
                {suggestions.map((suggestion, index) => (
                  <div key={index} className="suggestion-item">
                    <span>{suggestion}</span>
                    <button
                      onClick={() => handleApplySuggestion(suggestion)}
                      className="btn-apply"
                    >
                      Add
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Suggest Connections Feature */}
        {activeFeature === 'connections' && (
          <div className="ai-feature-content">
            <h4>Suggest Hidden Connections</h4>
            <p className="feature-description">
              AI will analyze your nodes and suggest meaningful relationships that might not be obvious.
            </p>

            <button
              onClick={handleSuggestConnections}
              className="btn-primary"
              disabled={loading || nodes.length < 2}
            >
              {loading ? 'Analyzing...' : 'Find Connections'}
            </button>

            {error && <div className="error-message">{error}</div>}

            {suggestions.length > 0 && (
              <div className="suggestions-list">
                <h5>Suggested Connections:</h5>
                {suggestions.map((connection, index) => {
                  const sourceNode = nodes.find((n) => n.id === connection.source_id);
                  const targetNode = nodes.find((n) => n.id === connection.target_id);

                  return (
                    <div key={index} className="suggestion-item connection-suggestion">
                      <div className="connection-info">
                        <strong>{sourceNode?.data.label}</strong> → <strong>{targetNode?.data.label}</strong>
                        <p className="connection-reason">{connection.reason}</p>
                        <span className="connection-label">Label: "{connection.label}"</span>
                      </div>
                      <button
                        onClick={() => handleApplySuggestion(connection)}
                        className="btn-apply"
                      >
                        Connect
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Summary Feature */}
        {activeFeature === 'summary' && (
          <div className="ai-feature-content">
            <h4>Generate Summary</h4>
            <p className="feature-description">
              AI will create a coherent paragraph summarizing your mind map or a specific branch.
            </p>

            <select
              value={selectedNodeId}
              onChange={(e) => setSelectedNodeId(e.target.value)}
              className="node-selector"
            >
              <option value="">Entire mind map</option>
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  Branch from: {node.data.label || node.data.content}
                </option>
              ))}
            </select>

            <button
              onClick={handleGenerateSummary}
              className="btn-primary"
              disabled={loading}
            >
              {loading ? 'Generating...' : 'Generate Summary'}
            </button>

            {error && <div className="error-message">{error}</div>}

            {summary && (
              <div className="summary-output">
                <h5>Summary:</h5>
                <p>{summary}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AIAssistPanel;
