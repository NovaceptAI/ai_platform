import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaLayerGroup,
  FaRocket,
  FaSyncAlt,
  FaDownload,
  FaCopy,
  FaSearch,
  FaFilter,
  FaCheck,
  FaClock,
  FaCloudUploadAlt,
  FaFileAlt,
  FaProjectDiagram
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './Clusters.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

const API_BASE = (config && config.API_BASE_URL) || process.env.REACT_APP_API_BASE_URL || '';

export default function Clusters() {
  const [tab, setTab] = useState('generate'); // generate | results

  // ---------- Knowledge Vault ----------
  const [source, setSource] = useState('vault'); // 'vault' | 'upload'
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]); // multiple files for clustering
  const [uploading, setUploading] = useState(false);

  // ---------- Generate params ----------
  const [maxClusters, setMaxClusters] = useState(5);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.3);
  const [clusteringMethod, setClusteringMethod] = useState('semantic'); // semantic | hierarchical | threshold
  const [force, setForce] = useState(false);

  // ---------- Progress ----------
  const [status, setStatus] = useState('idle'); // idle | starting | running | completed | failed
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const pollerRef = useRef(null);

  // ---------- Results ----------
  const [clusterResults, setClusterResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [copied, setCopied] = useState(false);

  // ---------- Auth headers ----------
  const accessToken = (typeof window !== 'undefined' && localStorage.getItem('access_token')) || '';
  const userId = (typeof window !== 'undefined' && (localStorage.getItem('user_id') || 'admin')) || 'admin';
  const headers = useMemo(() => {
    const h = { 'Content-Type': 'application/json', 'X-User-Id': userId || '' };

    // Add Authorization header - check both access_token and token
    const token = accessToken || (typeof window !== 'undefined' && localStorage.getItem('token')) || '';
    if (token) {
      h['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
    }

    console.log('Headers constructed:', { ...h, Authorization: h.Authorization ? '***' : 'missing' });
    return h;
  }, [accessToken, userId]);

  // ---------- Load vault files ----------
  useEffect(() => {
    (async () => {
      try {
        const res = await axiosInstance.get('/upload/files');
        const files = res.data.files || [];
        // Normalize the file structure - API returns fileId, we need id
        const normalizedFiles = files.map(file => ({
          id: file.fileId || file.id,
          name: file.name,
          stored_name: file.stored_name
        }));
        console.log('Loaded vault files:', normalizedFiles);
        setVaultFiles(normalizedFiles);
      } catch (err) {
        console.error('Error loading vault files:', err);
      }
    })();
    return () => { if (pollerRef.current) clearInterval(pollerRef.current); };
  }, []);

  // ---------- Refresh vault files ----------
  async function refreshVaultFiles() {
    try {
      const res = await axiosInstance.get('/upload/files');
      const files = res.data.files || [];
      const normalizedFiles = files.map(file => ({
        id: file.fileId || file.id,
        name: file.name,
        stored_name: file.stored_name
      }));
      console.log('Refreshed vault files:', normalizedFiles);
      setVaultFiles(normalizedFiles);
      return normalizedFiles;
    } catch (err) {
      console.error('Error refreshing vault files:', err);
      return [];
    }
  }

  // ---------- Upload to Vault ----------
  async function handleUpload(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setError('');
    setUploading(true);

    try {
      const uploadedIds = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fd = new FormData();
        fd.append('file', file);

        const res = await axiosInstance.post('/upload/upload', fd, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        const saved = res.data?.file || res.data;
        if (!saved) throw new Error('Upload failed');

        const fileId = saved.fileId || saved.id;
        console.log('Uploaded file with ID:', fileId);
        uploadedIds.push(fileId);
      }

      // Refresh the vault files list to show newly uploaded files
      await refreshVaultFiles();

      // Select the uploaded files and switch to vault view
      setSelectedFileIds(uploadedIds);
      setSource('vault');
    } catch (err) {
      setError(err?.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  // ---------- Toggle file selection ----------
  function toggleFileSelection(fileId) {
    console.log('Toggle called for fileId:', fileId, 'Type:', typeof fileId);
    setSelectedFileIds(prev => {
      console.log('Current selectedFileIds:', prev);
      console.log('Includes check:', prev.includes(fileId));
      if (prev.includes(fileId)) {
        const newIds = prev.filter(id => id !== fileId);
        console.log('Removing, new array:', newIds);
        return newIds;
      } else {
        const newIds = [...prev, fileId];
        console.log('Adding, new array:', newIds);
        return newIds;
      }
    });
  }

  // ---------- Start clustering ----------
  async function startClustering() {
    setError('');

    if (selectedFileIds.length === 0) {
      setError('Please select at least one file.');
      return;
    }

    try {
      setStatus('starting');
      setProgress(0);

      console.log('Starting clustering with:', {
        file_ids: selectedFileIds,
        user_id: userId,
        force,
        headers: { ...headers, Authorization: headers.Authorization ? '***' : 'missing' }
      });

      const res = await fetch(`${API_BASE}/organize/clusters/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          file_ids: selectedFileIds,
          user_id: userId,
          force
        })
      });

      console.log('Response status:', res.status);

      if (!res.ok) {
        const errorText = await res.text();
        console.error('Error response:', errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: errorText || `Server returned ${res.status}` };
        }
        throw new Error(errorData.error || errorData.msg || `Failed to start: ${res.status}`);
      }

      const data = await res.json();
      console.log('Clustering started:', data);
      const progressId = data.progress_id;
      setStatus('running');
      setProgress(0);
      pollProgress(progressId);
    } catch (err) {
      console.error('Clustering start error:', err);
      setStatus('failed');
      setError(err.message || 'Failed to start clustering.');
    }
  }

  // ---------- Poll progress ----------
  function pollProgress(progressId) {
    if (pollerRef.current) clearInterval(pollerRef.current);

    pollerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/organize/clusters/progress/${progressId}`, { headers });
        if (!res.ok) {
          const e = await res.json().catch(() => ({}));
          throw new Error(e.error || `Progress error: ${res.status}`);
        }
        const p = await res.json();

        const pct = Number(p.percentage || 0);
        setProgress(pct);

        if (p.status === 'completed') {
          clearInterval(pollerRef.current);
          pollerRef.current = null;
          setStatus('completed');
          setProgress(100);
          await fetchResults();
        } else if (p.status === 'failed') {
          clearInterval(pollerRef.current);
          pollerRef.current = null;
          setStatus('failed');
          setError(p.error_message || 'Clustering failed.');
        }
      } catch (err) {
        clearInterval(pollerRef.current);
        pollerRef.current = null;
        setStatus('failed');
        setError(err.message || 'Progress polling failed.');
      }
    }, 1200);
  }

  // ---------- Fetch results ----------
  async function fetchResults() {
    try {
      const fileIdsParam = selectedFileIds.join(',');
      const res = await fetch(`${API_BASE}/organize/clusters/results?file_ids=${fileIdsParam}`, { headers });

      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.error || `Failed to fetch results: ${res.status}`);
      }

      const data = await res.json();

      // Parse the result_data if it exists in Progress table
      if (data.results && data.results.length > 0) {
        // Results from DocumentClustersResult table
        setClusterResults(data.results[0]);
      } else {
        // Try to get from progress endpoint with result_data
        setError('No clustering results found. Please run clustering first.');
      }

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
    if (!clusterResults) return;
    const blob = new Blob([JSON.stringify(clusterResults, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `clusters_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------- Copy to clipboard ----------
  function copyToClipboard() {
    if (!clusterResults) return;
    navigator.clipboard.writeText(JSON.stringify(clusterResults, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // ---------- Filter clusters ----------
  function getFilteredClusters() {
    if (!clusterResults?.clusters) return [];

    if (!searchQuery.trim()) return clusterResults.clusters;

    const q = searchQuery.toLowerCase();
    return clusterResults.clusters.filter(cluster =>
      cluster.name?.toLowerCase().includes(q) ||
      cluster.description?.toLowerCase().includes(q) ||
      cluster.characteristics?.common_topics?.some(topic => topic.toLowerCase().includes(q))
    );
  }

  // ---------- Get cluster color ----------
  function getClusterColor(index) {
    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8'];
    return colors[index % colors.length];
  }

  // ---------- Render ----------
  return (
    <div className="clusters-wrap">
      <header className="clusters-header">
        <Link to="/organize" className="back-link">← Back to Organize</Link>
        <h1 className="clusters-title">
          <FaLayerGroup /> Document Clusters
        </h1>
        <p className="clusters-subtitle">
          Group related documents using AI-powered semantic clustering
        </p>
      </header>

      {/* Tab Navigation */}
      <div className="clusters-tabs">
        <button
          className={`tab-btn ${tab === 'generate' ? 'active' : ''}`}
          onClick={() => setTab('generate')}
        >
          <FaRocket /> Generate
        </button>
        <button
          className={`tab-btn ${tab === 'results' ? 'active' : ''}`}
          onClick={() => setTab('results')}
          disabled={!clusterResults}
        >
          <FaProjectDiagram /> Results
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Generate Tab */}
      {tab === 'generate' && (
        <div className="generate-section">
          {/* File Selection */}
          <div className="input-group">
            <label className="input-label">
              <FaFileAlt /> Select Documents to Cluster
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
                {vaultFiles.length === 0 ? (
                  <p className="no-files-msg">No files in vault. Upload some files first.</p>
                ) : (
                  <div className="file-list">
                    {vaultFiles.map((file) => {
                      console.log('Rendering file:', file.id, 'Name:', file.name, 'Selected:', selectedFileIds.includes(file.id));
                      return (
                        <div
                          key={file.id}
                          className={`file-item ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                          onClick={(e) => {
                            // Only toggle if clicking on the div itself, not the checkbox
                            if (e.target.type !== 'checkbox') {
                              console.log('Div clicked for file:', file.id);
                              toggleFileSelection(file.id);
                            }
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selectedFileIds.includes(file.id)}
                            onChange={(e) => {
                              console.log('Checkbox changed for file:', file.id);
                              toggleFileSelection(file.id);
                            }}
                            className="file-checkbox"
                          />
                          <FaFileAlt className="file-icon" />
                          <span className="file-name">{file.name || file.stored_name}</span>
                        </div>
                      );
                    })}
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

          {/* Clustering Parameters */}
          <div className="params-section">
            <h3 className="section-title">Clustering Parameters</h3>

            <div className="param-row">
              <label className="param-label">Clustering Method:</label>
              <select
                value={clusteringMethod}
                onChange={(e) => setClusteringMethod(e.target.value)}
                className="param-select"
              >
                <option value="semantic">Semantic (Content-based)</option>
                <option value="hierarchical">Hierarchical</option>
                <option value="threshold">Threshold-based</option>
              </select>
            </div>

            <div className="param-row">
              <label className="param-label">Max Clusters: {maxClusters}</label>
              <input
                type="range"
                min="2"
                max="10"
                value={maxClusters}
                onChange={(e) => setMaxClusters(Number(e.target.value))}
                className="param-slider"
              />
            </div>

            <div className="param-row">
              <label className="param-label">Similarity Threshold: {similarityThreshold.toFixed(2)}</label>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.1"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="param-slider"
              />
            </div>

            <div className="param-row">
              <label className="param-checkbox-label">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={(e) => setForce(e.target.checked)}
                  className="param-checkbox"
                />
                Force re-clustering (ignore cached results)
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              onClick={startClustering}
              disabled={status === 'running' || status === 'starting' || selectedFileIds.length === 0}
              className="btn-primary"
            >
              {status === 'running' || status === 'starting' ? (
                <>
                  <FaClock /> Processing...
                </>
              ) : (
                <>
                  <FaRocket /> Start Clustering
                </>
              )}
            </button>
          </div>

          {/* Progress Bar */}
          {(status === 'running' || status === 'starting') && (
            <div className="progress-container">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="progress-text">{progress}% complete</p>
            </div>
          )}

          {/* Success Message */}
          {status === 'completed' && (
            <div className="success-box">
              <FaCheck /> Clustering completed successfully! Switch to the Results tab to view clusters.
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
                placeholder="Search clusters..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>
          </div>

          {clusterResults && (
            <>
              {/* Statistics Overview */}
              <div className="stats-overview">
                <div className="stat-card">
                  <div className="stat-value">{clusterResults.clusters?.length || 0}</div>
                  <div className="stat-label">Total Clusters</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{clusterResults.statistics?.total_documents || 0}</div>
                  <div className="stat-label">Documents</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {(clusterResults.insights?.quality_assessment?.overall_quality * 100 || 0).toFixed(0)}%
                  </div>
                  <div className="stat-label">Quality Score</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {clusterResults.statistics?.cluster_size_distribution?.mean?.toFixed(1) || 0}
                  </div>
                  <div className="stat-label">Avg Cluster Size</div>
                </div>
              </div>

              {/* Insights */}
              {clusterResults.insights && (
                <div className="insights-section">
                  <h3 className="section-title">Insights</h3>

                  {clusterResults.insights.dominant_themes && clusterResults.insights.dominant_themes.length > 0 && (
                    <div className="dominant-themes">
                      <h4>Dominant Themes:</h4>
                      <div className="theme-tags">
                        {clusterResults.insights.dominant_themes.map((theme, idx) => (
                          <span key={idx} className="theme-tag">
                            {theme.theme} ({(theme.prevalence * 100).toFixed(0)}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Dominant Entities from all clusters */}
                  {clusterResults.clusters && clusterResults.clusters.length > 0 && (() => {
                    // Aggregate entities from all clusters
                    const allEntities = {};
                    clusterResults.clusters.forEach(cluster => {
                      if (cluster.characteristics?.dominant_entities) {
                        Object.entries(cluster.characteristics.dominant_entities).forEach(([entityType, entities]) => {
                          if (!allEntities[entityType]) {
                            allEntities[entityType] = new Set();
                          }
                          entities.forEach(entity => allEntities[entityType].add(entity));
                        });
                      }
                    });

                    // Convert to array and display if we have entities
                    const hasEntities = Object.keys(allEntities).length > 0;
                    if (!hasEntities) return null;

                    return (
                      <div className="dominant-entities">
                        <h4>Key Entities:</h4>
                        <div className="entities-by-type">
                          {Object.entries(allEntities).map(([entityType, entitySet]) => {
                            const entityArray = Array.from(entitySet).slice(0, 5); // Show top 5 per type
                            if (entityArray.length === 0) return null;

                            return (
                              <div key={entityType} className="entity-type-group">
                                <span className="entity-type-label">{entityType}:</span>
                                <div className="entity-tags">
                                  {entityArray.map((entity, idx) => (
                                    <span key={idx} className="entity-tag">
                                      {entity}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()}

                  {clusterResults.insights.recommendations && clusterResults.insights.recommendations.length > 0 && (
                    <div className="recommendations">
                      <h4>Recommendations:</h4>
                      <ul>
                        {clusterResults.insights.recommendations.map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Cluster Cards */}
              <div className="clusters-grid">
                {getFilteredClusters().map((cluster, idx) => (
                  <div
                    key={cluster.cluster_id || idx}
                    className={`cluster-card ${selectedCluster === idx ? 'expanded' : ''}`}
                    style={{ borderLeftColor: getClusterColor(idx) }}
                    onClick={() => setSelectedCluster(selectedCluster === idx ? null : idx)}
                  >
                    <div className="cluster-header">
                      <h3 className="cluster-name">{cluster.name || `Cluster ${idx + 1}`}</h3>
                      <span className="cluster-size-badge">
                        {cluster.file_details?.length || 0} docs
                      </span>
                    </div>

                    <p className="cluster-description">
                      {cluster.description || 'No description available'}
                    </p>

                    {cluster.characteristics?.common_topics && cluster.characteristics.common_topics.length > 0 && (
                      <div className="cluster-topics">
                        {cluster.characteristics.common_topics.map((topic, topicIdx) => (
                          <span key={topicIdx} className="topic-tag">
                            {topic}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="cluster-metrics">
                      <div className="metric">
                        <span className="metric-label">Quality:</span>
                        <span className="metric-value">
                          {(cluster.quality_score * 100 || 0).toFixed(0)}%
                        </span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Cohesion:</span>
                        <span className="metric-value">
                          {(cluster.metrics?.cohesion * 100 || 0).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    {selectedCluster === idx && cluster.file_details && (
                      <div className="cluster-files-expanded">
                        <h4>Documents in this cluster:</h4>
                        <ul className="file-details-list">
                          {cluster.file_details.map((file, fileIdx) => (
                            <li key={fileIdx} className="file-detail-item">
                              <FaFileAlt className="file-detail-icon" />
                              <div className="file-detail-content">
                                <div className="file-detail-name">{file.file_name}</div>
                                {file.summary && (
                                  <div className="file-detail-summary">{file.summary}</div>
                                )}
                                <div className="file-detail-similarity">
                                  Similarity to center: {(file.similarity_to_centroid * 100 || 0).toFixed(0)}%
                                </div>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {getFilteredClusters().length === 0 && (
                <div className="no-results">
                  <FaSearch size={48} />
                  <p>No clusters match your search.</p>
                </div>
              )}
            </>
          )}

          {!clusterResults && (
            <div className="no-results">
              <FaLayerGroup size={48} />
              <p>No clustering results available. Generate clusters first.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
