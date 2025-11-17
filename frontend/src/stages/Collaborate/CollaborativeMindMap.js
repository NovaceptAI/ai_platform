import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { FaBrain, FaPlus, FaSave, FaUsers, FaComments, FaLightbulb, FaDownload } from 'react-icons/fa';
import axiosInstance from '../../utils/axiosInstance';
import { useMindMapWebSocket } from './hooks/useMindMapWebSocket';
import CustomNode from './components/CustomNode';
import CollaborationPanel from './components/CollaborationPanel';
import AIAssistPanel from './components/AIAssistPanel';
import './CollaborativeMindMap.css';

const nodeTypes = {
  custom: CustomNode,
};

// Helper function to get user ID from JWT token (matching DigitalDebate pattern)
const getUserIdFromToken = () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub || payload.user_id || null;
  } catch (e) {
    console.error('Error decoding token:', e);
    return null;
  }
};

// Helper function to get username from JWT token
const getUsernameFromToken = () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return 'User';
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.username || 'User';
  } catch (e) {
    console.error('Error decoding token:', e);
    return 'User';
  }
};

function CollaborativeMindMap() {
  const navigate = useNavigate();

  // Mind Map State
  const [mindMaps, setMindMaps] = useState([]);
  const [publicMaps, setPublicMaps] = useState([]);
  const [viewMode, setViewMode] = useState('my-maps'); // 'my-maps' or 'public-maps'
  const [currentMindMap, setCurrentMindMap] = useState(null);
  const [mindMapId, setMindMapId] = useState(null);

  // ReactFlow State
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // UI State
  const [showNewMapModal, setShowNewMapModal] = useState(false);
  const [showCollabPanel, setShowCollabPanel] = useState(true);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [newMapTitle, setNewMapTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // WebSocket - Get user info from JWT token
  const userId = getUserIdFromToken();
  const username = getUsernameFromToken();

  const {
    isConnected,
    activeUsers,
    cursors,
    disconnectFromMindMap,
    broadcastNodeCreated,
    broadcastNodeUpdated,
    broadcastNodeDeleted,
    broadcastConnectionCreated,
    broadcastConnectionDeleted,
  } = useMindMapWebSocket(mindMapId, userId, username);

  // Custom node change handler to broadcast position updates
  // MUST be defined AFTER useMindMapWebSocket hook since it uses broadcastNodeUpdated
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);

    // Broadcast position changes to other users
    changes.forEach((change) => {
      if (change.type === 'position' && change.dragging === false && change.position) {
        // Only broadcast when drag is finished
        const nodeId = change.id;
        broadcastNodeUpdated(nodeId, { position: change.position });

        // Also save to backend
        axiosInstance.put(`/stages/collaborate/mind_map/${mindMapId}/nodes/${nodeId}`, {
          position_x: change.position.x,
          position_y: change.position.y,
        }).catch(err => console.error('Failed to save node position:', err));
      }
    });
  }, [onNodesChange, broadcastNodeUpdated, mindMapId]);

  // Load mind maps on mount
  useEffect(() => {
    fetchMindMaps();
  }, []);

  // Setup WebSocket event listeners for real-time collaboration
  useEffect(() => {
    if (!mindMapId) return;

    // Handler for node creation from other users
    const handleNodeCreated = (event) => {
      const { node, created_by } = event.detail;
      if (created_by === userId) return; // Skip our own updates

      console.log('[MindMap] Remote node created:', node);
      
      const newFlowNode = {
        id: node.id,
        type: 'custom',
        position: { x: node.position.x, y: node.position.y },
        data: {
          label: node.title || node.content,
          content: node.content,
          color: node.style?.color || '#6366f1',
          shape: node.style?.shape || 'rounded',
          icon: node.style?.icon || 'lightbulb',
          onUpdate: (nodeId, updates) => handleNodeUpdate(nodeId, updates),
          onDelete: (nodeId) => handleNodeDelete(nodeId),
        },
      };

      setNodes((nds) => [...nds, newFlowNode]);
    };

    // Handler for node updates from other users
    const handleNodeUpdated = (event) => {
      const { node_id, updates, updated_by } = event.detail;
      if (updated_by === userId) return; // Skip our own updates

      console.log('[MindMap] Remote node updated:', node_id, updates);
      
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === node_id) {
            return {
              ...node,
              position: updates.position || node.position,
              data: { ...node.data, ...updates },
            };
          }
          return node;
        })
      );
    };

    // Handler for node deletion from other users
    const handleNodeDeleted = (event) => {
      const { node_id, deleted_by } = event.detail;
      if (deleted_by === userId) return; // Skip our own updates

      console.log('[MindMap] Remote node deleted:', node_id);
      
      setNodes((nds) => nds.filter((node) => node.id !== node_id));
    };

    // Handler for connection creation from other users
    const handleConnectionCreated = (event) => {
      const { connection, created_by } = event.detail;
      if (created_by === userId) return; // Skip our own updates

      console.log('[MindMap] Remote connection created:', connection);
      
      const newEdge = {
        id: connection.id,
        source: connection.source_id,
        target: connection.target_id,
        label: connection.label,
        type: connection.style?.line_type === 'straight' ? 'straight' : 'default',
        animated: connection.style?.line_type === 'dotted',
        style: { stroke: connection.style?.line_color || '#999' },
      };

      setEdges((eds) => [...eds, newEdge]);
    };

    // Handler for connection deletion from other users
    const handleConnectionDeleted = (event) => {
      const { connection_id, deleted_by } = event.detail;
      if (deleted_by === userId) return; // Skip our own updates

      console.log('[MindMap] Remote connection deleted:', connection_id);
      
      setEdges((eds) => eds.filter((edge) => edge.id !== connection_id));
    };

    // Register event listeners
    window.addEventListener('mindmap:node_created', handleNodeCreated);
    window.addEventListener('mindmap:node_updated', handleNodeUpdated);
    window.addEventListener('mindmap:node_deleted', handleNodeDeleted);
    window.addEventListener('mindmap:connection_created', handleConnectionCreated);
    window.addEventListener('mindmap:connection_deleted', handleConnectionDeleted);

    // Cleanup on unmount
    return () => {
      window.removeEventListener('mindmap:node_created', handleNodeCreated);
      window.removeEventListener('mindmap:node_updated', handleNodeUpdated);
      window.removeEventListener('mindmap:node_deleted', handleNodeDeleted);
      window.removeEventListener('mindmap:connection_created', handleConnectionCreated);
      window.removeEventListener('mindmap:connection_deleted', handleConnectionDeleted);
    };
  }, [mindMapId, userId]);

  const fetchMindMaps = async () => {
    try {
      const response = await axiosInstance.get('/stages/collaborate/mind_map/');
      setMindMaps(response.data.mind_maps || []);
    } catch (err) {
      console.error('Error fetching mind maps:', err);
    }
  };

  const fetchPublicMindMaps = async () => {
    try {
      const response = await axiosInstance.get('/stages/collaborate/mind_map/public');
      setPublicMaps(response.data.mind_maps || []);
    } catch (err) {
      console.error('Error fetching public mind maps:', err);
    }
  };

  const createNewMindMap = async () => {
    if (!newMapTitle.trim()) {
      setError('Please enter a title');
      return;
    }

    setLoading(true);
    try {
      const response = await axiosInstance.post('/stages/collaborate/mind_map/', {
        title: newMapTitle,
        canvas_settings: { zoom: 1, center_x: 0, center_y: 0 }
      });

      const newMapId = response.data.mind_map_id;
      await fetchMindMaps();
      await openMindMap(newMapId);

      setShowNewMapModal(false);
      setNewMapTitle('');
    } catch (err) {
      setError('Failed to create mind map');
    } finally {
      setLoading(false);
    }
  };

  const openMindMap = async (mapId) => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/stages/collaborate/mind_map/${mapId}`);
      const mapData = response.data.mind_map;

      setCurrentMindMap(mapData);
      setMindMapId(mapId);

      // Convert backend nodes to ReactFlow format
      const flowNodes = mapData.nodes.map(node => ({
        id: node.id,
        type: 'custom',
        position: { x: node.position.x, y: node.position.y },
        data: {
          label: node.title || node.content,
          content: node.content,
          color: node.style.color,
          shape: node.style.shape,
          icon: node.style.icon,
          onUpdate: (nodeId, updates) => handleNodeUpdate(nodeId, updates),
          onDelete: (nodeId) => handleNodeDelete(nodeId),
        },
      }));

      // Convert backend connections to ReactFlow edges
      const flowEdges = mapData.connections.map(conn => ({
        id: conn.id,
        source: conn.source_id,
        target: conn.target_id,
        label: conn.label,
        type: conn.style.line_type === 'straight' ? 'straight' : 'default',
        animated: conn.style.line_type === 'dotted',
        style: { stroke: conn.style.line_color },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);

      // WebSocket will auto-connect via useEffect when mindMapId changes
      console.log('[MindMap] Mind map loaded, WebSocket will auto-connect');
    } catch (err) {
      setError('Failed to load mind map');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeUpdate = async (nodeId, updates) => {
    // Update locally
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: { ...node.data, ...updates },
          };
        }
        return node;
      })
    );

    // Update backend
    try {
      await axiosInstance.put(`/stages/collaborate/mind_map/${mindMapId}/nodes/${nodeId}`, updates);

      // Broadcast to collaborators
      broadcastNodeUpdated(nodeId, updates);
    } catch (err) {
      console.error('Failed to update node:', err);
    }
  };

  const handleNodeDelete = async (nodeId) => {
    try {
      await axiosInstance.delete(`/stages/collaborate/mind_map/${mindMapId}/nodes/${nodeId}`);

      setNodes((nds) => nds.filter((node) => node.id !== nodeId));

      broadcastNodeDeleted(nodeId);
    } catch (err) {
      console.error('Failed to delete node:', err);
    }
  };

  const addNewNode = async () => {
    const newNode = {
      type: 'text',
      content: 'New Idea',
      title: 'New Idea',
      position_x: Math.random() * 500,
      position_y: Math.random() * 500,
      color: '#667eea',
      shape: 'rectangle',
    };

    try {
      const response = await axiosInstance.post(
        `/stages/collaborate/mind_map/${mindMapId}/nodes`,
        newNode
      );

      const createdNode = response.data.node;

      const flowNode = {
        id: createdNode.id,
        type: 'custom',
        position: { x: createdNode.position.x, y: createdNode.position.y },
        data: {
          label: createdNode.content,
          content: createdNode.content,
          color: '#667eea',
          shape: 'rectangle',
          onUpdate: (nodeId, updates) => handleNodeUpdate(nodeId, updates),
          onDelete: (nodeId) => handleNodeDelete(nodeId),
        },
      };

      setNodes((nds) => [...nds, flowNode]);

      broadcastNodeCreated(createdNode);
    } catch (err) {
      console.error('Failed to create node:', err);
    }
  };

  const onConnect = useCallback(
    async (params) => {
      const newEdge = {
        ...params,
        type: 'default',
        animated: false,
      };

      setEdges((eds) => addEdge(newEdge, eds));

      // Save to backend
      try {
        const response = await axiosInstance.post(
          `/stages/collaborate/mind_map/${mindMapId}/connections`,
          {
            source_id: params.source,
            target_id: params.target,
            line_type: 'curved',
            line_color: '#9ca3af',
          }
        );

        broadcastConnectionCreated(response.data);
      } catch (err) {
        console.error('Failed to create connection:', err);
      }
    },
    [mindMapId]
  );

  const saveMindMap = async () => {
    if (!currentMindMap) return;

    try {
      await axiosInstance.put(`/stages/collaborate/mind_map/${mindMapId}`, {
        title: currentMindMap.title,
        canvas_settings: { zoom: 1 },
      });

      alert('Mind map saved successfully!');
    } catch (err) {
      setError('Failed to save mind map');
    }
  };

  const togglePublicAccess = async (mapId, currentStatus) => {
    try {
      await axiosInstance.put(`/stages/collaborate/mind_map/${mapId}`, {
        is_public: !currentStatus
      });

      // Refresh the lists
      await fetchMindMaps();
      if (viewMode === 'public-maps') {
        await fetchPublicMindMaps();
      }

      // Update current map if it's the one being toggled
      if (currentMindMap && currentMindMap.id === mapId) {
        setCurrentMindMap({ ...currentMindMap, is_public: !currentStatus });
      }

      alert(`Mind map is now ${!currentStatus ? 'public' : 'private'}`);
    } catch (err) {
      console.error('Failed to toggle public access:', err);
      setError('Failed to update public access');
    }
  };

  return (
    <div className="mind-map-container">
      {/* Header */}
      <header className="mind-map-header">
        <div className="header-left">
          <button className="back-button" onClick={() => navigate('/collaborate')}>
            ← Back to Collaborate
          </button>
        </div>
        
        <div className="header-center">
          <h1><FaBrain /> Collaborative Mind Mapping</h1>
        </div>
        
        <div className="header-right">
          {currentMindMap && (
            <div className="mind-map-title">
              <h2>{currentMindMap.title}</h2>
              <span className="connection-status">
                {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
              </span>
            </div>
          )}
        </div>
      </header>

      {!currentMindMap ? (
        /* Mind Map List View */
        <div className="mind-map-list">
          <div className="list-header">
            <h2>
              {viewMode === 'my-maps' ? 'Your Mind Maps' : 'Browse Public Mind Maps'}
            </h2>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button 
                onClick={() => setViewMode('my-maps')}
                className={viewMode === 'my-maps' ? 'btn-primary' : 'btn-ghost'}
                style={{ fontSize: '14px', padding: '10px 16px' }}
              >
                My Maps
              </button>
              <button 
                onClick={() => {
                  setViewMode('public-maps');
                  fetchPublicMindMaps();
                }}
                className={viewMode === 'public-maps' ? 'btn-primary' : 'btn-ghost'}
                style={{ fontSize: '14px', padding: '10px 16px' }}
              >
                🌐 Browse Public
              </button>
              {viewMode === 'my-maps' && (
                <button onClick={() => setShowNewMapModal(true)} className="btn-primary">
                  <FaPlus /> New Mind Map
                </button>
              )}
            </div>
          </div>

          <div className="maps-grid">
            {(viewMode === 'my-maps' ? mindMaps : publicMaps).map((map) => (
              <div key={map.id} className="map-card">
                <div onClick={() => openMindMap(map.id)} style={{ cursor: 'pointer', flex: 1 }}>
                  <h3>{map.title}</h3>
                  <div className="map-meta">
                    <span>{map.node_count} nodes</span>
                    <span>{map.collaborator_count} collaborators</span>
                  </div>
                  {viewMode === 'public-maps' && (
                    <small style={{ display: 'block', marginTop: '8px', color: '#667eea', fontWeight: 500 }}>
                      By: {map.owner_name}
                    </small>
                  )}
                  <small>{new Date(map.updated_at).toLocaleDateString()}</small>
                </div>
                {viewMode === 'my-maps' && map.is_owner && (
                  <div style={{ 
                    marginTop: '12px', 
                    paddingTop: '12px', 
                    borderTop: '1px solid #e5e7eb',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <label style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '6px',
                      cursor: 'pointer',
                      fontSize: '13px',
                      color: '#666'
                    }}>
                      <input
                        type="checkbox"
                        checked={map.is_public || false}
                        onChange={(e) => {
                          e.stopPropagation();
                          togglePublicAccess(map.id, map.is_public);
                        }}
                        style={{ cursor: 'pointer' }}
                      />
                      <span>🌐 Public (anyone can join)</span>
                    </label>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* New Map Modal */}
          {showNewMapModal && (
            <div className="modal-overlay" onClick={() => setShowNewMapModal(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h3>Create New Mind Map</h3>
                <input
                  type="text"
                  placeholder="Mind map title..."
                  value={newMapTitle}
                  onChange={(e) => setNewMapTitle(e.target.value)}
                  autoFocus
                />
                {error && <div className="error-text">{error}</div>}
                <div className="modal-actions">
                  <button onClick={() => setShowNewMapModal(false)} className="btn-ghost">
                    Cancel
                  </button>
                  <button onClick={createNewMindMap} className="btn-primary" disabled={loading}>
                    {loading ? 'Creating...' : 'Create'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Mind Map Canvas View */
        <div className="mind-map-canvas-container">
          {/* Toolbar */}
          <div className="toolbar">
            <button onClick={addNewNode} className="toolbar-btn" title="Add Node">
              <FaPlus /> Add Node
            </button>
            <button onClick={saveMindMap} className="toolbar-btn" title="Save">
              <FaSave /> Save
            </button>
            <button
              onClick={() => setShowCollabPanel(!showCollabPanel)}
              className={`toolbar-btn ${showCollabPanel ? 'active' : ''}`}
              title="Collaboration"
            >
              <FaUsers /> Collaborators ({activeUsers.length})
            </button>
            <button
              onClick={() => setShowAIPanel(!showAIPanel)}
              className={`toolbar-btn ${showAIPanel ? 'active' : ''}`}
              title="AI Assist"
            >
              <FaLightbulb /> AI Assist
            </button>
            <button onClick={() => alert('Export feature coming soon!')} className="toolbar-btn" title="Export">
              <FaDownload /> Export
            </button>
          </div>

          {/* ReactFlow Canvas */}
          <div className="flow-wrapper">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
            >
              <Background />
              <Controls />
              <MiniMap />

              {/* Live Cursors Overlay */}
              {cursors.map((cursor) => (
                <div
                  key={cursor.user_id}
                  className="live-cursor"
                  style={{
                    position: 'absolute',
                    left: cursor.x,
                    top: cursor.y,
                    pointerEvents: 'none',
                    zIndex: 1000,
                  }}
                >
                  <div className="cursor-pointer">▲</div>
                  <div className="cursor-label">{cursor.username}</div>
                </div>
              ))}
            </ReactFlow>
          </div>

          {/* Side Panels */}
          {showCollabPanel && (
            <CollaborationPanel
              mindMapId={mindMapId}
              activeUsers={activeUsers}
              onClose={() => setShowCollabPanel(false)}
            />
          )}

          {showAIPanel && (
            <AIAssistPanel
              mindMapId={mindMapId}
              nodes={nodes}
              onNodeExpand={(nodeId, suggestions) => {
                // Handle AI suggestions
                console.log('AI suggestions:', suggestions);
              }}
              onClose={() => setShowAIPanel(false)}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default CollaborativeMindMap;
