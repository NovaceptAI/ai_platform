// frontend/src/stages/Collaborate/components/CustomNode.js
import React, { useState, useCallback, useEffect } from 'react';
import { Handle, Position } from 'reactflow';
import { FaTrash, FaLightbulb, FaPalette } from 'react-icons/fa';

const CustomNode = ({ data, id, selected }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [content, setContent] = useState(data.content || data.label || '');

  // Sync content when data changes from remote updates
  useEffect(() => {
    if (!isEditing) {
      const newContent = data.content || data.label || '';
      if (newContent !== content) {
        console.log('[CustomNode] Syncing remote update:', { id, newContent, oldContent: content });
        setContent(newContent);
      }
    }
  }, [data.content, data.label, isEditing, content, id]);
  const [showColorPicker, setShowColorPicker] = useState(false);

  const colors = [
    '#667eea', '#764ba2', '#f093fb', '#4facfe',
    '#43e97b', '#fa709a', '#feca57', '#ff6b6b',
    '#48dbfb', '#1dd1a1', '#ee5a6f', '#c44569'
  ];

  const handleContentChange = (e) => {
    setContent(e.target.value);
  };

  const handleBlur = () => {
    setIsEditing(false);
    if (data.onUpdate && content !== data.content) {
      data.onUpdate(id, { content, label: content });
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleBlur();
    } else if (e.key === 'Escape') {
      setContent(data.content || data.label || '');
      setIsEditing(false);
    }
  };

  const handleColorChange = (color) => {
    if (data.onUpdate) {
      data.onUpdate(id, { color });
    }
    setShowColorPicker(false);
  };

  const handleDelete = () => {
    if (data.onDelete && window.confirm('Delete this node?')) {
      data.onDelete(id);
    }
  };

  const handleExpandWithAI = () => {
    if (data.onExpand) {
      data.onExpand(id, content);
    }
  };

  const nodeStyle = {
    background: data.color || '#667eea',
    border: selected ? '2px solid #4f46e5' : '2px solid transparent',
    borderRadius: data.shape === 'circle' ? '50%' : '12px',
    padding: '16px 20px',
    minWidth: '150px',
    maxWidth: '250px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '500',
    boxShadow: selected
      ? '0 10px 30px rgba(79, 70, 229, 0.3)'
      : '0 4px 15px rgba(0, 0, 0, 0.2)',
    transition: 'all 0.2s ease',
    position: 'relative',
  };

  return (
    <div style={nodeStyle} className="custom-node">
      {/* Connection Handles */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#fff', width: 10, height: 10 }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#fff', width: 10, height: 10 }}
      />
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#fff', width: 10, height: 10 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#fff', width: 10, height: 10 }}
      />

      {/* Node Content */}
      {isEditing ? (
        <textarea
          value={content}
          onChange={handleContentChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          autoFocus
          style={{
            width: '100%',
            minHeight: '40px',
            background: 'rgba(255, 255, 255, 0.9)',
            border: 'none',
            borderRadius: '6px',
            padding: '8px',
            color: '#333',
            fontSize: '14px',
            fontFamily: 'inherit',
            resize: 'vertical',
          }}
        />
      ) : (
        <div
          onDoubleClick={() => setIsEditing(true)}
          style={{
            cursor: 'text',
            wordBreak: 'break-word',
            userSelect: 'none',
          }}
        >
          {content}
        </div>
      )}

      {/* Toolbar (shown on hover/select) */}
      {selected && (
        <div
          style={{
            position: 'absolute',
            top: '-35px',
            right: '0',
            display: 'flex',
            gap: '4px',
            background: 'rgba(0, 0, 0, 0.8)',
            padding: '4px 8px',
            borderRadius: '6px',
          }}
        >
          <button
            onClick={() => setShowColorPicker(!showColorPicker)}
            title="Change Color"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#fff',
              cursor: 'pointer',
              padding: '4px 8px',
              fontSize: '14px',
            }}
          >
            <FaPalette />
          </button>
          <button
            onClick={handleExpandWithAI}
            title="Expand with AI"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#feca57',
              cursor: 'pointer',
              padding: '4px 8px',
              fontSize: '14px',
            }}
          >
            <FaLightbulb />
          </button>
          <button
            onClick={handleDelete}
            title="Delete"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ff6b6b',
              cursor: 'pointer',
              padding: '4px 8px',
              fontSize: '14px',
            }}
          >
            <FaTrash />
          </button>
        </div>
      )}

      {/* Color Picker Dropdown */}
      {showColorPicker && (
        <div
          style={{
            position: 'absolute',
            top: '-75px',
            right: '0',
            background: '#fff',
            padding: '8px',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '6px',
            zIndex: 1000,
          }}
        >
          {colors.map((color) => (
            <div
              key={color}
              onClick={() => handleColorChange(color)}
              style={{
                width: '24px',
                height: '24px',
                background: color,
                borderRadius: '4px',
                cursor: 'pointer',
                border: data.color === color ? '2px solid #000' : 'none',
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default CustomNode;
