import React, { useState, useEffect, useMemo } from 'react';
import axiosInstance from '../../utils/axiosInstance';
import '../StagesHome.css';

/**
 * Evidence Extractor Tool
 *
 * Extracts evidence, quotes, facts, statistics, and supporting statements from documents.
 * Useful for academic research, fact-checking, and argument analysis.
 */
function EvidenceExtractor() {
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
  const [evidenceData, setEvidenceData] = useState(null);
  const [error, setError] = useState('');

  // UI state
  const [activeView, setActiveView] = useState('all'); // all, by-type, by-confidence, stats
  const [selectedType, setSelectedType] = useState('all');
  const [selectedConfidence, setSelectedConfidence] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

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

  // Start evidence extraction
  const handleExtractEvidence = async (e) => {
    e.preventDefault();
    if (!selectedVaultFile) {
      setError('Please select a file first.');
      return;
    }

    setLoading(true);
    setError('');
    setEvidenceData(null);
    setProgressPercentage(0);

    try {
      // Get file_id from vault file
      const vaultFile = vaultFiles.find(f => f.stored_name === selectedVaultFile || f.name === selectedVaultFile);
      if (!vaultFile) {
        setError('Selected file not found in vault.');
        setLoading(false);
        return;
      }

      console.log('Starting evidence extraction for file:', {
        file_id: vaultFile.fileId || vaultFile.id,
        file_name: vaultFile.name,
        vaultFile
      });

      const response = await axiosInstance.post('/stages/discover/evidence_extractor/start', {
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
      setError(err?.response?.data?.error || 'Failed to start evidence extraction.');
      setLoading(false);
    }
  };

  // Poll progress every 3 seconds
  useEffect(() => {
    if (!progressId || !fileId) return;

    const interval = setInterval(async () => {
      try {
        const res = await axiosInstance.get(`/stages/discover/evidence_extractor/progress/${progressId}`);
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
          setError('Evidence extraction failed. Please try again.');
          setLoading(false);
        }
      } catch (e) {
        // Keep polling; transient errors are okay
        console.error('Error polling progress:', e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [progressId, fileId]);

  // Fetch results
  const fetchResults = async (fId) => {
    try {
      const response = await axiosInstance.get(`/stages/discover/evidence_extractor/results?file_id=${fId}`);
      setEvidenceData(response.data);
      setLoading(false);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to fetch evidence results.');
      setLoading(false);
    }
  };

  // Filter evidence based on selected filters
  const filteredEvidence = useMemo(() => {
    if (!evidenceData?.aggregated_evidence) return [];

    let evidence = evidenceData.aggregated_evidence;

    // Filter by type
    if (selectedType !== 'all') {
      evidence = evidence.filter(e => e.type === selectedType);
    }

    // Filter by confidence
    if (selectedConfidence !== 'all') {
      evidence = evidence.filter(e => e.confidence === selectedConfidence);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      evidence = evidence.filter(e =>
        e.content?.toLowerCase().includes(query) ||
        e.context?.toLowerCase().includes(query) ||
        e.themes?.some(t => t.toLowerCase().includes(query))
      );
    }

    return evidence;
  }, [evidenceData, selectedType, selectedConfidence, searchQuery]);

  // Get unique evidence types
  const evidenceTypes = useMemo(() => {
    if (!evidenceData?.aggregated_evidence) return [];
    const types = new Set(evidenceData.aggregated_evidence.map(e => e.type));
    return Array.from(types).sort();
  }, [evidenceData]);

  // Evidence type icon
  const getTypeIcon = (type) => {
    const icons = {
      quote: '💬',
      statistic: '📊',
      fact: '✓',
      expert_opinion: '🎓',
      case_study: '📋',
      research_finding: '🔬',
      anecdote: '📖',
      definition: '📚',
      other: '📄'
    };
    return icons[type] || '📄';
  };

  // Confidence badge color
  const getConfidenceColor = (confidence) => {
    const colors = {
      high: '#10b981',
      medium: '#f59e0b',
      low: '#6b7280'
    };
    return colors[confidence] || '#6b7280';
  };

  return (
    <div className="stage-wrap">
      {/* Header */}
      <header className="stage-header">
        <h1 className="stage-title">🔍 Evidence Extractor</h1>
        <p className="stage-subtitle">
          Extract evidence, quotes, facts, and supporting statements from your documents.
          Perfect for academic research, fact-checking, and argument analysis.
        </p>
      </header>

      {/* Compact Toolbar */}
      <div className="stage-grid">
        <div className="stage-card card-purple card-compact">
          <form onSubmit={handleExtractEvidence} className="tool-form compact-form">
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
                    setEvidenceData(null);
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
                {loading ? 'Processing…' : '🔍 Extract Evidence'}
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
      {evidenceData && (
        <>
          {/* Summary Stats */}
          <div style={{ margin: '32px auto', maxWidth: 1100 }}>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: 16,
              padding: 24,
              color: 'white',
              boxShadow: '0 10px 30px rgba(102, 126, 234, 0.3)'
            }}>
              <h2 style={{ margin: '0 0 16px 0', fontSize: 24 }}>📊 Evidence Summary</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                <StatCard
                  label="Total Evidence Items"
                  value={evidenceData.aggregated_evidence?.length || 0}
                  icon="📝"
                />
                <StatCard
                  label="High Confidence"
                  value={evidenceData.aggregated_evidence?.filter(e => e.confidence === 'high').length || 0}
                  icon="⭐"
                />
                <StatCard
                  label="Evidence Types"
                  value={evidenceTypes.length}
                  icon="🏷️"
                />
                <StatCard
                  label="Document"
                  value={evidenceData.file_name || 'N/A'}
                  icon="📄"
                  isText
                />
              </div>
            </div>
          </div>

          {/* View Tabs */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginBottom: 24 }}>
            {['all', 'by-type', 'by-confidence', 'stats'].map(view => (
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
                  transition: 'all 0.2s'
                }}
              >
                {view === 'all' && '📋 All Evidence'}
                {view === 'by-type' && '🏷️ By Type'}
                {view === 'by-confidence' && '⭐ By Confidence'}
                {view === 'stats' && '📊 Statistics'}
              </button>
            ))}
          </div>

          {/* Filters (for 'all' view) */}
          {activeView === 'all' && (
            <div style={{ maxWidth: 1100, margin: '0 auto 24px', display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="🔍 Search evidence..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: '1 1 300px',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #e5e7eb',
                  fontSize: 14
                }}
              />
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #e5e7eb',
                  fontSize: 14
                }}
              >
                <option value="all">All Types</option>
                {evidenceTypes.map(type => (
                  <option key={type} value={type}>
                    {getTypeIcon(type)} {type.replace('_', ' ')}
                  </option>
                ))}
              </select>
              <select
                value={selectedConfidence}
                onChange={(e) => setSelectedConfidence(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #e5e7eb',
                  fontSize: 14
                }}
              >
                <option value="all">All Confidence Levels</option>
                <option value="high">⭐ High</option>
                <option value="medium">📊 Medium</option>
                <option value="low">📝 Low</option>
              </select>
              {(searchQuery || selectedType !== 'all' || selectedConfidence !== 'all') && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedType('all');
                    setSelectedConfidence('all');
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: '1px solid #e5e7eb',
                    background: 'white',
                    cursor: 'pointer',
                    fontSize: 14
                  }}
                >
                  ✕ Clear
                </button>
              )}
            </div>
          )}

          {/* Content Views */}
          {activeView === 'all' && (
            <AllEvidenceView evidence={filteredEvidence} getTypeIcon={getTypeIcon} getConfidenceColor={getConfidenceColor} />
          )}
          {activeView === 'by-type' && (
            <ByTypeView evidenceData={evidenceData} evidenceTypes={evidenceTypes} getTypeIcon={getTypeIcon} getConfidenceColor={getConfidenceColor} />
          )}
          {activeView === 'by-confidence' && (
            <ByConfidenceView evidenceData={evidenceData} getConfidenceColor={getConfidenceColor} getTypeIcon={getTypeIcon} />
          )}
          {activeView === 'stats' && (
            <StatsView evidenceData={evidenceData} evidenceTypes={evidenceTypes} getTypeIcon={getTypeIcon} />
          )}
        </>
      )}

      {/* Empty State */}
      {!evidenceData && !loading && !error && (
        <div style={{ textAlign: 'center', padding: 60, opacity: 0.5 }}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>🔍</div>
          <p style={{ fontSize: 18, color: '#6b7280' }}>Select a file and click "Extract Evidence" to begin</p>
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
        <strong>Processing...</strong>
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
function StatCard({ label, value, icon, isText = false }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 12, padding: 16 }}>
      <div style={{ fontSize: 28, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: isText ? 12 : 28, fontWeight: 700, marginBottom: 4, wordBreak: 'break-word' }}>
        {isText ? (value.length > 30 ? value.substring(0, 30) + '...' : value) : value}
      </div>
      <div style={{ fontSize: 12, opacity: 0.9 }}>{label}</div>
    </div>
  );
}

