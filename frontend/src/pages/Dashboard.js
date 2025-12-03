import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axiosInstance from "../utils/axiosInstance";
import "./Dashboard.css";
import { FaFilePdf, FaFileAlt, FaFileWord, FaTimesCircle } from "react-icons/fa";
import { Link } from "react-router-dom";
export default function Dashboard() {
  const navigate = useNavigate();
  const [processingFiles, setProcessingFiles] = useState([]);
  const [researchProjects, setResearchProjects] = useState([]);
  const [showCreateResearch, setShowCreateResearch] = useState(false);
  const [newProjectTitle, setNewProjectTitle] = useState('');
  const [newProjectTopic, setNewProjectTopic] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');

  useEffect(() => {
    const fetchProgressData = async () => {
      try {
        const response = await axiosInstance.get("/progress/all");
        const inProgress = (response.data || []).filter(file => file.status === "in_progress");
        setProcessingFiles(inProgress);
      } catch (error) {
        console.error("Failed to fetch progress data", error);
      }
    };

    const fetchResearchProjects = async () => {
      try {
        const response = await axiosInstance.get("/research/projects");
        setResearchProjects(response.data || []);
      } catch (error) {
        console.error("Failed to fetch research projects", error);
      }
    };

    fetchProgressData();
    fetchResearchProjects();
    const interval = setInterval(fetchProgressData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateResearch = async () => {
    if (!newProjectTitle.trim()) {
      alert('Please enter a project title');
      return;
    }

    try {
      const response = await axiosInstance.post('/research/projects', {
        title: newProjectTitle,
        topic: newProjectTopic,
        description: newProjectDescription
      });

      const projectId = response.data.id;
      navigate(`/research/${projectId}`);
    } catch (error) {
      console.error('Failed to create research project:', error);
      alert('Failed to create research project. Please try again.');
    }
  };

  return (
    <div className="dashboard-container">
      {/* Top Bar */}
      <div className="top-bar">
        <h1 className="title animate-fade-in">Welcome to Scoolish</h1>
      </div>

      {/* Top Row - 3 Cards */}
      <div className="card-grid-top animate-fade-in">
        <div className="card card-tools" onClick={() => navigate("/scoolish")}>
          <div className="card-image">
            <img src="/demo/tools.png" alt="Go to Tools" />
          </div>
          <div className="card-content">
            <h2>Go to Tools</h2>
            <p>Explore AI-powered tools for research, summarization, and more.</p>
          </div>
        </div>

        <div className="card card-learning" onClick={() => navigate("/learning-path")}>
          <div className="card-image">
            <img src="/demo/learningpath.png" alt="Learning Path" />
          </div>
          <div className="card-content">
            <h2>Learning Path</h2>
            <p>Personalized AI-curated roadmap for your interests and goals.</p>
          </div>
        </div>

        <div className="card card-project" onClick={() => navigate("/project/new")}>
          <div className="card-image">
            <img src="/demo/project.png" alt="Start Project" />
          </div>
          <div className="card-content">
            <h2>Start Project</h2>
            <p>Create and manage your learning projects with AI assistance.</p>
          </div>
        </div>
      </div>

      {/* Bottom Row - 3 Cards */}
      <div className="card-grid-bottom animate-fade-in">
        <div className="card card-vault" onClick={() => navigate("/vault")}>
          <div className="card-image">
            <img src="/demo/knowledgevault.png" alt="Knowledge Vault" />
          </div>
          <div className="card-content">
            <h2>Knowledge Vault</h2>
            <p>View and manage all your uploaded documents and media files.</p>
          </div>
        </div>

        <div className="card card-progress">
          <div className="card-image">
            <img src="/demo/progress.png" alt="Progress" />
          </div>
          <div className="card-content">
            <h2>Progress</h2>
            <p>Track your progress across tools, tasks, and learning milestones.</p>
          </div>
        </div>

        <div className="card card-research" onClick={() => setShowCreateResearch(true)}>
          <div className="card-image">
            <div className="research-icon">🔬</div>
          </div>
          <div className="card-content">
            <h2>Research Workspace</h2>
            <p>Start AI-powered research with your documents and live insights.</p>
          </div>
        </div>
      </div>

      {/* Research Projects Section */}
      {researchProjects.length > 0 && (
        <div className="research-projects-section animate-slide-up">
          <h3>My Research Projects</h3>
          <div className="research-projects-grid">
            {researchProjects.map((project) => (
              <div
                key={project.id}
                className="research-project-card"
                onClick={() => navigate(`/research/${project.id}`)}
              >
                <div className="project-icon">📚</div>
                <h4>{project.title}</h4>
                <p className="project-topic">{project.topic || 'General Research'}</p>
                <span className={`project-status status-${project.status}`}>
                  {project.status || 'active'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing Files Section */}
      <div className="processing-section animate-slide-up">
        <h3>Processing Files</h3>
        <div className="processing-grid">
          {processingFiles.length === 0 ? (
            <p className="empty-message">No files are currently being processed.</p>
          ) : (
            processingFiles.map((file, index) => {
              const extension = file.original_name?.split('.').pop().toLowerCase();
              const getFileIcon = () => {
                if (extension === 'pdf') return <FaFilePdf className="file-icon" />;
                if (['doc', 'docx'].includes(extension)) return <FaFileWord className="file-icon" />;
                return <FaFileAlt className="file-icon" />;
              };

              const estimatedTime = `${Math.max(
                1,
                Math.ceil((100 - (file.percentage || 0)) / 20)
              )} min`;

              const handleCancel = () => {
                alert(`Canceling ${file.original_name}... (feature pending backend support)`);
              };

              return (
                <div key={index} className="processing-card animate-fade-in">
                  <div className="processing-header">
                    <div className="file-info" title={file.original_name}>
                      {getFileIcon()}
                      <span className="filename">{file.original_name}</span>
                    </div>
                    <span className="percent-badge">{file.percentage || 0}%</span>
                  </div>

                  <div className="status">Status: {file.status}</div>

                  {/* Progress bar inside card */}
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.max(0, Math.min(100, file.percentage || 0))}%` }}
                    ></div>
                  </div>
                  <div className="percent-label">{file.percentage || 0}%</div>

                  <div className="estimated-time">⏱ {estimatedTime}</div>

                  <div className="cancel-button" onClick={handleCancel}>
                    <FaTimesCircle />
                    Cancel
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Create Research Project Modal */}
      {showCreateResearch && (
        <div className="modal-overlay" onClick={() => setShowCreateResearch(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Research Project</h2>
              <button className="close-button" onClick={() => setShowCreateResearch(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Project Title *</label>
                <input
                  type="text"
                  placeholder="e.g., AI Research Study"
                  value={newProjectTitle}
                  onChange={(e) => setNewProjectTitle(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Topic</label>
                <input
                  type="text"
                  placeholder="e.g., Artificial Intelligence"
                  value={newProjectTopic}
                  onChange={(e) => setNewProjectTopic(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  placeholder="Briefly describe your research goals..."
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  rows={4}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-cancel" onClick={() => setShowCreateResearch(false)}>
                Cancel
              </button>
              <button className="btn-create" onClick={handleCreateResearch}>
                Create & Start Research
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
