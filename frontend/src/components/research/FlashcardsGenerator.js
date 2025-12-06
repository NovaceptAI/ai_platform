import React, { useState } from 'react';
import axiosInstance from '../../utils/axiosInstance';

const FlashcardsGenerator = ({ sessionId, selectedFiles, onComplete, onCancel }) => {
  const [title, setTitle] = useState('');
  const [options, setOptions] = useState({
    max_cards: 20,
    difficulty: 'medium',
    include_definitions: true,
    include_concepts: true,
    include_facts: true
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    if (!title.trim()) {
      setError('Please enter a title');
      return;
    }

    if (selectedFiles.length === 0) {
      setError('Please select at least one document');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      // Start generation
      const response = await axiosInstance.post(
        `/research/sessions/${sessionId}/flashcards`,
        {
          file_ids: selectedFiles.map(f => f.fileId),
          title: title,
          options: options
        }
      );

      const { artifact_id, progress_id } = response.data;

      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const progressRes = await axiosInstance.get(
            `/research/artifacts/${artifact_id}/progress`
          );

          setProgress(progressRes.data);

          if (progressRes.data.artifact_status === 'completed') {
            clearInterval(pollInterval);
            // Get full artifact
            const artifactRes = await axiosInstance.get(
              `/research/artifacts/${artifact_id}`
            );
            onComplete(artifactRes.data);
          } else if (progressRes.data.artifact_status === 'failed') {
            clearInterval(pollInterval);
            setError(progressRes.data.error_message || 'Generation failed');
            setIsGenerating(false);
          }
        } catch (err) {
          console.error('Progress poll error:', err);
        }
      }, 2000);

      // Cleanup on unmount
      return () => clearInterval(pollInterval);

    } catch (err) {
      console.error('Generation error:', err);
      setError(err.response?.data?.error || 'Failed to start generation');
      setIsGenerating(false);
    }
  };

  return (
    <div className="generator-container">
      {!isGenerating ? (
        <>
          <div className="generator-form">
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                placeholder="e.g., Chapter 5 Study Cards"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label>Documents ({selectedFiles.length} selected)</label>
              <div className="selected-files-preview">
                {selectedFiles.length === 0 ? (
                  <p className="no-files-hint">Select documents from the left panel</p>
                ) : (
                  selectedFiles.map(file => (
                    <div key={file.fileId} className="file-chip">
                      📄 {file.name}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="form-group">
              <label>Maximum Cards</label>
              <select
                value={options.max_cards}
                onChange={(e) => setOptions({ ...options, max_cards: parseInt(e.target.value) })}
                className="form-select"
              >
                <option value={10}>10 cards</option>
                <option value={20}>20 cards</option>
                <option value={30}>30 cards</option>
                <option value={50}>50 cards</option>
              </select>
            </div>

            <div className="form-group">
              <label>Difficulty</label>
              <select
                value={options.difficulty}
                onChange={(e) => setOptions({ ...options, difficulty: e.target.value })}
                className="form-select"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div className="form-group">
              <label>Include Content Types</label>
              <div className="checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={options.include_definitions}
                    onChange={(e) => setOptions({ ...options, include_definitions: e.target.checked })}
                  />
                  <span>Definitions</span>
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={options.include_concepts}
                    onChange={(e) => setOptions({ ...options, include_concepts: e.target.checked })}
                  />
                  <span>Concepts</span>
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={options.include_facts}
                    onChange={(e) => setOptions({ ...options, include_facts: e.target.checked })}
                  />
                  <span>Facts</span>
                </label>
              </div>
            </div>

            {error && (
              <div className="error-message">
                ⚠️ {error}
              </div>
            )}
          </div>

          <div className="generator-actions">
            <button className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button
              className="btn-primary"
              onClick={handleGenerate}
              disabled={selectedFiles.length === 0}
            >
              Generate Flashcards
            </button>
          </div>
        </>
      ) : (
        <div className="generation-progress">
          <div className="progress-icon">🃏</div>
          <h3>Generating Flashcards...</h3>
          {progress && (
            <>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress.percentage || 0}%` }}
                />
              </div>
              <p className="progress-text">
                {progress.percentage || 0}% - {progress.message || 'Processing...'}
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default FlashcardsGenerator;
