import React, { useState, useEffect } from 'react';
import ToolsList from './ToolsList';
import FlashcardsGenerator from './FlashcardsGenerator';
import PresentationGenerator from './PresentationGenerator';
import FlashcardsViewer from './FlashcardsViewer';
import PresentationViewer from './PresentationViewer';
import ArtifactsList from './ArtifactsList';
import './ResearchStudio.css';

const StudioPanel = ({ sessionId, selectedFiles, projectId }) => {
  const [activeView, setActiveView] = useState('tools'); // 'tools' | 'generate-flashcards' | 'generate-presentation' | 'view-flashcards' | 'view-presentation' | 'artifacts'
  const [currentArtifact, setCurrentArtifact] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [isLoadingArtifacts, setIsLoadingArtifacts] = useState(false);

  // Load artifacts when session changes
  useEffect(() => {
    if (sessionId) {
      loadArtifacts();
    }
  }, [sessionId]);

  const loadArtifacts = async () => {
    if (!sessionId) return;
    
    setIsLoadingArtifacts(true);
    try {
      // Load both flashcards and presentations
      const [flashcardsRes, presentationsRes] = await Promise.all([
        fetch(`/api/research/sessions/${sessionId}/flashcards`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }),
        fetch(`/api/research/sessions/${sessionId}/presentations`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
      ]);

      const flashcards = await flashcardsRes.json();
      const presentations = await presentationsRes.json();

      // Combine and sort by created_at
      const combined = [...flashcards, ...presentations].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );

      setArtifacts(combined);
    } catch (error) {
      console.error('Failed to load artifacts:', error);
    } finally {
      setIsLoadingArtifacts(false);
    }
  };

  const handleToolSelect = (tool) => {
    if (tool === 'flashcards') {
      setActiveView('generate-flashcards');
    } else if (tool === 'presentation') {
      setActiveView('generate-presentation');
    }
  };

  const handleGenerationComplete = (artifact) => {
    loadArtifacts(); // Refresh artifacts list
    setCurrentArtifact(artifact);
    // Auto-switch to viewer
    if (artifact.artifact_type === 'flashcards') {
      setActiveView('view-flashcards');
    } else if (artifact.artifact_type === 'presentation') {
      setActiveView('view-presentation');
    }
  };

  const handleArtifactSelect = (artifact) => {
    setCurrentArtifact(artifact);
    if (artifact.artifact_type === 'flashcards') {
      setActiveView('view-flashcards');
    } else if (artifact.artifact_type === 'presentation') {
      setActiveView('view-presentation');
    }
  };

  const handleBack = () => {
    setActiveView('tools');
    setCurrentArtifact(null);
  };

  const handleShowArtifacts = () => {
    setActiveView('artifacts');
  };

  const handleDeleteArtifact = (deletedArtifactId) => {
    // Remove from artifacts list
    setArtifacts(prev => prev.filter(a => a.id !== deletedArtifactId));
  };

  return (
    <div className="studio-panel">
      {/* Header */}
      <div className="studio-header">
        {activeView !== 'tools' && activeView !== 'artifacts' && (
          <button className="back-btn" onClick={handleBack}>
            ← Back
          </button>
        )}
        <h3 className="studio-title">
          {activeView === 'tools' && 'Studio'}
          {activeView === 'generate-flashcards' && 'Generate Flashcards'}
          {activeView === 'generate-presentation' && 'Create Presentation'}
          {activeView === 'view-flashcards' && 'Flashcards'}
          {activeView === 'view-presentation' && 'Presentation'}
          {activeView === 'artifacts' && 'Artifacts'}
        </h3>
        <button 
          className="artifacts-btn"
          onClick={handleShowArtifacts}
          title="View all artifacts"
        >
          📚 {artifacts.length}
        </button>
      </div>

      {/* Content Area */}
      <div className="studio-content">
        {activeView === 'tools' && (
          <ToolsList onSelectTool={handleToolSelect} />
        )}

        {activeView === 'generate-flashcards' && (
          <FlashcardsGenerator
            sessionId={sessionId}
            selectedFiles={selectedFiles}
            onComplete={handleGenerationComplete}
            onCancel={handleBack}
          />
        )}

        {activeView === 'generate-presentation' && (
          <PresentationGenerator
            sessionId={sessionId}
            selectedFiles={selectedFiles}
            projectId={projectId}
            onComplete={handleGenerationComplete}
            onCancel={handleBack}
          />
        )}

        {activeView === 'view-flashcards' && currentArtifact && (
          <FlashcardsViewer
            artifact={currentArtifact}
            onBack={handleBack}
            onDelete={handleDeleteArtifact}
          />
        )}

        {activeView === 'view-presentation' && currentArtifact && (
          <PresentationViewer
            artifact={currentArtifact}
            onBack={handleBack}
            onDelete={handleDeleteArtifact}
          />
        )}

        {activeView === 'artifacts' && (
          <ArtifactsList
            artifacts={artifacts}
            isLoading={isLoadingArtifacts}
            onSelectArtifact={handleArtifactSelect}
            onRefresh={loadArtifacts}
            onBack={handleBack}
          />
        )}
      </div>
    </div>
  );
};

export default StudioPanel;
