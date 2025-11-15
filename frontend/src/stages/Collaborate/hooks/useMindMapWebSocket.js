// frontend/src/stages/Collaborate/hooks/useMindMapWebSocket.js
import { useEffect, useState, useCallback, useRef } from 'react';
import io from 'socket.io-client';
import axiosInstance from '../../../utils/axiosInstance';

export function useMindMapWebSocket(mindMapId, userId, username) {
  const [isConnected, setIsConnected] = useState(false);
  const [activeUsers, setActiveUsers] = useState([]);
  const [cursors, setCursors] = useState([]);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!mindMapId || !userId) {
      setIsConnected(false);
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      console.error('[MindMap] No authentication token found');
      setIsConnected(false);
      return;
    }

    console.log('[MindMap] Initializing WebSocket connection...');
    console.log('[MindMap] Mind Map ID:', mindMapId);
    console.log('[MindMap] User ID:', userId);

    // Use the same base URL as the API (without /api path) - matching DigitalDebate pattern
    const apiBaseUrl = axiosInstance.defaults.baseURL.replace('/api', '');
    console.log('[MindMap] Socket URL:', apiBaseUrl);

    // Initialize Socket.IO connection to /mindmap namespace
    const socket = io(`${apiBaseUrl}/mindmap`, {
      path: '/socket.io',  // Explicitly set the path for nginx proxy
      query: { token },  // Send authentication token
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
      withCredentials: true,  // Include credentials for CORS
    });

    socketRef.current = socket;

    // Connection handlers
    socket.on('connect', () => {
      console.log('[MindMap] WebSocket connected');
      setIsConnected(true);
      
      // Auto-join the mind map room when socket connects
      if (mindMapId && userId && username) {
        console.log('[MindMap] Auto-joining room:', mindMapId);
        console.log('[MindMap] User ID:', userId, 'Type:', typeof userId);
        socket.emit('join_mindmap', {
          mind_map_id: mindMapId,
          user_id: String(userId), // Ensure it's a string
          username: username,
        });
      }
    });

    socket.on('disconnect', () => {
      console.log('[MindMap] WebSocket disconnected');
      setIsConnected(false);
    });

    socket.on('error', (error) => {
      console.error('[MindMap] WebSocket error:', error);
    });

    socket.on('connect_error', (error) => {
      console.error('[MindMap] WebSocket connection error:', error.message);
      setIsConnected(false);
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`[MindMap] WebSocket reconnection attempt ${attemptNumber}`);
    });

    socket.on('reconnect_failed', () => {
      console.error('[MindMap] WebSocket reconnection failed after all attempts');
      setIsConnected(false);
    });

    // Collaboration event handlers
    socket.on('active_users', (data) => {
      console.log('[MindMap] Received active_users:', data.users);
      setActiveUsers(data.users || []);
    });

    socket.on('user_joined', (data) => {
      console.log(`[MindMap] User ${data.username} joined`, data);
      // Don't manually add to activeUsers - the backend will send updated active_users list
      // setActiveUsers((prev) => [...prev, data]); // REMOVED - causes duplicates
    });

    socket.on('user_left', (data) => {
      setActiveUsers((prev) => prev.filter((u) => u.user_id !== data.user_id));
      setCursors((prev) => prev.filter((c) => c.user_id !== data.user_id));
      console.log(`[MindMap] User ${data.username} left`);
    });

    socket.on('cursor_moved', (data) => {
      setCursors((prev) => {
        const existing = prev.findIndex((c) => c.user_id === data.user_id);
        if (existing !== -1) {
          const updated = [...prev];
          updated[existing] = { ...data.cursor, user_id: data.user_id, username: data.username };
          return updated;
        } else {
          return [...prev, { ...data.cursor, user_id: data.user_id, username: data.username }];
        }
      });
    });

    // Node event handlers
    socket.on('node_created', (data) => {
      // This will be handled by the parent component
      window.dispatchEvent(new CustomEvent('mindmap:node_created', { detail: data }));
    });

    socket.on('node_updated', (data) => {
      window.dispatchEvent(new CustomEvent('mindmap:node_updated', { detail: data }));
    });

    socket.on('node_deleted', (data) => {
      window.dispatchEvent(new CustomEvent('mindmap:node_deleted', { detail: data }));
    });

    // Connection event handlers
    socket.on('connection_created', (data) => {
      window.dispatchEvent(new CustomEvent('mindmap:connection_created', { detail: data }));
    });

    socket.on('connection_deleted', (data) => {
      window.dispatchEvent(new CustomEvent('mindmap:connection_deleted', { detail: data }));
    });

    // Comment event handlers
    socket.on('comment_added', (data) => {
      window.dispatchEvent(new CustomEvent('mindmap:comment_added', { detail: data }));
    });

    socket.on('comment_resolved', (data) => {
      window.dispatchEvent(new CustomEvent('mindmap:comment_resolved', { detail: data }));
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [mindMapId, userId]);

  const connectToMindMap = useCallback(() => {
    if (socketRef.current && mindMapId && userId) {
      console.log('[MindMap] Manually joining room:', mindMapId);
      console.log('[MindMap] Socket connected?', socketRef.current.connected);
      
      if (socketRef.current.connected) {
        socketRef.current.emit('join_mindmap', {
          mind_map_id: mindMapId,
          user_id: userId,
          username: username,
        });
      } else {
        console.log('[MindMap] Socket not connected yet, waiting for auto-join on connect');
      }
    } else {
      console.log('[MindMap] Cannot join - missing:', {
        hasSocket: !!socketRef.current,
        mindMapId,
        userId
      });
    }
  }, [mindMapId, userId, username]);

  const disconnectFromMindMap = useCallback(() => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('leave_mindmap', {
        mind_map_id: mindMapId,
      });
    }
  }, [mindMapId]);

  const broadcastNodeCreated = useCallback((node) => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('node_created', {
        mind_map_id: mindMapId,
        node: node,
        created_by: userId,
      });
    }
  }, [mindMapId, userId]);

  const broadcastNodeUpdated = useCallback((nodeId, updates) => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('node_updated', {
        mind_map_id: mindMapId,
        node_id: nodeId,
        updates: updates,
        updated_by: userId,
      });
    }
  }, [mindMapId, userId]);

  const broadcastNodeDeleted = useCallback((nodeId) => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('node_deleted', {
        mind_map_id: mindMapId,
        node_id: nodeId,
        deleted_by: userId,
      });
    }
  }, [mindMapId, userId]);

  const broadcastConnectionCreated = useCallback((connection) => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('connection_created', {
        mind_map_id: mindMapId,
        connection: connection,
        created_by: userId,
      });
    }
  }, [mindMapId, userId]);

  const broadcastConnectionDeleted = useCallback((connectionId) => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('connection_deleted', {
        mind_map_id: mindMapId,
        connection_id: connectionId,
        deleted_by: userId,
      });
    }
  }, [mindMapId, userId]);

  const broadcastCursorMove = useCallback((cursor) => {
    if (socketRef.current && mindMapId) {
      socketRef.current.emit('cursor_moved', {
        mind_map_id: mindMapId,
        user_id: userId,
        username: username,
        cursor: cursor,
      });
    }
  }, [mindMapId, userId, username]);

  return {
    isConnected,
    activeUsers,
    cursors,
    connectToMindMap,
    disconnectFromMindMap,
    broadcastNodeCreated,
    broadcastNodeUpdated,
    broadcastNodeDeleted,
    broadcastConnectionCreated,
    broadcastConnectionDeleted,
    broadcastCursorMove,
  };
}
