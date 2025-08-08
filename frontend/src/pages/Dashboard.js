import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axiosInstance from "../utils/axiosInstance";
import "./Dashboard.css";
import { FaFilePdf, FaFileAlt, FaFileWord, FaTimesCircle } from "react-icons/fa"; // add to imports at top

export default function Dashboard() {
  const navigate = useNavigate();
  const [processingFiles, setProcessingFiles] = useState([]);

  useEffect(() => {
    const fetchProgressData = async () => {
      try {
        // Fetch all user progress (only in_progress)
        const response = await axiosInstance.get("/progress/all");
        const inProgress = (response.data || []).filter(file => file.status === "in_progress");
        setProcessingFiles(inProgress);
      } catch (error) {
        console.error("Failed to fetch progress data", error);
      }
    };

    fetchProgressData();
    const interval = setInterval(fetchProgressData, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Top Bar */}
      <div className="top-bar">
        <h1 className="title">Welcome to Scoolish</h1>
        <div className="profile-id">Profile ID: #USR0329</div>
      </div>

      <div className="card-grid">
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

        <div className="card card-vault" onClick={() => navigate("/vault")}>
          <h2>Knowledge Vault</h2>
          <p>View and manage all your uploaded documents and media files.</p>
        </div>
      </div>

      {/* Processing Files Section */}
      <div className="processing-section">
        <h3>Processing Files</h3>
        <div className="processing-grid">
          {processingFiles.length === 0 ? (
            <p className="empty-message">No files are currently being processed.</p>
          ) : (
            processingFiles.map((file, index) => {
              // Determine icon based on extension (fallback to text icon)
              const extension = file.original_name?.split('.').pop().toLowerCase();
              const getFileIcon = () => {
                if (extension === 'pdf') return <FaFilePdf className="file-icon" />;
                if (['doc', 'docx'].includes(extension)) return <FaFileWord className="file-icon" />;
                return <FaFileAlt className="file-icon" />;
              };

              const estimatedTime = `${Math.max(1, Math.ceil((100 - file.percentage) / 20))} min`;

              const handleCancel = () => {
                // Replace this with actual cancel logic if available
                alert(`Canceling ${file.original_name}... (feature pending backend support)`);
              };

              return (
                <div key={index} className="processing-card animate-fade-in">
                  <div className="processing-header">
                    <div className="file-info" title={file.original_name}>
                      {getFileIcon()}
                      <span className="filename">{file.original_name}</span>
                    </div>
                    <span className="percent-badge" title="Progress">{file.percentage}%</span>
                  </div>

                  <div className="status" title="Processing status">
                    Status: {file.status}
                  </div>

                  <div className="estimated-time" title="Estimated time remaining">
                    ⏱ {estimatedTime}
                  </div>

                  <div className="cancel-button" onClick={handleCancel} title="Cancel processing">
                    <FaTimesCircle />
                    Cancel
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Talk to AI Bot Floating Button */}
      <div className="chatbot-button" onClick={() => alert("Coming soon: AI Copilot!")}>💬 Talk to AI Bot</div>
    </div>
  );
}
