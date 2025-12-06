import React, { useState, useEffect } from 'react';
import axiosInstance from '../../utils/axiosInstance';
import DeleteConfirmModal from './DeleteConfirmModal';

const PresentationViewer = ({ artifact, onBack, onDelete }) => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [showInlineViewer, setShowInlineViewer] = useState(false);
  const [slides, setSlides] = useState([]);
  const [isLoadingSlides, setIsLoadingSlides] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const presentationId = artifact?.result_data?.presentation_id;
  const totalSlides = artifact?.result_data?.total_slides || 0;
  const title = artifact?.result_data?.title || artifact?.title;

  // Load slide data when inline viewer is opened
  useEffect(() => {
    if (showInlineViewer && slides.length === 0 && presentationId) {
      loadSlides();
    }
  }, [showInlineViewer, presentationId]);

  if (!artifact?.result_data?.presentation_id) {
    return (
      <div className="viewer-error">
        <p>No presentation data available</p>
        <button onClick={onBack} className="btn-secondary">Go Back</button>
      </div>
    );
  }

  const loadSlides = async () => {
    setIsLoadingSlides(true);
    try {
      const response = await axiosInstance.get(
        `/ai_presentation_builder/presentations/${presentationId}`
      );
      
      if (response.data.slides_data) {
        setSlides(response.data.slides_data);
      }
    } catch (error) {
      console.error('Failed to load slides:', error);
    } finally {
      setIsLoadingSlides(false);
    }
  };

  const handlePrevSlide = () => {
    setCurrentSlide(prev => Math.max(0, prev - 1));
  };

  const handleNextSlide = () => {
    setCurrentSlide(prev => Math.min(slides.length - 1, prev + 1));
  };

  const handleDownload = async () => {
    try {
      // Download the presentation file
      const response = await axiosInstance.get(
        `/ai_presentation_builder/presentations/${presentationId}/download`,
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${title}.pptx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download presentation');
    }
  };

  const handleViewFull = () => {
    // Open the presentation in the AI Presentation Builder page
    window.open(`/demo/ai_presentation_builder?view=${presentationId}`, '_blank');
  };

  const toggleInlineViewer = () => {
    setShowInlineViewer(!showInlineViewer);
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    setShowDeleteModal(false);
    setIsDeleting(true);
    try {
      await axiosInstance.delete(`/research/artifacts/${artifact.id}`);
      if (onDelete) {
        onDelete(artifact.id);
      }
      onBack();
    } catch (error) {
      console.error('Failed to delete presentation:', error);
      alert('Failed to delete presentation: ' + (error.response?.data?.error || error.message));
      setIsDeleting(false);
    }
  };

  return (
    <div className="presentation-viewer">
      {/* Header */}
      <div className="viewer-header">
        <div className="viewer-title">
          <h4>{title}</h4>
          <span className="slide-counter">
            {totalSlides} slides
          </span>
        </div>
      </div>

      {/* Show inline viewer if toggled */}
      {showInlineViewer ? (
        <div className="inline-slide-viewer">
          {isLoadingSlides ? (
            <div className="loading-slides">
              <div className="spinner"></div>
              <p>Loading slides...</p>
            </div>
          ) : slides.length > 0 ? (
            <>
              <div className="slide-display">
                <div className="slide-content">
                  <h3 className="slide-title">{slides[currentSlide]?.title}</h3>
                  <div className="slide-body">
                    {slides[currentSlide]?.content?.map((item, idx) => (
                      <p key={idx}>{item}</p>
                    ))}
                  </div>
                  {slides[currentSlide]?.image_prompt && (
                    <div className="slide-image-note">
                      🖼️ Image: {slides[currentSlide].image_prompt}
                    </div>
                  )}
                </div>
              </div>
              
              <div className="slide-navigation">
                <button 
                  onClick={handlePrevSlide} 
                  disabled={currentSlide === 0}
                  className="nav-btn"
                >
                  ← Previous
                </button>
                <span className="slide-indicator">
                  {currentSlide + 1} / {slides.length}
                </span>
                <button 
                  onClick={handleNextSlide} 
                  disabled={currentSlide === slides.length - 1}
                  className="nav-btn"
                >
                  Next →
                </button>
              </div>
            </>
          ) : (
            <div className="no-slides">
              <p>No slide data available</p>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Preview Info */}
          <div className="presentation-preview">
            <div className="preview-icon">📊</div>
            <h3>{title}</h3>
            <p className="preview-meta">
              {totalSlides} slides • {artifact.config_data?.options?.theme || 'Professional'} theme
            </p>
            <p className="preview-description">
              Generated from {artifact.config_data?.options?.source_type === 'file' ? 'document' : 'text prompt'}
            </p>
          </div>
        </>
      )}

      {/* Actions */}
      <div className="presentation-actions">
        <button className="action-btn primary" onClick={toggleInlineViewer}>
          <span>{showInlineViewer ? '📋' : '👁️'}</span>
          {showInlineViewer ? 'Show Info' : 'Preview Slides'}
        </button>
        <button className="action-btn secondary" onClick={handleViewFull}>
          <span>🔗</span>
          Open in New Tab
        </button>
        <button className="action-btn secondary" onClick={handleDownload}>
          <span>⬇️</span>
          Download PPTX
        </button>
        <button 
          className="action-btn danger" 
          onClick={handleDeleteClick}
          disabled={isDeleting}
        >
          <span>🗑️</span>
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteConfirm}
        title="Delete Presentation"
        message="Are you sure you want to delete this presentation? This will also delete the PowerPoint file from storage. This action cannot be undone."
        itemType="Presentation"
      />

      {/* Info - Only show when not in inline viewer mode */}
      {!showInlineViewer && (
        <div className="viewer-info">
          <h5>Details</h5>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Slides</span>
              <span className="info-value">{totalSlides}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Theme</span>
              <span className="info-value">
                {artifact.config_data?.options?.theme?.replace(/_/g, ' ') || 'Professional'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Source</span>
              <span className="info-value">
                {artifact.config_data?.options?.source_type || 'text'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Status</span>
              <span className="info-value status-completed">
                {artifact.status}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Created date */}
      <div className="viewer-footer">
        <small>
          Created {new Date(artifact.created_at).toLocaleDateString()} at{' '}
          {new Date(artifact.created_at).toLocaleTimeString()}
        </small>
      </div>
    </div>
  );
};

export default PresentationViewer;
