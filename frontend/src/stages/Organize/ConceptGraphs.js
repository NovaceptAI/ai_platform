import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  FaProjectDiagram,
  FaRocket,
  FaSyncAlt,
  FaDownload,
  FaCopy,
  FaSearch,
  FaCheck,
  FaClock,
  FaCloudUploadAlt,
  FaFileAlt,
  FaCircle,
  FaExpand,
  FaCompress,
  FaCog,
  FaNetworkWired
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './ConceptGraphs.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';
import ForceGraph from './ForceGraph';

const API_BASE = (config && config.API_BASE_URL) || process.env.REACT_APP_API_BASE_URL || '';

export default function ConceptGraphs() {
  const [tab, setTab] = useState('generate'); // generate | results

  // ---------- Knowledge Vault ----------
  const [source, setSource] = useState('vault'); // 'vault' | 'upload'
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [fileValidation, setFileValidation] = useState(null); // Validation status for selected files

  // ---------- Generate params ----------
  const [maxNodes, setMaxNodes] = useState(100);
  const [minEdgeWeight, setMinEdgeWeight] = useState(0.1);
  const [graphLayout, setGraphLayout] = useState('force_directed'); // force_directed | hierarchical | circular | grid
  const [includeEntities, setIncludeEntities] = useState(true);
  const [includeTopics, setIncludeTopics] = useState(true);
  const [includeConcepts, setIncludeConcepts] = useState(true);
  const [force, setForce] = useState(false);

  // ---------- Progress ----------
  const [status, setStatus] = useState('idle'); // idle | starting | running | completed | failed
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const pollerRef = useRef(null);

  // ---------- Results ----------
  const [graphResults, setGraphResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [copied, setCopied] = useState(false);
  const [filterByType, setFilterByType] = useState('all'); // all | entity | topic | concept
  const [isFullscreen, setIsFullscreen] = useState(false);

  // ---------- Auth headers ----------
  const accessToken = (typeof window !== 'undefined' && localStorage.getItem('access_token')) || '';
  const userId = (typeof window !== 'undefined' && (localStorage.getItem('user_id') || 'admin')) || 'admin';
  const headers = useMemo(() => {
    const h = { 'Content-Type': 'application/json', 'X-User-Id': userId || '' };

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

  // ---------- Validate selected files ----------
  useEffect(() => {
    if (selectedFileIds.length > 0) {
      validateFiles().then(validation => {
        if (validation) {
          setFileValidation(validation);
        }
      });
    } else {
      setFileValidation(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFileIds]);

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

      await refreshVaultFiles();
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

  // ---------- Validate files before generation ----------
  async function validateFiles() {
    try {
      const res = await fetch(`${API_BASE}/discover/explore_document/validate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          file_ids: selectedFileIds
        })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || 'Validation failed');
      }

      const data = await res.json();

      // Transform common validation response to concept graph format
      const filesWithoutData = data.files.filter(f =>
        !f.has_summary && !f.has_topics && !f.has_entities
      );

      return {
        validated: true,
        all_complete: data.all_complete, // Keep all_complete from backend
        can_proceed: data.all_complete ? true : (filesWithoutData.length < data.files.length),
        total_files: data.files.length,
        ready_files: data.files.filter(f => f.has_summary || f.has_topics || f.has_entities).length,
        missing_data_files: filesWithoutData.length,
        files: data.files.map(f => ({
          file_id: f.file_id,
          file_name: f.file_name,
          has_summary: f.has_summary,
          has_topics: f.has_topics,
          has_entities: f.has_entities,
          has_data: f.has_summary || f.has_topics || f.has_entities
        })),
        message: data.message
      };
    } catch (err) {
      console.error('File validation error:', err);
      return null;
    }
  }

  // ---------- Start concept graph generation ----------
  async function startConceptGraph() {
    setError('');

    if (selectedFileIds.length === 0) {
      setError('Please select at least one file.');
      return;
    }

    // Validate files first
    const validation = await validateFiles();
    if (validation) {
      if (!validation.can_proceed) {
        setError(
          `${validation.message}\n\n` +
          'Please run the files through the Document Summarization tool in the Discover stage first to extract summaries, topics, and entities.'
        );
        return;
      }

      // Show warning if some files are missing data
      if (validation.missing_data_files > 0) {
        const missingFiles = validation.files
          .filter(f => !f.has_data)
          .map(f => f.file_name)
          .join(', ');

        console.warn(`Warning: The following files are missing data: ${missingFiles}`);
        // Continue anyway since can_proceed is true
      }
    }

    try {
      setStatus('starting');
      setProgress(0);

      console.log('Starting concept graph with:', {
        file_ids: selectedFileIds,
        user_id: userId,
        force,
        headers: { ...headers, Authorization: headers.Authorization ? '***' : 'missing' }
      });

      const res = await fetch(`${API_BASE}/organize/concept_graph/start`, {
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
      console.log('Concept graph started:', data);
      const progressId = data.progress_id;

      // Check if we're using a cached result
      if (data.cached) {
        console.log('Using cached concept graph result from:', data.cached_at);
        setStatus('completed');
        setProgress(100);
        await fetchResults();
      } else {
        setStatus('running');
        setProgress(0);
        pollProgress(progressId);
      }
    } catch (err) {
      console.error('Concept graph start error:', err);
      setStatus('failed');
      setError(err.message || 'Failed to start concept graph generation.');
    }
  }

  // ---------- Poll progress ----------
  function pollProgress(progressId) {
    if (pollerRef.current) clearInterval(pollerRef.current);

    pollerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/organize/concept_graph/progress/${progressId}`, { headers });
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
          setError(p.error_message || 'Concept graph generation failed.');
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
      const res = await fetch(`${API_BASE}/organize/concept_graph/results?file_ids=${fileIdsParam}`, { headers });

      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.error || `Failed to fetch results: ${res.status}`);
      }

      const data = await res.json();

      if (data.results && data.results.length > 0) {
        setGraphResults(data.results[0]);
      } else {
        setError('No concept graph results found. Please run generation first.');
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
    if (!graphResults) return;
    const blob = new Blob([JSON.stringify(graphResults, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `concept_graph_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------- Copy to clipboard ----------
  function copyToClipboard() {
    if (!graphResults) return;
    navigator.clipboard.writeText(JSON.stringify(graphResults, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // ---------- Filter nodes ----------
  function getFilteredNodes() {
    if (!graphResults?.nodes) return [];

    let filtered = graphResults.nodes;

    // Filter by type
    if (filterByType !== 'all') {
      filtered = filtered.filter(node => node.type === filterByType);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(node =>
        node.label?.toLowerCase().includes(q) ||
        node.type?.toLowerCase().includes(q) ||
        node.entity_type?.toLowerCase().includes(q)
      );
    }

    return filtered;
  }

  // ---------- Get edges for filtered nodes ----------
  function getFilteredEdges() {
    if (!graphResults?.edges) return [];

    const filteredNodes = getFilteredNodes();
    const nodeIds = new Set(filteredNodes.map(n => n.id));

    // Only show edges where both source and target are in filtered nodes
    return graphResults.edges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );
  }

  // ---------- Get node color ----------
  function getNodeColor(node) {
    if (node.color) return node.color;
    
    const colorMap = {
      entity: '#FF6B6B',
      topic: '#FFEAA7',
      concept: '#98D8C8'
    };
    
    return colorMap[node.type] || '#CCCCCC';
  }

  // ---------- Get connected nodes ----------
  function getConnectedNodes(nodeId) {
    if (!graphResults?.edges) return [];
    
    const connected = new Set();
    graphResults.edges.forEach(edge => {
      if (edge.source === nodeId) connected.add(edge.target);
      if (edge.target === nodeId) connected.add(edge.source);
    });
    
    return Array.from(connected).map(id => 
      graphResults.nodes.find(n => n.id === id)
    ).filter(Boolean);
  }

  // ---------- Prepare graph data for visualization ----------
  const graphData = useMemo(() => {
    if (!graphResults?.nodes || !graphResults?.edges) return { nodes: [], edges: [] };

    const filteredNodes = getFilteredNodes();
    const filteredEdges = getFilteredEdges();

    // Transform nodes for D3
    const nodes = filteredNodes.map(node => ({
      id: node.id,
      name: node.label || node.name || 'Unknown',
      type: node.type,
      frequency: node.frequency || 1,
      entity_type: node.entity_type,
      ...node
    }));

    // Transform edges for D3
    const edges = filteredEdges.map(edge => ({
      source: edge.source,
      target: edge.target,
      weight: edge.weight || 1,
      relation_type: edge.relation_type,
      ...edge
    }));

    return { nodes, edges };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphResults, searchQuery, filterByType]);

  // ---------- Handle node click ----------
  const handleNodeClick = useCallback((node) => {
    // Scroll to the node card
    const nodeCard = document.getElementById(`node-${node.id}`);
    if (nodeCard) {
      nodeCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Highlight the card
      nodeCard.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.6)';
      setTimeout(() => {
        nodeCard.style.boxShadow = '';
      }, 2000);
    }
  }, []);

  // ---------- Toggle fullscreen ----------
  function toggleFullscreen() {
    setIsFullscreen(!isFullscreen);
  }

  // ---------- Render ----------
  return (
    <div className={`concept-graphs-wrap ${isFullscreen ? 'fullscreen' : ''}`}>
      <header className="concept-graphs-header">
        <Link to="/organize" className="back-link">← Back to Organize</Link>
        <h1 className="concept-graphs-title">
          <FaProjectDiagram /> Concept Graphs
        </h1>
        <p className="concept-graphs-subtitle">
          Visualize knowledge graphs and concept relationships from your documents
        </p>
      </header>

      {/* Tab Navigation */}
      <div className="concept-graphs-tabs">
        <button
          className={`tab-btn ${tab === 'generate' ? 'active' : ''}`}
          onClick={() => setTab('generate')}
        >
          <FaRocket /> Generate
        </button>
        <button
          className={`tab-btn ${tab === 'results' ? 'active' : ''}`}
          onClick={() => setTab('results')}
          disabled={!graphResults}
        >
          <FaNetworkWired /> Results
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
              <FaFileAlt /> Select Documents for Knowledge Graph
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

          {/* File Validation Warning */}
          {fileValidation && selectedFileIds.length > 0 && (
            <div className={`validation-info ${!fileValidation.can_proceed ? 'validation-error' : fileValidation.missing_data_files > 0 ? 'validation-warning' : 'validation-success'}`}>
              {!fileValidation.can_proceed ? (
                <>
                  <strong>⚠️ Cannot Generate Concept Graph</strong>
                  <p>{fileValidation.message}</p>
                  <p className="help-text">
                    Please process these files first to extract summaries, topics, and entities.
                  </p>
                  <Link to="/summarizer" className="validation-link">
                    Go to Document Summarization Tool →
                  </Link>
                </>
              ) : fileValidation.missing_data_files > 0 ? (
                <>
                  <strong>⚠️ Warning: Some Files Missing Data</strong>
                  <p>{fileValidation.ready_files} of {fileValidation.total_files} files are ready.</p>
                  <p className="help-text">
                    Files without data will have limited contribution to the concept graph.
                    For best results, process all files first.
                  </p>
                  <Link to="/summarizer" className="validation-link">
                    Go to Document Summarization Tool →
                  </Link>
                  <details style={{ marginTop: '0.75rem' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: '500' }}>Show file details</summary>
                    <ul style={{ marginTop: '0.5rem', marginLeft: '1rem' }}>
                      {fileValidation.files.map((file, idx) => (
                        <li key={idx} style={{ marginBottom: '0.25rem' }}>
                          {file.has_data ? '✓' : '✗'} {file.file_name}
                          {!file.has_data && (
                            <span style={{ fontSize: '0.85em', color: '#888', marginLeft: '0.5rem' }}>
                              (missing: {!file.has_summary && 'summary'}{!file.has_topics && (file.has_summary ? '' : ', ') + 'topics'}{!file.has_entities && (file.has_summary || file.has_topics ? ', ' : '') + 'entities'})
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </details>
                </>
              ) : (
                <>
                  <strong>✓ All Files Ready</strong>
                  <p>All {fileValidation.total_files} selected file(s) have the required data for concept graph generation.</p>
                </>
              )}
            </div>
          )}

          {/* Graph Configuration */}
          <div className="params-section">
            <h3 className="section-title"><FaCog /> Graph Configuration</h3>

            <div className="param-row">
              <label className="param-label">Graph Layout:</label>
              <select
                value={graphLayout}
                onChange={(e) => setGraphLayout(e.target.value)}
                className="param-select"
              >
                <option value="force_directed">Force-Directed (Network)</option>
                <option value="hierarchical">Hierarchical (Tree)</option>
                <option value="circular">Circular</option>
                <option value="grid">Grid</option>
              </select>
            </div>

            <div className="param-row">
              <label className="param-label">Max Nodes: {maxNodes}</label>
              <input
                type="range"
                min="20"
                max="200"
                step="10"
                value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
                className="param-slider"
              />
            </div>

            <div className="param-row">
              <label className="param-label">Min Edge Weight: {minEdgeWeight.toFixed(2)}</label>
              <input
                type="range"
                min="0.05"
                max="0.5"
                step="0.05"
                value={minEdgeWeight}
                onChange={(e) => setMinEdgeWeight(Number(e.target.value))}
                className="param-slider"
              />
            </div>

            <div className="param-row">
              <label className="param-checkbox-label">
                <input
                  type="checkbox"
                  checked={includeEntities}
                  onChange={(e) => setIncludeEntities(e.target.checked)}
                  className="param-checkbox"
                />
                Include Entities (People, Organizations, Locations)
              </label>
            </div>

            <div className="param-row">
              <label className="param-checkbox-label">
                <input
                  type="checkbox"
                  checked={includeTopics}
                  onChange={(e) => setIncludeTopics(e.target.checked)}
                  className="param-checkbox"
                />
                Include Topics
              </label>
            </div>

            <div className="param-row">
              <label className="param-checkbox-label">
                <input
                  type="checkbox"
                  checked={includeConcepts}
                  onChange={(e) => setIncludeConcepts(e.target.checked)}
                  className="param-checkbox"
                />
                Include Concepts
              </label>
            </div>

            <div className="param-row">
              <label className="param-checkbox-label">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={(e) => setForce(e.target.checked)}
                  className="param-checkbox"
                />
                Force re-generation (ignore cached results)
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              onClick={startConceptGraph}
              disabled={
                status === 'running' || 
                status === 'starting' || 
                selectedFileIds.length === 0 || 
                (fileValidation && !fileValidation.all_complete)
              }
              className="btn-primary"
            >
              {status === 'running' || status === 'starting' ? (
                <>
                  <FaClock /> Generating...
                </>
              ) : (
                <>
                  <FaRocket /> Generate Concept Graph
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
              <FaCheck /> Concept graph generated successfully! Switch to the Results tab to explore.
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
              <button onClick={toggleFullscreen} className="btn-ghost">
                {isFullscreen ? <><FaCompress /> Exit Fullscreen</> : <><FaExpand /> Fullscreen</>}
              </button>
            </div>

            <div className="cg-search-filter-container">
              <div className="cg-search-container">
                <FaSearch className="cg-search-icon" />
                <input
                  type="text"
                  placeholder="Search nodes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="cg-search-input"
                />
              </div>

              <div className="cg-filter-container">
                <select
                  value={filterByType}
                  onChange={(e) => setFilterByType(e.target.value)}
                  className="cg-filter-select"
                >
                  <option value="all">All Types</option>
                  <option value="entity">Entities</option>
                  <option value="topic">Topics</option>
                  <option value="concept">Concepts</option>
                </select>
              </div>
            </div>
          </div>

          {graphResults && (
            <>
              {/* Statistics Overview */}
              <div className="stats-overview">
                <div className="stat-card">
                  <div className="stat-value">{graphResults.nodes?.length || 0}</div>
                  <div className="stat-label">Total Nodes</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{graphResults.edges?.length || 0}</div>
                  <div className="stat-label">Relationships</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {graphResults.graph_metadata?.density
                      ? (graphResults.graph_metadata.density * 100).toFixed(0)
                      : 0}%
                  </div>
                  <div className="stat-label">Graph Density</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {graphResults.analysis?.basic_metrics?.average_degree?.toFixed(1) || 0}
                  </div>
                  <div className="stat-label">Avg Connections</div>
                </div>
              </div>

              {/* Insights */}
              {graphResults.insights && (
                <div className="insights-section">
                  <h3 className="section-title">Graph Insights</h3>

                  {graphResults.insights.key_concepts && graphResults.insights.key_concepts.length > 0 && (
                    <div className="key-concepts">
                      <h4>Key Concepts (High Centrality):</h4>
                      <div className="concept-tags">
                        {graphResults.insights.key_concepts.map((concept, idx) => (
                          <span key={idx} className="concept-tag">
                            {concept.label} ({(concept.centrality * 100).toFixed(0)}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {graphResults.insights.dominant_themes && graphResults.insights.dominant_themes.length > 0 && (
                    <div className="dominant-themes">
                      <h4>Dominant Themes:</h4>
                      <div className="theme-tags">
                        {graphResults.insights.dominant_themes.map((theme, idx) => (
                          <span key={idx} className="theme-tag">
                            {theme.theme} (Strength: {theme.strength})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {graphResults.insights.graph_quality && (
                    <div className="graph-quality">
                      <h4>Graph Quality:</h4>
                      <ul>
                        <li>
                          <strong>Connectivity:</strong>{' '}
                          {graphResults.insights.graph_quality.connectivity ? 'Connected' : 'Disconnected'}
                        </li>
                        <li>
                          <strong>Density:</strong>{' '}
                          {graphResults.insights.graph_quality.density_assessment || 'N/A'}
                        </li>
                        <li>
                          <strong>Clusters:</strong>{' '}
                          {graphResults.insights.graph_quality.cluster_count || 0}
                        </li>
                      </ul>
                    </div>
                  )}

                  {graphResults.insights.recommendations && graphResults.insights.recommendations.length > 0 && (
                    <div className="recommendations">
                      <h4>Recommendations:</h4>
                      <ul>
                        {graphResults.insights.recommendations.map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {graphResults.insights.knowledge_gaps && graphResults.insights.knowledge_gaps.length > 0 && (
                    <div className="knowledge-gaps">
                      <h4>Knowledge Gaps:</h4>
                      <ul>
                        {graphResults.insights.knowledge_gaps.map((gap, idx) => (
                          <li key={idx}>
                            <strong>{gap.gap_type}:</strong> {gap.description}
                            <br />
                            <em>{gap.suggestion}</em>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Graph Visualization */}
              <div className="graph-visualization-container">
                {graphData.nodes.length > 0 ? (
                  <ForceGraph
                    nodes={graphData.nodes}
                    edges={graphData.edges}
                    onNodeClick={handleNodeClick}
                  />
                ) : (
                  <div className="graph-placeholder">
                    <FaProjectDiagram size={64} />
                    <p>No graph data available</p>
                    <p className="graph-note">
                      Generate a concept graph to see the visualization
                    </p>
                  </div>
                )}
              </div>

              {/* Nodes List */}
              <div className="nodes-section">
                <h3 className="section-title">
                  Concept Nodes ({getFilteredNodes().length})
                </h3>
                <div className="nodes-grid">
                  {getFilteredNodes().slice(0, 50).map((node) => (
                    <div
                      key={node.id}
                      id={`node-${node.id}`}
                      data-node-id={node.id}
                      className={`node-card ${selectedNode === node.id ? 'selected' : ''}`}
                      style={{ borderLeftColor: getNodeColor(node) }}
                      onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}
                    >
                      <div className="node-header">
                        <FaCircle style={{ color: getNodeColor(node), fontSize: '0.8rem' }} />
                        <h4 className="node-label">{node.label}</h4>
                        <span className="node-type-badge">{node.type}</span>
                      </div>

                      <div className="node-details">
                        {node.entity_type && (
                          <div className="node-detail-item">
                            <span className="detail-label">Entity Type:</span>
                            <span className="detail-value">{node.entity_type}</span>
                          </div>
                        )}
                        <div className="node-detail-item">
                          <span className="detail-label">Frequency:</span>
                          <span className="detail-value">{node.frequency || 0}</span>
                        </div>
                        <div className="node-detail-item">
                          <span className="detail-label">Sources:</span>
                          <span className="detail-value">{node.sources?.length || 0}</span>
                        </div>
                        <div className="node-detail-item">
                          <span className="detail-label">Relevance:</span>
                          <span className="detail-value">
                            {(node.relevance_score * 100 || 0).toFixed(0)}%
                          </span>
                        </div>
                      </div>

                      {selectedNode === node.id && (
                        <div className="node-expanded">
                          {node.descriptions && node.descriptions.length > 0 && (
                            <div className="node-descriptions">
                              <h5>Descriptions:</h5>
                              <ul>
                                {node.descriptions.map((desc, idx) => (
                                  <li key={idx}>{desc}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {getConnectedNodes(node.id).length > 0 && (
                            <div className="node-connections">
                              <h5>Connected to:</h5>
                              <div className="connection-tags">
                                {getConnectedNodes(node.id).slice(0, 5).map((connNode, idx) => (
                                  <span
                                    key={idx}
                                    className="connection-tag"
                                    style={{ borderColor: getNodeColor(connNode) }}
                                  >
                                    {connNode.label}
                                  </span>
                                ))}
                                {getConnectedNodes(node.id).length > 5 && (
                                  <span className="connection-tag-more">
                                    +{getConnectedNodes(node.id).length - 5} more
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {getFilteredNodes().length === 0 && (
                  <div className="no-results">
                    <FaSearch size={48} />
                    <p>No nodes match your search or filter criteria.</p>
                  </div>
                )}
              </div>
            </>
          )}

          {!graphResults && (
            <div className="no-results">
              <FaProjectDiagram size={48} />
              <p>No concept graph available. Generate a graph first.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
