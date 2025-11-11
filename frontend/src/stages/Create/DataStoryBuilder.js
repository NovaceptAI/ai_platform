// src/stages/Create/DataStoryBuilder.js
import React, { useState, useEffect } from 'react';
import axiosInstance from '../../utils/axiosInstance';
import './DataStoryBuilder.css';
import { FileText, Upload, Database, Sparkles, Eye, Trash2, BarChart3 } from 'lucide-react';

function DataStoryBuilder() {
  const [activeTab, setActiveTab] = useState('create');
  
  // Source type
  const [sourceType, setSourceType] = useState('vault'); // 'vault' | 'upload'
  
  // Vault files
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedFileId, setSelectedFileId] = useState(null);
  
  // Upload
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadedFileId, setUploadedFileId] = useState(null);
  
  // Stage 1 state
  const [storyTitle, setStoryTitle] = useState('');
  const [stage1Loading, setStage1Loading] = useState(false);
  const [stage1Progress, setStage1Progress] = useState(0);
  const [stage1ProgressId, setStage1ProgressId] = useState(null);
  const [error, setError] = useState('');
  
  // Stage 1 results
  const [dataProfile, setDataProfile] = useState(null);
  const [insights, setInsights] = useState(null);
  const [currentStoryId, setCurrentStoryId] = useState(null);
  
  // Stage 2 state
  const [selectedCharts, setSelectedCharts] = useState([]);
  const [stage2Loading, setStage2Loading] = useState(false);
  const [stage2Progress, setStage2Progress] = useState(0);
  const [stage2ProgressId, setStage2ProgressId] = useState(null);
  
  // Gallery state
  const [gallery, setGallery] = useState([]);
  const [viewingStory, setViewingStory] = useState(null);
  const [isLoadingGallery, setIsLoadingGallery] = useState(false);

  // ========== FETCH VAULT FILES ==========

  useEffect(() => {
    if (sourceType === 'vault') {
      fetchVaultFiles();
    }
  }, [sourceType]);

  useEffect(() => {
    if (activeTab === 'gallery') {
      loadGallery();
    }
  }, [activeTab]);

  const fetchVaultFiles = async () => {
    try {
      const response = await axiosInstance.get('/upload/files');
      const files = response.data.files || [];

      // Normalize file structure and filter for CSV/Excel files
      const dataFiles = files.filter(file => {
        const ext = file.name?.toLowerCase();
        return ext?.endsWith('.csv') || ext?.endsWith('.xlsx') || ext?.endsWith('.xls');
      });

      const normalizedFiles = dataFiles.map(file => ({
        id: file.fileId || file.id,
        name: file.name,
        stored_name: file.stored_name
      }));

      setVaultFiles(normalizedFiles);
    } catch (err) {
      console.error('Error fetching vault files:', err);
      setError('Failed to load Knowledge Vault files');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validExtensions = ['.csv', '.xlsx', '.xls'];
    const fileExt = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!validExtensions.includes(fileExt)) {
      setError('Please upload a CSV or Excel file (.csv, .xlsx, .xls)');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axiosInstance.post('/upload/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setUploadedFile(file);
      setUploadedFileId(response.data.file_id);
      setError('');
    } catch (err) {
      console.error('Upload error:', err);
      setError('Failed to upload file: ' + (err.response?.data?.error || err.message));
    }
  };

  const toggleFileSelection = (fileId) => {
    setSelectedFileId(fileId === selectedFileId ? null : fileId);
    setError('');
  };

  // ========== STAGE 1: PROFILE & INSIGHTS ==========

  const handleStartStage1 = async () => {
    // Validate input based on source type
    let file_id = null;

    if (sourceType === 'vault') {
      if (!selectedFileId) {
        setError('Please select a file from vault');
        return;
      }
      file_id = selectedFileId;
    } else { // upload
      if (!uploadedFileId) {
        setError('Please upload a file');
        return;
      }
      file_id = uploadedFileId;
    }

    if (!storyTitle.trim()) {
      setError('Please enter a title for your data story');
      return;
    }

    setStage1Loading(true);
    setStage1Progress(0);
    setError('');

    try {
      const response = await axiosInstance.post('/data_story_builder/start_stage_1', {
        file_id: file_id,
        title: storyTitle.trim()
      });

      if (response.data.success) {
        setStage1ProgressId(response.data.progress_id);
        pollStage1Progress(response.data.progress_id);
      } else {
        throw new Error(response.data.error || 'Failed to start Stage 1');
      }
    } catch (err) {
      console.error('Error starting Stage 1:', err);
      setError(err.response?.data?.error || err.message);
      setStage1Loading(false);
    }
  };

  const pollStage1Progress = (progressId) => {
    const interval = setInterval(async () => {
      try {
        const response = await axiosInstance.get(`/data_story_builder/progress/${progressId}`);
        
        if (response.data.success) {
          setStage1Progress(response.data.percentage);

          if (response.data.status === 'completed') {
            clearInterval(interval);
            setStage1Loading(false);
            
            // Get story details
            const storyId = response.data.result_data.data_story_id;
            setCurrentStoryId(storyId);
            await loadStoryDetails(storyId);
            setActiveTab('insights');
          } else if (response.data.status === 'failed') {
            clearInterval(interval);
            setStage1Loading(false);
            setError(response.data.error_message || 'Generation failed');
          }
        }
      } catch (err) {
        console.error('Error polling progress:', err);
        clearInterval(interval);
        setStage1Loading(false);
        setError('Failed to check progress');
      }
    }, 2000); // Poll every 2 seconds
  };

  const loadStoryDetails = async (storyId) => {
    try {
      const response = await axiosInstance.get(`/data_story_builder/story/${storyId}`);
      
      if (response.data.success) {
        const story = response.data.story;
        setDataProfile(story.data_profile);
        setInsights(story.insights_data);
      }
    } catch (err) {
      console.error('Error loading story details:', err);
      setError('Failed to load story details');
    }
  };

  // ========== STAGE 2: VISUALIZATIONS ==========

  const handleChartSelection = (chart) => {
    setSelectedCharts(prev => {
      const exists = prev.find(c => c.title === chart.title);
      if (exists) {
        return prev.filter(c => c.title !== chart.title);
      } else {
        return [...prev, chart];
      }
    });
  };

  const handleStartStage2 = async () => {
    if (selectedCharts.length === 0) {
      setError('Please select at least one chart to generate');
      return;
    }

    setStage2Loading(true);
    setStage2Progress(0);
    setError('');

    try {
      const response = await axiosInstance.post('/data_story_builder/start_stage_2', {
        data_story_id: currentStoryId,
        selected_charts: selectedCharts
      });

      if (response.data.success) {
        setStage2ProgressId(response.data.progress_id);
        pollStage2Progress(response.data.progress_id);
      } else {
        throw new Error(response.data.error || 'Failed to start Stage 2');
      }
    } catch (err) {
      console.error('Error starting Stage 2:', err);
      setError(err.response?.data?.error || err.message);
      setStage2Loading(false);
    }
  };

  const pollStage2Progress = (progressId) => {
    const interval = setInterval(async () => {
      try {
        const response = await axiosInstance.get(`/data_story_builder/progress/${progressId}`);
        
        if (response.data.success) {
          setStage2Progress(response.data.percentage);

          if (response.data.status === 'completed') {
            clearInterval(interval);
            setStage2Loading(false);
            
            // Reload story to get visualizations
            await loadStoryDetails(currentStoryId);
            
            // Load the story for viewing and switch to view tab
            const storyResponse = await axiosInstance.get(`/data_story_builder/story/${currentStoryId}`);
            if (storyResponse.data.success) {
              setViewingStory(storyResponse.data.story);
              setActiveTab('view');
            }
          } else if (response.data.status === 'failed') {
            clearInterval(interval);
            setStage2Loading(false);
            setError(response.data.error_message || 'Generation failed');
          }
        }
      } catch (err) {
        console.error('Error polling progress:', err);
        clearInterval(interval);
        setStage2Loading(false);
        setError('Failed to check progress');
      }
    }, 2000);
  };

  // ========== GALLERY ==========

  const loadGallery = async () => {
    setIsLoadingGallery(true);
    try {
      const response = await axiosInstance.get('/data_story_builder/gallery');
      
      if (response.data.success) {
        setGallery(response.data.stories || []);
      }
    } catch (err) {
      console.error('Error loading gallery:', err);
      setError('Failed to load gallery');
    } finally {
      setIsLoadingGallery(false);
    }
  };

  const viewStory = async (storyId) => {
    try {
      const response = await axiosInstance.get(`/data_story_builder/story/${storyId}`);
      
      if (response.data.success) {
        setViewingStory(response.data.story);
        setActiveTab('view');
      }
    } catch (err) {
      console.error('Error viewing story:', err);
      setError('Failed to load story');
    }
  };

  const handleDeleteStory = async (storyId, event) => {
    // Prevent event bubbling
    if (event) {
      event.stopPropagation();
    }

    if (!window.confirm('Are you sure you want to delete this data story? This action cannot be undone.')) {
      return;
    }

    try {
      await axiosInstance.delete(`/data_story_builder/story/${storyId}`);

      // Reload gallery
      await loadGallery();

      // If viewing the deleted story, go back to gallery
      if (viewingStory && viewingStory.id === storyId) {
        setViewingStory(null);
        setActiveTab('gallery');
      }
    } catch (err) {
      console.error('Error deleting story:', err);
      setError(err.response?.data?.error || 'Failed to delete story');
    }
  };

  // ========== RENDER ==========

  return (
    <div className="data-story-builder">
      {/* Header */}
      <div className="dsb-hero">
        <h1>
          <BarChart3 size={40} />
          Data Story Builder
        </h1>
        <p className="dsb-subtitle">Transform your data into compelling visual stories with AI insights</p>
      </div>

      {/* Tabs */}
      <div className="dsb-tabs">
        <button 
          className={`dsb-tab ${activeTab === 'create' ? 'active' : ''}`}
          onClick={() => setActiveTab('create')}
          disabled={stage1Loading || stage2Loading}
        >
          <Sparkles size={18} />
          Create
        </button>
        <button 
          className={`dsb-tab ${activeTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveTab('insights')}
          disabled={!insights}
        >
          <Database size={18} />
          Insights
        </button>
        <button 
          className={`dsb-tab ${activeTab === 'visualizations' ? 'active' : ''}`}
          onClick={() => setActiveTab('visualizations')}
          disabled={!dataProfile}
        >
          <BarChart3 size={18} />
          Visualizations
        </button>
        <button 
          className={`dsb-tab ${activeTab === 'gallery' ? 'active' : ''}`}
          onClick={() => setActiveTab('gallery')}
        >
          <FileText size={18} />
          Gallery {gallery.length > 0 && `(${gallery.length})`}
        </button>
        {viewingStory && (
          <button 
            className={`dsb-tab ${activeTab === 'view' ? 'active' : ''}`}
            onClick={() => setActiveTab('view')}
          >
            <Eye size={18} />
            View Story
          </button>
        )}
      </div>

      <div className="dsb-section">
        {/* CREATE TAB */}
        {activeTab === 'create' && (
          <>
            <h2 className="dsb-section-title">Select Data Source</h2>

            {/* Source selector */}
            <div className="dsb-source-selector">
              <label className="dsb-radio">
                <input
                  type="radio"
                  value="vault"
                  checked={sourceType === 'vault'}
                  onChange={() => setSourceType('vault')}
                />
                <span>Knowledge Vault</span>
              </label>
              <label className="dsb-radio">
                <input
                  type="radio"
                  value="upload"
                  checked={sourceType === 'upload'}
                  onChange={() => setSourceType('upload')}
                />
                <span>Upload File</span>
              </label>
            </div>

            {/* Vault selection */}
            {sourceType === 'vault' && (
              <div className="dsb-form-group">
                <label className="dsb-label">Select Dataset from Vault</label>
                <div className="dsb-file-list">
                  {vaultFiles.length === 0 ? (
                    <div className="dsb-empty-files">
                      No CSV or Excel files in vault. Upload files first.
                    </div>
                  ) : (
                    vaultFiles.map((file) => (
                      <div
                        key={file.id}
                        className={`dsb-file-item ${selectedFileId === file.id ? 'selected' : ''}`}
                        onClick={() => toggleFileSelection(file.id)}
                      >
                        <FileText size={18} />
                        <span className="dsb-file-name">{file.name}</span>
                        {selectedFileId === file.id && (
                          <span className="dsb-selected-badge">✓</span>
                        )}
                      </div>
                    ))
                  )}
                </div>
                {selectedFileId && (
                  <div className="dsb-selected-count">
                    File selected
                  </div>
                )}
              </div>
            )}

            {/* Upload */}
            {sourceType === 'upload' && (
              <div className="dsb-form-group">
                <label className="dsb-label">Upload Dataset (.csv, .xlsx, .xls)</label>
                <input
                  type="file"
                  className="dsb-input"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                />
                {uploadedFile && (
                  <div className="dsb-uploaded-list">
                    <div className="dsb-uploaded-item">
                      <FileText size={18} />
                      <span>{uploadedFile.name}</span>
                      <span className="dsb-file-size">
                        {(uploadedFile.size / 1024).toFixed(1)} KB
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Story Title */}
            <div className="dsb-form-group">
              <label className="dsb-label">Story Title</label>
              <input 
                type="text"
                className="dsb-input"
                value={storyTitle}
                onChange={(e) => setStoryTitle(e.target.value)}
                placeholder="Q4 Sales Analysis"
                disabled={stage1Loading}
              />
            </div>

            {/* Actions */}
            <div className="dsb-actions">
              <button 
                className="btn-primary"
                onClick={handleStartStage1}
                disabled={stage1Loading || (!selectedFileId && !uploadedFileId) || !storyTitle.trim()}
              >
                <Sparkles size={20} />
                {stage1Loading ? 'Analyzing Dataset...' : 'Analyze Dataset'}
              </button>
            </div>

            {/* Progress */}
            {stage1Loading && (
              <div className="dsb-progress-container">
                <div className="dsb-progress-bar">
                  <div
                    className="dsb-progress-fill"
                    style={{ width: `${stage1Progress}%` }}
                  />
                </div>
                <div className="dsb-progress-text">
                  {stage1Progress}% - Analyzing dataset and generating insights...
                </div>
              </div>
            )}

            {/* Error */}
            {error && <div className="dsb-error">{error}</div>}
          </>
        )}

        {/* INSIGHTS TAB */}
        {activeTab === 'insights' && insights && (
          <div className="insights-tab">
            <h2>AI Insights</h2>

            <div className="narrative-section">
              <h3>Story Narrative</h3>
              <div className="narrative-card">
                <h4>Introduction</h4>
                <p>{insights.narrative?.introduction}</p>
                
                <h4>Key Findings</h4>
                <p>{insights.narrative?.key_findings}</p>
                
                <h4>Conclusion</h4>
                <p>{insights.narrative?.conclusion}</p>
              </div>
            </div>

            <div className="insights-section">
              <h3>Key Insights</h3>
              {insights.key_insights?.map((insight, idx) => (
                <div key={idx} className="insight-card">
                  <span className={`insight-type ${insight.type}`}>{insight.type}</span>
                  <h4>{insight.title}</h4>
                  <p>{insight.description}</p>
                  <span className={`confidence ${insight.confidence}`}>
                    Confidence: {insight.confidence}
                  </span>
                </div>
              ))}
            </div>

            <div className="recommendations-section">
              <h3>Recommendations</h3>
              <ul>
                {insights.recommendations?.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
              <button 
                className="btn-primary"
                onClick={() => setActiveTab('visualizations')}
              >
                Next: Create Visualizations →
              </button>
              {dataProfile && (
                <button 
                  className="btn-ghost"
                  onClick={() => setActiveTab('visualizations')}
                >
                  Go to Visualizations
                </button>
              )}
            </div>
          </div>
        )}

        {/* VISUALIZATIONS TAB */}
        {activeTab === 'visualizations' && dataProfile && (
          <div className="visualizations-tab">
            <h2>Generate Visualizations</h2>
            <p>Select charts to generate from your data:</p>

            {viewingStory && viewingStory.id === currentStoryId && viewingStory.visualizations && viewingStory.visualizations.length > 0 && (
              <div style={{ 
                padding: '1rem', 
                background: '#dbeafe', 
                borderRadius: '8px', 
                marginBottom: '1.5rem',
                border: '2px solid #3b82f6'
              }}>
                <p style={{ margin: 0, color: '#1e40af', fontWeight: 500 }}>
                  ✓ You already have {viewingStory.visualizations.length} visualization{viewingStory.visualizations.length !== 1 ? 's' : ''} generated. 
                  You can select different charts and regenerate, or view your current story.
                </p>
                <button 
                  className="btn-primary btn-sm"
                  style={{ marginTop: '0.75rem' }}
                  onClick={() => setActiveTab('view')}
                >
                  <Eye size={16} />
                  View Current Story
                </button>
              </div>
            )}

            <div className="charts-grid">
              {dataProfile.suggested_charts?.map((chart, idx) => (
                <div 
                  key={idx}
                  className={`chart-card ${selectedCharts.find(c => c.title === chart.title) ? 'selected' : ''}`}
                  onClick={() => handleChartSelection(chart)}
                >
                  <h4>{chart.title}</h4>
                  <p>Type: {chart.chart_type}</p>
                  <span className={`priority ${chart.priority}`}>{chart.priority}</span>
                </div>
              ))}
            </div>

            {stage2Loading ? (
              <div className="loading-section">
                <div className="progress-bar">
                  <div className="progress-fill" style={{width: `${stage2Progress}%`}}></div>
                </div>
                <p>Generating visualizations... {stage2Progress}%</p>
              </div>
            ) : (
              <button 
                className="primary-btn"
                onClick={handleStartStage2}
                disabled={selectedCharts.length === 0}
              >
                Generate {selectedCharts.length} Chart{selectedCharts.length !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        )}

        {/* GALLERY TAB */}
        {activeTab === 'gallery' && (
          <>
            <div className="dsb-section-header">
              <h2 className="dsb-section-title">Data Story Gallery</h2>
              <div className="dsb-header-info">
                {gallery.length} stor{gallery.length !== 1 ? 'ies' : 'y'} created
              </div>
            </div>

            {/* Creating overlay */}
            {stage1Loading && (
              <div className="dsb-creating-overlay">
                <div className="dsb-creating-message">
                  <Sparkles size={32} />
                  <p>Creating new data story...</p>
                  <div className="dsb-progress-bar">
                    <div
                      className="dsb-progress-fill"
                      style={{ width: `${stage1Progress}%` }}
                    />
                  </div>
                  <div className="dsb-progress-text">
                    {stage1Progress}% - Analyzing dataset...
                  </div>
                </div>
              </div>
            )}

            {isLoadingGallery ? (
              <div className="dsb-empty">
                Loading gallery...
              </div>
            ) : gallery.length === 0 ? (
              <div className="dsb-empty">
                No data stories created yet. Go to Create tab to make your first data story!
              </div>
            ) : (
              <div className="dsb-stories-grid">
                {gallery.map((story) => (
                  <div key={story.id} className="dsb-story-card">
                    <div className="dsb-story-header">
                      <h3 className="dsb-story-title">
                        {story.title}
                      </h3>
                      <div className="dsb-story-meta">
                        {story.dataset_name && `${story.dataset_name} • `}
                        {story.source_type}
                        {story.total_visualizations && ` • ${story.total_visualizations} charts`}
                      </div>
                    </div>

                    {/* Preview thumbnail */}
                    {story.thumbnail_url && (
                      <div className="dsb-story-preview">
                        <img
                          src={story.thumbnail_url}
                          alt="Story preview"
                          className="dsb-preview-image"
                        />
                      </div>
                    )}

                    <div className="dsb-story-actions">
                      <button
                        className="btn-primary btn-sm"
                        onClick={() => viewStory(story.id)}
                      >
                        <Eye size={16} />
                        View Story
                      </button>
                      <button
                        className="btn-ghost btn-sm"
                        onClick={(e) => handleDeleteStory(story.id, e)}
                        style={{ color: '#dc2626' }}
                      >
                        <Trash2 size={16} />
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* VIEW STORY TAB */}
        {activeTab === 'view' && viewingStory && (
          <>
            <div className="dsb-story-viewer">
              <div className="dsb-viewer-header">
                <h2 className="dsb-section-title">
                  {viewingStory.title}
                </h2>
                <button
                  className="btn-ghost"
                  onClick={() => setActiveTab('gallery')}
                >
                  Back to Gallery
                </button>
              </div>

              {/* Visualizations */}
              {viewingStory.visualizations && viewingStory.visualizations.length > 0 && (
                <div className="dsb-visualizations">
                  {viewingStory.visualizations.map((viz, idx) => (
                    <div key={idx} className="dsb-visualization-card">
                      <h3>{viz.title}</h3>
                      {viz.chart_url && (
                        <img src={viz.chart_url} alt={viz.title} />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* PDF/HTML Export links */}
              {(viewingStory.pdf_url || viewingStory.html_url) && (
                <div className="dsb-export-section">
                  <h3>Exports</h3>
                  <div className="dsb-export-buttons">
                    {viewingStory.pdf_url && (
                      <a
                        href={viewingStory.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-primary"
                      >
                        Download PDF
                      </a>
                    )}
                    {viewingStory.html_url && (
                      <a
                        href={viewingStory.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-primary"
                      >
                        View HTML Report
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default DataStoryBuilder;
