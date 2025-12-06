import React, { useState } from 'react';
import axiosInstance from '../../utils/axiosInstance';
import DeleteConfirmModal from './DeleteConfirmModal';

const FlashcardsViewer = ({ artifact, onBack, onDelete }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [studyMode, setStudyMode] = useState(false);
  const [masteredCards, setMasteredCards] = useState(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  if (!artifact?.result_data?.flashcards) {
    return (
      <div className="viewer-error">
        <p>No flashcards data available</p>
        <button onClick={onBack} className="btn-secondary">Go Back</button>
      </div>
    );
  }

  const flashcards = artifact.result_data.flashcards;
  const currentCard = flashcards[currentIndex];

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
      console.error('Failed to delete flashcards:', error);
      alert('Failed to delete flashcards: ' + (error.response?.data?.error || error.message));
      setIsDeleting(false);
    }
  };

  const handleNext = () => {
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev + 1) % flashcards.length);
  };

  const handlePrevious = () => {
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev - 1 + flashcards.length) % flashcards.length);
  };

  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  const handleMastered = () => {
    setMasteredCards(prev => new Set([...prev, currentCard.id]));
    handleNext();
  };

  const handleNeedReview = () => {
    handleNext();
  };

  const progress = ((masteredCards.size / flashcards.length) * 100).toFixed(0);

  return (
    <div className="flashcards-viewer">
      {/* Header */}
      <div className="viewer-header">
        <div className="viewer-title">
          <h4>{artifact.title}</h4>
          <span className="card-counter">
            {currentIndex + 1} / {flashcards.length}
          </span>
        </div>
        {studyMode && (
          <div className="study-progress">
            <div className="progress-bar-mini">
              <div
                className="progress-fill-mini"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="progress-label">{masteredCards.size} mastered</span>
          </div>
        )}
      </div>

      {/* Flashcard */}
      <div className="flashcard-container">
        <div
          className={`flashcard ${isFlipped ? 'flipped' : ''}`}
          onClick={handleFlip}
        >
          <div className="flashcard-front">
            <div className="card-type-badge">
              {currentCard.type || 'Question'}
            </div>
            <div className="card-content">
              <p className="card-text">{currentCard.front || currentCard.question}</p>
            </div>
            <div className="flip-hint">
              Click to flip
            </div>
          </div>
          <div className="flashcard-back">
            <div className="card-content">
              <p className="card-text">{currentCard.back || currentCard.answer}</p>
            </div>
            {currentCard.explanation && (
              <div className="card-explanation">
                <small>{currentCard.explanation}</small>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flashcard-nav">
        <button
          className="nav-btn"
          onClick={handlePrevious}
          disabled={flashcards.length === 1}
        >
          ← Previous
        </button>

        {studyMode && isFlipped && (
          <div className="study-actions">
            <button className="study-btn need-review" onClick={handleNeedReview}>
              Need Review
            </button>
            <button className="study-btn mastered" onClick={handleMastered}>
              Mastered ✓
            </button>
          </div>
        )}

        <button
          className="nav-btn"
          onClick={handleNext}
          disabled={flashcards.length === 1}
        >
          Next →
        </button>
      </div>

      {/* Controls */}
      <div className="viewer-controls">
        <button
          className={`control-btn ${studyMode ? 'active' : ''}`}
          onClick={() => setStudyMode(!studyMode)}
        >
          📚 Study Mode
        </button>
        <button className="control-btn" onClick={() => setCurrentIndex(0)}>
          🔄 Restart
        </button>
        <button className="control-btn" onClick={() => setIsFlipped(false)}>
          ↩️ Reset Flip
        </button>
        <button 
          className="control-btn delete-btn" 
          onClick={handleDeleteClick}
          disabled={isDeleting}
        >
          {isDeleting ? '⏳ Deleting...' : '🗑️ Delete'}
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteConfirm}
        title="Delete Flashcards"
        message="Are you sure you want to delete these flashcards? This action cannot be undone."
        itemType="Flashcards"
      />

      {/* Info */}
      <div className="viewer-info">
        <div className="info-stats">
          <div className="stat-item">
            <span className="stat-label">Total Cards</span>
            <span className="stat-value">{flashcards.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Difficulty</span>
            <span className="stat-value">{artifact.config_data?.options?.difficulty || 'N/A'}</span>
          </div>
          {studyMode && (
            <div className="stat-item">
              <span className="stat-label">Mastered</span>
              <span className="stat-value">{masteredCards.size}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FlashcardsViewer;
