import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axiosInstance from "../utils/axiosInstance";
import "./Dashboard.css";
import { FaFilePdf, FaFileAlt, FaFileWord, FaTimesCircle } from "react-icons/fa";
import { Link } from "react-router-dom";
export default function Dashboard() {
  const navigate = useNavigate();
  const [processingFiles, setProcessingFiles] = useState([]);

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

    fetchProgressData();
    const interval = setInterval(fetchProgressData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Top Bar */}
      <div className="top-bar">
        <h1 className="title animate-fade-in">Welcome to Scoolish</h1>
      </div>

      <div className="card-grid animate-fade-in">
        <div className="card card-tools" onClick={() => navigate("/scoolish")}>
          <h2>Go to Tools</h2>
          <p>Explore AI-powered tools for research, summarization, and more.</p>
        </div>

        <div className="card card-learning" onClick={() => navigate("/learning-path")}>
          <h2>Learning Path</h2>
          <p>Personalized AI-curated roadmap for your interests and goals.</p>
        </div>

        <div className="card card-progress">
          <h2>Progress</h2>
          <p>Track your progress across tools, tasks, and learning milestones.</p>
        </div>

        <div className="card" onClick={() => navigate("/vault")}>
          <h2>Knowledge Vault</h2>
          <p>View and manage all your uploaded documents and media files.</p>
        </div>

        <div className="card card-project" onClick={() => navigate("/project/new")}>
          <h2>Start Project</h2>
          <p>View and manage all your uploaded documents and media files.</p>
        </div>
      </div>

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
    </div>
  );
}
