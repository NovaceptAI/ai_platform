import React from 'react';

const ArtifactsList = ({ artifacts, isLoading, onSelectArtifact, onRefresh, onBack }) => {
  const getStatusBadge = (status) => {
    const badges = {
      pending: { icon: '⏳', class: 'status-pending', label: 'Pending' },
      processing: { icon: '⚙️', class: 'status-processing', label: 'Processing' },
      completed: { icon: '✓', class: 'status-completed', label: 'Completed' },
      failed: { icon: '✗', class: 'status-failed', label: 'Failed' }
    };
    return badges[status] || badges.pending;
  };

  const getArtifactIcon = (type) => {
    return type === 'flashcards' ? '🃏' : '📊';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="artifacts-list loading">
        <div className="loading-spinner"></div>
        <p>Loading artifacts...</p>
      </div>
    );
  }

  return (
    <div className="artifacts-list">
      {/* Header */}
      <div className="artifacts-header">
        <button className="refresh-btn" onClick={onRefresh} title="Refresh">
          🔄
        </button>
      </div>

      {/* List */}
      <div className="artifacts-items">
        {artifacts.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📚</div>
            <h4>No Artifacts Yet</h4>
            <p>Generate flashcards or presentations to see them here</p>
            <button className="btn-primary" onClick={onBack}>
              Create First Artifact
            </button>
          </div>
        ) : (
          artifacts.map(artifact => {
            const badge = getStatusBadge(artifact.status);
            const icon = getArtifactIcon(artifact.artifact_type);

            return (
              <div
                key={artifact.id}
                className={`artifact-item ${artifact.status}`}
                onClick={() => artifact.status === 'completed' && onSelectArtifact(artifact)}
                style={{ cursor: artifact.status === 'completed' ? 'pointer' : 'default' }}
              >
                <div className="artifact-icon">{icon}</div>
                <div className="artifact-details">
                  <h5 className="artifact-title">{artifact.title}</h5>
                  <div className="artifact-meta">
                    <span className="artifact-type">
                      {artifact.artifact_type}
                    </span>
                    <span className="artifact-date">
                      {formatDate(artifact.created_at)}
                    </span>
                  </div>
                  {artifact.error_message && (
                    <p className="artifact-error">{artifact.error_message}</p>
                  )}
                </div>
                <div className={`artifact-status ${badge.class}`}>
                  <span className="status-icon">{badge.icon}</span>
                  <span className="status-label">{badge.label}</span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Summary */}
      {artifacts.length > 0 && (
        <div className="artifacts-summary">
          <div className="summary-stat">
            <span className="summary-value">{artifacts.length}</span>
            <span className="summary-label">Total</span>
          </div>
          <div className="summary-stat">
            <span className="summary-value">
              {artifacts.filter(a => a.artifact_type === 'flashcards').length}
            </span>
            <span className="summary-label">Flashcards</span>
          </div>
          <div className="summary-stat">
            <span className="summary-value">
              {artifacts.filter(a => a.artifact_type === 'presentation').length}
            </span>
            <span className="summary-label">Presentations</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ArtifactsList;
