import React, { useState, useEffect, useCallback } from 'react';
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
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isFileUploaded, setIsFileUploaded] = useState(false);
  const [activeStage, setActiveStage] = useState('discover');
  const [userProgress, setUserProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stageProgress, setStageProgress] = useState({});
  const [isInitialized, setIsInitialized] = useState(false);
  
  // New states for learning paths management
  const [userLearningPaths, setUserLearningPaths] = useState([]);
  const [currentLearningPathId, setCurrentLearningPathId] = useState(null); // Start with null

  // --- Vault integration (reused from Summarizer.js style) ---
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedVaultFile, setSelectedVaultFile] = useState('');
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [uploading, setUploading] = useState(false);

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
    return m?.file_id || m?.id || null;
  };

  useEffect(() => { fetchVaultFiles(); }, [fetchVaultFiles]);
  
  const handleInlineUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const r = await axiosInstance.post('/upload/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const storedAs = r.data?.stored_as || r.data?.name;
      await fetchVaultFiles();
      setSelectedVaultFile(storedAs || '');
      setSelectedFileId(resolveFileId(storedAs || ''));
    } catch {
      // optionally toast
    } finally {
      setUploading(false);
    }
  };

  const handleStartStageFromVault = async () => {
    const fid = selectedFileId || resolveFileId(selectedVaultFile);
    if (!fid) {
      alert('Please upload or choose a file from the Knowledge Vault.');
      return;
    }
    setUploadedFile({ id: fid });
    setIsFileUploaded(true);
    await startStage(activeStage, [fid]);  // uses existing function
  };
  // --- End vault integration ---

  // Deep Reading Investigation Learning Path ID (current selected one, can be null)
  const LEARNING_PATH_ID = currentLearningPathId;

  // Fetch user's learning paths
  const fetchUserLearningPaths = async () => {
    try {
      const response = await axiosInstance.get('/learning_paths/');
      setUserLearningPaths(response.data.items || []);
    } catch (err) {
      console.error('Error fetching user learning paths:', err);
    }
  };

  // Load specific learning path state
  const loadLearningPathState = async (pathId) => {
    try {
      setLoading(true);
      setCurrentLearningPathId(pathId);
      
      const statusResponse = await axiosInstance.get(`/learning_paths/${pathId}/status`);
      
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
        
        // If user has file IDs, assume they have uploaded files
        if (status.file_ids && status.file_ids.length > 0) {
          setIsFileUploaded(true);
          setUploadedFile({ id: status.file_ids[0] });
        } else {
          setIsFileUploaded(false);
          setUploadedFile(null);
        }
      }
    } catch (err) {
      console.error('Error loading learning path state:', err);
      setUserProgress(null);
    } finally {
      setLoading(false);
    }
  };

  // Reset to default state (no learning path selected)
  const resetToDefaultState = () => {
    setCurrentLearningPathId(null);
    setUserProgress(null);
    setStageProgress({});
    setActiveStage('discover');
    setIsFileUploaded(false);
    setUploadedFile(null);
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

  // Initialize the learning path - fetch user's learning paths but don't auto-load any specific one
  useEffect(() => {
    const initializeLearningPath = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch user's learning paths first
        await fetchUserLearningPaths();
        
        // Don't auto-load any learning path - let user choose
        resetToDefaultState();
        
      } catch (err) {
        console.error('Error initializing learning path:', err);
        setUserProgress(null);
      } finally {
        setLoading(false);
        setIsInitialized(true);
      }
    };

    initializeLearningPath();
  }, []);

  // Start/update a stage (this will handle enrollment automatically)
  const startStage = async (stage, fileIds = []) => {
    if (!LEARNING_PATH_ID) {
      alert('Please select a learning path first!');
      return;
    }
    
    try {
      const stageData = {
        file_ids: fileIds
      };

      await axiosInstance.post(`/learning_paths/${LEARNING_PATH_ID}/start-stage/${stage}`, stageData);
      
      // Refresh the learning path state from backend
      await loadLearningPathState(LEARNING_PATH_ID);
      
    } catch (err) {
      console.error('Error starting stage:', err);
      // Don't block user interaction if API call fails
    }
  };

  // Handle stage tab changes - only switch if stage is unlocked, but don't trigger any API calls
  const handleStageChange = async (stageId) => {
    if (!currentLearningPathId) {
      // If no learning path selected, only allow discover stage
      if (stageId === 'discover') {
        setActiveStage(stageId);
      } else {
        alert('Please select a learning path first to access other stages!');
      }
      return;
    }
    
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
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      {/* Header */}
      <div style={{ backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                Learning Path Navigator
              </h1>
              <p style={{ marginTop: '0.5rem', fontSize: '1.125rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                Manage and navigate your learning journey through structured educational paths
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FaGraduationCap style={{ height: '1.25rem', width: '1.25rem', color: '#9ca3af' }} />
              <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                {userLearningPaths.length} Learning Path{userLearningPaths.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>

        {/* Learning Paths Selection at Bottom */}
        <div style={{ 
          backgroundColor: 'white', 
          borderRadius: '0.5rem', 
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
          padding: '1.5rem'
        }}>
          <h3 style={{ 
            fontSize: '1.125rem', 
            fontWeight: '600', 
            color: '#111827', 
            marginBottom: '1rem',
            margin: '0 0 1rem 0'
          }}>
            Choose a Learning Path
          </h3>
          
          {userLearningPaths.length > 0 ? (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
              gap: '1rem' 
            }}>
              {userLearningPaths.map((learningPath) => (
                <button
                  key={learningPath.id}
                  onClick={() => loadLearningPathState(learningPath.id)}
                  style={{ 
                    backgroundColor: learningPath.id === currentLearningPathId ? '#eff6ff' : '#f9fafb', 
                    border: learningPath.id === currentLearningPathId ? '2px solid #3b82f6' : '1px solid #e5e7eb', 
                    borderRadius: '0.5rem', 
                    padding: '1rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease-in-out',
                    width: '100%'
                  }}
                  onMouseEnter={(e) => {
                    if (learningPath.id !== currentLearningPathId) {
                      e.target.style.backgroundColor = '#f3f4f6';
                      e.target.style.borderColor = '#d1d5db';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (learningPath.id !== currentLearningPathId) {
                      e.target.style.backgroundColor = '#f9fafb';
                      e.target.style.borderColor = '#e5e7eb';
                    }
                  }}
                >
                  <h4 style={{ 
                    fontWeight: '600', 
                    color: '#111827', 
                    marginBottom: '0.5rem',
                    margin: '0 0 0.5rem 0'
                  }}>
                    {learningPath.title}
                  </h4>
                  <p style={{ 
                    fontSize: '0.875rem', 
                    color: '#6b7280', 
                    marginBottom: '0.75rem',
                    margin: '0 0 0.75rem 0'
                  }}>
                    {learningPath.description || 'No description available'}
                  </p>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{ 
                      fontSize: '0.75rem', 
                      color: '#9ca3af' 
                    }}>
                      Est. {learningPath.est_minutes || 60} min
                    </span>
                    {learningPath.id === currentLearningPathId && (
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        backgroundColor: '#10b981',
                        color: 'white',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem'
                      }}>
                        Active
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '2rem',
              color: '#6b7280'
            }}>
              <p>No learning paths found. You may need to enroll in learning paths first.</p>
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '2rem 1.5rem' }}>
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
                // If no learning path selected, only discover is unlocked
                const isUnlocked = currentLearningPathId ? 
                  (stageStatus?.visited || stage.id === 'discover') : 
                  (stage.id === 'discover');
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
                  {!currentLearningPathId ? (
                    <div style={{
                      backgroundColor: '#f0f9ff',
                      border: '1px solid #0ea5e9',
                      borderRadius: '0.5rem',
                      padding: '1rem',
                      textAlign: 'center'
                    }}>
                      <p style={{ color: '#0c4a6e', margin: 0, fontSize: '1rem' }}>
                        📚 Please select a learning path below to begin your journey and unlock the other stages.
                      </p>
                    </div>
                  ) : (
                    <div style={{
                      backgroundColor: '#ecfdf5',
                      border: '1px solid #10b981',
                      borderRadius: '0.5rem',
                      padding: '1rem',
                      textAlign: 'center'
                    }}>
                      <p style={{ color: '#065f46', margin: 0, fontSize: '1rem' }}>
                        ✅ Learning path selected! You can now upload and organize your files.
                      </p>
                    </div>
                  )}
                  
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
                          cursor: 'pointer',
                          background: '#f9fafb'
                        }}
                        title="Upload a file into Knowledge Vault"
                      >
                        ⬆️ Upload
                        <input
                          id="lpVaultUpload"
                          type="file"
                          onChange={handleInlineUpload}
                          style={{ display: 'none' }}
                          disabled={uploading}
                        />
                      </label>

                      {/* Vault select */}
                      <select
                        value={selectedVaultFile}
                        onChange={(e) => {
                          setSelectedVaultFile(e.target.value);
                          setSelectedFileId(resolveFileId(e.target.value));
                        }}
                        style={{
                          minWidth: 260,
                          padding: '0.4rem 0.5rem',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.375rem',
                          background: 'white',
                          color: '#111827'
                        }}
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
                          backgroundColor: '#2563eb',
                          color: 'white',
                          borderRadius: '0.375rem',
                          border: 'none',
                          cursor: 'pointer',
                          transition: 'background-color 0.15s ease-in-out'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#1d4ed8'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
                        title="Start the Discover stage with the selected file"
                      >
                        Start Stage
                      </button>
                    </div>
                  </div>
                  
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
                    gap: '1rem' 
                  }}>
                    {/* 1) Summarizer */}
                    <div style={{ 
                      backgroundColor: 'white', 
                      border: '1px solid #e5e7eb', 
                      borderRadius: '0.5rem', 
                      padding: '1rem',
                      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                      transition: 'box-shadow 0.15s ease-in-out'
                    }}>
                      <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                        📄 Document Summarizer
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                        Generate comprehensive summaries of your document
                      </p>
                    </div>

                    {/* 2) Segmenter (tba) */}
                    <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)' }}>
                      <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                        ✂️ Segmenter
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                        Split content into coherent sections and chunks
                      </p>
                    </div>

                    {/* 3) Document Analysis (tba) */}
                    <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)' }}>
                      <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                        🔎 Document Analysis
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                        Understand structure, themes, entities, and insights
                      </p>
                    </div>

                    {/* 4) Evidence Extractor (tba) */}
                    <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)' }}>
                      <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                        📑 Evidence Extractor
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                        Pull verifiable claims, facts, citations, and quotes
                      </p>
                    </div>

                    {/* 5) Chronology (strict) (tba) */}
                    <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)' }}>
                      <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                        ⏱️ Chronology (Strict)
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                        Build strict chronological timelines from events and dates
                      </p>
                    </div>

                    {/* 6) Comparison (tba) */}
                    <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)' }}>
                      <h4 style={{ fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0' }}>
                        🔁 Comparison
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0 }}>
                        Compare sections, versions, or multiple documents
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Add a simple fallback for other stages */}
              {activeStage !== 'discover' && (
                <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                  <div style={{ color: '#9ca3af', fontSize: '1.125rem' }}>
                    {stages.find(s => s.id === activeStage)?.description}
                  </div>
                  <p style={{ color: '#6b7280', marginTop: '0.5rem' }}>
                    Tools coming soon...
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
  );
};

export default DeepReadingInvestigation;
