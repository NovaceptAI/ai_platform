import React, { useState, useEffect, useMemo } from 'react';
import axiosInstance from '../../utils/axiosInstance';
import '../StagesHome.css';

/**
 * Readability and Style Analyzer Tool
 *
 * Evaluates clarity, complexity, and writing style of documents.
 * Provides readability scores, style analysis, and improvement recommendations.
 */
function ReadabilityAnalyzer() {
  // File selection state
  const [selectedVaultFile, setSelectedVaultFile] = useState('');
  const [vaultFiles, setVaultFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  // Processing state
  const [loading, setLoading] = useState(false);
  const [progressId, setProgressId] = useState(null);
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [fileId, setFileId] = useState(null);

  // Results state
  const [analysisData, setAnalysisData] = useState(null);
  const [error, setError] = useState('');

  // UI state
  const [activeView, setActiveView] = useState('overview'); // overview, per-page, issues, recommendations

  // Fetch vault files on mount
  useEffect(() => {
    fetchVaultFiles();
  }, []);

  const fetchVaultFiles = async () => {
    try {
      const response = await axiosInstance.get('/upload/files');
      setVaultFiles(response.data.files || []);
    } catch (err) {
      console.error('Failed to fetch vault files:', err);
    }
  };

  // Handle file upload to vault
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
      setError(err?.response?.data?.error || 'File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  // Start readability analysis
  const handleAnalyzeReadability = async (e) => {
    e.preventDefault();
    if (!selectedVaultFile) {
      setError('Please select a file first.');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysisData(null);
    setProgressPercentage(0);

    try {
      // Get file_id from vault file
      const vaultFile = vaultFiles.find(f => f.stored_name === selectedVaultFile || f.name === selectedVaultFile);
      if (!vaultFile) {
        setError('Selected file not found in vault.');
        setLoading(false);
        return;
      }

      console.log('Starting readability analysis for file:', {
        file_id: vaultFile.fileId || vaultFile.id,
        file_name: vaultFile.name,
        vaultFile
      });

      const response = await axiosInstance.post('/stages/discover/readability/start', {
        file_id: vaultFile.fileId || vaultFile.id,
        force: false
      });

      const { message, progress_id, file_id: respFileId, cached } = response.data;

      if (cached) {
        // Results already exist - fetch them
        setFileId(respFileId);
        await fetchResults(respFileId);
      } else {
        // Processing started - poll for progress
        setProgressId(progress_id);
        setFileId(respFileId);
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to start readability analysis.');
      setLoading(false);
    }
  };

  // Poll progress every 3 seconds
  useEffect(() => {
    if (!progressId || !fileId) return;

    const interval = setInterval(async () => {
      try {
        const res = await axiosInstance.get(`/stages/discover/readability/progress/${progressId}`);
        const { percentage = 0, status } = res.data || {};
        setProgressPercentage(percentage ?? 0);

        // Check for completion
        if (status === 'completed' || (percentage ?? 0) >= 100) {
          clearInterval(interval);
          setProgressId(null);
          await fetchResults(fileId);
        } else if (status === 'failed') {
          clearInterval(interval);
          setProgressId(null);
          setError('Readability analysis failed. Please try again.');
          setLoading(false);
        }
      } catch (e) {
        console.error('Error polling progress:', e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [progressId, fileId]);

  // Fetch results
  const fetchResults = async (fId) => {
    try {
      const response = await axiosInstance.get(`/stages/discover/readability/results?file_id=${fId}`);
      setAnalysisData(response.data);
      setLoading(false);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to fetch readability results.');
      setLoading(false);
    }
  };

  // Get readability level badge color
  const getReadabilityColor = (level) => {
    const colors = {
      very_easy: '#10b981',
      easy: '#84cc16',
      moderate: '#f59e0b',
      difficult: '#ef4444',
      very_difficult: '#dc2626'
    };
    return colors[level] || '#6b7280';
  };

  // Get severity badge color
  const getSeverityColor = (severity) => {
    const colors = {
      high: '#ef4444',
      medium: '#f59e0b',
      low: '#84cc16'
    };
    return colors[severity] || '#6b7280';
  };

  return (
    <div className="stage-wrap">
      {/* Header */}
      <header className="stage-header">
        <h1 className="stage-title">📖 Readability & Style Analyzer</h1>
        <p className="stage-subtitle">
          Evaluate the clarity, complexity, and writing style of your documents.
          Get readability scores, style insights, and improvement recommendations.
        </p>
      </header>

      {/* Compact Toolbar */}
      <div className="stage-grid">
        <div className="stage-card card-purple card-compact">
          <form onSubmit={handleAnalyzeReadability} className="tool-form compact-form">
            <div className="compact-row">
              {/* Upload button */}
              <input
                id="filePicker"
                type="file"
                onChange={handleFileUpload}
                disabled={uploading || loading}
                style={{ display: 'none' }}
                accept=".pdf,.txt,.doc,.docx"
              />
              <label htmlFor="filePicker" className="btn-ghost compact-btn" style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}>
                ⬆️ Upload
              </label>

              <span className="dot-divider" aria-hidden="true">•</span>

              {/* Vault select */}
              <select
                value={selectedVaultFile}
                onChange={(e) => setSelectedVaultFile(e.target.value)}
                className="compact-select"
                disabled={loading || uploading}
              >
                <option value="">Vault: choose file…</option>
                {vaultFiles.map((vf, idx) => (
                  <option key={idx} value={vf.stored_name}>
                    {vf.name}
                  </option>
                ))}
              </select>

              {/* Clear button */}
              {selectedVaultFile && !loading && (
                <button
                  type="button"
                  className="btn-ghost compact-btn"
                  onClick={() => {
                    setSelectedVaultFile('');
                    setAnalysisData(null);
                    setError('');
                  }}
                >
                  ✕
                </button>
              )}

              {/* Primary action */}
              <button
                type="submit"
                className="btn-primary compact-btn"
                disabled={loading || uploading || !selectedVaultFile}
              >
                {loading ? 'Analyzing…' : '📖 Analyze'}
              </button>
            </div>

            {/* Status line */}
            {(error || uploading || (progressId && progressPercentage < 100)) && (
              <div className="compact-status" style={{ marginTop: 8 }}>
                {error && <span className="error-text">{error}</span>}
                {uploading && <span className="muted">Uploading file...</span>}
                {progressId && progressPercentage < 100 && (
                  <div style={{ marginTop: 8 }}>
                    <InlineProgress percentage={progressPercentage} />
                  </div>
                )}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Results Section */}
      {analysisData && (
        <>
          {/* Summary Stats Card */}
          <div style={{ margin: '32px auto', maxWidth: 1100 }}>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: 16,
              padding: 24,
              color: 'white',
              boxShadow: '0 10px 30px rgba(102, 126, 234, 0.3)'
            }}>
              <h2 style={{ margin: '0 0 16px 0', fontSize: 24 }}>📊 Readability Summary</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                <StatCard
                  label="Total Words"
                  value={analysisData.doc_metrics?.total_words || 0}
                  icon="📝"
                />
                <StatCard
                  label="Readability Score"
                  value={analysisData.readability_scores?.flesch_reading_ease?.toFixed(1) || 'N/A'}
                  icon="⭐"
                />
                <StatCard
                  label="Grade Level"
                  value={analysisData.readability_scores?.flesch_kincaid_grade?.toFixed(1) || 'N/A'}
                  icon="🎓"
                />
                <StatCard
                  label="Issues Found"
                  value={analysisData.issues?.length || 0}
                  icon="⚠️"
                />
              </div>
              <div style={{ marginTop: 16, fontSize: 14, opacity: 0.95 }}>
                <strong>Interpretation:</strong> {analysisData.readability_scores?.interpretation || 'N/A'}
              </div>
            </div>
          </div>

          {/* View Tabs */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginBottom: 24 }}>
            {['overview', 'per-page', 'issues', 'recommendations'].map(view => (
              <button
                key={view}
                onClick={() => setActiveView(view)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 8,
                  border: activeView === view ? '2px solid #667eea' : '1px solid #e5e7eb',
                  background: activeView === view ? '#eef2ff' : 'white',
                  color: activeView === view ? '#667eea' : '#4b5563',
                  fontWeight: activeView === view ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  textTransform: 'capitalize'
                }}
              >
                {view === 'overview' && '📊 Overview'}
                {view === 'per-page' && '📄 Per Page'}
                {view === 'issues' && '⚠️ Issues'}
                {view === 'recommendations' && '💡 Recommendations'}
              </button>
            ))}
          </div>

          {/* Content Views */}
          {activeView === 'overview' && (
            <OverviewView analysisData={analysisData} getReadabilityColor={getReadabilityColor} />
          )}
          {activeView === 'per-page' && (
            <PerPageView analysisData={analysisData} getReadabilityColor={getReadabilityColor} />
          )}
          {activeView === 'issues' && (
            <IssuesView analysisData={analysisData} getSeverityColor={getSeverityColor} />
          )}
          {activeView === 'recommendations' && (
            <RecommendationsView analysisData={analysisData} />
          )}
        </>
      )}

      {/* Empty State */}
      {!analysisData && !loading && !error && (
        <div style={{ textAlign: 'center', padding: 60, opacity: 0.5 }}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>📖</div>
          <p style={{ fontSize: 18, color: '#6b7280' }}>Select a file and click "Analyze" to begin</p>
        </div>
      )}
    </div>
  );
}

// Inline Progress Component
function InlineProgress({ percentage = 0 }) {
  const pct = Math.max(0, Math.min(100, Number(percentage) || 0));
  return (
    <div style={{ padding: 12, borderRadius: 8, background: 'rgba(0,0,0,0.04)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
        <strong>Analyzing...</strong>
        <span>{pct}%</span>
      </div>
      <div style={{ height: 8, borderRadius: 4, overflow: 'hidden', background: 'rgba(0,0,0,0.08)' }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          transition: 'width .4s ease',
          background: 'linear-gradient(90deg, #667eea, #764ba2)'
        }} />
      </div>
      <div style={{ fontSize: 11, opacity: 0.6, marginTop: 6 }}>Auto-refreshing every 3 seconds...</div>
    </div>
  );
}

// Stat Card Component
function StatCard({ label, value, icon }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 12, padding: 16 }}>
      <div style={{ fontSize: 28, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 12, opacity: 0.9 }}>{label}</div>
    </div>
  );
}

// Overview View
function OverviewView({ analysisData, getReadabilityColor }) {
  const metrics = analysisData.doc_metrics || {};
  const style = analysisData.style_analysis || {};
  const scores = analysisData.readability_scores || {};

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Document Metrics */}
      <MetricsCard title="📊 Document Metrics" metrics={[
        { label: 'Total Words', value: metrics.total_words },
        { label: 'Sentences', value: metrics.total_sentences },
        { label: 'Paragraphs', value: metrics.total_paragraphs },
        { label: 'Avg Words/Sentence', value: metrics.avg_words_per_sentence },
        { label: 'Complex Words', value: `${metrics.complex_word_percentage}%` },
        { label: 'Pages Analyzed', value: metrics.pages_analyzed }
      ]} />

      {/* Style Analysis */}
      <div style={{ background: 'white', borderRadius: 12, padding: 20, marginTop: 16, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: 18, fontWeight: 700 }}>🎨 Style Analysis</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Dominant Tone</div>
            <div style={{ fontSize: 16, fontWeight: 600, textTransform: 'capitalize' }}>
              {style.dominant_tone?.replace('_', ' ') || 'Unknown'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Readability Level</div>
            <div style={{
              fontSize: 16,
              fontWeight: 600,
              textTransform: 'capitalize',
              color: getReadabilityColor(style.dominant_readability_level)
            }}>
              {style.dominant_readability_level?.replace('_', ' ') || 'Unknown'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Target Audience</div>
            <div style={{ fontSize: 16, fontWeight: 600, textTransform: 'capitalize' }}>
              {analysisData.target_audience?.replace('_', ' ') || 'General'}
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      {analysisData.summary && (
        <div style={{ background: '#f9fafb', borderRadius: 12, padding: 20, marginTop: 16, borderLeft: '4px solid #667eea' }}>
          <div style={{ fontSize: 14, lineHeight: 1.6, color: '#374151' }}>
            {analysisData.summary}
          </div>
        </div>
      )}
    </div>
  );
}

// Metrics Card Component
function MetricsCard({ title, metrics }) {
  return (
    <div style={{ background: 'white', borderRadius: 12, padding: 20, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: 18, fontWeight: 700 }}>{title}</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 16 }}>
        {metrics.map((metric, idx) => (
          <div key={idx}>
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>{metric.label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#1f2937' }}>{metric.value || 'N/A'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Per-Page View
function PerPageView({ analysisData, getReadabilityColor }) {
  const perPage = analysisData.per_page_analysis || [];

  if (perPage.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40, opacity: 0.5 }}>
        <p>No per-page analysis data available.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'grid', gap: 16 }}>
        {perPage.map((item, idx) => {
          const analysis = item.analysis || {};
          return (
            <div key={idx} style={{
              background: 'white',
              borderRadius: 12,
              padding: 20,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Page {item.page}</h4>
                <span style={{
                  padding: '4px 12px',
                  borderRadius: 999,
                  fontSize: 12,
                  fontWeight: 600,
                  background: getReadabilityColor(analysis.readability_level) + '20',
                  color: getReadabilityColor(analysis.readability_level)
                }}>
                  {analysis.readability_level?.replace('_', ' ') || 'N/A'}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>Words</div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{analysis.word_count || 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>Sentences</div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{analysis.sentence_count || 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>Avg Length</div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{analysis.avg_sentence_length || 0}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>Tone</div>
                  <div style={{ fontSize: 16, fontWeight: 600, textTransform: 'capitalize' }}>{analysis.tone || 'N/A'}</div>
                </div>
              </div>

              {analysis.issues && analysis.issues.length > 0 && (
                <div style={{ marginTop: 12, fontSize: 13, color: '#6b7280' }}>
                  <strong>Issues:</strong> {analysis.issues.length} found
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Issues View
function IssuesView({ analysisData, getSeverityColor }) {
  const issues = analysisData.issues || [];

  if (issues.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40, opacity: 0.5 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
        <p style={{ fontSize: 18, color: '#10b981' }}>No major readability issues detected!</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 16, fontSize: 14, color: '#6b7280' }}>
        Found {issues.length} issue{issues.length !== 1 ? 's' : ''} that could be improved
      </div>
      <div style={{ display: 'grid', gap: 12 }}>
        {issues.map((issue, idx) => (
          <div key={idx} style={{
            background: 'white',
            borderRadius: 12,
            padding: 16,
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            borderLeft: `4px solid ${getSeverityColor(issue.severity)}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{
                fontSize: 12,
                padding: '3px 8px',
                borderRadius: 999,
                background: '#f3f4f6',
                color: '#374151',
                fontWeight: 600,
                textTransform: 'capitalize'
              }}>
                {issue.type?.replace('_', ' ') || 'Issue'}
              </span>
              <span style={{
                fontSize: 12,
                padding: '3px 8px',
                borderRadius: 999,
                background: getSeverityColor(issue.severity) + '20',
                color: getSeverityColor(issue.severity),
                fontWeight: 600,
                textTransform: 'uppercase'
              }}>
                {issue.severity} severity
              </span>
            </div>

            <div style={{ fontSize: 14, color: '#1f2937', marginBottom: 8 }}>
              <strong>Issue:</strong> {issue.description}
            </div>

            {issue.suggestion && (
              <div style={{ fontSize: 13, color: '#059669', background: '#d1fae5', padding: 8, borderRadius: 6 }}>
                <strong>💡 Suggestion:</strong> {issue.suggestion}
              </div>
            )}

            {issue.page && (
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
                Page {issue.page}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Recommendations View
function RecommendationsView({ analysisData }) {
  const recommendations = analysisData.recommendations || [];

  if (recommendations.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40, opacity: 0.5 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
        <p style={{ fontSize: 18, color: '#10b981' }}>Your document is well-written! No specific recommendations at this time.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ background: 'white', borderRadius: 12, padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: 20, fontWeight: 700 }}>💡 Recommendations to Improve Readability</h3>
        <div style={{ display: 'grid', gap: 16 }}>
          {recommendations.map((rec, idx) => (
            <div key={idx} style={{
              padding: 16,
              background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)',
              borderRadius: 8,
              borderLeft: '4px solid #667eea'
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: '#667eea',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  flexShrink: 0
                }}>
                  {idx + 1}
                </div>
                <div style={{ fontSize: 15, lineHeight: 1.6, color: '#1f2937', flex: 1 }}>
                  {rec}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ReadabilityAnalyzer;
