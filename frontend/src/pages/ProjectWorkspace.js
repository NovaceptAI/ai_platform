import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import './ProjectWorkspace.css';

// Placeholder data
const tools = [
    { name: 'Summarizer' },
    { name: 'Timeline Explorer' },
    { name: 'Topic Modeler' },
    { name: 'Visual Study Guide' },
    { name: 'Other AI Tools' },
];

const feeds = [
    { type: 'browser', text: 'Searching the web for key concepts...', timestamp: '10:45 AM' },
    { type: 'scraper', text: 'Pulling in new structured data.', timestamp: '10:44 AM' },
    { type: 'ai', text: 'Detected core topic: "data modeling".', timestamp: '10:43 AM' },
];

// A custom hook to persist theme preference
const useLocalStorage = (key, initialValue) => {
    const [storedValue, setStoredValue] = useState(() => {
        try {
            const item = window.localStorage.getItem(key);
            return item ? JSON.parse(item) : initialValue;
        } catch (error) {
            console.log(error);
            return initialValue;
        }
    });

    useEffect(() => {
        try {
            window.localStorage.setItem(key, JSON.stringify(storedValue));
        } catch (error) {
            console.log(error);
        }
    }, [key, storedValue]);

    return [storedValue, setStoredValue];
};

const ProjectWorkspace = () => {
    const { id } = useParams();
    const location = useLocation();
    const projectData = location.state;
    const [isToolsCollapsed, setIsToolsCollapsed] = useState(false);
    const [theme, setTheme] = useLocalStorage('theme', 'dark');

    const toggleTheme = () => {
        setTheme(theme === 'dark' ? 'light' : 'dark');
    };

    if (!projectData) {
        return <div className="loading-state">Loading project data for ID: {id}...</div>;
    }

    const projectName = projectData?.topic || 'Untitled Project';
    const projectDescription = projectData?.description || 'No description provided.';
    const projectTags = projectData?.tags || [];
    const documents = projectData?.files || [];

    return (
        <div className={`project-workspace-container ${theme}-theme`}>
            {/* Theme Toggle Button */}
            <button className="theme-toggle-btn" onClick={toggleTheme}>
                Switch to {theme === 'dark' ? 'Light' : 'Dark'} Theme
            </button>
            
            {/* Left Sidebar */}
            <div className="left-sidebar">
                <div className="project-info">
                    <h3>{projectName}</h3>
                    <p className="project-description">{projectDescription}</p>
                    <div className="project-tags">
                        {projectTags.map(tag => (
                            <span key={tag} className="tag">{tag}</span>
                        ))}
                    </div>
                </div>
                <div className="tools-menu">
                    <h4 className="collapsible-header" onClick={() => setIsToolsCollapsed(!isToolsCollapsed)}>
                        Tools Menu
                        <span className={`collapse-icon ${isToolsCollapsed ? 'collapsed' : ''}`}>&#9660;</span>
                    </h4>
                    {!isToolsCollapsed && (
                        <ul className="tool-list">
                            {tools.map(tool => (
                                <li key={tool.name} className="tool-item">{tool.name}</li>
                            ))}
                        </ul>
                    )}
                </div>
                <div className="knowledge-vault-shortcut">
                    <button>Knowledge Vault</button>
                </div>
            </div>

            {/* Main Work Area */}
            <div className="main-work-area">
                <div className="ai-chat-panel">
                    <div className="chat-messages">
                        <div className="chat-message user">Hello! Can you summarize this project's files?</div>
                        <div className="chat-message assistant">I'm on it. Processing the documents now...</div>
                    </div>
                    <div className="chat-input-area">
                        <input type="text" placeholder="Ask a research question..." />
                        <button>Send</button>
                    </div>
                </div>
                <div className="document-viewer">
                    <div className="document-selector">
                        {documents.map(doc => (
                            <div key={doc.name} className="doc-item">{doc.name}</div>
                        ))}
                    </div>
                    <div className="doc-content-placeholder">
                        <p>Content of selected document will appear here.</p>
                        <p>You can highlight text to send to the AI Chat.</p>
                    </div>
                </div>
            </div>

            {/* Right Panel */}
            <div className="right-panel">
                <h4>Live Knowledge Monitor</h4>
                <div className="feed-container">
                    {feeds.map((feed, index) => (
                        <div key={index} className={`feed-item ${feed.type}`}>
                            <span className="timestamp">{feed.timestamp}</span>
                            <p className="feed-text">{feed.text}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Bottom Panel */}
            <div className="bottom-panel">
                <div className="progress-metrics">
                    <p><b>Progress:</b> Starting to analyze files...</p>
                </div>
                <div className="export-actions">
                    <button>Export Results</button>
                    <button>Save Snapshot</button>
                </div>
            </div>
        </div>
    );
};

export default ProjectWorkspace;