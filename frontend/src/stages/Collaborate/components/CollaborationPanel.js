// frontend/src/stages/Collaborate/components/CollaborationPanel.js
import React, { useState, useEffect } from 'react';
import { FaTimes, FaUsers, FaComments, FaUserPlus } from 'react-icons/fa';
import axiosInstance from '../../../utils/axiosInstance';

const CollaborationPanel = ({ mindMapId, activeUsers, onClose }) => {
  const [activeTab, setActiveTab] = useState('users'); // 'users', 'chat', 'comments'
  const [collaborators, setCollaborators] = useState([]);
  const [comments, setComments] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);

  useEffect(() => {
    if (mindMapId) {
      fetchCollaborators();
      fetchComments();
    }
  }, [mindMapId]);

  const fetchCollaborators = async () => {
    try {
      const response = await axiosInstance.get(`/stages/collaborate/mind_map/${mindMapId}/collaborators`);
      setCollaborators(response.data.collaborators || []);
    } catch (err) {
      console.error('Error fetching collaborators:', err);
    }
  };

  const fetchComments = async () => {
    try {
      const response = await axiosInstance.get(`/stages/collaborate/mind_map/${mindMapId}/comments`);
      setComments(response.data.comments || []);
    } catch (err) {
      console.error('Error fetching comments:', err);
    }
  };

  const handleAddCollaborator = async () => {
    if (!inviteEmail.trim()) return;

    try {
      await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/collaborators`, {
        email: inviteEmail,
        permission_level: 'edit',
      });
      setInviteEmail('');
      setShowInviteModal(false);
      fetchCollaborators();
    } catch (err) {
      alert('Failed to add collaborator');
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;

    try {
      const response = await axiosInstance.post(`/stages/collaborate/mind_map/${mindMapId}/comments`, {
        content: newComment,
        node_id: null, // General comment, not attached to node
      });
      setComments([...comments, response.data.comment]);
      setNewComment('');
    } catch (err) {
      alert('Failed to add comment');
    }
  };

  const handleResolveComment = async (commentId) => {
    try {
      await axiosInstance.put(`/stages/collaborate/mind_map/${mindMapId}/comments/${commentId}/resolve`);
      setComments(comments.map((c) => (c.id === commentId ? { ...c, is_resolved: true } : c)));
    } catch (err) {
      alert('Failed to resolve comment');
    }
  };

  return (
    <div className="collaboration-panel">
      <div className="panel-header">
        <h3>Collaboration</h3>
        <button onClick={onClose} className="close-btn">
          <FaTimes />
        </button>
      </div>

      {/* Tabs */}
      <div className="panel-tabs">
        <button
          onClick={() => setActiveTab('users')}
          className={activeTab === 'users' ? 'tab-active' : ''}
        >
          <FaUsers /> Users ({activeUsers.length})
        </button>
        <button
          onClick={() => setActiveTab('comments')}
          className={activeTab === 'comments' ? 'tab-active' : ''}
        >
          <FaComments /> Comments ({comments.filter((c) => !c.is_resolved).length})
        </button>
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="panel-content">
          <button onClick={() => setShowInviteModal(true)} className="btn-primary-small">
            <FaUserPlus /> Invite Collaborator
          </button>

          <div className="users-list">
            <h4>Online Now</h4>
            {activeUsers.length === 0 ? (
              <p className="empty-state">No other users online</p>
            ) : (
              activeUsers.map((user) => (
                <div key={user.session_id} className="user-item">
                  <div className="user-avatar" style={{ background: '#43e97b' }}>
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <span>{user.username}</span>
                  <span className="status-dot online"></span>
                </div>
              ))
            )}

            <h4>All Collaborators</h4>
            {collaborators.map((collab) => (
              <div key={collab.id} className="user-item">
                <div className="user-avatar" style={{ background: collab.is_online ? '#43e97b' : '#95a5a6' }}>
                  {collab.username?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span>{collab.username || collab.email}</span>
                <span className="permission-badge">{collab.permission_level}</span>
                {collab.is_online && <span className="status-dot online"></span>}
              </div>
            ))}
          </div>

          {/* Invite Modal */}
          {showInviteModal && (
            <div className="modal-overlay" onClick={() => setShowInviteModal(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h3>Invite Collaborator</h3>
                <input
                  type="email"
                  placeholder="Enter email address..."
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  autoFocus
                />
                <div className="modal-actions">
                  <button onClick={() => setShowInviteModal(false)} className="btn-ghost">
                    Cancel
                  </button>
                  <button onClick={handleAddCollaborator} className="btn-primary">
                    Send Invite
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Comments Tab */}
      {activeTab === 'comments' && (
        <div className="panel-content">
          <div className="comment-input-section">
            <textarea
              placeholder="Add a comment..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              rows={3}
            />
            <button onClick={handleAddComment} className="btn-primary-small">
              Post Comment
            </button>
          </div>

          <div className="comments-list">
            {comments.length === 0 ? (
              <p className="empty-state">No comments yet</p>
            ) : (
              comments.map((comment) => (
                <div
                  key={comment.id}
                  className={`comment-item ${comment.is_resolved ? 'resolved' : ''}`}
                >
                  <div className="comment-header">
                    <strong>{comment.author_name || 'User'}</strong>
                    <span className="comment-time">
                      {new Date(comment.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p>{comment.content}</p>
                  {!comment.is_resolved && (
                    <button
                      onClick={() => handleResolveComment(comment.id)}
                      className="btn-resolve"
                    >
                      Resolve
                    </button>
                  )}
                  {comment.is_resolved && <span className="resolved-badge">✓ Resolved</span>}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CollaborationPanel;