// All Evidence View
function AllEvidenceView({ evidence, getTypeIcon, getConfidenceColor }) {
  if (evidence.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40, opacity: 0.5 }}>
        <p>No evidence items match your filters.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 12, fontSize: 13, opacity: 0.7 }}>
        Showing {evidence.length} evidence item{evidence.length !== 1 ? 's' : ''}
      </div>
      <div style={{ display: 'grid', gap: 16 }}>
        {evidence.map((item, idx) => (
          <EvidenceCard key={idx} item={item} getTypeIcon={getTypeIcon} getConfidenceColor={getConfidenceColor} />
        ))}
      </div>
    </div>
  );
}

// Evidence Card Component
function EvidenceCard({ item, getTypeIcon, getConfidenceColor }) {
  return (
    <div style={{
      background: 'white',
      borderRadius: 12,
      padding: 20,
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      border: '1px solid #e5e7eb',
      transition: 'all 0.2s'
    }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {/* Header with type and confidence */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{
          fontSize: 13,
          padding: '4px 10px',
          borderRadius: 999,
          background: '#f3f4f6',
          color: '#374151',
          fontWeight: 600
        }}>
          {getTypeIcon(item.type)} {item.type.replace('_', ' ')}
        </span>
        <span style={{
          fontSize: 12,
          padding: '4px 10px',
          borderRadius: 999,
          background: getConfidenceColor(item.confidence) + '20',
          color: getConfidenceColor(item.confidence),
          fontWeight: 600,
          border: `1px solid ${getConfidenceColor(item.confidence)}40`
        }}>
          {item.confidence} confidence
        </span>
      </div>

      {/* Content */}
      <div style={{
        fontSize: 15,
        lineHeight: 1.6,
        color: '#1f2937',
        marginBottom: 12,
        padding: 12,
        background: '#fafafa',
        borderRadius: 8,
        borderLeft: `3px solid ${getConfidenceColor(item.confidence)}`
      }}>
        "{item.content}"
      </div>

      {/* Context */}
      {item.context && (
        <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 12, lineHeight: 1.5 }}>
          <strong>Context:</strong> {item.context}
        </div>
      )}

      {/* Supporting Info */}
      {item.supporting_info && Object.keys(item.supporting_info).length > 0 && (
        <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 12 }}>
          {item.supporting_info.author && <div>👤 Author: {item.supporting_info.author}</div>}
          {item.supporting_info.source && <div>📚 Source: {item.supporting_info.source}</div>}
          {item.supporting_info.date && <div>📅 Date: {item.supporting_info.date}</div>}
        </div>
      )}

      {/* Themes */}
      {item.themes && item.themes.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {item.themes.map((theme, i) => (
            <span key={i} style={{
              fontSize: 11,
              padding: '3px 8px',
              borderRadius: 999,
              background: '#eef2ff',
              color: '#4f46e5',
              border: '1px solid #c7d2fe'
            }}>
              {theme}
            </span>
          ))}
        </div>
      )}

      {/* Page number */}
      {item.page_number && (
        <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8, textAlign: 'right' }}>
          Page {item.page_number}
        </div>
      )}
    </div>
  );
}

