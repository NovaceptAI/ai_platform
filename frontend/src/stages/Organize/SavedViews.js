import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  FaSave,
  FaRocket,
  FaSyncAlt,
  FaDownload,
  FaCopy,
  FaSearch,
  FaCheck,
  FaClock,
  FaCloudUploadAlt,
  FaFileAlt,
  FaEye,
  FaFilter,
  FaLayerGroup,
  FaExpand,
  FaCompress,
  FaStar,
  FaFolder,
  FaTags,
  FaChartLine
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './SavedViews.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

const API_BASE = (config && config.API_BASE_URL) || process.env.REACT_APP_API_BASE_URL || '';

// Helper function to convert field names to readable labels
const getFieldLabel = (fieldName) => {
  const fieldLabels = {
    'file_name': 'File Name',
    'created_at': 'Date Created',
    'modified_at': 'Date Modified',
    'file_type': 'File Type',
    'file_size': 'File Size',
    'summary': 'Summary',
    'priority_score': 'Priority',
    'relevance_score': 'Relevance',
    'evidence_count': 'Evidence Count',
    'topic_count': 'Topic Count',
    'similarity_score': 'Similarity',
    'citation_count': 'Citations',
    'review_status': 'Review Status',
    'priority': 'Priority'
  };
  return fieldLabels[fieldName] || fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

export default function SavedViews() {
  const [tab, setTab] = useState('generate'); // generate | results

  // ---------- Knowledge Vault ----------
  const [source, setSource] = useState('vault'); // 'vault' | 'upload'
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [uploading, setUploading] = useState(false);

  // ---------- Progress ----------
  const [status, setStatus] = useState('idle'); // idle | starting | running | completed | failed
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const pollerRef = useRef(null);
  const currentProgressId = useRef(null);

  // ---------- Results ----------
  const [viewsResults, setViewsResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterViewType, setFilterViewType] = useState('all'); // all | default | contextual
  const [selectedView, setSelectedView] = useState(null);
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // ---------- Fetch Knowledge Vault ----------
  useEffect(() => {
    if (source === 'vault') {
      fetchVaultFiles();
    }
  }, [source]);

  async function fetchVaultFiles() {
    try {
      const res = await axiosInstance.get('/upload/files');
      const files = res.data.files || [];

      const normalizedFiles = files.map(file => ({
        id: file.fileId || file.id,
        name: file.name,
        stored_name: file.stored_name
      }));

      setVaultFiles(normalizedFiles);
    } catch (err) {
      console.error('Error fetching vault files:', err);
    }
  }

  async function refreshVaultFiles() {
    await fetchVaultFiles();
  }

  // ---------- File Selection ----------
  function toggleFileSelection(fileId) {
    setSelectedFileIds(prev => {
      if (prev.includes(fileId)) {
        return prev.filter(id => id !== fileId);
      } else {
        return [...prev, fileId];
      }
    });
  }

  function selectAllFiles() {
    if (source === 'vault') {
      setSelectedFileIds(vaultFiles.map(f => f.id));
    }
  }

  function clearSelection() {
    setSelectedFileIds([]);
  }

  // ---------- Upload ----------
  async function handleUpload(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const res = await axiosInstance.post('/upload/files', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const uploadedFileIds = res.data.files.map((f) => f.fileId || f.id);
      setSelectedFileIds(uploadedFileIds);
      setSource('vault');
      await fetchVaultFiles();
    } catch (err) {
      setError('File upload failed');
    } finally {
      setUploading(false);
    }
  }

  // ---------- Start Saved Views Generation ----------
  async function startSavedViews() {
    if (!selectedFileIds || selectedFileIds.length === 0) {
      setError('Please select at least one file.');
      return;
    }

    setStatus('starting');
    setError('');
    setProgress(0);

    try {
      const accessToken = localStorage.getItem('access_token');
      const token = accessToken || (typeof window !== 'undefined' && localStorage.getItem('token')) || '';
      const userId = (typeof window !== 'undefined' && (localStorage.getItem('user_id') || 'admin')) || 'admin';

      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/organize/saved_views/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          file_ids: selectedFileIds,
          user_id: userId
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to start saved views generation');
      }

      const data = await response.json();
      currentProgressId.current = data.progress_id;

      setStatus('running');
      pollProgress(data.progress_id, headers);
    } catch (err) {
      console.error('Error starting saved views:', err);
      setError(err.message || 'Failed to start saved views generation');
      setStatus('failed');
    }
  }

  // ---------- Poll Progress ----------
  function pollProgress(progressId, headers) {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
    }

    pollerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/organize/saved_views/progress/${progressId}`, { headers });
        const data = await res.json();

        setProgress(Number(data.percentage || 0));

        if (data.status === 'completed') {
          clearInterval(pollerRef.current);
          setStatus('completed');
          await fetchResults();
          setTab('results');
        } else if (data.status === 'failed') {
          clearInterval(pollerRef.current);
          setStatus('failed');
          setError('Saved views generation failed');
        }
      } catch (err) {
        console.error('Error polling progress:', err);
      }
    }, 1200);
  }

  useEffect(() => {
    return () => {
      if (pollerRef.current) {
        clearInterval(pollerRef.current);
      }
    };
  }, []);

  // ---------- Fetch Results ----------
  async function fetchResults() {
    if (!selectedFileIds || selectedFileIds.length === 0) {
      setError('No file IDs selected to fetch results.');
      return;
    }

    try {
      const accessToken = localStorage.getItem('access_token');
      const token = accessToken || (typeof window !== 'undefined' && localStorage.getItem('token')) || '';

      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
      }

      const fileIdsParam = selectedFileIds.join(',');
      const res = await fetch(`${API_BASE}/organize/saved_views/results?file_ids=${fileIdsParam}`, { headers });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to fetch results');
      }

      const data = await res.json();
      setViewsResults(data.results && data.results.length > 0 ? data.results[0] : null);

      setTab('results');
    } catch (err) {
      setError(err.message || 'Failed to fetch results.');
    }
  }

  // ---------- Refresh results ----------
  async function refreshResults() {
    setError('');
    await fetchResults();
  }

  // ---------- Download JSON ----------
  function downloadJSON() {
    if (!viewsResults) return;
    const blob = new Blob([JSON.stringify(viewsResults, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `saved_views_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------- Copy to clipboard ----------
  function copyToClipboard() {
    if (!viewsResults) return;
    navigator.clipboard.writeText(JSON.stringify(viewsResults, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // ---------- Filter views ----------
  function getFilteredViews() {
    if (!viewsResults?.views) return { default_views: [], contextual_views: [] };

    const defaultViews = viewsResults.views.default_views || [];
    const contextualViews = viewsResults.views.contextual_views || [];

    let filteredDefault = defaultViews;
    let filteredContextual = contextualViews;

    // Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filteredDefault = defaultViews.filter(view =>
        view.name?.toLowerCase().includes(q) ||
        view.description?.toLowerCase().includes(q) ||
        view.type?.toLowerCase().includes(q)
      );
      filteredContextual = contextualViews.filter(view =>
        view.name?.toLowerCase().includes(q) ||
        view.description?.toLowerCase().includes(q) ||
        view.type?.toLowerCase().includes(q)
      );
    }

    // Filter by view type
    if (filterViewType === 'default') {
      filteredContextual = [];
    } else if (filterViewType === 'contextual') {
      filteredDefault = [];
    }

    return {
      default_views: filteredDefault,
      contextual_views: filteredContextual
    };
  }

  // ---------- Get view icon ----------
  function getViewIcon(view) {
    const iconMap = {
      complete: FaFileAlt,
      temporal: FaClock,
      priority: FaStar,
      category: FaFolder,
      collection: FaLayerGroup,
      special: FaFilter,
      topic_focused: FaTags,
      entity_focused: FaTags,
      cluster: FaLayerGroup,
      workflow: FaChartLine,
      comprehensive_single: FaEye,
      document_view: FaFileAlt
    };
    
    return iconMap[view.type] || FaEye;
  }

  // ---------- Get view color ----------
  function getViewColor(view) {
    return view.color || '#10b981';
  }

  // ---------- Toggle fullscreen ----------
  function toggleFullscreen() {
    setIsFullscreen(!isFullscreen);
  }

  // ---------- Render ----------
  return (
    <div className={`saved-views-wrap ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Header */}
      <div className="organize-header">
        <div className="header-left">
          <FaSave className="header-icon" />
          <div>
            <h1>Saved Views</h1>
            <p style={{ color: '#000000' }}>
              Create custom organizational views and filters for quick access
            </p>
          </div>
        </div>
        <Link to="/organize" className="back-link">
          ← Back to Organize
        </Link>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${tab === 'generate' ? 'active' : ''}`}
          onClick={() => setTab('generate')}
        >
          <FaRocket /> Generate Views
        </button>
        <button
          className={`tab-btn ${tab === 'results' ? 'active' : ''}`}
          onClick={() => setTab('results')}
          disabled={!viewsResults}
        >
          <FaEye /> View Results
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* GENERATE TAB */}
      {tab === 'generate' && (
        <div className="generate-section">
          {/* File Selection */}
          <div className="input-group">
            <label className="input-label">
              <FaFileAlt /> Select Documents for View Generation
            </label>
            <div className="source-toggle">
              <button
                className={`source-btn ${source === 'vault' ? 'active' : ''}`}
                onClick={() => setSource('vault')}
              >
                Knowledge Vault
              </button>
              <button
                className={`source-btn ${source === 'upload' ? 'active' : ''}`}
                onClick={() => setSource('upload')}
              >
                Upload Files
              </button>
            </div>

            {source === 'vault' && (
              <div className="vault-files-container">
                <div className="vault-header">
                  <span className="file-count">
                    {selectedFileIds.length} of {vaultFiles.length} selected
                  </span>
                  <div className="vault-actions">
                    <button className="action-btn-sm" onClick={selectAllFiles}>
                      Select All
                    </button>
                    <button className="action-btn-sm" onClick={clearSelection}>
                      Clear
                    </button>
                    <button className="action-btn-sm" onClick={refreshVaultFiles}>
                      <FaSyncAlt /> Refresh
                    </button>
                  </div>
                </div>

                {vaultFiles.length === 0 ? (
                  <p className="no-files-msg">No files in vault. Upload some files first.</p>
                ) : (
                  <div className="file-list">
                    {vaultFiles.map((file) => (
                      <div
                        key={file.id}
                        className={`file-item ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                        onClick={() => toggleFileSelection(file.id)}
                      >
                        <input
                          type="checkbox"
                          checked={selectedFileIds.includes(file.id)}
                          onChange={() => toggleFileSelection(file.id)}
                          className="file-checkbox"
                        />
                        <FaFileAlt className="file-icon" />
                        <span className="file-name">{file.name || file.stored_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {source === 'upload' && (
              <div className="upload-section">
                <label className="upload-btn-label">
                  <FaCloudUploadAlt />
                  {uploading ? ' Uploading...' : ' Choose Files (Multiple)'}
                  <input
                    type="file"
                    multiple
                    onChange={handleUpload}
                    disabled={uploading}
                    style={{ display: 'none' }}
                  />
                </label>
                {selectedFileIds.length > 0 && (
                  <p className="upload-success">
                    <FaCheck /> {selectedFileIds.length} file(s) uploaded and selected
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              className="primary-btn"
              onClick={startSavedViews}
              disabled={status === 'running' || selectedFileIds.length === 0}
            >
              <FaRocket />
              {status === 'running' ? ' Generating...' : ' Generate Saved Views'}
            </button>
          </div>

          {/* Progress */}
          {status === 'running' && (
            <div className="progress-container">
              <div className="progress-header">
                <FaClock className="progress-icon rotating" />
                <span>Generating saved views... {progress}%</span>
              </div>
              <div className="progress-bar-bg">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {status === 'completed' && (
            <div className="success-banner">
              <FaCheck /> Saved views generated successfully! Click "View Results" to explore.
            </div>
          )}
        </div>
      )}

      {/* RESULTS TAB */}
      {tab === 'results' && viewsResults && (
        <div className="results-section">
          {/* Toolbar */}
          <div className="results-toolbar">
            <div className="toolbar-left">
              <button className="icon-btn" onClick={refreshResults} title="Refresh">
                <FaSyncAlt />
              </button>
              <button className="icon-btn" onClick={downloadJSON} title="Download JSON">
                <FaDownload />
              </button>
              <button className="icon-btn" onClick={copyToClipboard} title="Copy to Clipboard">
                {copied ? <FaCheck /> : <FaCopy />}
              </button>
              <button className="icon-btn" onClick={toggleFullscreen} title="Toggle Fullscreen">
                {isFullscreen ? <FaCompress /> : <FaExpand />}
              </button>
            </div>

            <div className="toolbar-right">
              <div className="search-box">
                <FaSearch className="search-icon" />
                <input
                  type="text"
                  placeholder="Search views..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-input"
                />
              </div>
              
              <select
                className="filter-select"
                value={filterViewType}
                onChange={(e) => setFilterViewType(e.target.value)}
              >
                <option value="all">All Views</option>
                <option value="default">Default Views</option>
                <option value="contextual">Contextual Views</option>
              </select>
            </div>
          </div>

          {/* Summary Statistics */}
          <div className="stats-overview">
            <div className="stat-card">
              <div className="stat-icon">
                <FaEye />
              </div>
              <div className="stat-content">
                <div className="stat-value">{viewsResults.total_views || 0}</div>
                <div className="stat-label">Total Views</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <FaLayerGroup />
              </div>
              <div className="stat-content">
                <div className="stat-value">{viewsResults.default_views_count || 0}</div>
                <div className="stat-label">Default Views</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <FaTags />
              </div>
              <div className="stat-content">
                <div className="stat-value">{viewsResults.contextual_views_count || 0}</div>
                <div className="stat-label">Contextual Views</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <FaFilter />
              </div>
              <div className="stat-content">
                <div className="stat-value">
                  {Object.keys(viewsResults.view_metadata?.filter_combinations?.quick_filters || {}).length}
                </div>
                <div className="stat-label">Quick Filters</div>
              </div>
            </div>
          </div>

          {/* Default Views Section */}
          {getFilteredViews().default_views.length > 0 && (
            <div className="views-section">
              <h3 className="section-title">
                <FaLayerGroup /> Default Views ({getFilteredViews().default_views.length})
              </h3>
              <div className="views-grid">
                {getFilteredViews().default_views.map((view) => {
                  const IconComponent = getViewIcon(view);
                  return (
                    <div
                      key={view.view_id}
                      className={`view-card ${selectedView?.view_id === view.view_id ? 'selected' : ''}`}
                      style={{ borderLeftColor: getViewColor(view) }}
                      onClick={() => setSelectedView(selectedView?.view_id === view.view_id ? null : view)}
                    >
                      <div className="view-header">
                        <IconComponent style={{ color: getViewColor(view), fontSize: '1.5rem' }} />
                        <h4 className="view-name">{view.name}</h4>
                        {view.is_system_view && <span className="system-badge">System</span>}
                      </div>

                      <p className="view-description">{view.description}</p>

                      <div className="view-meta">
                        <span className="view-type-badge">{view.type}</span>
                        {view.file_count && (
                          <span className="view-count">{view.file_count} files</span>
                        )}
                        <span className="view-display">{view.display_mode}</span>
                      </div>

                      {selectedView?.view_id === view.view_id && (
                        <div className="view-details">
                          {view.files && view.files.length > 0 && (
                            <div className="detail-item">
                              <strong>Files ({view.files.length}):</strong>
                              <div className="file-list">
                                {view.files.map((file, idx) => (
                                  <div key={idx} className="file-item">
                                    <FaFileAlt style={{ marginRight: '6px', fontSize: '0.85rem', color: '#10b981' }} />
                                    <span className="file-name">{file.file_name || 'Unnamed File'}</span>
                                    {file.file_type && (
                                      <span className="file-type-tag">{file.file_type}</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {view.sort_order && (
                            <div className="detail-item">
                              <strong>Sort:</strong> {view.sort_order.map(s => `${getFieldLabel(s.field)} (${s.direction === 'asc' ? 'A-Z' : 'Z-A'})`).join(', ')}
                            </div>
                          )}
                          {view.columns && (
                            <div className="detail-item">
                              <strong>Columns:</strong> {view.columns.map(col => getFieldLabel(col)).join(', ')}
                            </div>
                          )}
                          {view.filters && Object.keys(view.filters).length > 0 && (
                            <div className="detail-item">
                              <strong>Filters:</strong>
                              <div className="filter-preview">
                                {Object.entries(view.filters).map(([key, value]) => (
                                  <div key={key} className="filter-chip">
                                    <strong>{key}:</strong> {typeof value === 'object' ? value.operation || 'custom' : value}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Contextual Views Section */}
          {getFilteredViews().contextual_views.length > 0 && (
            <div className="views-section">
              <h3 className="section-title">
                <FaTags /> Contextual Views ({getFilteredViews().contextual_views.length})
              </h3>
              <div className="views-grid">
                {getFilteredViews().contextual_views.map((view) => {
                  const IconComponent = getViewIcon(view);
                  return (
                    <div
                      key={view.view_id}
                      className={`view-card ${selectedView?.view_id === view.view_id ? 'selected' : ''}`}
                      style={{ borderLeftColor: getViewColor(view) }}
                      onClick={() => setSelectedView(selectedView?.view_id === view.view_id ? null : view)}
                    >
                      <div className="view-header">
                        <IconComponent style={{ color: getViewColor(view), fontSize: '1.5rem' }} />
                        <h4 className="view-name">{view.name}</h4>
                      </div>

                      <p className="view-description">{view.description}</p>

                      <div className="view-meta">
                        <span className="view-type-badge">{view.type}</span>
                        {view.files && (
                          <span className="view-count">{view.files.length} files</span>
                        )}
                        {view.display_mode && (
                          <span className="view-display">{view.display_mode}</span>
                        )}
                      </div>

                      {selectedView?.view_id === view.view_id && (
                        <div className="view-details">
                          {view.files && view.files.length > 0 && (
                            <div className="detail-item">
                              <strong>Files ({view.files.length}):</strong>
                              <div className="file-list">
                                {view.files.map((file, idx) => (
                                  <div key={idx} className="file-item">
                                    <FaFileAlt style={{ marginRight: '6px', fontSize: '0.85rem', color: '#10b981' }} />
                                    <span className="file-name">{file.file_name || 'Unnamed File'}</span>
                                    {file.file_type && (
                                      <span className="file-type-tag">{file.file_type}</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {view.sections?.overview && (
                            <div className="detail-item">
                              <strong>Overview:</strong>
                              <div className="overview-content">
                                <p><strong>Summary:</strong> {view.sections.overview.summary}</p>
                                <p><strong>Pages:</strong> {view.sections.overview.page_count}</p>
                                <p><strong>Type:</strong> {view.sections.overview.file_type}</p>
                              </div>
                            </div>
                          )}
                          {view.sections?.content_analysis && (
                            <div className="detail-item">
                              <strong>Content Analysis:</strong>
                              <div className="content-tags">
                                {view.sections.content_analysis.topics?.length > 0 && (
                                  <div>
                                    <strong>Topics:</strong> {view.sections.content_analysis.topics.slice(0, 5).join(', ')}
                                  </div>
                                )}
                                {view.sections.content_analysis.keywords?.length > 0 && (
                                  <div>
                                    <strong>Keywords:</strong> {view.sections.content_analysis.keywords.slice(0, 5).join(', ')}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                          {view.metadata && (
                            <div className="detail-item">
                              <strong>Details:</strong>
                              <div className="metadata-list">
                                {Object.entries(view.metadata).map(([key, value]) => (
                                  <div key={key} className="metadata-row">
                                    <span className="meta-key">{key.replace(/_/g, ' ')}:</span>
                                    <span className="meta-value">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {view.filters && Object.keys(view.filters).length > 0 && (
                            <div className="detail-item">
                              <strong>Filters:</strong>
                              <div className="filter-preview">
                                {Object.entries(view.filters).map(([key, value]) => (
                                  <div key={key} className="filter-chip">
                                    <strong>{key}:</strong> {typeof value === 'object' ? (value.operation || 'custom') : String(value)}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* View Templates Section */}
          {viewsResults.view_metadata?.view_templates && viewsResults.view_metadata.view_templates.length > 0 && (
            <div className="views-section">
              <h3 className="section-title">
                <FaFolder /> View Templates ({viewsResults.view_metadata.view_templates.length})
              </h3>
              <div className="templates-list">
                {viewsResults.view_metadata.view_templates.map((template) => (
                  <div key={template.template_id} className="template-card">
                    <h4>{template.name}</h4>
                    <p>{template.description}</p>
                    <div className="template-views">
                      {template.views && template.views.map((v, idx) => (
                        <span key={idx} className="template-view-badge">
                          {v.name} ({v.type})
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Results */}
          {getFilteredViews().default_views.length === 0 && getFilteredViews().contextual_views.length === 0 && (
            <div className="no-results">
              <FaSearch size={48} />
              <p>No views found matching your search.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
