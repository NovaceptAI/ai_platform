import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axiosInstance from "../utils/axiosInstance";
import "./ProjectDashboard.css";
import { FaPlus, FaRocket, FaUpload, FaSearch, FaTimesCircle } from "react-icons/fa";

// Sample hardcoded data to simulate user projects.
const SAMPLE_PROJECTS = [
    { id: "proj-001", name: "Climate Change Research", topic: "Climate Change", date: "2023-10-26" },
    { id: "proj-002", name: "Organic Chemistry Deep Dive", topic: "Organic Chemistry", date: "2023-10-25" },
];

// New Project Form Component - integrated into the main dashboard
function NewProjectForm({ onClose, onStart }) {
    const [topic, setTopic] = useState("");
    const [learningPath, setLearningPath] = useState("");
    const [localFiles, setLocalFiles] = useState([]);
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedVaultFile, setSelectedVaultFile] = useState('');
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false); // New state for file upload status
    const [error, setError] = useState(null);

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            setVaultFiles(response.data.files || []);
        } catch (err) {
            console.error("Failed to fetch vault files:", err);
            setError("Failed to load files from Vault.");
        }
    };

    useEffect(() => {
        fetchVaultFiles();
    }, []);

    const handleFileUpload = (e) => {
        const files = Array.from(e.target.files);
        setLocalFiles(files.map(f => f.name));
    };

    const handleStart = () => {
        // Your existing file checks...
        if (localFiles.length === 0 && !selectedVaultFile) {
            setError('Please select a file to upload or from the vault.');
            return;
        }

        // Call the onStart prop, which contains the navigation logic
        onStart({ topic, learningPath, files: [...localFiles, selectedVaultFile].filter(Boolean) });
    };

    return (
        <div className="form-container">
            <div className="form-header">
                <h2 className="form-title">Start a New Project</h2>
                <button onClick={onClose} className="close-btn">
                    &times;
                </button>
            </div>

            {/* Topic */}
            <div className="form-field">
                <label className="field-label">Select Topic</label>
                <input
                    type="text"
                    className="field-input"
                    placeholder="e.g. Climate Change Research"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                />
            </div>

            {/* Learning Path */}
            <div className="form-field">
                <label className="field-label">Choose Learning Path</label>
                <select
                    className="field-select"
                    value={learningPath}
                    onChange={(e) => setLearningPath(e.target.value)}
                >
                    <option value="">-- Select Path --</option>
                    <option value="Curious Explorer">Curious Explorer</option>
                    <option value="Academic Researcher">Academic Researcher</option>
                    <option value="Startup Thinker">Startup Thinker</option>
                    <option value="Creative Writer">Creative Writer</option>
                    <option value="Professional Upskiller">Professional Upskiller</option>
                    <option value="Policy Analyst">Policy Analyst</option>
                    <option value="Lifelong Learner">Lifelong Learner</option>
                </select>
            </div>

            {/* Files */}
            <div className="form-field">
                <label className="field-label">
                    Upload Files or Select from Vault
                </label>
                <div className="file-input-group">
                    <input
                        type="file"
                        multiple
                        onChange={handleFileUpload}
                        className="field-file-input"
                    />
                    <span className="file-upload-divider">or</span>
                    <select
                        value={selectedVaultFile}
                        onChange={(e) => {
                            setSelectedVaultFile(e.target.value);
                            setLocalFiles([]);
                        }}
                        className="field-select"
                        aria-label="Select from Knowledge Vault"
                    >
                        <option value="">Vault: choose file…</option>
                        {vaultFiles.map((vf, idx) => (
                            <option key={idx} value={vf.stored_name}>{vf.name}</option>
                        ))}
                    </select>
                    {selectedVaultFile && (
                        <button
                            type="button"
                            className="clear-vault-btn"
                            onClick={() => setSelectedVaultFile('')}
                            title="Clear vault selection"
                        >
                            <FaTimesCircle />
                        </button>
                    )}
                </div>
                {localFiles.length > 0 && (
                    <ul className="file-list">
                        {localFiles.map((f, i) => (
                            <li key={i}>{f}</li>
                        ))}
                    </ul>
                )}
            </div>
            {error && <div className="form-error">{error}</div>}

            <button onClick={handleStart} className="form-submit-btn">
                Start Project
            </button>
        </div>
    );
}

export default function ProjectDashboard() {
    const navigate = useNavigate();
    const [projects, setProjects] = useState(SAMPLE_PROJECTS);
    const [showForm, setShowForm] = useState(false);
    const [message, setMessage] = useState(null);
    const { id } = useParams(); // Get ID from URL if editing

    const handleCreateProject = () => {
        setShowForm(true);
    };

    const handleStartProject = (projectDetails) => {
        // Define dummy data for the workspace to use
        const mockProjectData = {
            id: id || 'mock-project-123', // Use existing ID or new mock ID
            topic: projectDetails.topic || 'Quantum Computing Research',
            learningPath: projectDetails.learningPath,
            files: projectDetails.files.map(name => ({ name })),
            description: 'An in-depth study...',
            tags: ['AI Research', 'Physics', 'Simulation']
        };

        setMessage(`🚀 Project Started! Topic: ${mockProjectData.topic}`);
        setShowForm(false);

        // Navigate to the workspace and pass the data via state
        navigate(`/project/${mockProjectData.id}/workspace`, { state: mockProjectData });
    };

    return (
        <div className="project-dashboard-container">
            <div className="header-section animate-fade-in">
                <h1 className="title">Your Projects</h1>
                <p className="subtitle">
                    Organize your research and explorations in one place.
                </p>
            </div>

            {message && <div className="system-message animate-fade-in">{message}</div>}

            {projects.length === 0 ? (
                // Empty State View
                <div className="empty-state animate-fade-in">
                    <p className="empty-message">You don’t have an active project yet.</p>
                    <button onClick={handleCreateProject} className="create-project-btn">
                        <FaPlus />
                        Create a New Project
                    </button>
                    <div className="suggestion-grid">
                        <div className="suggestion-card">
                            <FaRocket className="suggestion-icon" />
                            <h3>Start with a Learning Path</h3>
                            <p>Get a personalized roadmap from our AI.</p>
                        </div>
                        <div className="suggestion-card">
                            <FaUpload className="suggestion-icon" />
                            <h3>Upload files from Knowledge Vault</h3>
                            <p>Analyze and organize your existing documents.</p>
                        </div>
                        <div className="suggestion-card">
                            <FaSearch className="suggestion-icon" />
                            <h3>Explore demo project</h3>
                            <p>See what's possible with sample data.</p>
                        </div>
                    </div>
                </div>
            ) : (
                // Projects List View
                <div className="projects-list-section animate-fade-in">
                    <button onClick={handleCreateProject} className="create-project-btn-small">
                        <FaPlus />
                        New Project
                    </button>
                    <div className="projects-grid">
                        {projects.map((proj) => (
                            <div key={proj.id} className="project-card" onClick={() => navigate(`/project/${proj.id}`)}>
                                <h3 className="project-name">{proj.name}</h3>
                                <span className="project-topic">{proj.topic}</span>
                                <span className="project-date">Created: {proj.date}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {showForm && (
                <div className="form-modal-overlay animate-fade-in">
                    <NewProjectForm onClose={() => setShowForm(false)} onStart={handleStartProject} />
                </div>
            )}
        </div>
    );
}