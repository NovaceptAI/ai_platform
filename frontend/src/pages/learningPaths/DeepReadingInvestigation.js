import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import axiosInstance from '../../utils/axiosInstance';
import {
  FaCheckCircle,
  FaFileAlt,
  FaFlask,
  FaChartLine,
  FaUsers,
  FaGraduationCap
} from 'react-icons/fa';

const DeepReadingInvestigation = () => {
  const { slug } = useParams(); // Get learning path slug from URL
  const [activeStage, setActiveStage] = useState('discover');
  const [userProgress, setUserProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stageProgress, setStageProgress] = useState({});
  const [isInitialized, setIsInitialized] = useState(false);

  // Learning path state (no longer needs selection UI)
  const [currentLearningPathId, setCurrentLearningPathId] = useState(null);
  const [learningPathTitle, setLearningPathTitle] = useState('');

  // --- Vault integration (reused from Summarizer.js style) ---
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedVaultFile, setSelectedVaultFile] = useState('');
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState('');

  // Global file IDs for the learning path (selected in Discover, reused in all stages)
  const [learningPathFileIds, setLearningPathFileIds] = useState([]);

  // Orchestration states
  const [orchestrationProgress, setOrchestrationProgress] = useState(null);
  const [progressId, setProgressId] = useState(null);
  const [isOrchestrating, setIsOrchestrating] = useState(false);

  // Results states
  const [showResults, setShowResults] = useState(false);
  const [resultsData, setResultsData] = useState({});
  const [loadingResults, setLoadingResults] = useState(false);
  const [expandedTools, setExpandedTools] = useState({});

  // Active sessions state
  const [activeSessions, setActiveSessions] = useState([]);
  const [loadingActiveSessions, setLoadingActiveSessions] = useState(true);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [showSessionSelector, setShowSessionSelector] = useState(false);

  // Notification state
  const [notification, setNotification] = useState(null); // { message, type: 'success' | 'error' | 'info' }

  // Show notification helper
  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    // Auto-hide after 4 seconds
    setTimeout(() => setNotification(null), 4000);
  };

  // Save files to the current session
  const saveFilesToSession = async (fileIds) => {
    if (!selectedSessionId || !currentLearningPathId) {
      console.warn('Cannot save files: no session or learning path ID');
      return;
    }

    try {
      await axiosInstance.post(
        `/learning_paths/${currentLearningPathId}/session/${selectedSessionId}/files`,
        { file_ids: fileIds }
      );
      console.log('Files saved to session:', fileIds);
    } catch (err) {
      console.error('Error saving files to session:', err);
    }
  };

  const fetchVaultFiles = useCallback(async () => {
    try {
      const { data } = await axiosInstance.get('/upload/files');
      const files = data?.files || [];
      setVaultFiles(files);
      if (selectedVaultFile) {
        const m = files.find(v => v.stored_name === selectedVaultFile || v.name === selectedVaultFile);
        setSelectedFileId(m?.file_id || m?.id || null);
      }
    } catch {
      // non-blocking
    }
  }, [selectedVaultFile]);

  const resolveFileId = (storedName) => {
    const m = vaultFiles.find(v => v.stored_name === storedName || v.name === storedName);
    // Handle both 'fileId' (from /files endpoint) and 'file_id' (from upload endpoint)
    return m?.fileId || m?.file_id || m?.id || null;
  };

  useEffect(() => { fetchVaultFiles(); }, [fetchVaultFiles]);
  
  const handleInlineUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name); // Show file name immediately
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const r = await axiosInstance.post('/upload/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      // Extract file ID directly from upload response
      const uploadResult = r.data?.results?.[0]; // Upload returns results array
      const fileId = uploadResult?.file_id;
      const storedAs = uploadResult?.stored_as;
      
      if (!fileId) {
        console.error('No file_id in upload response:', r.data);
        alert('Upload succeeded but no file ID returned. Please select from vault.');
        await fetchVaultFiles();
        return;
      }
      
      // Set file ID DIRECTLY from upload response (no race condition)
      setSelectedFileId(fileId);
      setSelectedVaultFile(storedAs || '');
      
      // Refresh vault files in background (doesn't affect selectedFileId anymore)
      await fetchVaultFiles();
      
    } catch (err) {
      console.error('Upload error:', err);
      setSelectedFileName('');
    } finally {
      setUploading(false);
    }
  };

  const handleStartStageFromVault = async () => {
    const pathId = currentLearningPathId; // Capture the current value

    // For Discover stage, use file from UI. For other stages, use saved file IDs
    let fileIds = [];
    if (activeStage === 'discover') {
      const fid = selectedFileId || resolveFileId(selectedVaultFile);
      if (!fid) {
        alert('Please upload or choose a file from the Knowledge Vault.');
        return;
      }
      fileIds = [fid];
      // Store file IDs globally for reuse in subsequent stages
      setLearningPathFileIds(fileIds);
      // Save files to the current session
      await saveFilesToSession(fileIds);
    } else {
      // For subsequent stages, use the file IDs from Discover
      if (learningPathFileIds.length === 0) {
        alert('No files selected. Please complete the Discover stage first.');
        return;
      }
      fileIds = learningPathFileIds;
    }

    if (!pathId) {
      console.error('No learning path ID available');
      alert('Learning path not loaded. Please refresh the page and try again.');
      return;
    }

    setIsOrchestrating(true);

    try {
      // Start the stage - this triggers all tools via the backend
      const stageResponse = await axiosInstance.post(
        `/learning_paths/${pathId}/start-stage/${activeStage}`,
        {
          file_ids: fileIds,
          session_id: selectedSessionId  // Pass the current session ID
        }
      );

      const progId = stageResponse.data.progress_id;
      setProgressId(progId);

      // Start polling the stage progress
      startProgressPolling(progId);

      // Refresh learning path state
      await loadLearningPathState(pathId);

    } catch (err) {
      console.error('Error starting stage:', err);
      alert(`Failed to start stage. ${err.response?.data?.error || 'Please try again.'}`);
      setIsOrchestrating(false);
    }
  };

  // Progress polling function - polls the stage progress
  const startProgressPolling = (progId) => {
    const pollProgress = async () => {
      try {
        // Get the stage progress (this is the overall orchestration progress)
        const progressResponse = await axiosInstance.get(`/progress/${progId}`);
        const stageProgress = progressResponse.data;

        // Create a progress object with tool-specific tracking
        const progressData = {
          progress_id: progId,
          status: stageProgress.status,
          percentage: stageProgress.percentage || 0,
          tools_completed: stageProgress.tools_completed || [],
          tools_running: stageProgress.tools_running || [],
          tools_pending: stageProgress.tools_pending || []
        };

        setOrchestrationProgress(progressData);

        // Stop polling when complete
        if (stageProgress.status === 'completed') {
          setIsOrchestrating(false);
          await completeStage(activeStage);
          return;
        } else if (stageProgress.status === 'failed') {
          setIsOrchestrating(false);
          alert('Stage processing failed. Please check the logs or try again.');
          return;
        }

        // Continue polling every 2 seconds
        setTimeout(() => pollProgress(), 2000);
      } catch (err) {
        console.error('Error polling progress:', err);
        setIsOrchestrating(false);
        alert('Failed to get progress updates. Please refresh the page.');
      }
    };

    pollProgress();
  };

  // Complete stage function
  const completeStage = async (stageName) => {
    try {
      // Refresh learning path state to get updated stage status
      await loadLearningPathState(LEARNING_PATH_ID);

      showNotification(`🎉 Congratulations! You've completed the ${stageName} stage! The next stage is now unlocked.`, 'success');
    } catch (err) {
      console.error('Error completing stage:', err);
    }
  };

  // Fetch results for the current stage and file
  const fetchStageResults = async () => {
    const fid = selectedFileId || resolveFileId(selectedVaultFile);
    if (!fid) {
      alert('Please select a file to view results');
      return;
    }

    setLoadingResults(true);
    setShowResults(true);

    try {
      const tools = {
        summarizer: { endpoint: '/summarizer/results', label: 'Document Summarizer' },
        segmenter: { endpoint: '/segmenter/results', label: 'Content Segmentation' },
        doc_analysis: { endpoint: '/doc_analysis/results', label: 'Document Analysis' },
        chronology: { endpoint: '/chronology/results', label: 'Chronology Timeline' },
        evidence_extractor: { endpoint: '/stages/discover/evidence_extractor/results', label: 'Evidence Extraction' }
      };

      const results = {};

      for (const [toolKey, toolConfig] of Object.entries(tools)) {
        try {
          const response = await axiosInstance.get(`${toolConfig.endpoint}?file_id=${fid}`);
          if (response.data) {
            results[toolKey] = {
              ...response.data,
              label: toolConfig.label,
              hasData: true
            };
          }
        } catch (err) {
          console.log(`No results for ${toolKey}:`, err.response?.status);
          results[toolKey] = {
            label: toolConfig.label,
            hasData: false,
            error: err.response?.status === 404 ? 'No data available' : 'Error loading data'
          };
        }
      }

      setResultsData(results);
    } catch (err) {
      console.error('Error fetching results:', err);
      alert('Failed to load results');
    } finally {
      setLoadingResults(false);
    }
  };

  const toggleToolExpanded = (toolKey) => {
    setExpandedTools(prev => ({
      ...prev,
      [toolKey]: !prev[toolKey]
    }));
  };

  // Fetch active learning path sessions for this user and path
  const fetchActiveSessions = async (pathId) => {
    if (!pathId) return;

    setLoadingActiveSessions(true);
    try {
      const response = await axiosInstance.get(`/learning_paths/${pathId}/active-sessions`);
      const sessions = response.data.active_sessions || [];
      setActiveSessions(sessions);

      // Always show selector if we're not already in a session
      // User must explicitly choose: new session OR existing session
      if (!selectedSessionId) {
        setShowSessionSelector(true);
      }
    } catch (err) {
      console.error('Error fetching active sessions:', err);
      setActiveSessions([]);
      setShowSessionSelector(true); // Still show selector even on error
    } finally {
      setLoadingActiveSessions(false);
    }
  };

  // Resume a specific learning path session
  const handleResumeSession = async (sessionId) => {
    const pathId = currentLearningPathId;

    try {
      // Fetch vault files to ensure we have the latest list
      console.log('Fetching vault files...');
      const { data: vaultData } = await axiosInstance.get('/upload/files');
      const freshVaultFiles = vaultData?.files || [];
      console.log('Fresh vault files loaded:', freshVaultFiles.length);

      // Call resume endpoint
      const response = await axiosInstance.post(`/learning_paths/${pathId}/resume/${sessionId}`);
      const sessionData = response.data.session;

      console.log('Resume session data:', sessionData);

      // Load the session state
      setSelectedSessionId(sessionId);
      setLearningPathFileIds(sessionData.file_ids || []);
      setActiveStage(sessionData.current_stage || 'discover');

      // Set the first file as selected for display
      if (sessionData.file_ids && sessionData.file_ids.length > 0) {
        const firstFileId = sessionData.file_ids[0];
        console.log('Setting selected file ID:', firstFileId);
        setSelectedFileId(firstFileId);

        // Try to find the file name from fresh vault files
        // Check for fileId (camelCase), file_id (snake_case), or id
        const matchedFile = freshVaultFiles.find(v => {
          const match = v.fileId === firstFileId || v.file_id === firstFileId || v.id === firstFileId;
          if (match) {
            console.log(`✓ Found matching vault file:`, v);
          }
          return match;
        });

        if (matchedFile) {
          const fileName = matchedFile.name || matchedFile.original_filename || matchedFile.originalFilename;
          const storedName = matchedFile.stored_name || matchedFile.stored_filename || matchedFile.storedFilename;

          setSelectedFileName(fileName);
          setSelectedVaultFile(storedName);

          console.log('✓ Set selected file - Name:', fileName, 'Stored:', storedName);
        } else {
          console.warn('✗ Could not find matching vault file for ID:', firstFileId);
          console.warn('Available file IDs:', freshVaultFiles.map(v => v.fileId || v.file_id || v.id));
        }
      }

      // Fetch full learning path state for THIS SPECIFIC SESSION
      await loadLearningPathState(pathId, sessionId);

      // Hide session selector
      setShowSessionSelector(false);

      showNotification(`📂 Resumed learning path! Continue from ${sessionData.current_stage} stage.`, 'success');
    } catch (err) {
      console.error('Error resuming session:', err);
      showNotification('Failed to resume session. Please try again.', 'error');
    }
  };

  // Start a new learning path (ignore existing sessions)
  const handleStartNewPath = async () => {
    const pathId = currentLearningPathId;

    try {
      // Create a new session in the backend
      const response = await axiosInstance.post(`/learning_paths/${pathId}/create-session`);
      const sessionData = response.data.session;

      // Set the new session ID
      setSelectedSessionId(sessionData.user_learning_path_id);

      // Clear files for the new session
      setLearningPathFileIds([]);
      setSelectedFileId(null);
      setSelectedFileName('');
      setSelectedVaultFile('');

      // Reset to Discover stage
      setActiveStage('discover');

      // Initialize default stage progress
      setStageProgress({
        discover: { visited: true, completed: false },
        organize: { visited: false, completed: false },
        master: { visited: false, completed: false },
        create: { visited: false, completed: false },
        collaborate: { visited: false, completed: false }
      });

      // Hide session selector
      setShowSessionSelector(false);

      // Clear user progress
      setUserProgress(null);

      showNotification('🆕 New learning path session started!', 'success');
    } catch (err) {
      console.error('Error creating new session:', err);
      showNotification('Failed to create new session. Please try again.', 'error');
    }
  };

  // --- End vault integration ---

  // Deep Reading Investigation Learning Path ID
  const LEARNING_PATH_ID = currentLearningPathId;

  // Fetch learning path by slug from URL
  const fetchLearningPathBySlug = async (pathSlug) => {
    try {
      console.log('Fetching learning path for slug:', pathSlug);

      // Use the proper by-slug endpoint instead of fetching all paths
      const response = await axiosInstance.get(`/learning_paths/by-slug/${pathSlug}`);
      console.log('API response:', response.data);

      const matchedPath = response.data;

      if (matchedPath && matchedPath.id) {
        console.log('✓ Matched learning path:', matchedPath);
        console.log('Setting learning path ID to:', matchedPath.id);
        setCurrentLearningPathId(matchedPath.id);
        setLearningPathTitle(matchedPath.title);

        // DON'T auto-load state - let fetchActiveSessions handle showing the selector first
        // The session selector will be shown by the useEffect that watches currentLearningPathId
        console.log('Learning path ID set, waiting for session selector to show');
      } else {
        console.error('✗ No learning path found for slug:', pathSlug);
        alert(`Learning path "${pathSlug}" not found.`);
      }
    } catch (err) {
      console.error('Error fetching learning path:', err);
      console.error('Error details:', err.response?.data || err.message);

      if (err.response?.status === 404) {
        alert(`Learning path "${pathSlug}" not found. Please check the URL.`);
      } else {
        alert('Failed to load learning path. Please try again.');
      }
    }
  };


  // Load specific learning path state
  const loadLearningPathState = async (pathId, sessionId = null) => {
    try {
      console.log('Loading learning path state for ID:', pathId, 'Session:', sessionId || selectedSessionId);
      setCurrentLearningPathId(pathId);

      // Use session-specific endpoint if we have a session ID
      const activeSessionId = sessionId || selectedSessionId;
      const statusUrl = activeSessionId
        ? `/learning_paths/${pathId}/session/${activeSessionId}/status`
        : `/learning_paths/${pathId}/status`;

      const statusResponse = await axiosInstance.get(statusUrl);
      console.log('Learning path status response:', statusResponse.data);
      
      if (statusResponse.data) {
        const status = statusResponse.data;
        setUserProgress(status);
        
        // Convert backend stage status to frontend format
        const backendStageProgress = {};
        status.stages.forEach(stage => {
          backendStageProgress[stage.name] = {
            visited: stage.status === 'unlocked' || stage.status === 'completed',
            completed: stage.status === 'completed'
          };
        });
        setStageProgress(backendStageProgress);
        
        // Set current stage from backend
        if (status.current_stage) {
          setActiveStage(status.current_stage);
        } else if (status.next_stage) {
          setActiveStage(status.next_stage);
        } else {
          setActiveStage('discover'); // Default to discover
        }
        
        // If user has file IDs, restore them globally and set the selected file for display
        if (status.file_ids && status.file_ids.length > 0) {
          setLearningPathFileIds(status.file_ids); // Store globally for all stages

          const fileId = status.file_ids[0];
          setSelectedFileId(fileId);
          // Optionally fetch the file name from vault files
          const matchedFile = vaultFiles.find(v => v.file_id === fileId || v.id === fileId);
          if (matchedFile) {
            setSelectedFileName(matchedFile.name);
            setSelectedVaultFile(matchedFile.stored_name);
          }
        }
      }
    } catch (err) {
      console.error('Error loading learning path state:', err);
      console.error('Error details:', err.response?.data || err.message);

      // If 404, user is not enrolled yet - that's okay, just set default state
      if (err.response?.status === 404) {
        console.log('User not enrolled in learning path, initializing default state');
        setUserProgress(null);
        setStageProgress({
          discover: { visited: true, completed: false },
          organize: { visited: false, completed: false },
          master: { visited: false, completed: false },
          create: { visited: false, completed: false },
          collaborate: { visited: false, completed: false }
        });
      } else {
        setUserProgress(null);
      }
      // Don't re-throw - we still want the learning path ID to be set
    }
  };

  const stages = [
    {
      id: 'discover',
      name: 'Discover',
      icon: FaFlask,
      description: 'Analyze and extract insights from your document'
    },
    {
      id: 'organize',
      name: 'Organize',
      icon: FaFileAlt,
      description: 'Structure and categorize your findings'
    },
    {
      id: 'create',
      name: 'Create',
      icon: FaChartLine,
      description: 'Generate content based on your analysis'
    },
    {
      id: 'master',
      name: 'Master',
      icon: FaGraduationCap,
      description: 'Test and reinforce your understanding'
    },
    {
      id: 'collaborate',
      name: 'Collaborate',
      icon: FaUsers,
      description: 'Share and discuss with peers'
    }
  ];

  // Initialize the learning path from URL slug
  useEffect(() => {
    const initializeLearningPath = async () => {
      try {
        setLoading(true);

        if (!slug) {
          console.error('No slug in URL');
          setLoading(false);
          setIsInitialized(true);
          return;
        }

        // Fetch and load the learning path based on URL slug
        await fetchLearningPathBySlug(slug);

      } catch (err) {
        console.error('Error initializing learning path:', err);
        setUserProgress(null);
      } finally {
        setLoading(false);
        setIsInitialized(true);
      }
    };

    initializeLearningPath();
  }, [slug]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch active sessions after learning path ID is set
  useEffect(() => {
    if (currentLearningPathId && isInitialized) {
      fetchActiveSessions(currentLearningPathId);
    }
  }, [currentLearningPathId, isInitialized]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle stage tab changes - only switch if stage is unlocked
  const handleStageChange = async (stageId) => {
    const stageStatus = stageProgress[stageId];

    // Only allow switching to unlocked or completed stages
    if (stageStatus && (stageStatus.visited || stageStatus.completed)) {
      setActiveStage(stageId);
    } else if (stageId === 'discover') {
      // Always allow switching to discover stage
      setActiveStage(stageId);
    }
  };

  // Show loading state while initializing
  if (loading && !isInitialized) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        backgroundColor: '#f9fafb', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center' 
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ 
            animation: 'spin 1s linear infinite',
            borderRadius: '50%',
            height: '3rem',
            width: '3rem',
            borderBottom: '2px solid #2563eb',
            margin: '0 auto 1rem auto'
          }}></div>
          <p style={{ color: '#6b7280' }}>Loading your learning path...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
        {/* Header */}
      <div style={{ backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                {learningPathTitle || 'Learning Path'}
              </h1>
              <p style={{ marginTop: '0.5rem', fontSize: '1.125rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                Navigate your learning journey through structured stages
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FaGraduationCap style={{ height: '1.25rem', width: '1.25rem', color: '#9ca3af' }} />
              <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                {stages.length} Stages
              </span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '2rem 1.5rem' }}>
        {/* Active Sessions Selector - Always show to let user choose */}
        {showSessionSelector && !loadingActiveSessions && (
          <div style={{
            backgroundColor: '#fef3c7',
            border: '2px solid #f59e0b',
            borderRadius: '0.5rem',
            padding: '1.5rem',
            marginBottom: '2rem'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem'
            }}>
              <h3 style={{
                fontSize: '1.25rem',
                fontWeight: '600',
                color: '#92400e',
                margin: 0
              }}>
                📂 Choose Your Learning Path Session
              </h3>
              <button
                onClick={handleStartNewPath}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '500',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#059669'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#10b981'}
              >
                🆕 Start New Session
              </button>
            </div>

            <p style={{ color: '#78350f', marginBottom: '1rem', fontSize: '0.875rem', margin: '0 0 1rem 0' }}>
              {activeSessions.length > 0
                ? `Select from ${activeSessions.length} existing session${activeSessions.length > 1 ? 's' : ''} or start a new one.`
                : 'Start a new learning path session to begin.'}
            </p>

            {/* Session Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '1rem'
            }}>
              {activeSessions.map((session) => (
                <div
                  key={session.user_learning_path_id}
                  style={{
                    backgroundColor: 'white',
                    border: '1px solid #fbbf24',
                    borderRadius: '0.5rem',
                    padding: '1rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onClick={() => handleResumeSession(session.user_learning_path_id)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                    e.currentTarget.style.borderColor = '#f59e0b';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'none';
                    e.currentTarget.style.borderColor = '#fbbf24';
                  }}
                >
                  {/* Progress Badge */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.75rem'
                  }}>
                    <span style={{
                      backgroundColor: '#dbeafe',
                      color: '#1e40af',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      fontWeight: '600'
                    }}>
                      {session.current_stage.toUpperCase()}
                    </span>
                    <span style={{
                      color: '#10b981',
                      fontWeight: '600',
                      fontSize: '0.875rem'
                    }}>
                      {session.progress_percentage}%
                    </span>
                  </div>

                  {/* Files Info */}
                  <div style={{ marginBottom: '0.5rem' }}>
                    <div style={{
                      fontSize: '0.875rem',
                      color: '#374151',
                      fontWeight: '500',
                      marginBottom: '0.25rem'
                    }}>
                      📄 {session.file_count} file{session.file_count > 1 ? 's' : ''}
                    </div>
                    {session.file_names.length > 0 && (
                      <div style={{
                        fontSize: '0.75rem',
                        color: '#6b7280',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {session.file_names[0]}
                        {session.file_names.length > 1 && ` +${session.file_names.length - 1} more`}
                      </div>
                    )}
                  </div>

                  {/* Stage Progress */}
                  <div style={{
                    fontSize: '0.75rem',
                    color: '#6b7280',
                    marginBottom: '0.75rem'
                  }}>
                    {session.stages_completed} of {session.total_stages} stages completed
                  </div>

                  {/* Timestamp */}
                  <div style={{
                    fontSize: '0.7rem',
                    color: '#9ca3af',
                    borderTop: '1px solid #e5e7eb',
                    paddingTop: '0.5rem'
                  }}>
                    Updated: {new Date(session.updated_at).toLocaleDateString()}
                  </div>

                  {/* Click Prompt */}
                  <div style={{
                    marginTop: '0.75rem',
                    textAlign: 'center',
                    color: '#f59e0b',
                    fontSize: '0.875rem',
                    fontWeight: '500'
                  }}>
                    Click to Select →
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stage Navigation and Content - Always show, remove file upload dependency */}
        <div style={{ 
          backgroundColor: 'white', 
          borderRadius: '0.5rem', 
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
          marginBottom: '2rem'
        }}>
          <div style={{ borderBottom: '1px solid #e5e7eb' }}>
            <nav style={{ display: 'flex', gap: '2rem', padding: '0 1.5rem' }} aria-label="Tabs">
              {stages.map((stage) => {
                const isActive = activeStage === stage.id;
                const stageStatus = stageProgress[stage.id];
                const isCompleted = stageStatus?.completed;
                const isUnlocked = stageStatus?.visited || stage.id === 'discover';
                const Icon = stage.icon;
                
                return (
                  <button
                    key={stage.id}
                    onClick={() => handleStageChange(stage.id)}
                    disabled={!isUnlocked}
                    style={{
                      whiteSpace: 'nowrap',
                      padding: '1rem 0.25rem',
                      borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
                      fontWeight: '500',
                      fontSize: '0.875rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      backgroundColor: 'transparent',
                      border: 'none',
                      cursor: isUnlocked ? 'pointer' : 'not-allowed',
                      color: isActive ? '#3b82f6' : 
                             isCompleted ? '#059669' :
                             isUnlocked ? '#6b7280' : '#d1d5db',
                      transition: 'all 0.15s ease-in-out',
                      opacity: isUnlocked ? 1 : 0.5
                    }}
                    onMouseEnter={(e) => {
                      if (isUnlocked && !isActive) {
                        e.target.style.color = '#374151';
                        e.target.style.borderBottomColor = '#d1d5db';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (isUnlocked && !isActive) {
                        e.target.style.color = isCompleted ? '#059669' : '#6b7280';
                        e.target.style.borderBottomColor = 'transparent';
                      }
                    }}
                  >
                    <Icon style={{ height: '1.25rem', width: '1.25rem' }} />
                    <span>{stage.name}</span>
                    {isCompleted && <FaCheckCircle style={{ height: '1rem', width: '1rem', color: '#22c55e' }} />}
                  </button>
                );
              })}
            </nav>
          </div>

            {/* Stage Content */}
            <div style={{ padding: '1.5rem' }}>
              {activeStage === 'discover' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <FaFlask style={{ 
                      margin: '0 auto 1rem auto', 
                      height: '4rem', 
                      width: '4rem', 
                      color: '#3b82f6',
                      display: 'block'
                    }} />
                    <h3 style={{ 
                      fontSize: '1.5rem', 
                      fontWeight: 'bold', 
                      color: '#111827', 
                      margin: '0 0 0.5rem 0' 
                    }}>
                      Discover Stage
                    </h3>
                    <p style={{ color: '#6b7280', margin: 0 }}>
                      Analyze and extract insights from your document using AI-powered tools
                    </p>

                    {/* Only show file upload if not showing session selector */}
                    {!showSessionSelector && (
                      <>
                    {/* Compact Upload + Vault picker (reuses Summarizer.js patterns) */}
                    <div style={{
                      marginTop: '1rem',
                      display: 'flex',
                      gap: '0.5rem',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexWrap: 'wrap'
                    }}>
                      {/* Upload */}
                      <label
                        htmlFor="lpVaultUpload"
                        style={{
                          padding: '0.4rem 0.75rem',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.375rem',
                          cursor: uploading ? 'wait' : 'pointer',
                          background: uploading ? '#f3f4f6' : '#f9fafb',
                          opacity: uploading ? 0.6 : 1
                        }}
                        title="Upload a file into Knowledge Vault"
                      >
                        {uploading ? '⏳ Uploading...' : '⬆️ Upload'}
                        <input
                          id="lpVaultUpload"
                          type="file"
                          onChange={handleInlineUpload}
                          style={{ display: 'none' }}
                          disabled={uploading || isOrchestrating}
                        />
                      </label>

                      {/* Vault select */}
                      <select
                        value={selectedVaultFile}
                        onChange={(e) => {
                          const storedName = e.target.value;
                          setSelectedVaultFile(storedName);
                          setSelectedFileId(resolveFileId(storedName));
                          const matchedFile = vaultFiles.find(v => v.stored_name === storedName);
                          setSelectedFileName(matchedFile?.name || '');
                        }}
                        style={{
                          minWidth: 260,
                          padding: '0.4rem 0.5rem',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.375rem',
                          background: 'white',
                          color: '#111827'
                        }}
                        disabled={isOrchestrating}
                        aria-label="Select from Knowledge Vault"
                      >
                        <option value="">Vault: choose file…</option>
                        {vaultFiles.map((vf, idx) => (
                          <option key={idx} value={vf.stored_name}>
                            {vf.name}
                          </option>
                        ))}
                      </select>

                      {/* Refresh Vault */}
                      <button
                        type="button"
                        onClick={fetchVaultFiles}
                        style={{
                          padding: '0.4rem 0.75rem',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.375rem',
                          background: '#fff',
                          cursor: 'pointer'
                        }}
                        disabled={isOrchestrating}
                        title="Refresh Knowledge Vault"
                      >
                        ↻ Refresh
                      </button>

                      {/* Start Stage */}
                      <button
                        type="button"
                        onClick={handleStartStageFromVault}
                        style={{
                          padding: '0.5rem 1rem',
                          backgroundColor: isOrchestrating ? '#9ca3af' : '#2563eb',
                          color: 'white',
                          borderRadius: '0.375rem',
                          border: 'none',
                          cursor: isOrchestrating ? 'wait' : 'pointer',
                          transition: 'background-color 0.15s ease-in-out'
                        }}
                        disabled={isOrchestrating}
                        onMouseEnter={(e) => !isOrchestrating && (e.currentTarget.style.backgroundColor = '#1d4ed8')}
                        onMouseLeave={(e) => !isOrchestrating && (e.currentTarget.style.backgroundColor = '#2563eb')}
                        title="Start the Discover stage with the selected file"
                      >
                        {isOrchestrating ? '⏳ Processing...' : 'Start Stage'}
                      </button>
                    </div>

                    {/* Selected File Display */}
                    {selectedFileName && (
                      <div style={{
                        marginTop: '1rem',
                        display: 'flex',
                        justifyContent: 'center'
                      }}>
                        <div style={{
                          backgroundColor: '#dbeafe',
                          border: '1px solid #3b82f6',
                          borderRadius: '0.375rem',
                          padding: '0.5rem 1rem',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.5rem'
                        }}>
                          <FaFileAlt style={{ color: '#2563eb' }} />
                          <span style={{ color: '#1e40af', fontWeight: '500' }}>
                            {selectedFileName}
                          </span>
                          <button
                            onClick={() => {
                              setSelectedFileName('');
                              setSelectedVaultFile('');
                              setSelectedFileId(null);
                            }}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#3b82f6',
                              cursor: 'pointer',
                              padding: '0 0.25rem',
                              fontSize: '1.2rem',
                              lineHeight: '1'
                            }}
                            disabled={isOrchestrating}
                            title="Clear selection"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    )}
                      </>
                    )}
                  </div>

                  {/* Progress Display */}
                  {orchestrationProgress && (
                    <div style={{
                      marginTop: '1.5rem',
                      backgroundColor: '#f0f9ff',
                      border: '1px solid #3b82f6',
                      borderRadius: '0.5rem',
                      padding: '1rem'
                    }}>
                      <h4 style={{
                        fontWeight: '600',
                        color: '#1e40af',
                        margin: '0 0 0.75rem 0',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}>
                        <div style={{
                          width: '1rem',
                          height: '1rem',
                          border: '2px solid #3b82f6',
                          borderTopColor: 'transparent',
                          borderRadius: '50%',
                          animation: orchestrationProgress.status === 'in_progress' || orchestrationProgress.status === 'queued' ? 'spin 1s linear infinite' : 'none'
                        }} />
                        {activeStage.charAt(0).toUpperCase() + activeStage.slice(1)} Stage Progress
                      </h4>
                      <div style={{
                        marginTop: '0.75rem',
                        backgroundColor: '#dbeafe',
                        borderRadius: '0.25rem',
                        height: '0.5rem',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          backgroundColor: '#3b82f6',
                          height: '100%',
                          width: `${orchestrationProgress.percentage || 0}%`,
                          transition: 'width 0.3s ease-in-out'
                        }} />
                      </div>
                      <p style={{
                        fontSize: '0.75rem',
                        color: '#60a5fa',
                        margin: '0.5rem 0 0 0',
                        textAlign: 'right'
                      }}>
                        {orchestrationProgress.percentage || 0}% Complete {orchestrationProgress.status === 'completed' ? '✓' : ''}
                      </p>
                      <p style={{
                        fontSize: '0.75rem',
                        color: '#64748b',
                        margin: '0.5rem 0 0 0',
                        fontStyle: 'italic'
                      }}>
                        Running all {activeStage} tools in the background...
                      </p>
                    </div>
                  )}

                  {/* Tool Cards */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                    gap: '1rem',
                    marginTop: '1.5rem'
                  }}>
                    {[
                      { key: 'summarizer', icon: '📄', name: 'Document Summarizer', desc: 'Generate comprehensive summaries of your document' },
                      { key: 'segmenter', icon: '✂️', name: 'Segmenter', desc: 'Split content into coherent sections and chunks' },
                      { key: 'doc_analysis', icon: '🔎', name: 'Document Analysis', desc: 'Understand structure, themes, entities, and insights' },
                      { key: 'evidence_extractor', icon: '📑', name: 'Evidence Extractor', desc: 'Pull verifiable claims, facts, and quotes' },
                      { key: 'chronology', icon: '⏱️', name: 'Chronology', desc: 'Build chronological timelines from events and dates' },
                      { key: 'comparison', icon: '🔁', name: 'Comparison', desc: 'Compare sections, versions, or multiple documents' }
                    ].map((tool) => {
                      const isCompleted = orchestrationProgress?.tools_completed?.includes(tool.key);
                      const isRunning = orchestrationProgress?.tools_running?.includes(tool.key);

                      return (
                        <div
                          key={tool.key}
                          style={{
                            backgroundColor: 'white',
                            border: `1px solid ${isCompleted ? '#10b981' : isRunning ? '#3b82f6' : '#e5e7eb'}`,
                            borderRadius: '0.5rem',
                            padding: '1rem',
                            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                            position: 'relative',
                            transition: 'all 0.15s ease-in-out'
                          }}
                        >
                          {isRunning && (
                            <div style={{
                              position: 'absolute',
                              top: '0.75rem',
                              right: '0.75rem',
                              width: '1.25rem',
                              height: '1.25rem',
                              border: '2px solid #3b82f6',
                              borderTopColor: 'transparent',
                              borderRadius: '50%',
                              animation: 'spin 1s linear infinite'
                            }} />
                          )}

                          {isCompleted && (
                            <FaCheckCircle style={{
                              position: 'absolute',
                              top: '0.75rem',
                              right: '0.75rem',
                              color: '#10b981',
                              fontSize: '1.25rem'
                            }} />
                          )}

                          <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                            {tool.icon} {tool.name}
                          </h4>
                          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                            {tool.desc}
                          </p>

                          {isCompleted && (
                            <div style={{
                              marginTop: '0.75rem',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#d1fae5',
                              color: '#065f46',
                              borderRadius: '0.25rem',
                              fontSize: '0.75rem',
                              fontWeight: '500',
                              display: 'inline-block'
                            }}>
                              ✓ Complete
                            </div>
                          )}

                          {isRunning && (
                            <div style={{
                              marginTop: '0.75rem',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#dbeafe',
                              color: '#1e40af',
                              borderRadius: '0.25rem',
                              fontSize: '0.75rem',
                              fontWeight: '500',
                              display: 'inline-block'
                            }}>
                              ⏳ Processing...
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* View Results Button */}
                  {(selectedFileId || selectedVaultFile) && stageProgress?.discover?.completed && (
                    <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                      <button
                        onClick={fetchStageResults}
                        disabled={loadingResults}
                        style={{
                          backgroundColor: '#10b981',
                          color: 'white',
                          padding: '0.75rem 2rem',
                          border: 'none',
                          borderRadius: '0.5rem',
                          fontSize: '1rem',
                          fontWeight: '600',
                          cursor: loadingResults ? 'not-allowed' : 'pointer',
                          opacity: loadingResults ? 0.6 : 1,
                          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          if (!loadingResults) {
                            e.currentTarget.style.backgroundColor = '#059669';
                            e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = '#10b981';
                          e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                        }}
                      >
                        {loadingResults ? '📊 Loading Results...' : '📊 View Discover Results'}
                      </button>
                    </div>
                  )}

                  {/* Results Display */}
                  {showResults && Object.keys(resultsData).length > 0 && (
                    <div style={{
                      marginTop: '2rem',
                      backgroundColor: '#f9fafb',
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      padding: '1.5rem'
                    }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '1.5rem'
                      }}>
                        <h3 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 'bold', color: '#111827' }}>
                          📋 Discover Stage Results
                        </h3>
                        <button
                          onClick={() => setShowResults(false)}
                          style={{
                            backgroundColor: 'transparent',
                            border: 'none',
                            color: '#6b7280',
                            fontSize: '1.5rem',
                            cursor: 'pointer',
                            padding: '0.25rem'
                          }}
                          title="Close results"
                        >
                          ✕
                        </button>
                      </div>

                      {Object.entries(resultsData).map(([toolKey, toolData]) => (
                        <div
                          key={toolKey}
                          style={{
                            backgroundColor: 'white',
                            border: '1px solid #e5e7eb',
                            borderRadius: '0.5rem',
                            marginBottom: '1rem',
                            overflow: 'hidden'
                          }}
                        >
                          {/* Tool Header */}
                          <button
                            onClick={() => toggleToolExpanded(toolKey)}
                            style={{
                              width: '100%',
                              padding: '1rem',
                              backgroundColor: toolData.hasData ? '#f0fdf4' : '#fef2f2',
                              border: 'none',
                              borderBottom: expandedTools[toolKey] ? '1px solid #e5e7eb' : 'none',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              cursor: 'pointer',
                              textAlign: 'left'
                            }}
                          >
                            <div>
                              <h4 style={{
                                margin: 0,
                                fontSize: '1.125rem',
                                fontWeight: '600',
                                color: '#111827'
                              }}>
                                {toolData.hasData ? '✅' : '❌'} {toolData.label}
                              </h4>
                              {!toolData.hasData && (
                                <p style={{
                                  margin: '0.25rem 0 0 0',
                                  fontSize: '0.875rem',
                                  color: '#ef4444'
                                }}>
                                  {toolData.error}
                                </p>
                              )}
                            </div>
                            <span style={{
                              fontSize: '1.5rem',
                              color: '#6b7280',
                              transform: expandedTools[toolKey] ? 'rotate(180deg)' : 'rotate(0)',
                              transition: 'transform 0.2s'
                            }}>
                              ▼
                            </span>
                          </button>

                          {/* Tool Content */}
                          {expandedTools[toolKey] && toolData.hasData && (
                            <div style={{ padding: '1rem' }}>
                              {/* Summarizer Results */}
                              {toolKey === 'summarizer' && toolData.summaries && (
                                <div>
                                  <p style={{ margin: '0 0 1rem 0', color: '#6b7280' }}>
                                    <strong>File:</strong> {toolData.file_name} | <strong>Total Pages:</strong> {toolData.total_pages}
                                  </p>
                                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {toolData.summaries.map((summary, idx) => (
                                      <div
                                        key={idx}
                                        style={{
                                          marginBottom: '1rem',
                                          padding: '0.75rem',
                                          backgroundColor: '#f9fafb',
                                          borderLeft: '3px solid #3b82f6',
                                          borderRadius: '0.25rem'
                                        }}
                                      >
                                        <div style={{ fontWeight: '600', color: '#3b82f6', marginBottom: '0.5rem' }}>
                                          Page {summary.page_number}
                                        </div>
                                        <div style={{ color: '#374151', lineHeight: '1.6' }}>
                                          {summary.summary}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Segmenter Results */}
                              {toolKey === 'segmenter' && toolData.segments && (
                                <div>
                                  <p style={{ margin: '0 0 1rem 0', color: '#6b7280' }}>
                                    <strong>Total Segments:</strong> {toolData.num_segments || toolData.segments.length}
                                  </p>
                                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {toolData.segments.map((segment, idx) => (
                                      <div
                                        key={idx}
                                        style={{
                                          marginBottom: '1rem',
                                          padding: '0.75rem',
                                          backgroundColor: '#fef3c7',
                                          borderLeft: '3px solid #f59e0b',
                                          borderRadius: '0.25rem'
                                        }}
                                      >
                                        <div style={{ fontWeight: '600', color: '#b45309', marginBottom: '0.5rem' }}>
                                          {segment.title || `Segment ${segment.id}`}
                                        </div>
                                        {segment.summary && (
                                          <div style={{ color: '#78350f', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                                            {segment.summary}
                                          </div>
                                        )}
                                        <div style={{ color: '#92400e', fontSize: '0.75rem' }}>
                                          Pages: {segment.page_start} - {segment.page_end}
                                          {segment.tags && segment.tags.length > 0 && (
                                            <span style={{ marginLeft: '1rem' }}>
                                              Tags: {segment.tags.join(', ')}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Document Analysis Results */}
                              {toolKey === 'doc_analysis' && (
                                <div>
                                  {/* Stats */}
                                  {toolData.stats && (
                                    <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#f0f9ff', borderRadius: '0.25rem' }}>
                                      <h5 style={{ margin: '0 0 0.5rem 0', color: '#0369a1', fontWeight: '600' }}>Document Statistics</h5>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.5rem', fontSize: '0.875rem' }}>
                                        {toolData.stats.pages && <div><strong>Pages:</strong> {toolData.stats.pages}</div>}
                                        {toolData.stats.tokens && <div><strong>Tokens:</strong> {toolData.stats.tokens}</div>}
                                        {toolData.stats.language && <div><strong>Language:</strong> {toolData.stats.language}</div>}
                                        {toolData.stats.reading_time_min && <div><strong>Reading Time:</strong> {toolData.stats.reading_time_min} min</div>}
                                      </div>
                                    </div>
                                  )}

                                  {/* Key Points */}
                                  {toolData.key_points && toolData.key_points.length > 0 && (
                                    <div style={{ marginBottom: '1rem' }}>
                                      <h5 style={{ margin: '0 0 0.5rem 0', color: '#111827', fontWeight: '600' }}>Key Points</h5>
                                      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                        {toolData.key_points.map((point, idx) => (
                                          <div key={idx} style={{ marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: '#f9fafb', borderRadius: '0.25rem' }}>
                                            <div style={{ color: '#374151', fontSize: '0.875rem' }}>{point.text}</div>
                                            {point.page && <div style={{ color: '#9ca3af', fontSize: '0.75rem', marginTop: '0.25rem' }}>Page {point.page}</div>}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Outline */}
                                  {toolData.outline && toolData.outline.length > 0 && (
                                    <div style={{ marginBottom: '1rem' }}>
                                      <h5 style={{ margin: '0 0 0.5rem 0', color: '#111827', fontWeight: '600' }}>Document Outline</h5>
                                      <div style={{ maxHeight: '200px', overflowY: 'auto', fontSize: '0.875rem' }}>
                                        {toolData.outline.map((item, idx) => (
                                          <div key={idx} style={{ marginLeft: `${(item.level - 1) * 1}rem`, marginBottom: '0.25rem', color: '#374151' }}>
                                            {item.title} <span style={{ color: '#9ca3af' }}>(p.{item.page})</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Chronology Results */}
                              {toolKey === 'chronology' && toolData.events && (
                                <div>
                                  <p style={{ margin: '0 0 1rem 0', color: '#6b7280' }}>
                                    <strong>Total Events:</strong> {toolData.events.length}
                                    {toolData.start_date && toolData.end_date && (
                                      <span style={{ marginLeft: '1rem' }}>
                                        <strong>Timespan:</strong> {toolData.start_date} to {toolData.end_date}
                                      </span>
                                    )}
                                  </p>
                                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {toolData.events.map((event, idx) => (
                                      <div
                                        key={idx}
                                        style={{
                                          marginBottom: '1rem',
                                          padding: '0.75rem',
                                          backgroundColor: '#fce7f3',
                                          borderLeft: '3px solid #ec4899',
                                          borderRadius: '0.25rem'
                                        }}
                                      >
                                        <div style={{ fontWeight: '600', color: '#9f1239', marginBottom: '0.5rem' }}>
                                          {event.when || event.date} - {event.title}
                                        </div>
                                        {event.desc && (
                                          <div style={{ color: '#831843', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                            {event.desc}
                                          </div>
                                        )}
                                        <div style={{ color: '#9f1239', fontSize: '0.75rem' }}>
                                          Page: {event.page}
                                          {event.entities && event.entities.length > 0 && (
                                            <span style={{ marginLeft: '1rem' }}>
                                              Entities: {event.entities.join(', ')}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Evidence Extractor Results */}
                              {toolKey === 'evidence_extractor' && toolData.aggregated_evidence && (
                                <div>
                                  {toolData.summary && (
                                    <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.25rem' }}>
                                      <div style={{ color: '#065f46', fontSize: '0.875rem' }}>
                                        <strong>Total Evidence:</strong> {toolData.summary.total_evidence || 0}
                                        {toolData.summary.confidence_avg && (
                                          <span style={{ marginLeft: '1rem' }}>
                                            <strong>Avg Confidence:</strong> {(toolData.summary.confidence_avg * 100).toFixed(1)}%
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  )}

                                  {/* Quotes */}
                                  {toolData.aggregated_evidence.quotes && toolData.aggregated_evidence.quotes.length > 0 && (
                                    <div style={{ marginBottom: '1rem' }}>
                                      <h5 style={{ margin: '0 0 0.5rem 0', color: '#111827', fontWeight: '600' }}>Quotes</h5>
                                      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                        {toolData.aggregated_evidence.quotes.slice(0, 5).map((quote, idx) => (
                                          <div key={idx} style={{ marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: '#f9fafb', borderLeft: '3px solid #10b981', borderRadius: '0.25rem' }}>
                                            <div style={{ color: '#374151', fontSize: '0.875rem', fontStyle: 'italic' }}>"{quote.text || quote}"</div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Facts */}
                                  {toolData.aggregated_evidence.facts && toolData.aggregated_evidence.facts.length > 0 && (
                                    <div style={{ marginBottom: '1rem' }}>
                                      <h5 style={{ margin: '0 0 0.5rem 0', color: '#111827', fontWeight: '600' }}>Facts</h5>
                                      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                        {toolData.aggregated_evidence.facts.slice(0, 5).map((fact, idx) => (
                                          <div key={idx} style={{ marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: '#f9fafb', borderRadius: '0.25rem' }}>
                                            <div style={{ color: '#374151', fontSize: '0.875rem' }}>{fact.text || fact}</div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Fallback for tools without custom formatting */}
                              {!['summarizer', 'segmenter', 'doc_analysis', 'chronology', 'evidence_extractor'].includes(toolKey) && (
                                <div style={{
                                  maxHeight: '400px',
                                  overflowY: 'auto',
                                  backgroundColor: '#f9fafb',
                                  padding: '1rem',
                                  borderRadius: '0.25rem',
                                  fontFamily: 'monospace',
                                  fontSize: '0.875rem'
                                }}>
                                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                    {JSON.stringify(toolData, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Organize Stage */}
              {activeStage === 'organize' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <FaFileAlt style={{
                      margin: '0 auto 1rem auto',
                      height: '4rem',
                      width: '4rem',
                      color: '#8b5cf6',
                      display: 'block'
                    }} />
                    <h3 style={{
                      fontSize: '1.5rem',
                      fontWeight: 'bold',
                      color: '#111827',
                      margin: '0 0 0.5rem 0'
                    }}>
                      Organize Stage
                    </h3>
                    <p style={{ color: '#6b7280', margin: '0 0 1rem 0' }}>
                      Structure and categorize your findings from the Discover stage
                    </p>

                    {/* Show selected files info */}
                    {learningPathFileIds.length > 0 && (
                      <div style={{
                        marginTop: '1rem',
                        padding: '0.75rem',
                        backgroundColor: '#f0fdf4',
                        border: '1px solid #10b981',
                        borderRadius: '0.5rem',
                        display: 'inline-block'
                      }}>
                        <span style={{ color: '#065f46', fontWeight: '500' }}>
                          📁 Using {learningPathFileIds.length} file(s) from Discover stage
                        </span>
                      </div>
                    )}

                    {/* Start Stage Button */}
                    <div style={{ marginTop: '1rem' }}>
                      <button
                        type="button"
                        onClick={handleStartStageFromVault}
                        style={{
                          padding: '0.5rem 1rem',
                          backgroundColor: isOrchestrating ? '#9ca3af' : '#8b5cf6',
                          color: 'white',
                          borderRadius: '0.375rem',
                          border: 'none',
                          cursor: isOrchestrating ? 'wait' : 'pointer',
                          transition: 'background-color 0.15s ease-in-out'
                        }}
                        disabled={isOrchestrating || learningPathFileIds.length === 0}
                        onMouseEnter={(e) => !isOrchestrating && (e.currentTarget.style.backgroundColor = '#7c3aed')}
                        onMouseLeave={(e) => !isOrchestrating && (e.currentTarget.style.backgroundColor = '#8b5cf6')}
                        title="Start the Organize stage"
                      >
                        {isOrchestrating ? '⏳ Processing...' : 'Start Stage'}
                      </button>
                    </div>
                  </div>

                  {/* Progress Display */}
                  {orchestrationProgress && (
                    <div style={{
                      marginTop: '1.5rem',
                      backgroundColor: '#faf5ff',
                      border: '1px solid #8b5cf6',
                      borderRadius: '0.5rem',
                      padding: '1rem'
                    }}>
                      <h4 style={{
                        fontWeight: '600',
                        color: '#6b21a8',
                        margin: '0 0 0.75rem 0',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}>
                        <div style={{
                          width: '1rem',
                          height: '1rem',
                          border: '2px solid #8b5cf6',
                          borderTopColor: 'transparent',
                          borderRadius: '50%',
                          animation: orchestrationProgress.status === 'in_progress' || orchestrationProgress.status === 'queued' ? 'spin 1s linear infinite' : 'none'
                        }} />
                        Organize Stage Progress
                      </h4>
                      <div style={{
                        marginTop: '0.75rem',
                        backgroundColor: '#f3e8ff',
                        borderRadius: '0.25rem',
                        height: '0.5rem',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          backgroundColor: '#8b5cf6',
                          height: '100%',
                          width: `${orchestrationProgress.percentage || 0}%`,
                          transition: 'width 0.3s ease-in-out'
                        }} />
                      </div>
                      <p style={{
                        fontSize: '0.75rem',
                        color: '#a78bfa',
                        margin: '0.5rem 0 0 0',
                        textAlign: 'right'
                      }}>
                        {orchestrationProgress.percentage || 0}% Complete {orchestrationProgress.status === 'completed' ? '✓' : ''}
                      </p>
                    </div>
                  )}

                  {/* Tool Cards */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                    gap: '1rem',
                    marginTop: '1.5rem'
                  }}>
                    {[
                      { key: 'collections', icon: '📂', name: 'Collections / Boards', desc: 'Organize documents into smart collections and boards' },
                      { key: 'tags', icon: '🏷️', name: 'Tag & Taxonomy Manager', desc: 'Create hierarchical tags and categorize content' },
                      { key: 'clusters', icon: '🔗', name: 'Cluster Builder', desc: 'Group similar documents using ML clustering' },
                      { key: 'concept_graph', icon: '🕸️', name: 'Concept Graph', desc: 'Visualize relationships between concepts and entities' },
                      { key: 'saved_views', icon: '👁️', name: 'Saved Views', desc: 'Create custom views and filters for your content' }
                    ].map((tool) => {
                      const isCompleted = orchestrationProgress?.tools_completed?.includes(tool.key);
                      const isRunning = orchestrationProgress?.tools_running?.includes(tool.key);

                      return (
                        <div
                          key={tool.key}
                          style={{
                            backgroundColor: 'white',
                            border: `1px solid ${isCompleted ? '#10b981' : isRunning ? '#8b5cf6' : '#e5e7eb'}`,
                            borderRadius: '0.5rem',
                            padding: '1rem',
                            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                            position: 'relative',
                            transition: 'all 0.15s ease-in-out'
                          }}
                        >
                          {isRunning && (
                            <div style={{
                              position: 'absolute',
                              top: '0.75rem',
                              right: '0.75rem',
                              width: '1.25rem',
                              height: '1.25rem',
                              border: '2px solid #8b5cf6',
                              borderTopColor: 'transparent',
                              borderRadius: '50%',
                              animation: 'spin 1s linear infinite'
                            }} />
                          )}

                          {isCompleted && (
                            <FaCheckCircle style={{
                              position: 'absolute',
                              top: '0.75rem',
                              right: '0.75rem',
                              color: '#10b981',
                              fontSize: '1.25rem'
                            }} />
                          )}

                          <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                            {tool.icon} {tool.name}
                          </h4>
                          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                            {tool.desc}
                          </p>

                          {isCompleted && (
                            <div style={{
                              marginTop: '0.75rem',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#d1fae5',
                              color: '#065f46',
                              borderRadius: '0.25rem',
                              fontSize: '0.75rem',
                              fontWeight: '500',
                              display: 'inline-block'
                            }}>
                              ✓ Complete
                            </div>
                          )}

                          {isRunning && (
                            <div style={{
                              marginTop: '0.75rem',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#f3e8ff',
                              color: '#6b21a8',
                              borderRadius: '0.25rem',
                              fontSize: '0.75rem',
                              fontWeight: '500',
                              display: 'inline-block'
                            }}>
                              ⏳ Processing...
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* View Results Button - TO BE IMPLEMENTED */}
                  {learningPathFileIds.length > 0 && stageProgress?.organize?.completed && (
                    <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                      <button
                        onClick={() => alert('Organize results display coming soon!')}
                        style={{
                          backgroundColor: '#8b5cf6',
                          color: 'white',
                          padding: '0.75rem 2rem',
                          border: 'none',
                          borderRadius: '0.5rem',
                          fontSize: '1rem',
                          fontWeight: '600',
                          cursor: 'pointer',
                          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = '#7c3aed';
                          e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = '#8b5cf6';
                          e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                        }}
                      >
                        📊 View Organize Results
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Other Stages Placeholder */}
              {['master', 'create', 'collaborate'].includes(activeStage) && (
                <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                  <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
                    {stages.find(s => s.id === activeStage)?.icon &&
                      React.createElement(stages.find(s => s.id === activeStage).icon, {
                        style: { display: 'inline-block', color: '#9ca3af' }
                      })
                    }
                  </div>
                  <h3 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0 0 0.5rem 0' }}>
                    {stages.find(s => s.id === activeStage)?.name} Stage
                  </h3>
                  <div style={{ color: '#6b7280', fontSize: '1.125rem' }}>
                    {stages.find(s => s.id === activeStage)?.description}
                  </div>

                  {/* Show selected files info */}
                  {learningPathFileIds.length > 0 && (
                    <div style={{
                      marginTop: '1.5rem',
                      padding: '0.75rem',
                      backgroundColor: '#f0fdf4',
                      border: '1px solid #10b981',
                      borderRadius: '0.5rem',
                      display: 'inline-block'
                    }}>
                      <span style={{ color: '#065f46', fontWeight: '500' }}>
                        📁 Using {learningPathFileIds.length} file(s) from Discover stage
                      </span>
                    </div>
                  )}

                  <p style={{ color: '#9ca3af', marginTop: '1rem', fontSize: '0.875rem' }}>
                    Stage implementation coming soon...
                  </p>
                </div>
              )}
            </div>
          </div>

        {/* Current Learning Path Status */}
        {userProgress && (
          <div style={{ 
            backgroundColor: 'white', 
            borderRadius: '0.5rem', 
            boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', 
            border: '1px solid #e5e7eb', 
            padding: '1.5rem' 
          }}>
            <h3 style={{ 
              fontSize: '1.125rem', 
              fontWeight: '600', 
              color: '#111827', 
              marginBottom: '1rem',
              margin: '0 0 1rem 0'
            }}>
              Current Learning Path Status
            </h3>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
              gap: '1rem',
              marginBottom: '1rem'
            }}>
              <div style={{ 
                backgroundColor: '#eff6ff', 
                borderRadius: '0.5rem', 
                padding: '1rem' 
              }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 'bold', 
                  color: '#2563eb',
                  marginBottom: '0.25rem'
                }}>
                  {userProgress.counts?.completed || 0}
                </div>
                <div style={{ 
                  fontSize: '0.875rem', 
                  color: '#1d4ed8' 
                }}>
                  Completed Stages
                </div>
              </div>
              
              <div style={{ 
                backgroundColor: '#fefce8', 
                borderRadius: '0.5rem', 
                padding: '1rem' 
              }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 'bold', 
                  color: '#ca8a04',
                  marginBottom: '0.25rem'
                }}>
                  {userProgress.counts?.unlocked || 0}
                </div>
                <div style={{ 
                  fontSize: '0.875rem', 
                  color: '#a16207' 
                }}>
                  Available Stages
                </div>
              </div>
              
              <div style={{ 
                backgroundColor: '#f0fdf4', 
                borderRadius: '0.5rem', 
                padding: '1rem' 
              }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 'bold', 
                  color: '#15803d',
                  marginBottom: '0.25rem'
                }}>
                  {userProgress.percent_complete || 0}%
                </div>
                <div style={{ 
                  fontSize: '0.875rem', 
                  color: '#166534' 
                }}>
                  Overall Progress
                </div>
              </div>
            </div>
            
            {userProgress.next_stage && (
              <div style={{
                backgroundColor: '#f9fafb',
                borderRadius: '0.375rem',
                padding: '0.75rem',
                borderLeft: '4px solid #3b82f6'
              }}>
                <span style={{ fontSize: '0.875rem', color: '#374151' }}>
                  Next Stage: <strong>{userProgress.next_stage}</strong>
                </span>
              </div>
            )}
          </div>
        )}
      </div>
      </div>

      {/* Custom Notification Toast */}
      {notification && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          backgroundColor: notification.type === 'success' ? '#10b981' : notification.type === 'error' ? '#ef4444' : '#3b82f6',
          color: 'white',
          padding: '1rem 1.5rem',
          borderRadius: '0.5rem',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          zIndex: 9999,
          maxWidth: '400px',
          animation: 'slideInRight 0.3s ease-out',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <span style={{ fontSize: '1.25rem' }}>
            {notification.type === 'success' ? '✓' : notification.type === 'error' ? '✕' : 'ℹ'}
          </span>
          <span style={{ flex: 1, fontSize: '0.95rem' }}>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              fontSize: '1.25rem',
              padding: '0',
              opacity: 0.8,
              transition: 'opacity 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '0.8'}
          >
            ×
          </button>
        </div>
      )}

      {/* Add keyframe animation */}
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default DeepReadingInvestigation;
