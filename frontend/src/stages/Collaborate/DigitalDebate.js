import React, { useState, useEffect, useRef } from 'react';
import './DigitalDebate.css';
import axiosInstance from '../../utils/axiosInstance';
import io from 'socket.io-client';
import {
    MessageSquare, Users, Trophy, TrendingUp, Send,
    Clock, Play, Pause, SkipForward, CheckCircle,
    AlertCircle, ThumbsUp, ThumbsDown, FileText,
    BarChart3, Brain, Search, Filter, Plus, X
} from 'lucide-react';

// Helper function to get username from JWT token
const getUsernameFromToken = () => {
    try {
        const token = localStorage.getItem('token');
        if (!token) return 'User';
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.username || 'User';
    } catch (e) {
        console.error('Error decoding token:', e);
        return 'User';
    }
};

// Helper function to get user ID from JWT token
const getUserIdFromToken = () => {
    try {
        const token = localStorage.getItem('token');
        if (!token) return null;
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.sub || payload.user_id || null;
    } catch (e) {
        console.error('Error decoding token:', e);
        return null;
    }
};

function DigitalDebate() {
    // Tab state
    const [activeTab, setActiveTab] = useState('browse'); // browse, create, debate, results

    // Create debate state
    const [motion, setMotion] = useState('');
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState('politics');
    const [format, setFormat] = useState('parliamentary');
    const [settings, setSettings] = useState({
        allow_audience: true,
        enable_voice: false,
        enable_video: false,
        auto_fact_check: true,
        ai_moderation: true,
        argument_analysis: true,
        public_debate: true  // Changed to true so debates are discoverable by default
    });

    // Browse debates state
    const [debates, setDebates] = useState([]);
    const [publicDebates, setPublicDebates] = useState([]);
    const [isLoadingDebates, setIsLoadingDebates] = useState(false);
    const [filterStatus, setFilterStatus] = useState('all'); // all, waiting, in_progress, completed
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('all');

    // Active debate state
    const [currentDebate, setCurrentDebate] = useState(null);
    const [currentParticipant, setCurrentParticipant] = useState(null);
    const [debateMessages, setDebateMessages] = useState([]);
    const [participants, setParticipants] = useState([]);

    // Message input state
    const [messageInput, setMessageInput] = useState('');
    const [messageType, setMessageType] = useState('argument'); // argument, rebuttal, chat
    const [isTyping, setIsTyping] = useState(false);
    const [typingUsers, setTypingUsers] = useState([]);

    // WebSocket
    const [socket, setSocket] = useState(null);
    const [isConnected, setIsConnected] = useState(false);

    // Error and loading
    const [error, setError] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [isJoining, setIsJoining] = useState(false);

    // Refs
    const messagesEndRef = useRef(null);
    const typingTimeoutRef = useRef(null);

    // Categories and formats
    const categories = [
        { id: 'politics', name: 'Politics & Policy', icon: '🏛️' },
        { id: 'science', name: 'Science & Technology', icon: '🔬' },
        { id: 'philosophy', name: 'Philosophy & Ethics', icon: '🤔' },
        { id: 'education', name: 'Education', icon: '📚' },
        { id: 'environment', name: 'Environment', icon: '🌍' },
        { id: 'economics', name: 'Economics', icon: '💰' }
    ];

    const formats = [
        { id: 'parliamentary', name: 'Parliamentary', desc: 'Structured rounds with opening, rebuttal, closing' },
        { id: 'lincoln_douglas', name: 'Lincoln-Douglas', desc: '1v1 value debate' },
        { id: 'public_forum', name: 'Public Forum', desc: 'Team-based accessible format' },
        { id: 'free_form', name: 'Free Form', desc: 'Unstructured discussion' }
    ];

    // Fetch debates on mount and restore active debate
    useEffect(() => {
        fetchMyDebates();
        fetchPublicDebates();

        // Restore active debate from localStorage after refresh
        const savedDebateId = localStorage.getItem('active_debate_id');
        const savedParticipantId = localStorage.getItem('active_participant_id');

        if (savedDebateId && savedParticipantId) {
            // Attempt to reconnect to the debate
            reconnectToDebate(savedDebateId, savedParticipantId);
        }
    }, []);

    // WebSocket connection
    useEffect(() => {
        if (currentDebate && currentParticipant) {
            initializeWebSocket();
        }

        return () => {
            if (socket) {
                socket.disconnect();
            }
        };
    }, [currentDebate, currentParticipant]);

    // Auto-scroll messages
    useEffect(() => {
        scrollToBottom();
    }, [debateMessages]);

    const initializeWebSocket = () => {
        // Properly cleanup old socket before creating new one
        if (socket) {
            if (socket.connected) {
                console.log('WebSocket already connected, skipping initialization');
                return;
            } else {
                // Socket exists but disconnected - clean it up
                console.log('Cleaning up disconnected socket before reconnecting');
                socket.removeAllListeners();
                socket.disconnect();
            }
        }

        const token = localStorage.getItem('token');  // Use 'token' not 'access_token'
        if (!token) {
            console.error('No authentication token found. User must be logged in.');
            setError('Authentication required. Please log in.');
            return;
        }

        if (!currentDebate || !currentParticipant) {
            console.error('Cannot initialize WebSocket - missing debate or participant info');
            return;
        }

        console.log('Initializing WebSocket connection...');

        // Use the same base URL as the API (without /api path)
        const apiBaseUrl = axiosInstance.defaults.baseURL.replace('/api', '');

        const newSocket = io(`${apiBaseUrl}/collaborate`, {
            path: '/socket.io',
            query: { token },
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000
        });

        newSocket.on('connect', () => {
            console.log('WebSocket connected');
            setIsConnected(true);

            // Join debate room
            newSocket.emit('join_debate', {
                debate_id: currentDebate.id,
                participant_id: currentParticipant.id
            });
        });

        newSocket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            setIsConnected(false);
        });

        newSocket.on('debate_joined', (data) => {
            console.log('Joined debate:', data);
            setDebateMessages([]); // Will fetch via API
            setParticipants(data.current_participants || []);
            // Fetch messages for this specific debate
            if (data.debate_id) {
                fetchDebateMessagesById(data.debate_id);
            }
        });

        newSocket.on('message_received', (data) => {
            setDebateMessages(prev => [...prev, data]);
        });

        newSocket.on('participant_joined', (data) => {
            setParticipants(prev => {
                // Check if participant already exists to prevent duplicates
                const exists = prev.some(p => p.participant_id === data.participant_id);
                if (exists) {
                    console.log('Participant already in list, skipping duplicate:', data.participant_id);
                    return prev;
                }
                console.log('Adding new participant:', data.participant_id);
                return [...prev, data];
            });
        });

        newSocket.on('participant_left', (data) => {
            setParticipants(prev => prev.filter(p => p.participant_id !== data.participant_id));
        });

        newSocket.on('typing_status', (data) => {
            if (data.is_typing) {
                setTypingUsers(prev => [...prev.filter(u => u !== data.display_name), data.display_name]);
            } else {
                setTypingUsers(prev => prev.filter(u => u !== data.display_name));
            }
        });

        newSocket.on('round_advanced', (data) => {
            setCurrentDebate(prev => ({ ...prev, current_round: data.current_round }));
        });

        newSocket.on('debate_update', (data) => {
            console.log('Debate update received:', data.type);
            if (data.type === 'debate_started') {
                // Update debate status to in_progress for all participants
                setCurrentDebate(prev => ({
                    ...prev,
                    status: 'in_progress',
                    actual_start: data.debate.actual_start,
                    current_round: data.debate.current_round
                }));
                console.log('Debate started! Status updated to in_progress');
            } else if (data.type === 'debate_ended') {
                setCurrentDebate(prev => ({ ...prev, status: 'completed', results: data.results }));
                setActiveTab('results');
            }
        });

        newSocket.on('error', (data) => {
            console.error('WebSocket error:', data);
            setError(data?.message || 'WebSocket connection error');
        });

        newSocket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error.message);
            setIsConnected(false);
        });

        newSocket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`WebSocket reconnection attempt ${attemptNumber}`);
        });

        newSocket.on('reconnect_failed', () => {
            console.error('WebSocket reconnection failed after all attempts');
            setError('Failed to reconnect to debate. Please refresh the page.');
            setIsConnected(false);
        });

        setSocket(newSocket);
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchMyDebates = async () => {
        setIsLoadingDebates(true);
        try {
            const response = await axiosInstance.get('/stages/collaborate/debate/my-debates');
            setDebates(response.data.debates || []);
        } catch (err) {
            console.error('Error fetching debates:', err);
        } finally {
            setIsLoadingDebates(false);
        }
    };

    const fetchPublicDebates = async () => {
        try {
            const response = await axiosInstance.get('/stages/collaborate/debate/public');
            setPublicDebates(response.data.debates || []);
        } catch (err) {
            console.error('Error fetching public debates:', err);
        }
    };

    const fetchDebateMessages = async () => {
        if (!currentDebate) return;
        await fetchDebateMessagesById(currentDebate.id);
    };

    const fetchDebateMessagesById = async (debateId) => {
        try {
            const response = await axiosInstance.get(`/stages/collaborate/debate/${debateId}/messages`);
            setDebateMessages(response.data.messages || []);
            console.log(`Fetched ${response.data.messages?.length || 0} messages for debate ${debateId}`);
        } catch (err) {
            console.error('Error fetching messages:', err);
        }
    };

    const reconnectToDebate = async (debateId, participantId) => {
        console.log('Attempting to reconnect to debate:', debateId);
        try {
            // Fetch the debate details
            const debateResponse = await axiosInstance.get(`/stages/collaborate/debate/${debateId}`);
            const debate = debateResponse.data.debate;

            // Find the participant
            const participant = debate.participants?.find(p => p.id === participantId);

            if (!participant) {
                console.error('Participant not found in debate');
                localStorage.removeItem('active_debate_id');
                localStorage.removeItem('active_participant_id');
                return;
            }

            // Restore the debate state
            setCurrentDebate(debate);
            setCurrentParticipant(participant);
            setActiveTab('debate');

            // Fetch messages
            const messagesResponse = await axiosInstance.get(`/stages/collaborate/debate/${debateId}/messages`);
            setDebateMessages(messagesResponse.data.messages || []);

            console.log('Successfully reconnected to debate');
        } catch (err) {
            console.error('Error reconnecting to debate:', err);
            // Clear invalid debate data
            localStorage.removeItem('active_debate_id');
            localStorage.removeItem('active_participant_id');
            setError('Failed to reconnect to debate. It may have ended.');
        }
    };

    const saveDebateState = (debate, participant) => {
        // Save to localStorage for reconnection after refresh
        if (debate && participant) {
            localStorage.setItem('active_debate_id', debate.id);
            localStorage.setItem('active_participant_id', participant.id);
        }
    };

    const clearDebateState = () => {
        localStorage.removeItem('active_debate_id');
        localStorage.removeItem('active_participant_id');
    };

    const handleCreateDebate = async () => {
        setError('');

        if (motion.trim().length < 10) {
            setError('Motion must be at least 10 characters');
            return;
        }

        setIsCreating(true);

        try {
            const username = getUsernameFromToken();
            const response = await axiosInstance.post('/stages/collaborate/debate/create', {
                motion: motion.trim(),
                description: description.trim(),
                category,
                format,
                settings,
                creator_role: 'proposition',
                display_name: username
            });

            const debate = response.data.debate;
            const participant = debate.participants[0];

            setCurrentDebate(debate);
            setCurrentParticipant(participant);
            setActiveTab('debate');

            // Save state for reconnection after refresh
            saveDebateState(debate, participant);

            await fetchMyDebates();
        } catch (err) {
            console.error('Error creating debate:', err);
            setError(err.response?.data?.error || 'Failed to create debate');
        } finally {
            setIsCreating(false);
        }
    };

    const handleJoinDebate = async (debate, role = 'opposition') => {
        if (isJoining) {
            console.log('Already joining a debate, ignoring duplicate request');
            return;
        }

        setError('');
        setIsJoining(true);

        try {
            const username = getUsernameFromToken();
            const response = await axiosInstance.post(`/stages/collaborate/debate/${debate.id}/join`, {
                role,
                display_name: username
            });

            const joinedDebate = response.data.debate;
            const participant = response.data.participant;

            setCurrentDebate(joinedDebate);
            setCurrentParticipant(participant);
            setActiveTab('debate');

            // Save state for reconnection after refresh
            saveDebateState(joinedDebate, participant);
        } catch (err) {
            console.error('Error joining debate:', err);
            setError(err.response?.data?.error || 'Failed to join debate');
        } finally {
            setIsJoining(false);
        }
    };

    const handleStartDebate = async () => {
        if (!currentDebate) return;

        try {
            const response = await axiosInstance.post(`/stages/collaborate/debate/${currentDebate.id}/start`);
            setCurrentDebate(response.data.debate);
        } catch (err) {
            console.error('Error starting debate:', err);
            setError(err.response?.data?.error || 'Failed to start debate');
        }
    };

    const handleEndDebate = async () => {
        if (!currentDebate) return;

        try {
            const response = await axiosInstance.post(`/stages/collaborate/debate/${currentDebate.id}/end`);
            setCurrentDebate(response.data.debate);
            setActiveTab('results');

            // Clear saved state since debate has ended
            clearDebateState();
        } catch (err) {
            console.error('Error ending debate:', err);
            setError(err.response?.data?.error || 'Failed to end debate');
        }
    };

    const handleLeaveDebate = () => {
        // Disconnect WebSocket
        if (socket) {
            socket.disconnect();
        }

        // Clear debate state
        setCurrentDebate(null);
        setCurrentParticipant(null);
        setDebateMessages([]);
        setParticipants([]);
        setIsConnected(false);
        setActiveTab('browse');

        // Clear saved state
        clearDebateState();
    };

    const handleManualReconnect = async () => {
        console.log('Manual reconnect requested');

        // Check if we have saved debate state
        const savedDebateId = localStorage.getItem('active_debate_id');
        const savedParticipantId = localStorage.getItem('active_participant_id');

        if (savedDebateId && savedParticipantId && !currentDebate) {
            // No current debate loaded - reconnect from localStorage
            console.log('Reconnecting from localStorage:', savedDebateId);
            await reconnectToDebate(savedDebateId, savedParticipantId);
        } else if (currentDebate && currentParticipant) {
            // Already have debate loaded - just reconnect WebSocket
            console.log('Reconnecting WebSocket for current debate');
            if (socket) {
                socket.disconnect();
                setSocket(null);
            }
            setIsConnected(false);

            // The useEffect will trigger initializeWebSocket automatically
            // when socket becomes null
            setTimeout(() => {
                initializeWebSocket();
            }, 100);
        } else {
            console.error('Cannot reconnect - no debate information available');
            setError('Cannot reconnect. Please select a debate first.');
        }
    };

    const handleDeleteDebate = async (debateId) => {
        if (!window.confirm('Are you sure you want to delete this debate? This action cannot be undone.')) {
            return;
        }

        try {
            await axiosInstance.delete(`/stages/collaborate/debate/${debateId}`);

            // Clear saved state if this was the active debate
            const savedDebateId = localStorage.getItem('active_debate_id');
            if (savedDebateId === debateId) {
                clearDebateState();
                setCurrentDebate(null);
                setCurrentParticipant(null);
            }

            // Refresh the debate list
            await fetchMyDebates();

            console.log('Debate deleted successfully');
        } catch (err) {
            console.error('Error deleting debate:', err);
            setError(err.response?.data?.error || 'Failed to delete debate');
        }
    };

    const handleSendMessage = () => {
        if (!messageInput.trim() || !socket || !currentDebate || !currentParticipant) return;

        socket.emit('debate_message', {
            debate_id: currentDebate.id,
            participant_id: currentParticipant.id,
            message_type: messageType,
            content: messageInput.trim()
        });

        setMessageInput('');
        setIsTyping(false);
    };

    const handleTyping = (e) => {
        setMessageInput(e.target.value);

        if (!socket || !currentDebate || !currentParticipant) return;

        if (!isTyping) {
            setIsTyping(true);
            socket.emit('typing_indicator', {
                debate_id: currentDebate.id,
                participant_id: currentParticipant.id,
                is_typing: true
            });
        }

        clearTimeout(typingTimeoutRef.current);
        typingTimeoutRef.current = setTimeout(() => {
            setIsTyping(false);
            socket.emit('typing_indicator', {
                debate_id: currentDebate.id,
                participant_id: currentParticipant.id,
                is_typing: false
            });
        }, 2000);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const getStatusBadge = (status) => {
        const badges = {
            created: { color: 'bg-gray-100 text-gray-700', text: 'Created' },
            waiting: { color: 'bg-yellow-100 text-yellow-700', text: 'Waiting' },
            ready: { color: 'bg-blue-100 text-blue-700', text: 'Ready' },
            in_progress: { color: 'bg-green-100 text-green-700', text: 'In Progress' },
            completed: { color: 'bg-purple-100 text-purple-700', text: 'Completed' }
        };

        const badge = badges[status] || badges.created;
        return <span className={`badge ${badge.color}`}>{badge.text}</span>;
    };

    const getRoleBadge = (role) => {
        const badges = {
            proposition: 'badge-blue',
            opposition: 'badge-red',
            moderator: 'badge-purple',
            audience: 'badge-gray'
        };

        return <span className={`badge ${badges[role] || badges.audience}`}>{role}</span>;
    };

    const getMessageTypeIcon = (type) => {
        switch (type) {
            case 'opening': return <FileText size={16} />;
            case 'argument': return <Brain size={16} />;
            case 'rebuttal': return <AlertCircle size={16} />;
            case 'closing': return <CheckCircle size={16} />;
            default: return <MessageSquare size={16} />;
        }
    };

    // Filter debates based on status, search query, and category
    const filteredDebates = debates.filter(d => {
        const matchesStatus = filterStatus === 'all' || d.status === filterStatus;
        const matchesSearch = searchQuery === '' ||
            d.motion.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (d.description && d.description.toLowerCase().includes(searchQuery.toLowerCase()));
        const matchesCategory = selectedCategory === 'all' || d.category === selectedCategory;

        return matchesStatus && matchesSearch && matchesCategory;
    });

    // Filter public debates - exclude debates where user is already a participant
    const currentUserId = getUserIdFromToken();
    const filteredPublicDebates = publicDebates.filter(d => {
        const matchesSearch = searchQuery === '' ||
            d.motion.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory = selectedCategory === 'all' || d.category === selectedCategory;

        // Exclude debates where current user is a participant
        const isParticipant = d.participants?.some(p => p.user_id === currentUserId);

        return matchesSearch && matchesCategory && !isParticipant;
    });

    return (
        <div className="digital-debate-container">
            {/* Header */}
            <div className="debate-header">
                <h1><MessageSquare className="inline-icon" /> Digital Debate Platform</h1>
                <p>AI-assisted structured debates for learning and collaboration</p>
            </div>

            {/* Tabs */}
            <div className="debate-tabs">
                <button
                    className={activeTab === 'browse' ? 'active' : ''}
                    onClick={() => setActiveTab('browse')}
                >
                    <Search size={18} /> Browse Debates
                </button>
                <button
                    className={activeTab === 'create' ? 'active' : ''}
                    onClick={() => setActiveTab('create')}
                >
                    <Plus size={18} /> Create Debate
                </button>
                {currentDebate && (
                    <button
                        className={activeTab === 'debate' ? 'active' : ''}
                        onClick={() => setActiveTab('debate')}
                    >
                        <MessageSquare size={18} /> Active Debate
                    </button>
                )}
                {currentDebate?.status === 'completed' && (
                    <button
                        className={activeTab === 'results' ? 'active' : ''}
                        onClick={() => setActiveTab('results')}
                    >
                        <Trophy size={18} /> Results
                    </button>
                )}
            </div>

            {/* Error Message */}
            {error && (
                <div className="error-message">
                    <AlertCircle size={18} />
                    <span>{error}</span>
                    <button onClick={() => setError('')}><X size={16} /></button>
                </div>
            )}

            {/* Browse Tab */}
            {activeTab === 'browse' && (
                <div className="browse-tab">
                    {/* Search and Filter Bar */}
                    <div className="search-filter-bar" style={{marginBottom: '20px', display: 'flex', gap: '15px', flexWrap: 'wrap'}}>
                        <div style={{flex: '1', minWidth: '300px'}}>
                            <input
                                type="text"
                                placeholder="🔍 Search debates by motion or description..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '12px 16px',
                                    border: '2px solid #e0e0e0',
                                    borderRadius: '8px',
                                    fontSize: '14px'
                                }}
                            />
                        </div>
                        <select
                            value={selectedCategory}
                            onChange={(e) => setSelectedCategory(e.target.value)}
                            style={{
                                padding: '12px 16px',
                                border: '2px solid #e0e0e0',
                                borderRadius: '8px',
                                fontSize: '14px',
                                minWidth: '150px'
                            }}
                        >
                            <option value="all">All Categories</option>
                            {categories.map(cat => (
                                <option key={cat.id} value={cat.id}>{cat.icon} {cat.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="debates-header">
                        <h2>My Debates</h2>
                        <div className="filter-buttons">
                            {['all', 'waiting', 'in_progress', 'completed'].map(status => (
                                <button
                                    key={status}
                                    className={filterStatus === status ? 'active' : ''}
                                    onClick={() => setFilterStatus(status)}
                                >
                                    {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
                                </button>
                            ))}
                        </div>
                    </div>

                    {isLoadingDebates ? (
                        <div className="loading">Loading debates...</div>
                    ) : (
                        <div className="debates-grid">
                            {filteredDebates.length === 0 ? (
                                <div className="empty-state">
                                    <MessageSquare size={48} />
                                    <p>No debates found. Create one to get started!</p>
                                </div>
                            ) : (
                                filteredDebates.map(debate => (
                                    <div key={debate.id} className="debate-card">
                                        <div className="debate-card-header">
                                            <span className="category-badge">{debate.category}</span>
                                            {getStatusBadge(debate.status)}
                                        </div>
                                        <h3>{debate.motion}</h3>
                                        <div className="debate-card-meta">
                                            <span><Users size={14} /> {debate.participants?.length || 0} participants</span>
                                            <span><Clock size={14} /> Round {debate.current_round}/{debate.total_rounds}</span>
                                        </div>
                                        <div className="debate-card-actions">
                                            <button
                                                onClick={() => {
                                                    // Clear previous debate data
                                                    setDebateMessages([]);
                                                    setError('');

                                                    setCurrentDebate(debate);
                                                    const currentUserId = getUserIdFromToken();
                                                    const participant = debate.participants?.find(p => p.user_id === currentUserId);
                                                    console.log('Entering debate:', {
                                                        debateId: debate.id,
                                                        currentUserId,
                                                        foundParticipant: participant?.id,
                                                        totalParticipants: debate.participants?.length
                                                    });
                                                    setCurrentParticipant(participant);
                                                    setActiveTab(debate.status === 'completed' ? 'results' : 'debate');
                                                }}
                                                className="btn-primary"
                                            >
                                                {debate.status === 'completed' ? 'View Results' : 'Enter Debate'}
                                            </button>
                                            {/* Show delete button only for debates in 'created' status and user is creator */}
                                            {(() => {
                                                const currentUserId = getUserIdFromToken();
                                                const isCreator = debate.creator_id === currentUserId;
                                                const isCreatedStatus = debate.status === 'created';

                                                // Debug logging
                                                if (isCreatedStatus) {
                                                    console.log('Delete button check:', {
                                                        debateId: debate.id,
                                                        debateStatus: debate.status,
                                                        creatorId: debate.creator_id,
                                                        currentUserId: currentUserId,
                                                        isCreator: isCreator,
                                                        willShowButton: isCreatedStatus && isCreator
                                                    });
                                                }

                                                return isCreatedStatus && isCreator ? (
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDeleteDebate(debate.id);
                                                        }}
                                                        className="btn-delete"
                                                        title="Delete this debate"
                                                    >
                                                        <X size={14} /> Delete
                                                    </button>
                                                ) : null;
                                            })()}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* Public Debates */}
                    {filteredPublicDebates.length > 0 && (
                        <>
                            <h2 className="section-title">Public Debates ({filteredPublicDebates.length})</h2>
                            <div className="debates-grid">
                                {filteredPublicDebates.map(debate => (
                                    <div key={debate.id} className="debate-card">
                                        <div className="debate-card-header">
                                            <span className="category-badge">{debate.category}</span>
                                            {getStatusBadge(debate.status)}
                                        </div>
                                        <h3>{debate.motion}</h3>
                                        <div className="debate-card-meta">
                                            <span><Users size={14} /> {debate.participants?.length || 0}/{debate.max_participants}</span>
                                        </div>
                                        <div className="debate-card-actions">
                                            <button
                                                onClick={() => handleJoinDebate(debate)}
                                                className="btn-primary"
                                                disabled={isJoining}
                                            >
                                                {isJoining ? 'Joining...' : 'Join as Opposition'}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Create Tab */}
            {activeTab === 'create' && (
                <div className="create-tab">
                    <h2>Create New Debate</h2>

                    <div className="form-section">
                        <label>Debate Motion *</label>
                        <input
                            type="text"
                            value={motion}
                            onChange={(e) => setMotion(e.target.value)}
                            placeholder="This house believes that..."
                            className="form-input"
                        />
                        <small>Enter the debate motion or topic (minimum 10 characters)</small>
                    </div>

                    <div className="form-section">
                        <label>Description</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Additional context or background information..."
                            rows={3}
                            className="form-input"
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-section">
                            <label>Category</label>
                            <select value={category} onChange={(e) => setCategory(e.target.value)} className="form-input">
                                {categories.map(cat => (
                                    <option key={cat.id} value={cat.id}>
                                        {cat.icon} {cat.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="form-section">
                            <label>Format</label>
                            <select value={format} onChange={(e) => setFormat(e.target.value)} className="form-input">
                                {formats.map(fmt => (
                                    <option key={fmt.id} value={fmt.id}>
                                        {fmt.name}
                                    </option>
                                ))}
                            </select>
                            <small>{formats.find(f => f.id === format)?.desc}</small>
                        </div>
                    </div>

                    <div className="form-section">
                        <label>Settings</label>
                        <div className="settings-grid">
                            {Object.entries({
                                auto_fact_check: 'Auto Fact-Check',
                                argument_analysis: 'AI Argument Analysis',
                                ai_moderation: 'AI Moderation',
                                public_debate: 'Public Debate'
                            }).map(([key, label]) => (
                                <label key={key} className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={settings[key]}
                                        onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
                                    />
                                    <span>{label}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleCreateDebate}
                        disabled={isCreating || motion.trim().length < 10}
                        className="btn-create"
                    >
                        {isCreating ? 'Creating...' : 'Create Debate'}
                    </button>
                </div>
            )}

            {/* Debate Tab */}
            {activeTab === 'debate' && currentDebate && (
                <div className="debate-tab">
                    {/* Debate Header */}
                    <div className="debate-info">
                        <div className="debate-title-row">
                            <h2>{currentDebate.motion}</h2>
                            {getStatusBadge(currentDebate.status)}
                        </div>
                        <div className="debate-meta">
                            <span><Clock size={16} /> Round {currentDebate.current_round}/{currentDebate.total_rounds}</span>
                            <span><Users size={16} /> {(() => {
                                // Count unique participants by user_id
                                const uniqueUserIds = new Set(currentDebate.participants?.map(p => p.user_id) || []);
                                return uniqueUserIds.size;
                            })()} connected</span>
                            {isConnected ? (
                                <span className="status-connected">● Connected</span>
                            ) : (
                                <span className="status-disconnected">
                                    ● Disconnected
                                    <button
                                        onClick={handleManualReconnect}
                                        className="btn-reconnect"
                                        style={{marginLeft: '10px', padding: '4px 12px', fontSize: '12px'}}
                                    >
                                        Reconnect
                                    </button>
                                </span>
                            )}
                        </div>

                        {/* Control Buttons */}
                        <div className="debate-controls" style={{display: 'flex', gap: '10px', marginTop: '10px'}}>
                            {(() => {
                                const currentUserId = getUserIdFromToken();
                                const isCreator = currentDebate.creator_id === currentUserId;
                                const isModerator = currentParticipant?.role === 'moderator';
                                const canControl = isCreator || isModerator;

                                return canControl && (
                                    <>
                                        {(currentDebate.status === 'created' || currentDebate.status === 'ready') && (
                                            <button onClick={handleStartDebate} className="btn-start">
                                                <Play size={16} /> Start Debate
                                            </button>
                                        )}
                                        {currentDebate.status === 'in_progress' && (
                                            <button onClick={handleEndDebate} className="btn-end">
                                                <CheckCircle size={16} /> End Debate
                                            </button>
                                        )}
                                    </>
                                );
                            })()}
                            {/* Leave button for all participants */}
                            <button
                                onClick={handleLeaveDebate}
                                className="btn-leave"
                                style={{marginLeft: 'auto'}}
                            >
                                <X size={16} /> Leave Debate
                            </button>
                        </div>
                    </div>

                    {/* Main Content Area */}
                    <div className="debate-content">
                        {/* Participants Sidebar */}
                        <div className="participants-sidebar">
                            <h3><Users size={18} /> Participants</h3>
                            <div className="participants-list">
                                {(() => {
                                    // Use currentDebate.participants as source of truth and deduplicate by user_id
                                    const uniqueParticipants = currentDebate.participants?.reduce((acc, p) => {
                                        // Keep only one participant per user_id (the most recent one)
                                        const existingIndex = acc.findIndex(existing => existing.user_id === p.user_id);
                                        if (existingIndex === -1) {
                                            acc.push(p);
                                        }
                                        return acc;
                                    }, []) || [];

                                    return uniqueParticipants.map(p => (
                                        <div key={p.id} className="participant-item">
                                            <div className="participant-avatar">{p.display_name?.[0] || '?'}</div>
                                            <div className="participant-details">
                                                <div className="participant-name">{p.display_name}</div>
                                                {getRoleBadge(p.role)}
                                            </div>
                                            {p.is_connected && <span className="online-dot">●</span>}
                                        </div>
                                    ));
                                })()}
                            </div>
                        </div>

                        {/* Messages Area */}
                        <div className="messages-area">
                            <div className="messages-list">
                                {debateMessages.map((msg, idx) => (
                                    <div key={idx} className={`message message-${msg.role}`}>
                                        <div className="message-header">
                                            <span className="message-author">
                                                {getMessageTypeIcon(msg.message_type)}
                                                <strong>{msg.display_name}</strong> ({msg.role})
                                            </span>
                                            <span className="message-time">
                                                {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                                            </span>
                                        </div>
                                        <div className="message-content">{msg.content}</div>

                                        {/* AI Analysis */}
                                        {msg.ai_analysis && (
                                            <div className="ai-analysis">
                                                <div className="analysis-header">
                                                    <Brain size={14} /> AI Analysis
                                                </div>
                                                <div className="analysis-scores">
                                                    <span>Strength: {msg.ai_analysis.argument_strength || 0}/10</span>
                                                    <span>Persuasiveness: {msg.ai_analysis.persuasiveness || 0}/10</span>
                                                    <span>Evidence: {msg.ai_analysis.evidence_quality || 0}/10</span>
                                                </div>
                                                {msg.ai_analysis.fallacies_detected?.length > 0 && (
                                                    <div className="fallacies-detected">
                                                        <AlertCircle size={14} /> Fallacies:
                                                        {msg.ai_analysis.fallacies_detected.map((f, i) => (
                                                            <span key={i} className="fallacy-tag">{f.type}</span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Reactions */}
                                        <div className="message-actions">
                                            <button className="reaction-btn">
                                                <ThumbsUp size={14} /> {msg.upvotes || 0}
                                            </button>
                                            <button className="reaction-btn">
                                                <ThumbsDown size={14} /> {msg.downvotes || 0}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Typing Indicator */}
                            {typingUsers.length > 0 && (
                                <div className="typing-indicator">
                                    {typingUsers.join(', ')} {typingUsers.length === 1 ? 'is' : 'are'} typing...
                                </div>
                            )}

                            {/* Message Input */}
                            {currentDebate.status === 'in_progress' && currentParticipant && (
                                <div className="message-input-container">
                                    <select
                                        value={messageType}
                                        onChange={(e) => setMessageType(e.target.value)}
                                        className="message-type-select"
                                    >
                                        <option value="argument">Argument</option>
                                        <option value="rebuttal">Rebuttal</option>
                                        <option value="chat">Chat</option>
                                    </select>
                                    <textarea
                                        value={messageInput}
                                        onChange={handleTyping}
                                        onKeyPress={handleKeyPress}
                                        placeholder={`Type your ${messageType}...`}
                                        rows={2}
                                        className="message-input"
                                    />
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={!messageInput.trim()}
                                        className="btn-send"
                                    >
                                        <Send size={18} />
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Results Tab */}
            {activeTab === 'results' && currentDebate?.status === 'completed' && (
                <div className="results-tab">
                    <h2><Trophy size={24} /> Debate Results</h2>

                    <div className="results-grid">
                        <div className="result-card winner-card">
                            <h3>Winner</h3>
                            <div className="winner-label">
                                {currentDebate.results?.winner || currentDebate.ai_summary?.winner || 'Tie'}
                            </div>
                        </div>

                        <div className="result-card stats-card">
                            <h3>Statistics</h3>
                            <div className="stat-row">
                                <span>Total Arguments:</span>
                                <strong>{currentDebate.ai_summary?.statistics?.total_arguments || 0}</strong>
                            </div>
                            <div className="stat-row">
                                <span>Total Rebuttals:</span>
                                <strong>{currentDebate.ai_summary?.statistics?.total_rebuttals || 0}</strong>
                            </div>
                            <div className="stat-row">
                                <span>Overall Quality:</span>
                                <strong>{currentDebate.ai_summary?.overall_quality || 0}/10</strong>
                            </div>
                        </div>
                    </div>

                    {currentDebate.ai_summary?.strongest_arguments && (
                        <div className="strongest-arguments-section">
                            <h3>Strongest Arguments</h3>
                            {currentDebate.ai_summary.strongest_arguments.map((arg, idx) => (
                                <div key={idx} className="argument-card">
                                    <div className="argument-side-label">{arg.side}</div>
                                    <div className="argument-text">{arg.argument}</div>
                                    <div className="argument-score">{arg.strength}/10</div>
                                </div>
                            ))}
                        </div>
                    )}

                    <button onClick={() => setActiveTab('debate')} className="btn-secondary">
                        View Full Debate
                    </button>
                </div>
            )}
        </div>
    );
}

export default DigitalDebate;
