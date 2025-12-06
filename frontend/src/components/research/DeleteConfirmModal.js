import React from 'react';

const DeleteConfirmModal = ({ isOpen, onClose, onConfirm, title, message, itemType }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title || 'Confirm Delete'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="modal-icon warning">⚠️</div>
          <p>{message || 'Are you sure you want to delete this item? This action cannot be undone.'}</p>
        </div>
        
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-danger" onClick={onConfirm}>
            Delete {itemType || 'Item'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DeleteConfirmModal;
