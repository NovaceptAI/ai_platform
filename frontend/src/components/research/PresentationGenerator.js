import React, { useState } from 'react';
import axiosInstance from '../../utils/axiosInstance';

const PresentationGenerator = ({ sessionId, selectedFiles, projectId, onComplete, onCancel }) => {
  const [title, setTitle] = useState('');
  const [sourceType, setSourceType] = useState('text'); // 'text' | 'file'
  const [selectedFileId, setSelectedFileId] = useState('');
  const [textPrompt, setTextPrompt] = useState('');
  const [totalSlides, setTotalSlides] = useState(10);
  const [theme, setTheme] = useState('professional_blue');
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);

  const themes = [
    { value: 'professional_blue', label: 'Professional Blue' },
    { value: 'creative_gradient', label: 'Creative Gradient' },
    { value: 'minimalist_gray', label: 'Minimalist Gray' },
    { value: 'academic_formal', label: 'Academic Formal' },
    { value: 'dark_elegant', label: 'Dark Elegant' },
    { value: 'nature_green', label: 'Nature Green' }
  ];

  const handleGenerate = async () => {
    if (!title.trim()) {
      setError('Please enter a title');
      return;
    }

    if (sourceType === 'file' && !selectedFileId) {
      setError('Please select a document');
      return;
    }

    if (sourceType === 'text' && !textPrompt.trim()) {
      setError('Please enter a topic or description');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      // Start generation
      const response = await axiosInstance.post(
        `/research/sessions/${sessionId}/presentations`,
        {
          file_id: sourceType === 'file' ? selectedFileId : null,
          title: title,
          options: {
            source_type: sourceType,
            text_prompt: sourceType === 'text' ? textPrompt : '',
            total_slides: totalSlides,
            theme: theme
          }
        }
      );

      const { artifact_id } = response.data;

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
              <label>Presentation Title</label>
              <input
                type="text"
                placeholder="e.g., AI in Education"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label>Source Type</label>
              <div className="radio-group">
                <label className="radio-label">
                  <input
                    type="radio"
                    name="sourceType"
                    value="text"
                    checked={sourceType === 'text'}
                    onChange={(e) => setSourceType(e.target.value)}
                  />
                  <span>Topic/Description</span>
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="sourceType"
                    value="file"
                    checked={sourceType === 'file'}
                    onChange={(e) => setSourceType(e.target.value)}
                  />
                  <span>From Document</span>
                </label>
              </div>
            </div>

            {sourceType === 'text' && (
              <div className="form-group">
                <label>Topic or Description</label>
                <textarea
                  placeholder="Describe what you want the presentation to be about..."
                  value={textPrompt}
                  onChange={(e) => setTextPrompt(e.target.value)}
                  className="form-textarea"
                  rows={4}
                />
              </div>
            )}

            {sourceType === 'file' && (
              <div className="form-group">
                <label>Select Document</label>
                <select
                  value={selectedFileId}
                  onChange={(e) => setSelectedFileId(e.target.value)}
                  className="form-select"
                >
                  <option value="">Choose a document...</option>
                  {selectedFiles.map(file => (
                    <option key={file.fileId} value={file.fileId}>
                      {file.name}
                    </option>
                  ))}
                </select>
                {selectedFiles.length === 0 && (
                  <p className="form-hint">Select documents from the left panel first</p>
                )}
              </div>
            )}

            <div className="form-group">
              <label>Number of Slides</label>
              <select
                value={totalSlides}
                onChange={(e) => setTotalSlides(parseInt(e.target.value))}
                className="form-select"
              >
                <option value={5}>5 slides</option>
                <option value={8}>8 slides</option>
                <option value={10}>10 slides</option>
                <option value={15}>15 slides</option>
                <option value={20}>20 slides</option>
              </select>
            </div>

            <div className="form-group">
              <label>Theme</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="form-select"
              >
                {themes.map(t => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
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
            >
              Create Presentation
            </button>
          </div>
        </>
      ) : (
        <div className="generation-progress">
          <div className="progress-icon">📊</div>
          <h3>Creating Presentation...</h3>
          {progress && (
            <>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress.percentage || 0}%` }}
                />
              </div>
              <p className="progress-text">
                {progress.percentage || 0}% - {progress.message || 'Generating slides...'}
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default PresentationGenerator;
