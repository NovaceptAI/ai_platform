import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../../utils/axiosInstance';
import '../../stages/StagesHome.css'; // use the shared styles

function RichTextDisplay({ title, content, colorClass = 'card-blue' }) {
  return (
    <div className={`stage-card ${colorClass}`}>
      <div className="card-top">
        <h3 className="card-title" title={title}>{title}</h3>
      </div>
      <div className="rich-body">
        {Array.isArray(content) ? (
          <ul>
            {content.map((item, idx) => <li key={idx}>{item}</li>)}
          </ul>
        ) : (
          <p>{content}</p>
        )}
      </div>
    </div>
  );
}

export default function Summarizer() {
  const navigate = useNavigate();
  const [selectedVaultFile, setSelectedVaultFile] = useState('');
  const [vaultFiles, setVaultFiles] = useState([]);
  const [summaryPages, setSummaryPages] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showProcessingModal, setShowProcessingModal] = useState(false);
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [progressId, setProgressId] = useState(null);
  const [fileId, setFileId] = useState(null);

  useEffect(() => { fetchVaultFiles(); }, []);

  useEffect(() => {
    if (progressId && fileId) {
      const interval = setInterval(() => {
        axiosInstance.get(`/summarizer/progress/${progressId}`)
          .then((res) => {
            const { percentage, status } = res.data;
            setProgressPercentage(percentage);
            if (status === 'done') {
              clearInterval(interval);
              fetchSummary(fileId);
              setShowProcessingModal(false);
            }
          })
          .catch((err) => console.error('Progress check failed', err));
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [progressId, fileId]);

  const fetchVaultFiles = async () => {
    try {
      const response = await axiosInstance.get('/upload/files');
      setVaultFiles(response.data.files || []);
    } catch {
      setError('Failed to fetch vault files.');
    }
  };

  const resetOutputStates = () => {
    setError('');
    setSummaryPages([]);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axiosInstance.post('/upload/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const storedAs = response.data.name || response.data.stored_as;
      await fetchVaultFiles();
      setSelectedVaultFile(storedAs);
    } catch (err) {
      console.error(err);
      setError('File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileSubmit = async (e) => {
    e.preventDefault();
    resetOutputStates();
    setLoading(true);

    try {
      if (selectedVaultFile) {
        const resp = await axiosInstance.post('/summarizer/summarize_file', {
          filename: selectedVaultFile,
          fromVault: true,
        });

        const { message, progress_id, file_id } = resp.data;

        if (message?.includes('Processing')) {
          setProgressId(progress_id);
          setFileId(file_id);
          setShowProcessingModal(true);
        } else {
          fetchSummary(file_id);
        }
      } else {
        setError('Please select or upload a file.');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while summarizing the file.');
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async (fid) => {
    try {
      const response = await axiosInstance.get(`/summarizer/get_summary/${fid}`);
      const pages = response.data.pages || [];
      setSummaryPages(pages);
    } catch (err) {
      console.error('Failed to fetch summary', err);
    }
  };

  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🖊️ Summarizer</h1>
        <p className="stage-subtitle">
          Upload or pick a file from your Knowledge Vault and generate crisp, page-wise summaries.
        </p>
      </header>

      {/* Form Card */}
      <div className="stage-grid">
        <div className="stage-card card-purple">
          <div className="card-top">
            <h3 className="card-title">Select Source</h3>
          </div>

          <form onSubmit={handleFileSubmit} className="tool-form">
            <label className="form-label">
              Upload File
              <input
                type="file"
                onChange={handleFileUpload}
                disabled={uploading}
                className="form-input"
              />
            </label>

            <label className="form-label">
              Or Select from Knowledge Vault
              <select
                value={selectedVaultFile}
                onChange={(e) => setSelectedVaultFile(e.target.value)}
                className="form-select"
              >
                <option value="">-- Select a file --</option>
                {vaultFiles.map((vf, idx) => (
                  <option key={idx} value={vf.stored_name}>{vf.name}</option>
                ))}
              </select>
            </label>

            <div className="form-actions">
              <button type="submit" className="try-btn" disabled={loading || uploading}>
                {loading ? 'Summarizing…' : 'Summarize File →'}
              </button>
            </div>

            {(uploading || loading) && <p className="muted">{uploading ? 'Uploading…' : 'Working…'}</p>}
            {error && <p className="error-text">{error}</p>}
          </form>
        </div>
      </div>

      {/* Summaries */}
      {summaryPages.length > 0 && (
        <>
          <div className="stage-header" style={{ marginTop: 24 }}>
            <h2 className="stage-title" style={{ fontSize: 24 }}>Page-wise Summary</h2>
            <p className="stage-subtitle">Each card below represents a summarized page.</p>
          </div>

          <div className="stage-grid">
            {summaryPages.map((p, idx) => (
              <RichTextDisplay
                key={idx}
                title={`Page ${p.page_number}`}
                content={p.summary}
                colorClass="card-blue"
              />
            ))}
          </div>
        </>
      )}

      {/* Processing Modal */}
      {showProcessingModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Summarization in Progress</h2>
            <p className="muted">{progressPercentage}% completed</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowProcessingModal(false)}>
                Stay Here
              </button>
              <button className="btn-primary" onClick={() => navigate('/dashboard')}>
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}