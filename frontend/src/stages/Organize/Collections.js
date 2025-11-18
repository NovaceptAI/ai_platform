import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaFolderOpen,
  FaRocket,
  FaSyncAlt,
  FaDownload,
  FaCopy,
  FaSearch,
  FaCheck,
  FaClock,
  FaCloudUploadAlt,
  FaFileAlt,
  FaPlus,
  FaShare,
  FaTags,
  FaEllipsisV,
  FaCodeBranch,
  FaClone,
  FaBookOpen,
  FaLayerGroup
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './Collections.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

const API_BASE = (config && config.API_BASE_URL) || process.env.REACT_APP_API_BASE_URL || '';

export default function Collections() {
  const [tab, setTab] = useState('generate'); // generate | results

  // ---------- Knowledge Vault ----------
  const [source, setSource] = useState('vault'); // 'vault' | 'upload'
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]); // multiple files for collections
  const [uploading, setUploading] = useState(false);

  // ---------- Generate params ----------
  const [force, setForce] = useState(false);

  // ---------- Progress ----------
  const [status, setStatus] = useState('idle'); // idle | starting | running | completed | failed
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const pollerRef = useRef(null);

  // ---------- Results ----------
  const [collectionsResults, setCollectionsResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [copied, setCopied] = useState(false);

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

      // Normalize file structure
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
  async function handleFileUpload(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    setUploading(true);
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    try {
      const accessToken = localStorage.getItem('access_token');
      const headers = {};
      if (accessToken) {
        headers['Authorization'] = accessToken.startsWith('Bearer ')
          ? accessToken
          : `Bearer ${accessToken}`;
      }

      const response = await fetch(`${API_BASE}/upload/upload`, {
        method: 'POST',
        headers,
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        const uploadedIds = data.file_ids || [];

        // Refresh the vault files list to show newly uploaded files
        await refreshVaultFiles();

        // Select the uploaded files and switch to vault view
        setSelectedFileIds(uploadedIds);
        setSource('vault');
      }
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  }

  // ---------- Start Collections ----------
  async function startCollections() {
    if (selectedFileIds.length === 0) {
      setError('Please select at least one file');
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

      const response = await fetch(`${API_BASE}/organize/collections/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          file_ids: selectedFileIds,
          user_id: userId,
          force
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to start collections');
      }

      const data = await response.json();
      const progressId = data.progress_id;

      setStatus('running');
      pollProgress(progressId, headers);

    } catch (err) {
      console.error('Error starting collections:', err);
      setError(err.message || 'Failed to start collections');
      setStatus('failed');
    }
  }

  function pollProgress(progressId, headers) {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
    }

    pollerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/organize/collections/progress/${progressId}`, { headers });
        const p = await res.json();

        setProgress(Number(p.percentage || 0));

        if (p.status === 'completed') {
          clearInterval(pollerRef.current);
          setStatus('completed');
          await fetchResults();
          setTab('results');
        } else if (p.status === 'failed') {
          clearInterval(pollerRef.current);
          setStatus('failed');
          setError('Collections creation failed');
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
    try {
      const accessToken = localStorage.getItem('access_token');
      const token = accessToken || (typeof window !== 'undefined' && localStorage.getItem('token')) || '';

      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
      }

      const fileIdsParam = selectedFileIds.join(',');
      const res = await fetch(`${API_BASE}/organize/collections/results?file_ids=${fileIdsParam}`, { headers });

      if (!res.ok) {
        console.error('Failed to fetch collections results');
        return;
      }

      const data = await res.json();
      setCollectionsResults(data);
    } catch (err) {
      console.error('Error fetching collections results:', err);
    }
  }

  async function refreshResults() {
    await fetchResults();
  }

  // ---------- Export & Copy ----------
  function downloadJSON() {
    if (!collectionsResults) return;
    const blob = new Blob([JSON.stringify(collectionsResults, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'collections_results.json';
    a.click();
  }

  function copyToClipboard() {
    if (!collectionsResults) return;
    navigator.clipboard.writeText(JSON.stringify(collectionsResults, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // ---------- Filter Collections ----------
  const getFilteredCollections = useMemo(() => {
    if (!collectionsResults || !collectionsResults.results) return [];

    // Flatten all collections from all results
    const allCollections = collectionsResults.results.flatMap(result => result.collections || []);

    if (!searchQuery.trim()) {
      console.log('No search query, returning all collections:', allCollections.length);
      return allCollections;
    }

    const q = searchQuery.toLowerCase();
    const filtered = allCollections.filter(collection => {
      const nameMatch = collection.name?.toLowerCase().includes(q);
      const descMatch = collection.description?.toLowerCase().includes(q);
      const tagsMatch = collection.features?.suggested_tags?.some(tag => tag.toLowerCase().includes(q));
      return nameMatch || descMatch || tagsMatch;
    });

    console.log('Filtered collections:', filtered.length, 'out of', allCollections.length, 'for query:', q);
    return filtered;
  }, [collectionsResults, searchQuery]);

  // ---------- Collection Color ----------
  const getCollectionColor = (idx) => {
    const colors = ['#ec4899', '#f43f5e', '#8b5cf6', '#d946ef', '#f97316', '#14b8a6', '#06b6d4'];
    return colors[idx % colors.length];
  };

  return (
    <div className="collections-wrap">
      <header className="collections-header">
        <Link to="/organize" className="back-link">← Back to Organize</Link>
        <h1 className="collections-title">
          <FaFolderOpen /> Collections
        </h1>
        <p className="collections-subtitle">
          Organize your documents into smart, thematic collections
        </p>
      </header>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={tab === 'generate' ? 'tab active' : 'tab'}
          onClick={() => setTab('generate')}
        >
          Generate
        </button>
        <button
          className={tab === 'results' ? 'tab active' : 'tab'}
          onClick={() => setTab('results')}
        >
          Results
        </button>
      </div>

      {/* Generate Tab */}
      {tab === 'generate' && (
        <div className="generate-section">
          {/* Source Selection */}
          <div className="source-selection">
            <h3 className="section-title">Select Files</h3>
            <div className="source-buttons">
              <button
                className={source === 'vault' ? 'source-btn active' : 'source-btn'}
                onClick={() => setSource('vault')}
              >
                <FaFolderOpen /> Knowledge Vault
              </button>
              <button
                className={source === 'upload' ? 'source-btn active' : 'source-btn'}
                onClick={() => setSource('upload')}
              >
                <FaCloudUploadAlt /> Upload Files
              </button>
            </div>
          </div>

          {/* Knowledge Vault */}
          {source === 'vault' && (
            <div className="vault-section">
              <div className="vault-header">
                <h4>Knowledge Vault Files</h4>
                <div className="vault-actions">
                  <button onClick={selectAllFiles} className="btn-ghost-small">Select All</button>
                  <button onClick={clearSelection} className="btn-ghost-small">Clear</button>
                </div>
              </div>
              <div className="file-list">
                {vaultFiles.length === 0 ? (
                  <p className="no-files">No files in vault. Upload files to get started.</p>
                ) : (
                  vaultFiles.map(file => (
                    <div
                      key={file.id}
                      className={selectedFileIds.includes(file.id) ? 'file-item selected' : 'file-item'}
                      onClick={(e) => {
                        if (e.target.type !== 'checkbox') {
                          toggleFileSelection(file.id);
                        }
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedFileIds.includes(file.id)}
                        onChange={() => toggleFileSelection(file.id)}
                      />
                      <FaFileAlt className="file-icon" />
                      <span className="file-name">{file.name}</span>
                    </div>
                  ))
                )}
              </div>
              {selectedFileIds.length > 0 && (
                <p className="selection-count">{selectedFileIds.length} file(s) selected</p>
              )}
            </div>
          )}

          {/* Upload Section */}
          {source === 'upload' && (
            <div className="upload-section">
              <label className="upload-box">
                <input
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
                <FaCloudUploadAlt className="upload-icon" />
                <p className="upload-text">
                  {uploading ? 'Uploading...' : 'Click or drag files here to upload'}
                </p>
              </label>
            </div>
          )}

          {/* Options */}
          <div className="options-section">
            <h3 className="section-title">Options</h3>
            <div className="param-row">
              <label className="param-checkbox-label">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={(e) => setForce(e.target.checked)}
                  className="param-checkbox"
                />
                Force re-processing (ignore cached results)
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              onClick={startCollections}
              disabled={status === 'running' || status === 'starting' || selectedFileIds.length === 0}
              className="btn-primary"
            >
              {status === 'running' || status === 'starting' ? (
                <>
                  <FaClock /> Processing...
                </>
              ) : (
                <>
                  <FaRocket /> Create Collections
                </>
              )}
            </button>
          </div>

          {/* Progress */}
          {(status === 'running' || status === 'starting') && (
            <div className="progress-section">
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <p className="progress-text">{progress}% complete</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Results Tab */}
      {tab === 'results' && (
        <div className="results-section">
          <div className="results-header">
            <div className="results-actions">
              <button onClick={refreshResults} className="btn-ghost">
                <FaSyncAlt /> Refresh
              </button>
              <button onClick={downloadJSON} className="btn-ghost">
                <FaDownload /> Download JSON
              </button>
              <button onClick={copyToClipboard} className="btn-ghost">
                {copied ? <><FaCheck /> Copied!</> : <><FaCopy /> Copy</>}
              </button>
            </div>

            <div className="search-container">
              <FaSearch className="search-icon" />
              <input
                type="text"
                name="searchCollections"
                id="searchCollections"
                placeholder="Search collections..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
                autoComplete="off"
              />
            </div>
          </div>

          {collectionsResults && collectionsResults.results && collectionsResults.results.length > 0 ? (
            <>
              {/* Statistics Overview */}
              <div className="stats-overview">
                <div className="stat-card">
                  <div className="stat-value">{getFilteredCollections.length}</div>
                  <div className="stat-label">Total Collections</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{collectionsResults.file_count || 0}</div>
                  <div className="stat-label">Documents</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {collectionsResults.results[0]?.metadata?.organization_efficiency
                      ? (collectionsResults.results[0].metadata.organization_efficiency * 100).toFixed(0)
                      : 0}%
                  </div>
                  <div className="stat-label">Organization Efficiency</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value top-collection">
                    {collectionsResults.results[0]?.metadata?.most_populated_collection || 'N/A'}
                  </div>
                  <div className="stat-label">Top Collection</div>
                </div>
              </div>

              {/* Collections Grid */}
              <div className="collections-grid" key={`grid-${searchQuery}-${getFilteredCollections.length}`}>
                {getFilteredCollections.map((collection, idx) => (
                  <div
                    key={collection.id || idx}
                    className={`collection-card ${selectedCollection === idx ? 'expanded' : ''}`}
                    style={{ borderLeftColor: getCollectionColor(idx) }}
                  >
                    <div className="collection-header">
                      <div className="collection-icon" style={{ backgroundColor: getCollectionColor(idx) }}>
                        <FaFolderOpen />
                      </div>
                      <div className="collection-info">
                        <h3 className="collection-name">{collection.name || `Collection ${idx + 1}`}</h3>
                        <div className="collection-badges">
                          <span className="collection-size-badge">
                            {collection.total_files || 0} docs
                          </span>
                          {(collection.total_sections || 0) > 0 && (
                            <span className="collection-size-badge sections-badge">
                              {collection.total_sections} sections
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        className="collection-menu-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCollection(selectedCollection === idx ? null : idx);
                        }}
                      >
                        <FaEllipsisV />
                      </button>
                    </div>

                    <p className="collection-description">
                      {collection.description || 'No description available'}
                    </p>

                    {collection.features?.suggested_tags && collection.features.suggested_tags.length > 0 && (
                      <div className="collection-tags">
                        <FaTags className="tags-icon" />
                        {collection.features.suggested_tags.slice(0, 5).map((tag, tagIdx) => (
                          <span key={tagIdx} className="tag">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="collection-stats">
                      <div className="stat">
                        <span className="stat-label">Relevance:</span>
                        <span className="stat-value">
                          {(collection.statistics?.avg_relevance_score * 100 || 0).toFixed(0)}%
                        </span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Diversity:</span>
                        <span className="stat-value">
                          {(collection.statistics?.content_diversity * 100 || 0).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    {selectedCollection === idx && (collection.files || collection.sections) && (
                      <div className="collection-files-expanded">
                        {/* Documents Section */}
                        {collection.files && collection.files.length > 0 && (
                          <>
                            <h4><FaFileAlt /> Documents ({collection.files.length})</h4>
                            <ul className="file-details-list">
                              {collection.files.map((file, fileIdx) => (
                                <li key={fileIdx} className="file-detail-item">
                                  <FaFileAlt className="file-detail-icon" />
                                  <div className="file-detail-content">
                                    <div className="file-detail-name">
                                      {file.file_name}
                                      {file.has_sections && (
                                        <span className="has-sections-badge">
                                          <FaLayerGroup /> {file.section_count} sections
                                        </span>
                                      )}
                                    </div>
                                    {file.summary && (
                                      <div className="file-detail-summary">{file.summary}</div>
                                    )}
                                    <div className="file-detail-relevance">
                                      Relevance: {(file.relevance_score * 100 || 0).toFixed(0)}%
                                    </div>
                                  </div>
                                </li>
                              ))}
                            </ul>
                          </>
                        )}

                        {/* Sections Section */}
                        {collection.sections && collection.sections.length > 0 && (
                          <>
                            <h4><FaBookOpen /> Sections ({collection.sections.length})</h4>
                            <ul className="file-details-list sections-list">
                              {collection.sections.map((section, sectionIdx) => (
                                <li key={sectionIdx} className="file-detail-item section-item">
                                  <FaBookOpen className="file-detail-icon section-icon" />
                                  <div className="file-detail-content">
                                    <div className="file-detail-name section-title">
                                      {section.section_title}
                                      <span className="page-range-badge">
                                        {section.page_start === section.page_end
                                          ? `Page ${section.page_start}`
                                          : `Pages ${section.page_range}`
                                        }
                                      </span>
                                    </div>
                                    <div className="section-source">
                                      From: {section.file_name}
                                    </div>
                                    {section.section_summary && (
                                      <div className="file-detail-summary">{section.section_summary}</div>
                                    )}
                                    {section.tags && section.tags.length > 0 && (
                                      <div className="section-tags">
                                        {section.tags.slice(0, 3).map((tag, tagIdx) => (
                                          <span key={tagIdx} className="section-tag">{tag}</span>
                                        ))}
                                      </div>
                                    )}
                                    <div className="file-detail-relevance">
                                      Relevance: {(section.relevance_score * 100 || 0).toFixed(0)}%
                                    </div>
                                  </div>
                                </li>
                              ))}
                            </ul>
                          </>
                        )}

                        {/* Quick Actions */}
                        {collection.features?.quick_actions && (
                          <div className="quick-actions">
                            {collection.features.quick_actions.slice(0, 3).map((action, actionIdx) => (
                              <button key={actionIdx} className="quick-action-btn" title={action.label}>
                                {action.icon === 'plus' && <FaPlus />}
                                {action.icon === 'download' && <FaDownload />}
                                {action.icon === 'share' && <FaShare />}
                                {action.icon === 'merge' && <FaCodeBranch />}
                                {action.icon === 'copy' && <FaClone />}
                                <span>{action.label}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="no-results">
              <FaFolderOpen size={64} />
              <p>No collections yet. Generate collections from your documents to see results here.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
