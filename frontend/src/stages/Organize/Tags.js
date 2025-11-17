import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  FaTags,
  FaRocket,
  FaSyncAlt,
  FaDownload,
  FaCopy,
  FaSearch,
  FaCheck,
  FaClock,
  FaCloudUploadAlt,
  FaFileAlt,
  FaFolder,
  FaChartLine,
  FaSitemap,
  FaLayerGroup,
  FaExpand,
  FaCompress,
  FaHashtag,
  FaFilter
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './Tags.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

const API_BASE = (config && config.API_BASE_URL) || process.env.REACT_APP_API_BASE_URL || '';

export default function Tags() {
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
  const [taxonomyResults, setTaxonomyResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('all'); // all | content_types | subject_areas | entities | concepts
  const [selectedTag, setSelectedTag] = useState(null);
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState({});

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

  // ---------- Start Tag Taxonomy Generation ----------
  async function startTagTaxonomy() {
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

      const res = await fetch(`${API_BASE}/organize/tags/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ file_ids: selectedFileIds, user_id: userId })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to start tag taxonomy generation');
      }

      const data = await res.json();
      currentProgressId.current = data.progress_id;
      setStatus('running');
      
      pollProgress(data.progress_id, headers);

    } catch (err) {
      setStatus('failed');
      setError(err.message || 'Failed to start tag taxonomy generation');
    }
  }

  // ---------- Poll Progress ----------
  function pollProgress(progressId, headers) {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
    }

    pollerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/organize/tags/progress/${progressId}`, { headers });
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
          setError('Tag taxonomy generation failed');
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
      const res = await fetch(`${API_BASE}/organize/tags/results?file_ids=${fileIdsParam}`, { headers });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to fetch results');
      }

      const data = await res.json();
      setTaxonomyResults(data.results && data.results.length > 0 ? data.results[0] : null);

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
    if (!taxonomyResults) return;

    const blob = new Blob([JSON.stringify(taxonomyResults, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tag-taxonomy-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------- Copy JSON ----------
  function copyJSON() {
    if (!taxonomyResults) return;

    const jsonStr = JSON.stringify(taxonomyResults, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  // ---------- Toggle Category Expansion ----------
  function toggleCategoryExpansion(categoryId) {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryId]: !prev[categoryId]
    }));
  }

  // ---------- Get Filtered Tags ----------
  function getFilteredTags() {
    if (!taxonomyResults || !taxonomyResults.taxonomy) {
      return {};
    }

    const taxonomy = taxonomyResults.taxonomy;
    let filtered = {};

    if (filterCategory === 'all') {
      filtered = taxonomy;
    } else {
      if (taxonomy[filterCategory]) {
        filtered = { [filterCategory]: taxonomy[filterCategory] };
      }
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const searchFiltered = {};
      
      Object.entries(filtered).forEach(([catName, category]) => {
        if (typeof category === 'object' && category.tags) {
          const matchingTags = category.tags.filter(tag => 
            tag.name.toLowerCase().includes(query)
          );
          
          if (matchingTags.length > 0) {
            searchFiltered[catName] = {
              ...category,
              tags: matchingTags
            };
          }
        }
      });
      
      return searchFiltered;
    }

    return filtered;
  }

  // ---------- Toggle Fullscreen ----------
  function toggleFullscreen() {
    setIsFullscreen(!isFullscreen);
  }

  // ---------- Get Tag Color ----------
  function getTagColor(tag) {
    if (tag.confidence >= 0.8) return '#10b981'; // High confidence - green
    if (tag.confidence >= 0.5) return '#3b82f6'; // Medium confidence - blue
    return '#94a3b8'; // Low confidence - gray
  }

  // ---------- Get Category Icon ----------
  function getCategoryIcon(categoryName) {
    const iconMap = {
      'content_types': FaFileAlt,
      'subject_areas': FaFolder,
      'entities': FaTags,
      'concepts': FaHashtag,
      'temporal': FaClock
    };
    return iconMap[categoryName] || FaTags;
  }

  return (
    <div className={`organize-container ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="organize-header">
        <div className="header-left">
          <FaTags className="header-icon" />
          <div>
            <h1>Tag Taxonomy Builder</h1>
            <p style={{ color: '#000000' }}>
              Auto-generate intelligent tag hierarchies for document organization
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
          <FaRocket /> Generate Taxonomy
        </button>
        <button
          className={`tab-btn ${tab === 'results' ? 'active' : ''}`}
          onClick={() => setTab('results')}
          disabled={!taxonomyResults}
        >
          <FaSitemap /> View Taxonomy
        </button>
      </div>

      {tab === 'generate' && (
        <div className="tab-content">
          {/* Source Selection */}
          <div className="source-section">
            <h3>Select Files</h3>
            <div className="source-tabs">
              <button
                className={`source-tab ${source === 'vault' ? 'active' : ''}`}
                onClick={() => setSource('vault')}
              >
                <FaFolder /> Knowledge Vault
              </button>
              <button
                className={`source-tab ${source === 'upload' ? 'active' : ''}`}
                onClick={() => setSource('upload')}
              >
                <FaCloudUploadAlt /> Upload Files
              </button>
            </div>

            {/* Knowledge Vault Files */}
            {source === 'vault' && (
              <div className="vault-section">
                <div className="vault-header">
                  <h4>Available Files ({vaultFiles.length})</h4>
                  <div className="vault-actions">
                    <button className="action-btn" onClick={refreshVaultFiles}>
                      <FaSyncAlt /> Refresh
                    </button>
                    <button className="action-btn" onClick={selectAllFiles}>
                      <FaCheck /> Select All
                    </button>
                    <button className="action-btn" onClick={clearSelection}>
                      Clear
                    </button>
                  </div>
                </div>

                <div className="files-list">
                  {vaultFiles.length === 0 && (
                    <p className="no-files">No files in Knowledge Vault. Please upload some files first.</p>
                  )}
                  {vaultFiles.map((file) => (
                    <div
                      key={file.id}
                      className={`file-item ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                      onClick={() => toggleFileSelection(file.id)}
                    >
                      <input
                        type="checkbox"
                        checked={selectedFileIds.includes(file.id)}
                        readOnly
                      />
                      <FaFileAlt className="file-icon" />
                      <span className="file-name">{file.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload Section */}
            {source === 'upload' && (
              <div className="upload-section">
                <label className="upload-box">
                  <FaCloudUploadAlt className="upload-icon" />
                  <span>Click to upload files or drag and drop</span>
                  <input
                    type="file"
                    multiple
                    onChange={handleUpload}
                    style={{ display: 'none' }}
                  />
                </label>
                {uploading && <p className="uploading">Uploading files...</p>}
              </div>
            )}
          </div>

          {/* Selected Files Summary */}
          {selectedFileIds.length > 0 && (
            <div className="selected-summary">
              <FaCheck className="summary-icon" />
              <span>{selectedFileIds.length} file(s) selected</span>
            </div>
          )}

          {/* Generate Button */}
          <div className="action-section">
            <button
              className="generate-btn"
              onClick={startTagTaxonomy}
              disabled={selectedFileIds.length === 0 || status === 'running'}
            >
              <FaRocket /> {status === 'running' ? 'Generating...' : 'Generate Tag Taxonomy'}
            </button>
          </div>

          {/* Progress */}
          {status === 'running' && (
            <div className="progress-section">
              <div className="progress-header">
                <FaClock /> Building tag taxonomy...
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${progress}%` }}></div>
              </div>
              <div className="progress-text">{progress}% complete</div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          {/* Success Message */}
          {status === 'completed' && (
            <div className="success-message">
              ✅ Tag taxonomy generated successfully! Click the "View Taxonomy" tab to see results.
            </div>
          )}
        </div>
      )}

      {tab === 'results' && (
        <div className="tab-content">
          {!taxonomyResults && (
            <div className="no-results">
              <FaTags className="no-results-icon" />
              <h3>No Taxonomy Generated Yet</h3>
              <p>Generate a tag taxonomy first to see results here.</p>
            </div>
          )}

          {taxonomyResults && (
            <>
              {/* Taxonomy Header with Actions */}
              <div className="results-header">
                <div className="results-title">
                  <FaSitemap className="title-icon" />
                  <h2>Tag Taxonomy Results</h2>
                </div>
                <div className="results-actions">
                  <button className="action-btn" onClick={refreshResults}>
                    <FaSyncAlt /> Refresh
                  </button>
                  <button className="action-btn" onClick={downloadJSON}>
                    <FaDownload /> Download JSON
                  </button>
                  <button className="action-btn" onClick={copyJSON}>
                    {copied ? <><FaCheck /> Copied!</> : <><FaCopy /> Copy JSON</>}
                  </button>
                  <button className="action-btn" onClick={toggleFullscreen}>
                    {isFullscreen ? <FaCompress /> : <FaExpand />}
                  </button>
                </div>
              </div>

              {/* Statistics Overview */}
              <div className="stats-overview">
                <div className="stat-card">
                  <div className="stat-icon">
                    <FaTags />
                  </div>
                  <div className="stat-content">
                    <div className="stat-value">{taxonomyResults.tag_statistics?.total_tags || 0}</div>
                    <div className="stat-label">Total Tags</div>
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-icon">
                    <FaLayerGroup />
                  </div>
                  <div className="stat-content">
                    <div className="stat-value">{taxonomyResults.tag_statistics?.total_categories || 0}</div>
                    <div className="stat-label">Categories</div>
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-icon">
                    <FaChartLine />
                  </div>
                  <div className="stat-content">
                    <div className="stat-value">
                      {(taxonomyResults.tag_statistics?.quality_metrics?.avg_tag_confidence * 100 || 0).toFixed(0)}%
                    </div>
                    <div className="stat-label">Avg Confidence</div>
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-icon">
                    <FaSitemap />
                  </div>
                  <div className="stat-content">
                    <div className="stat-value">
                      {(taxonomyResults.tag_statistics?.quality_metrics?.taxonomy_completeness * 100 || 0).toFixed(0)}%
                    </div>
                    <div className="stat-label">Completeness</div>
                  </div>
                </div>
              </div>

              {/* Search and Filter */}
              <div className="search-filter-section">
                <div className="search-box">
                  <FaSearch className="search-icon" />
                  <input
                    type="text"
                    placeholder="Search tags..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>

                <div className="filter-buttons">
                  <button
                    className={`filter-btn ${filterCategory === 'all' ? 'active' : ''}`}
                    onClick={() => setFilterCategory('all')}
                  >
                    All Categories
                  </button>
                  {taxonomyResults.taxonomy && Object.keys(taxonomyResults.taxonomy).map((catName) => (
                    <button
                      key={catName}
                      className={`filter-btn ${filterCategory === catName ? 'active' : ''}`}
                      onClick={() => setFilterCategory(catName)}
                    >
                      {catName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </button>
                  ))}
                </div>
              </div>

              {/* Taxonomy Display */}
              <div className="taxonomy-section">
                {Object.entries(getFilteredTags()).map(([categoryName, category]) => {
                  if (typeof category !== 'object' || !category.tags) return null;
                  
                  const CategoryIcon = getCategoryIcon(categoryName);
                  const isExpanded = expandedCategories[categoryName] !== false; // Default to expanded

                  return (
                    <div key={categoryName} className="category-card">
                      <div 
                        className="category-header"
                        onClick={() => toggleCategoryExpansion(categoryName)}
                      >
                        <div className="category-title">
                          <CategoryIcon className="category-icon" />
                          <h3>{category.name || categoryName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                          <span className="tag-count">{category.tags.length} tags</span>
                        </div>
                        <button className="expand-btn">
                          {isExpanded ? '−' : '+'}
                        </button>
                      </div>

                      {category.description && (
                        <p className="category-description">{category.description}</p>
                      )}

                      {isExpanded && (
                        <>
                          {/* Main Category Tags */}
                          {category.tags && category.tags.length > 0 && (
                            <div className="tags-grid">
                              {category.tags.map((tag, idx) => (
                                <div 
                                  key={idx} 
                                  className="tag-badge"
                                  style={{ borderColor: getTagColor(tag) }}
                                  onClick={() => setSelectedTag(selectedTag?.name === tag.name ? null : tag)}
                                >
                                  <span className="tag-name">#{tag.name}</span>
                                  <span className="tag-frequency">{tag.frequency}×</span>
                                  <div 
                                    className="tag-confidence-bar"
                                    style={{
                                      width: `${(tag.confidence * 100)}%`,
                                      backgroundColor: getTagColor(tag)
                                    }}
                                  />
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Subcategories */}
                          {category.children && Object.keys(category.children).length > 0 && (
                            <div className="subcategories">
                              {Object.entries(category.children).map(([subName, subCategory]) => (
                                <div key={subName} className="subcategory">
                                  <h4 className="subcategory-title">{subCategory.name}</h4>
                                  <div className="tags-grid">
                                    {subCategory.tags && subCategory.tags.map((tag, idx) => (
                                      <div 
                                        key={idx} 
                                        className="tag-badge small"
                                        style={{ borderColor: getTagColor(tag) }}
                                      >
                                        <span className="tag-name">#{tag.name}</span>
                                        <span className="tag-frequency">{tag.frequency}×</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Category Metadata */}
                          {category.metadata && (
                            <div className="category-metadata">
                              <div className="metadata-item">
                                <strong>Total Tags:</strong> {category.metadata.total_tags}
                              </div>
                              <div className="metadata-item">
                                <strong>Avg Confidence:</strong> {(category.metadata.avg_confidence * 100).toFixed(1)}%
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Selected Tag Details */}
              {selectedTag && (
                <div className="tag-details-panel">
                  <div className="tag-details-header">
                    <h3>Tag Details: #{selectedTag.name}</h3>
                    <button onClick={() => setSelectedTag(null)}>×</button>
                  </div>
                  <div className="tag-details-content">
                    <div className="detail-row">
                      <strong>Frequency:</strong> {selectedTag.frequency}
                    </div>
                    <div className="detail-row">
                      <strong>Confidence:</strong> {(selectedTag.confidence * 100).toFixed(1)}%
                    </div>
                    <div className="detail-row">
                      <strong>Type:</strong> {selectedTag.type}
                    </div>
                    {selectedTag.variants && selectedTag.variants.length > 0 && (
                      <div className="detail-row">
                        <strong>Variants:</strong>
                        <div className="variants-list">
                          {selectedTag.variants.map((variant, idx) => (
                            <span key={idx} className="variant-badge">{variant}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