// By Type View
function ByTypeView({ evidenceData, evidenceTypes, getTypeIcon, getConfidenceColor }) {
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {evidenceTypes.map(type => {
        const items = evidenceData.aggregated_evidence.filter(e => e.type === type);
        return (
          <div key={type} style={{ marginBottom: 32 }}>
            <h3 style={{
              fontSize: 20,
              fontWeight: 700,
              marginBottom: 16,
              color: '#374151',
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              <span style={{ fontSize: 28 }}>{getTypeIcon(type)}</span>
              {type.replace('_', ' ').toUpperCase()}
              <span style={{
                fontSize: 14,
                fontWeight: 500,
                color: '#9ca3af',
                marginLeft: 8
              }}>
                ({items.length})
              </span>
            </h3>
            <div style={{ display: 'grid', gap: 16 }}>
              {items.slice(0, 10).map((item, idx) => (
                <EvidenceCard key={idx} item={item} getTypeIcon={getTypeIcon} getConfidenceColor={getConfidenceColor} />
              ))}
              {items.length > 10 && (
                <div style={{ textAlign: 'center', padding: 16, fontSize: 13, color: '#6b7280' }}>
                  + {items.length - 10} more {type} items
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// By Confidence View
function ByConfidenceView({ evidenceData, getConfidenceColor, getTypeIcon }) {
  const confidenceLevels = ['high', 'medium', 'low'];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {confidenceLevels.map(confidence => {
        const items = evidenceData.aggregated_evidence.filter(e => e.confidence === confidence);
        if (items.length === 0) return null;

        return (
          <div key={confidence} style={{ marginBottom: 32 }}>
            <h3 style={{
              fontSize: 20,
              fontWeight: 700,
              marginBottom: 16,
              color: getConfidenceColor(confidence),
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              {confidence === 'high' && '⭐'}
              {confidence === 'medium' && '📊'}
              {confidence === 'low' && '📝'}
              {confidence.toUpperCase()} CONFIDENCE
              <span style={{
                fontSize: 14,
                fontWeight: 500,
                color: '#9ca3af',
                marginLeft: 8
              }}>
                ({items.length})
              </span>
            </h3>
            <div style={{ display: 'grid', gap: 16 }}>
              {items.slice(0, 10).map((item, idx) => (
                <EvidenceCard key={idx} item={item} getTypeIcon={getTypeIcon} getConfidenceColor={getConfidenceColor} />
              ))}
              {items.length > 10 && (
                <div style={{ textAlign: 'center', padding: 16, fontSize: 13, color: '#6b7280' }}>
                  + {items.length - 10} more {confidence} confidence items
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Stats View
function StatsView({ evidenceData, evidenceTypes, getTypeIcon }) {
  const stats = {
    total: evidenceData.aggregated_evidence?.length || 0,
    byType: {},
    byConfidence: {
      high: evidenceData.aggregated_evidence?.filter(e => e.confidence === 'high').length || 0,
      medium: evidenceData.aggregated_evidence?.filter(e => e.confidence === 'medium').length || 0,
      low: evidenceData.aggregated_evidence?.filter(e => e.confidence === 'low').length || 0
    },
    themes: {}
  };

  // Count by type
  evidenceTypes.forEach(type => {
    stats.byType[type] = evidenceData.aggregated_evidence.filter(e => e.type === type).length;
  });

  // Count themes
  evidenceData.aggregated_evidence.forEach(e => {
    e.themes?.forEach(theme => {
      stats.themes[theme] = (stats.themes[theme] || 0) + 1;
    });
  });

  const topThemes = Object.entries(stats.themes)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Type Distribution */}
      <div style={{ marginBottom: 32 }}>
        <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16, color: '#374151' }}>
          📊 Evidence Distribution by Type
        </h3>
        <div style={{ display: 'grid', gap: 12 }}>
          {Object.entries(stats.byType)
            .sort((a, b) => b[1] - a[1])
            .map(([type, count]) => {
              const percentage = ((count / stats.total) * 100).toFixed(1);
              return (
                <div key={type} style={{
                  background: 'white',
                  borderRadius: 8,
                  padding: 16,
                  boxShadow: '0 1px 4px rgba(0,0,0,0.06)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, color: '#374151' }}>
                      {getTypeIcon(type)} {type.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: 14, color: '#6b7280' }}>
                      {count} ({percentage}%)
                    </span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, background: '#e5e7eb', overflow: 'hidden' }}>
                    <div style={{
                      width: `${percentage}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #667eea, #764ba2)',
                      transition: 'width 0.5s ease'
                    }} />
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Confidence Distribution */}
      <div style={{ marginBottom: 32 }}>
        <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16, color: '#374151' }}>
          ⭐ Confidence Level Distribution
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          {Object.entries(stats.byConfidence).map(([level, count]) => {
            const colors = {
              high: { bg: '#10b98120', border: '#10b981', text: '#10b981' },
              medium: { bg: '#f59e0b20', border: '#f59e0b', text: '#f59e0b' },
              low: { bg: '#6b728020', border: '#6b7280', text: '#6b7280' }
            };
            const color = colors[level];
            const percentage = ((count / stats.total) * 100).toFixed(1);

            return (
              <div key={level} style={{
                background: color.bg,
                border: `2px solid ${color.border}`,
                borderRadius: 12,
                padding: 20,
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 36, fontWeight: 700, color: color.text, marginBottom: 8 }}>
                  {count}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: color.text, textTransform: 'uppercase' }}>
                  {level}
                </div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
                  {percentage}% of total
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Themes */}
      {topThemes.length > 0 && (
        <div>
          <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16, color: '#374151' }}>
            🏷️ Top Themes
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {topThemes.map(([theme, count]) => (
              <span key={theme} style={{
                fontSize: 14,
                padding: '8px 16px',
                borderRadius: 999,
                background: '#eef2ff',
                color: '#4f46e5',
                border: '1px solid #c7d2fe',
                fontWeight: 600
              }}>
                {theme} <span style={{ opacity: 0.6 }}>×{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default EvidenceExtractor;
