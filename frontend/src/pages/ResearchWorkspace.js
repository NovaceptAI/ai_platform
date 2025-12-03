import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import ReactMarkdown from 'react-markdown';
import axiosInstance from '../utils/axiosInstance';
import './ResearchWorkspace.css';

const ResearchWorkspace = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const chatEndRef = useRef(null);
  const documentViewerRef = useRef(null);

  // State management
  const [project, setProject] = useState(null);
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [availableFiles, setAvailableFiles] = useState([]);
  const [currentDocument, setCurrentDocument] = useState(null);
  const [documentContent, setDocumentContent] = useState('');
  const [knowledgeEvents, setKnowledgeEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('researchTheme') || 'dark');
  const [vaultFiles, setVaultFiles] = useState([]);
  const [isLoadingVault, setIsLoadingVault] = useState(false);
  const [selectedText, setSelectedText] = useState('');
  const [showTextAction, setShowTextAction] = useState(false);
  const [textActionPosition, setTextActionPosition] = useState({ x: 0, y: 0 });
  const [showAddSourcesModal, setShowAddSourcesModal] = useState(false);
  const [showDocumentModal, setShowDocumentModal] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [isLoadingDocument, setIsLoadingDocument] = useState(false);

  // Tools menu
  const tools = [
    { name: 'Summarizer', path: '/summarizer' },
    { name: 'Timeline Explorer', path: '/timeline_explorer' },
    { name: 'Topic Modeler', path: '/topic_modeller' },
    { name: 'Visual Study Guide', path: '/visual_study_guide_maker' },
    { name: 'Evidence Extractor', path: '/evidence_extractor' },
  ];

  // Load project data
  useEffect(() => {
    const loadProject = async () => {
      try {
        setIsLoading(true);
        const response = await axiosInstance.get(`/research/projects/${id}`);
        setProject(response.data);

        // Load files from vault if vault_folder is specified
        if (response.data.vault_folder) {
          const filesResponse = await axiosInstance.get('/files');
          setAvailableFiles(filesResponse.data.files || []);
        }

        // Start a research session
        await startSession();
      } catch (error) {
        console.error('Failed to load project:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      loadProject();
    }
  }, [id]);

  // Start research session
  const startSession = async () => {
    try {
      const response = await axiosInstance.post(`/research/projects/${id}/sessions/start`);
      // The session is created in the background, we can track progress if needed
      console.log('Session started:', response.data);
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  // Setup Server-Sent Events for knowledge monitor
  useEffect(() => {
    let eventSource;

    const setupSSE = () => {
      try {
        // Simulated SSE for now - replace with actual endpoint when ready
        // eventSource = new EventSource(`/api/research/events/stream?project_id=${id}`);

        // Simulated events for demo
        const simulateEvents = () => {
          const eventTypes = [
            { type: 'topic', text: 'Detected core topic: "artificial intelligence"' },
            { type: 'web', text: 'Searching the web for key concepts...' },
            { type: 'data', text: 'Pulling in new structured data from documents' },
            { type: 'entity', text: 'Extracted entities: neural networks, machine learning' },
          ];

          setTimeout(() => {
            const randomEvent = eventTypes[Math.floor(Math.random() * eventTypes.length)];
            addKnowledgeEvent(randomEvent.type, randomEvent.text);
          }, 3000);
        };

        simulateEvents();
      } catch (error) {
        console.error('SSE setup error:', error);
      }
    };

    if (id && session) {
      setupSSE();
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [id, session]);

  // Add knowledge event
  const addKnowledgeEvent = (type, text) => {
    const timestamp = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });

    setKnowledgeEvents(prev => [
      { type, text, timestamp, id: Date.now() },
      ...prev
    ].slice(0, 50)); // Keep last 50 events
  };

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle send message
  const handleSendMessage = async (messageText = inputMessage) => {
    if (!messageText.trim()) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsSending(true);

    try {
      // Call research chat API
      const response = await axiosInstance.post(`/research/chat`, {
        project_id: id,
        message: messageText,
        selected_file_ids: selectedFiles.map(f => f.fileId),
      });

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data.response || 'Processing your request...',
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Add event to knowledge monitor
      addKnowledgeEvent('ai', 'AI analyzed your question and provided insights');
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  };

  // Load vault files
  const loadVaultFiles = async () => {
    // If already loaded, no need to reload
    if (vaultFiles.length > 0) {
      return;
    }

    setIsLoadingVault(true);
    setIsLoadingFiles(true);

    try {
      const response = await axiosInstance.get('/upload/files');
      const files = (response.data.files || []).map(file => ({
        fileId: file.fileId || file.id,
        name: file.name,
        storedName: file.stored_name,
        fileType: file.fileType || 'PDF',
        pages: file.pages || 0
      }));
      setVaultFiles(files);
      addKnowledgeEvent('data', `Loaded ${files.length} files from vault`);
    } catch (error) {
      console.error('Failed to load vault files:', error);
      addKnowledgeEvent('data', 'Failed to load vault files');
    } finally {
      setIsLoadingVault(false);
      setIsLoadingFiles(false);
    }
  };

  // Add file from vault to workspace
  const addFileToWorkspace = (file) => {
    // Add to available files if not already there
    setAvailableFiles(prev => {
      const exists = prev.some(f => f.fileId === file.fileId);
      if (exists) {
        return prev;
      }
      return [...prev, file];
    });

    // Auto-select the file
    setSelectedFiles(prev => {
      const isSelected = prev.some(f => f.fileId === file.fileId);
      if (!isSelected) {
        return [...prev, file];
      }
      return prev;
    });

    addKnowledgeEvent('data', `Added to workspace: ${file.name}`);
  };

  // Handle file selection
  const toggleFileSelection = (file) => {
    setSelectedFiles(prev => {
      const isSelected = prev.some(f => f.fileId === file.fileId);
      if (isSelected) {
        return prev.filter(f => f.fileId !== file.fileId);
      } else {
        return [...prev, file];
      }
    });
  };

  // Load document content
  const loadDocumentContent = async (file) => {
    try {
      setCurrentDocument(file);
      setDocumentContent('Loading...');

      const response = await axiosInstance.get(`/research/vault/files/${file.fileId}/content`);
      setDocumentContent(response.data.content || 'No content available');

      addKnowledgeEvent('data', `Loaded document: ${file.name}`);
    } catch (error) {
      console.error('Failed to load document:', error);
      setDocumentContent('Failed to load document content');
    }
  };

  // View document in modal
  const viewDocument = async (fileId) => {
    setIsLoadingDocument(true);
    setShowDocumentModal(true);

    // Find the file in availableFiles
    const file = availableFiles.find(f => f.fileId === fileId);
    if (!file) {
      setIsLoadingDocument(false);
      return;
    }

    try {
      const response = await axiosInstance.get(`/research/vault/files/${fileId}/content`);
      setCurrentDocument({
        fileId: fileId,
        name: file.name,
        content: response.data.content || 'No content available',
        pages: response.data.pages
      });
      addKnowledgeEvent('data', `Viewing document: ${file.name}`);
    } catch (error) {
      console.error('Failed to load document:', error);
      setCurrentDocument({
        fileId: fileId,
        name: file.name,
        content: 'Failed to load document content',
        pages: 0
      });
    } finally {
      setIsLoadingDocument(false);
    }
  };

  // Handle text selection in document viewer
  const handleTextSelection = () => {
    const selection = window.getSelection();
    const text = selection.toString().trim();

    if (text.length > 0 && documentViewerRef.current?.contains(selection.anchorNode)) {
      setSelectedText(text);

      // Get selection position
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();

      setTextActionPosition({
        x: rect.left + (rect.width / 2),
        y: rect.top - 10
      });

      setShowTextAction(true);
    } else {
      setShowTextAction(false);
    }
  };

  useEffect(() => {
    document.addEventListener('mouseup', handleTextSelection);
    return () => document.removeEventListener('mouseup', handleTextSelection);
  }, []);

  // Send selected text to chat
  const sendSelectionToChat = () => {
    const message = `Analyze this excerpt: "${selectedText}"`;
    handleSendMessage(message);
    setShowTextAction(false);
    setSelectedText('');
  };

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('researchTheme', newTheme);
  };

  // Handle key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={`research-workspace ${theme}-theme`}>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading Research Workspace...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className={`research-workspace ${theme}-theme`}>
        <div className="error-container">
          <h2>Project Not Found</h2>
          <button onClick={() => navigate('/dashboard')}>Return to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`research-workspace ${theme}-theme`}>
      {/* Theme Toggle */}
      <button className="theme-toggle" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}>
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>

      <PanelGroup direction="horizontal" className="workspace-panels" autoSaveId="research-workspace-layout">
        {/* Sources Panel (Left) */}
        <Panel defaultSize={20} minSize={15} maxSize={40} id="sources-panel">
          <aside className="sources-panel">
        {/* Add Sources Button */}
        <div className="sources-header">
          <button className="add-sources-btn" onClick={() => {
            loadVaultFiles();
            setShowAddSourcesModal(true);
          }}>
            + Add sources
          </button>
        </div>

        {/* Sources List */}
        <div className="sources-list">
          {availableFiles.map(file => {
            const isSelected = selectedFiles.some(f => f.fileId === file.fileId);
            return (
              <div
                key={file.fileId}
                className={`source-item ${isSelected ? 'selected' : ''}`}
                onDoubleClick={() => viewDocument(file.fileId)}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleFileSelection(file)}
                />
                <span className="source-name">{file.name}</span>
                <button
                  className="source-remove-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setAvailableFiles(prev => prev.filter(f => f.fileId !== file.fileId));
                    setSelectedFiles(prev => prev.filter(f => f.fileId !== file.fileId));
                  }}
                  title="Remove from workspace"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>

        {/* Sources Footer */}
        <div className="sources-footer">
          {selectedFiles.length} source(s) selected
        </div>
      </aside>
        </Panel>

        {/* Resize Handle 1 */}
        <PanelResizeHandle className="resize-handle" />

        {/* Chat Section (Center) */}
        <Panel defaultSize={50} minSize={30} id="chat-panel">
      <section className="chat-section">
        {/* Project Header */}
        <div className="chat-section-header">
          <h2>{project.title}</h2>
          <span className="project-topic">{project.topic || 'General Research'}</span>
        </div>

        {/* Chat Messages */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-placeholder">
              <p>👋 Hello! I'm your AI research assistant.</p>
              <p>Ask me questions about your documents, request summaries, or explore topics.</p>
              <div className="suggestion-chips">
                <button onClick={() => handleSendMessage("Summarize the key concepts")}>
                  Summarize key concepts
                </button>
                <button onClick={() => handleSendMessage("What are the main topics?")}>
                  What are the main topics?
                </button>
                <button onClick={() => handleSendMessage("Extract important findings")}>
                  Extract important findings
                </button>
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <div
                key={msg.id}
                className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}
              >
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                <div className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            ))
          )}
          {isSending && (
            <div className="message assistant typing">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Chat Input */}
        <div className="chat-input-container">
          {selectedFiles.length > 0 && (
            <div className="selected-files-indicator">
              <span>📎 {selectedFiles.length} file(s) selected</span>
            </div>
          )}
          <div className="chat-input">
            <input
              type="text"
              placeholder="Ask a research question..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={isSending}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputMessage.trim() || isSending}
              className="send-button"
            >
              {isSending ? '⏳' : '➤'}
            </button>
          </div>
        </div>
      </section>
        </Panel>

        {/* Resize Handle 2 */}
        <PanelResizeHandle className="resize-handle" />

        {/* Studio Panel (Right) */}
        <Panel defaultSize={30} minSize={20} maxSize={40} id="studio-panel">
      <aside className="studio-panel">
        {/* Studio Header */}
        <div className="studio-header">
          <h3>Studio</h3>
        </div>

        {/* Create Tools */}
        <div className="studio-section">
          <h4>Create</h4>
          <div className="studio-tools">
            {tools.map(tool => (
              <button
                key={tool.name}
                className="studio-tool"
                onClick={() => navigate(tool.path)}
              >
                <span className="tool-icon">
                  {tool.name === 'Summarizer' && '📄'}
                  {tool.name === 'Timeline Explorer' && '📅'}
                  {tool.name === 'Topic Modeler' && '🏷️'}
                  {tool.name === 'Visual Study Guide' && '📚'}
                  {tool.name === 'Evidence Extractor' && '🔍'}
                </span>
                <span className="tool-name">{tool.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Recent Outputs */}
        <div className="studio-section">
          <h4>Recent</h4>
          <div className="recent-outputs">
            {knowledgeEvents.slice(0, 5).map(event => (
              <div key={event.id} className="output-item">
                <span className="output-icon">
                  {event.type === 'topic' && '🏷️'}
                  {event.type === 'web' && '🌐'}
                  {event.type === 'data' && '📊'}
                  {event.type === 'entity' && '🔖'}
                  {event.type === 'ai' && '🤖'}
                </span>
                <div className="output-info">
                  <span className="output-name">{event.text}</span>
                  <span className="output-time">{event.timestamp}</span>
                </div>
              </div>
            ))}
            {knowledgeEvents.length === 0 && (
              <p className="no-outputs">No recent activity</p>
            )}
          </div>
        </div>
      </aside>
        </Panel>
      </PanelGroup>

      {/* Add Sources Modal */}
      {showAddSourcesModal && (
        <div className="modal-overlay" onClick={() => setShowAddSourcesModal(false)}>
          <div className="modal-content add-sources-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Sources</h3>
              <button className="modal-close-btn" onClick={() => setShowAddSourcesModal(false)}>×</button>
            </div>

            <div className="modal-body">
              {/* Tab Navigation */}
              <div className="add-sources-tabs">
                <button className="tab-btn active">Knowledge Vault</button>
                <button className="tab-btn" disabled>Upload files</button>
                <button className="tab-btn" disabled>Web search</button>
              </div>

              {/* Vault Files List */}
              <div className="vault-files-list">
                {isLoadingFiles ? (
                  <div className="loading-placeholder">
                    <p>Loading files from your Knowledge Vault...</p>
                  </div>
                ) : vaultFiles.length === 0 ? (
                  <div className="empty-state">
                    <p>No files found in your Knowledge Vault</p>
                    <p className="empty-state-hint">Upload files to your vault first</p>
                  </div>
                ) : (
                  vaultFiles.map(file => {
                    const isInWorkspace = availableFiles.some(f => f.fileId === file.fileId);
                    const isSelected = selectedFiles.some(f => f.fileId === file.fileId);
                    return (
                      <div
                        key={file.fileId}
                        className={`vault-file-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => {
                          if (!isInWorkspace) {
                            addFileToWorkspace(file);
                          } else {
                            toggleFileSelection(file);
                          }
                        }}
                      >
                        <div className="file-checkbox">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}}
                          />
                        </div>
                        <div className="file-info">
                          <span className="file-name">{file.name}</span>
                          <span className="file-meta">
                            {file.fileType} • {file.pages} pages
                          </span>
                        </div>
                        {isSelected && <span className="file-selected-badge">✓</span>}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowAddSourcesModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={() => setShowAddSourcesModal(false)}
                disabled={selectedFiles.length === 0}
              >
                Add {selectedFiles.length} source{selectedFiles.length !== 1 ? 's' : ''}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Viewer Modal */}
      {showDocumentModal && currentDocument && (
        <div className="modal-overlay" onClick={() => setShowDocumentModal(false)}>
          <div className="modal-content document-viewer-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{currentDocument.name}</h3>
              <button className="modal-close-btn" onClick={() => setShowDocumentModal(false)}>×</button>
            </div>

            <div className="modal-body">
              <div className="document-content">
                {isLoadingDocument ? (
                  <div className="loading-placeholder">
                    <p>Loading document...</p>
                  </div>
                ) : (
                  <div className="document-text" onMouseUp={handleTextSelection}>
                    {currentDocument.content || 'No content available'}
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowDocumentModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Text Selection Popup */}
      {showTextAction && (
        <div
          className="text-action-popup"
          style={{
            left: `${textActionPosition.x}px`,
            top: `${textActionPosition.y}px`
          }}
        >
          <button onClick={sendSelectionToChat}>
            Send to Chat 💬
          </button>
        </div>
      )}
    </div>
  );
};

export default ResearchWorkspace;
