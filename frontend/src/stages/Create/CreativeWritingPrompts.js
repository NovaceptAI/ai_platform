import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaMagic,
  FaRocket,
  FaCopy,
  FaDownload,
  FaSyncAlt,
  FaFilter,
  FaCheck,
  FaLightbulb,
  FaBook,
  FaTimes
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './CreativeWritingPrompts.css';
import axiosInstance from '../../utils/axiosInstance';

function CreativeWritingPrompts() {
  // Three-tab state
  const [tab, setTab] = useState('generate');

  // File selection
  const [source, setSource] = useState('vault'); // vault | upload
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // Configuration
  const [numPrompts, setNumPrompts] = useState(10);
  const [genre, setGenre] = useState('mixed');
  const [force, setForce] = useState(false);

  // Status & progress
  const [status, setStatus] = useState('idle'); // idle | generating | completed | error
  const [progress, setProgress] = useState(0);
  const [progressId, setProgressId] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Results
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);

  // Filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [genreFilter, setGenreFilter] = useState('');
  const [toneFilter, setToneFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');

  // Fetch vault files on mount
  useEffect(() => {
    if (source === 'vault') {
      fetchVaultFiles();
    }
  }, [source]);

  // Poll for progress
  useEffect(() => {
    let interval;
    if (status === 'generating' && progressId) {
      interval = setInterval(() => {
        pollProgress();
      }, 1200);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [status, progressId]);

  const fetchVaultFiles = async () => {
    try {
      const res = await axiosInstance.get('/upload/files');
      const files = res.data.files || [];

      const normalizedFiles = files.map(file => ({
        id: file.fileId || file.id,
        name: file.name,
        stored_name: file.stored_name
      }));

      setVaultFiles(normalizedFiles);
    } catch (error) {
      console.error('Error fetching vault files:', error);
      setErrorMessage('Failed to load Knowledge Vault files');
    }
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    setUploadedFiles(files);
  };

  const toggleFileSelection = (fileId) => {
    setSelectedFileIds(prev =>
      prev.includes(fileId)
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const startGeneration = async () => {
    try {
      setStatus('generating');
      setProgress(0);
      setErrorMessage('');

      let fileIds = [];

      if (source === 'vault') {
        if (selectedFileIds.length === 0) {
          setErrorMessage('Please select at least one file');
          setStatus('idle');
          return;
        }
        fileIds = selectedFileIds;
      } else if (source === 'upload') {
        if (uploadedFiles.length === 0) {
          setErrorMessage('Please upload at least one file');
          setStatus('idle');
          return;
        }

        // Upload files first
        const formData = new FormData();
        uploadedFiles.forEach(file => {
          formData.append('files', file);
        });

        const uploadResponse = await axiosInstance.post('/upload/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        // Extract file IDs from successful uploads
        const successfulUploads = (uploadResponse.data.results || [])
          .filter(result => result.status === 'success' || result.status === 'duplicate')
          .map(result => result.file_id);

        fileIds = successfulUploads;

        if (fileIds.length === 0) {
          setErrorMessage('File upload failed');
          setStatus('idle');
          return;
        }
      }

      // Start generation for the first file (for now, we'll process one file)
      // You can extend this to handle multiple files if needed
      const fileId = fileIds[0];

      const res = await axiosInstance.post('/creative_prompts/start', {
        file_id: fileId,
        user_id: 'admin',
        num_prompts: numPrompts,
        genre,
        force
      });

      if (res.data.progress_id) {
        setProgressId(res.data.progress_id);
      } else {
        throw new Error('No progress_id returned');
      }
    } catch (error) {
      console.error('Error starting generation:', error);
      setErrorMessage(error.response?.data?.error || error.message || 'Failed to start generation');
      setStatus('error');
    }
  };

  const pollProgress = async () => {
    try {
      const res = await axiosInstance.get(`/creative_prompts/progress/${progressId}`);
      const { status: progressStatus, percentage } = res.data;

      setProgress(percentage || 0);

      if (progressStatus === 'completed') {
        setStatus('completed');
        await fetchResults();
        setTab('explore');
      } else if (progressStatus === 'failed') {
        setStatus('error');
        setErrorMessage('Generation failed. Please check server logs.');
      }
    } catch (error) {
      console.error('Error polling progress:', error);
      setStatus('error');
      setErrorMessage('Failed to check progress');
    }
  };

  const fetchResults = async () => {
    try {
      // Get the file_id from selectedFileIds or first uploaded file
      const fileId = selectedFileIds[0] || null;
      if (!fileId) return;

      const res = await axiosInstance.get('/creative_prompts/results', {
        params: {
          file_id: fileId,
          num_prompts: numPrompts,
          genre
        }
      });

      const promptsSet = res.data.prompts_set || {};
      setPrompts(promptsSet.prompts || []);
    } catch (error) {
      console.error('Error fetching results:', error);
      setErrorMessage('Failed to fetch results');
    }
  };

  const filteredPrompts = () => {
    let list = prompts;
    const q = searchQuery.toLowerCase();
    const g = genreFilter.toLowerCase();
    const t = toneFilter.toLowerCase();
    const tg = tagFilter.toLowerCase();

    if (q) {
      list = list.filter(
        (m) =>
          (m.prompt || '').toLowerCase().includes(q) ||
          (m.description || '').toLowerCase().includes(q) ||
          (m.genre || '').toLowerCase().includes(q) ||
          (m.tone || '').toLowerCase().includes(q) ||
          (m.tags || []).some((x) => x.toLowerCase().includes(q))
      );
    }
    if (g) {
      list = list.filter((m) => (m.genre || '').toLowerCase().includes(g));
    }
    if (t) {
      list = list.filter((m) => (m.tone || '').toLowerCase().includes(t));
    }
    if (tg) {
      list = list.filter((m) => (m.tags || []).some((x) => x.toLowerCase().includes(tg)));
    }
    return list;
  };

  const copyPrompt = (text) => {
    navigator.clipboard.writeText(text || '');
  };

  const downloadJSON = () => {
    const payload = {
      selected_files: selectedFileIds,
      num_prompts: numPrompts,
      genre,
      prompts
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.download = `creative_prompts_${Date.now()}.json`;
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
  };

  const canGenerate =
    (source === 'vault' && selectedFileIds.length > 0) ||
    (source === 'upload' && uploadedFiles.length > 0);
  const showResults = status === 'completed' && prompts.length > 0;

  return (
    <div className="cw-container">
      <header className="cw-hero">
        <div className="cw-hero-glow" />
        <h1 className="cw-title">
          <FaMagic className="cw-icon" /> Creative Writing Prompts
        </h1>
        <p className="cw-subtitle">Transform your documents into vivid, ready-to-use story starters.</p>
      </header>

      {/* Three-Tab Navigation */}
      <nav className="cw-tabs">
        <button
          className={`cw-tab ${tab === 'generate' ? 'active' : ''}`}
          onClick={() => setTab('generate')}
        >
          <FaRocket /> Generate
        </button>
        <button
          className={`cw-tab ${tab === 'explore' ? 'active' : ''}`}
          onClick={() => setTab('explore')}
          disabled={!showResults}
        >
          <FaLightbulb /> Explore
        </button>
        <button
          className={`cw-tab ${tab === 'review' ? 'active' : ''}`}
          onClick={() => setTab('review')}
          disabled={!selectedPrompt}
        >
          <FaBook /> Review
        </button>
      </nav>

      {/* Tab Content */}
      {tab === 'generate' && (
        <section className="cw-section card-ghost">
          <h2 className="cw-section-title">Generate Prompts</h2>

          {/* Source Selection */}
          <div className="cw-source-selector">
            <label className="cw-radio">
              <input
                type="radio"
                checked={source === 'vault'}
                onChange={() => setSource('vault')}
              />
              <span>From Knowledge Vault</span>
            </label>
            <label className="cw-radio">
              <input
                type="radio"
                checked={source === 'upload'}
                onChange={() => setSource('upload')}
              />
              <span>Upload New Files</span>
            </label>
          </div>

          {/* File Selection */}
          {source === 'vault' ? (
            <div className="cw-form-group">
              <label className="cw-label">
                <span>Select Files from Knowledge Vault ({selectedFileIds.length} selected)</span>
              </label>
              <div className="cw-file-list">
                {vaultFiles.length === 0 ? (
                  <p className="cw-empty-files">No files in Knowledge Vault. Upload files first.</p>
                ) : (
                  vaultFiles.map((file) => (
                    <div
                      key={file.id}
                      className={`cw-file-item ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                      onClick={() => toggleFileSelection(file.id)}
                    >
                      <input
                        type="checkbox"
                        checked={selectedFileIds.includes(file.id)}
                        onChange={() => toggleFileSelection(file.id)}
                      />
                      <span className="cw-file-name">{file.name}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="cw-form-group">
              <label className="cw-label">
                <span>Upload Files</span>
                <input
                  type="file"
                  className="cw-input"
                  accept=".pdf,.txt,.docx"
                  multiple
                  onChange={handleFileUpload}
                />
              </label>
              {uploadedFiles.length > 0 && (
                <div className="cw-uploaded-list">
                  {uploadedFiles.map((file, idx) => (
                    <div key={idx} className="cw-uploaded-item">
                      <span>{file.name}</span>
                      <span className="cw-file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Configuration */}
          <div className="cw-config">
            <label className="cw-label">
              <span>Number of Prompts</span>
              <input
                type="number"
                className="cw-input"
                min="1"
                max="30"
                value={numPrompts}
                onChange={(e) => setNumPrompts(Number(e.target.value))}
              />
            </label>

            <label className="cw-label">
              <span>Genre Focus</span>
              <select className="cw-input" value={genre} onChange={(e) => setGenre(e.target.value)}>
                <option value="mixed">Mixed (All genres)</option>
                <option value="fantasy">Fantasy</option>
                <option value="scifi">Science Fiction</option>
                <option value="mystery">Mystery</option>
                <option value="romance">Romance</option>
                <option value="horror">Horror</option>
              </select>
            </label>

            <label className="cw-checkbox">
              <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
              <span>Regenerate (ignore cached)</span>
            </label>
          </div>

          {/* Actions */}
          <div className="cw-actions">
            <button
              className="btn-primary"
              onClick={startGeneration}
              disabled={!canGenerate || status === 'generating'}
            >
              <FaRocket />{' '}
              {status === 'generating' ? 'Generating…' : 'Generate Prompts'}
            </button>
          </div>

          {/* Progress */}
          {status === 'generating' && (
            <div className="cw-progress-container">
              <div className="cw-progress-bar">
                <div className="cw-progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="cw-progress-text">{progress}%</div>
            </div>
          )}

          {errorMessage && <div className="cw-error">{errorMessage}</div>}
        </section>
      )}

      {tab === 'explore' && (
        <section className="cw-section">
          <div className="cw-section-header">
            <h2 className="cw-section-title">Explore Prompts</h2>
            <div className="cw-header-actions">
              <button className="btn-ghost" onClick={downloadJSON}>
                <FaDownload /> Download JSON
              </button>
              <button className="btn-ghost" onClick={fetchResults}>
                <FaSyncAlt /> Refresh
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="cw-filters card-ghost">
            <div className="cw-filter-group">
              <FaFilter className="cw-filter-icon" />
              <input
                className="cw-input"
                placeholder="Search prompt, description, tags…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="cw-filter-row">
              <input
                className="cw-input cw-filter-small"
                placeholder="Filter by genre"
                value={genreFilter}
                onChange={(e) => setGenreFilter(e.target.value)}
              />
              <input
                className="cw-input cw-filter-small"
                placeholder="Filter by tone"
                value={toneFilter}
                onChange={(e) => setToneFilter(e.target.value)}
              />
              <input
                className="cw-input cw-filter-small"
                placeholder="Filter by tag"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
              />
            </div>
          </div>

          {/* Prompt Cards */}
          <div className="cw-grid">
            {filteredPrompts().map((prompt, idx) => (
              <PromptCard
                key={idx}
                prompt={prompt}
                onCopy={copyPrompt}
                onSelect={() => {
                  setSelectedPrompt(prompt);
                  setTab('review');
                }}
              />
            ))}
          </div>

          {filteredPrompts().length === 0 && (
            <div className="cw-empty">No prompts match your filters.</div>
          )}
        </section>
      )}

      {tab === 'review' && selectedPrompt && (
        <section className="cw-section">
          <div className="cw-section-header">
            <h2 className="cw-section-title">Review Prompt</h2>
            <button
              className="btn-ghost"
              onClick={() => {
                setSelectedPrompt(null);
                setTab('explore');
              }}
            >
              <FaTimes /> Close
            </button>
          </div>

          <div className="cw-review-card card-ghost">
            <div className="cw-review-header">
              <div className="cw-review-meta">
                {selectedPrompt.genre && <span className="cw-chip">{selectedPrompt.genre}</span>}
                {selectedPrompt.tone && <span className="cw-chip">{selectedPrompt.tone}</span>}
              </div>
              <button
                className="btn-primary"
                onClick={() => copyPrompt(selectedPrompt.prompt)}
              >
                <FaCopy /> Copy Prompt
              </button>
            </div>

            <div className="cw-review-content">
              <h3 className="cw-review-prompt">"{selectedPrompt.prompt}"</h3>
              {selectedPrompt.description && (
                <p className="cw-review-description">{selectedPrompt.description}</p>
              )}
            </div>

            {selectedPrompt.tags && selectedPrompt.tags.length > 0 && (
              <div className="cw-review-tags">
                <strong>Tags:</strong>
                <div className="cw-tags-list">
                  {selectedPrompt.tags.map((tag, i) => (
                    <span key={i} className="cw-chip">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="cw-review-actions">
              <button
                className="btn-ghost"
                onClick={() => {
                  const idx = prompts.indexOf(selectedPrompt);
                  if (idx > 0) setSelectedPrompt(prompts[idx - 1]);
                }}
                disabled={prompts.indexOf(selectedPrompt) === 0}
              >
                ← Previous
              </button>
              <button
                className="btn-ghost"
                onClick={() => {
                  const idx = prompts.indexOf(selectedPrompt);
                  if (idx < prompts.length - 1) setSelectedPrompt(prompts[idx + 1]);
                }}
                disabled={prompts.indexOf(selectedPrompt) === prompts.length - 1}
              >
                Next →
              </button>
            </div>
          </div>
        </section>
      )}

      <footer className="cw-footer">
        <Link to="/create" className="cw-back-link">
          ← Back to Create
        </Link>
      </footer>
    </div>
  );
}

function PromptCard({ prompt, onCopy, onSelect }) {
  const [copied, setCopied] = useState(false);

  function handleCopy(e) {
    e.stopPropagation();
    onCopy(prompt.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 900);
  }

  return (
    <div className="cw-card" onClick={onSelect}>
      <div className="cw-card-body">
        <p className="cw-card-prompt">"{prompt.prompt}"</p>
        {prompt.description && <p className="cw-card-description">{prompt.description}</p>}
        <div className="cw-card-meta">
          {prompt.genre && <span className="cw-chip">{prompt.genre}</span>}
          {prompt.tone && <span className="cw-chip">{prompt.tone}</span>}
          {(prompt.tags || []).slice(0, 3).map((tag, i) => (
            <span key={i} className="cw-chip">
              #{tag}
            </span>
          ))}
        </div>
      </div>
      <div className="cw-card-actions">
        <button className="btn-primary btn-sm" onClick={handleCopy}>
          {copied ? <><FaCheck /> Copied</> : <><FaCopy /> Copy</>}
        </button>
      </div>
    </div>
  );
}

export default CreativeWritingPrompts;
