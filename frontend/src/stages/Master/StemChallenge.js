import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaFlask, FaCheckCircle, FaTimesCircle, FaRedo, FaDownload, FaPlay, FaCog, FaLightbulb, FaClipboardList } from 'react-icons/fa';
import './StemChallenge.css';
import axiosInstance from '../../utils/axiosInstance';

function StemChallenge() {
    const navigate = useNavigate();

    // State Management
    const [tab, setTab] = useState('generate'); // 'generate' | 'solve' | 'review'
    const [source, setSource] = useState('vault'); // 'vault' | 'upload'

    // File Selection
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileIds, setSelectedFileIds] = useState([]);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    // Challenge Configuration
    const [numChallenges, setNumChallenges] = useState(5);
    const [difficulty, setDifficulty] = useState('medium');
    const [challengeType, setChallengeType] = useState('mixed');

    // Progress Tracking
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'completed' | 'error'
    const [progress, setProgress] = useState(0);
    const [progressId, setProgressId] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');

    // Challenge Data
    const [challengesData, setChallengesData] = useState(null);
    const [currentChallenge, setCurrentChallenge] = useState(0);
    const [showHints, setShowHints] = useState([]);
    const [showSolution, setShowSolution] = useState(false);
    const [userSolutions, setUserSolutions] = useState({});
    const [challengesCompleted, setChallengesCompleted] = useState(false);

    // Fetch vault files on mount
    useEffect(() => {
        if (source === 'vault') {
            fetchVaultFiles();
        }
    }, [source]);

    // Poll for progress
    useEffect(() => {
        let interval;
        if (status === 'generating' && progressId) {
            interval = setInterval(() => {
                pollProgress();
            }, 1200);
        }
        return () => {
            if (interval) clearInterval(interval);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [status, progressId]);

    const fetchVaultFiles = async () => {
        try {
            const res = await axiosInstance.get('/upload/files');
            const files = res.data.files || [];

            // Normalize file structure
            const normalizedFiles = files.map(file => ({
                id: file.fileId || file.id,
                name: file.name,
                stored_name: file.stored_name
            }));

            setVaultFiles(normalizedFiles);
        } catch (error) {
            console.error('Error fetching vault files:', error);
            setErrorMessage('Failed to load Knowledge Vault files');
        }
    };

    const handleFileUpload = (e) => {
        const files = Array.from(e.target.files);
        setUploadedFiles(files);
    };

    const toggleFileSelection = (fileId) => {
        setSelectedFileIds(prev =>
            prev.includes(fileId)
                ? prev.filter(id => id !== fileId)
                : [...prev, fileId]
        );
    };

    const startChallengeGeneration = async () => {
        try {
            setStatus('generating');
            setProgress(0);
            setErrorMessage('');

            const token = localStorage.getItem('access_token');
            const userId = localStorage.getItem('user_id');

            let fileId;

            if (source === 'vault') {
                if (selectedFileIds.length === 0) {
                    setErrorMessage('Please select at least one file');
                    setStatus('idle');
                    return;
                }
                // Use first selected file
                fileId = selectedFileIds[0];
            } else {
                if (uploadedFiles.length === 0) {
                    setErrorMessage('Please upload at least one file');
                    setStatus('idle');
                    return;
                }
                // Upload file first
                const formData = new FormData();
                formData.append('file', uploadedFiles[0]);
                formData.append('user_id', userId);

                const uploadResponse = await axiosInstance.post('/upload/upload', formData, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'multipart/form-data'
                    }
                });

                fileId = uploadResponse.data.results[0].file_id;
            }

            // Start challenge generation
            const response = await axiosInstance.post('/master/stem_challenge/start', {
                file_id: fileId,
                user_id: userId,
                num_challenges: numChallenges,
                difficulty: difficulty,
                challenge_type: challengeType
            }, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-User-Id': userId
                }
            });

            if (response.data.progress_id) {
                setProgressId(response.data.progress_id);
            }
        } catch (error) {
            console.error('Error starting challenge generation:', error);
            setErrorMessage(error.response?.data?.error || 'Failed to start challenge generation');
            setStatus('error');
        }
    };

    const fetchChallengeResults = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const userId = localStorage.getItem('user_id');
            const fileId = selectedFileIds[0];

            const response = await axiosInstance.get('/master/stem_challenge/results', {
                params: {
                    file_id: fileId,
                    num_challenges: numChallenges,
                    difficulty: difficulty,
                    challenge_type: challengeType
                },
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-User-Id': userId
                }
            });

            setChallengesData(response.data.challenges_set);
            setTab('solve');
        } catch (error) {
            console.error('Error fetching challenge results:', error);
            setErrorMessage('Failed to fetch challenges');
            setStatus('error');
        }
    };

    const pollProgress = async () => {
        if (!progressId) return;

        try {
            const token = localStorage.getItem('access_token');
            const response = await axiosInstance.get(`/master/stem_challenge/progress/${progressId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const { status: taskStatus, percentage } = response.data;
            setProgress(percentage || 0);

            if (taskStatus === 'completed') {
                setStatus('completed');
                await fetchChallengeResults();
            } else if (taskStatus === 'failed') {
                setStatus('error');
                setErrorMessage('Challenge generation failed');
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    };

    const handleShowHint = (hintIndex) => {
        if (!showHints.includes(hintIndex)) {
            setShowHints(prev => [...prev, hintIndex]);
        }
    };

    const handleShowSolution = () => {
        setShowSolution(true);
    };

    const handleSolutionChange = (e) => {
        setUserSolutions(prev => ({
            ...prev,
            [currentChallenge]: e.target.value
        }));
    };

    const handleNext = () => {
        if (currentChallenge < challengesData.challenges.length - 1) {
            setCurrentChallenge(prev => prev + 1);
            setShowHints([]);
            setShowSolution(false);
        }
    };

    const handlePrevious = () => {
        if (currentChallenge > 0) {
            setCurrentChallenge(prev => prev - 1);
            setShowHints([]);
            setShowSolution(false);
        }
    };

    const handleFinishChallenges = () => {
        setChallengesCompleted(true);
        setTab('review');
    };

    const handleRestart = () => {
        setTab('generate');
        setStatus('idle');
        setProgress(0);
        setProgressId(null);
        setChallengesData(null);
        setCurrentChallenge(0);
        setShowHints([]);
        setShowSolution(false);
        setUserSolutions({});
        setChallengesCompleted(false);
        setErrorMessage('');
    };

    const handleRetakeChallenges = () => {
        setTab('solve');
        setCurrentChallenge(0);
        setShowHints([]);
        setShowSolution(false);
        setUserSolutions({});
        setChallengesCompleted(false);
    };

    const downloadChallenges = () => {
        const challengeExport = {
            title: challengesData.title,
            difficulty: challengesData.difficulty,
            challenge_type: challengesData.challenge_type,
            challenges: challengesData.challenges.map((ch, idx) => ({
                number: idx + 1,
                type: ch.type,
                problem: ch.problem,
                constraints: ch.constraints,
                hints: ch.hints,
                solution_approach: ch.solution_approach,
                user_solution: userSolutions[idx] || ''
            }))
        };

        const blob = new Blob([JSON.stringify(challengeExport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `stem_challenges_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const currentCh = challengesData?.challenges[currentChallenge];
    const hasSolution = userSolutions[currentChallenge]?.trim().length > 0;

    return (
        <div className="stem-challenge-container">
            <div className="stem-challenge-header">
                <button className="back-button" onClick={() => navigate('/master')}>
                    ← Back to Master
                </button>
                <h1><FaFlask /> STEM Challenge Generator</h1>
                <p className="subtitle">Generate challenging STEM problems from your documents</p>
            </div>

            {/* Tab Navigation */}
            <div className="stem-tabs">
                <button
                    className={`stem-tab ${tab === 'generate' ? 'active' : ''}`}
                    onClick={() => setTab('generate')}
                    disabled={status === 'generating'}
                >
                    <FaCog /> Generate Challenges
                </button>
                <button
                    className={`stem-tab ${tab === 'solve' ? 'active' : ''}`}
                    onClick={() => setTab('solve')}
                    disabled={!challengesData || challengesCompleted}
                >
                    <FaPlay /> Solve Challenges
                </button>
                <button
                    className={`stem-tab ${tab === 'review' ? 'active' : ''}`}
                    onClick={() => setTab('review')}
                    disabled={!challengesCompleted}
                >
                    <FaClipboardList /> Review
                </button>
            </div>

            {/* Generate Tab */}
            {tab === 'generate' && (
                <div className="generate-tab">
                    {status === 'idle' && (
                        <>
                            {/* Challenge Configuration */}
                            <div className="challenge-config-section">
                                <h2>Challenge Configuration</h2>
                                <div className="config-grid">
                                    <div className="config-item">
                                        <label>Number of Challenges</label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="10"
                                            value={numChallenges}
                                            onChange={(e) => setNumChallenges(Math.min(10, Math.max(1, parseInt(e.target.value) || 5)))}
                                        />
                                    </div>
                                    <div className="config-item">
                                        <label>Difficulty Level</label>
                                        <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                                            <option value="easy">Easy</option>
                                            <option value="medium">Medium</option>
                                            <option value="hard">Hard</option>
                                        </select>
                                    </div>
                                    <div className="config-item">
                                        <label>Challenge Type</label>
                                        <select value={challengeType} onChange={(e) => setChallengeType(e.target.value)}>
                                            <option value="mixed">Mixed</option>
                                            <option value="problem_solving">Problem Solving</option>
                                            <option value="design">Design</option>
                                            <option value="experiment">Experiment</option>
                                            <option value="coding">Coding</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            {/* Source Selection */}
                            <div className="source-selection">
                                <h2>Select Source</h2>
                                <div className="source-buttons">
                                    <button
                                        className={`source-btn ${source === 'vault' ? 'active' : ''}`}
                                        onClick={() => setSource('vault')}
                                    >
                                        Knowledge Vault
                                    </button>
                                    <button
                                        className={`source-btn ${source === 'upload' ? 'active' : ''}`}
                                        onClick={() => setSource('upload')}
                                    >
                                        Upload Files
                                    </button>
                                </div>
                            </div>

                            {/* File Selection */}
                            {source === 'vault' ? (
                                <div className="file-selection-section">
                                    <h3>Select File from Knowledge Vault</h3>
                                    <div className="vault-files-list">
                                        {vaultFiles.length === 0 ? (
                                            <p className="no-files">No files in Knowledge Vault</p>
                                        ) : (
                                            vaultFiles.map(file => (
                                                <div
                                                    key={file.id}
                                                    className={`vault-file-item ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                                                    onClick={() => toggleFileSelection(file.id)}
                                                >
                                                    <input
                                                        type="radio"
                                                        checked={selectedFileIds.includes(file.id)}
                                                        onChange={() => toggleFileSelection(file.id)}
                                                    />
                                                    <div className="file-info">
                                                        <span className="file-name">{file.name}</span>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="file-upload-section">
                                    <h3>Upload File</h3>
                                    <div className="upload-area">
                                        <input
                                            type="file"
                                            id="file-upload"
                                            onChange={handleFileUpload}
                                            accept=".pdf,.docx,.txt"
                                        />
                                        <label htmlFor="file-upload" className="upload-label">
                                            {uploadedFiles.length > 0
                                                ? uploadedFiles[0].name
                                                : 'Click to upload or drag and drop'}
                                        </label>
                                    </div>
                                </div>
                            )}

                            {errorMessage && (
                                <div className="error-message">
                                    <FaTimesCircle /> {errorMessage}
                                </div>
                            )}

                            <button
                                className="generate-btn"
                                onClick={startChallengeGeneration}
                                disabled={(source === 'vault' && selectedFileIds.length === 0) ||
                                         (source === 'upload' && uploadedFiles.length === 0)}
                            >
                                <FaPlay /> Generate Challenges
                            </button>
                        </>
                    )}

                    {status === 'generating' && (
                        <div className="progress-section">
                            <h2>Generating STEM Challenges...</h2>
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                            </div>
                            <p className="progress-text">{progress}% complete</p>
                        </div>
                    )}

                    {status === 'completed' && (
                        <div className="success-message">
                            <FaCheckCircle /> Challenges generated successfully! Switch to "Solve Challenges" tab.
                        </div>
                    )}

                    {status === 'error' && (
                        <div className="error-section">
                            <FaTimesCircle /> {errorMessage}
                            <button onClick={handleRestart} className="retry-btn">
                                <FaRedo /> Try Again
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Solve Tab */}
            {tab === 'solve' && challengesData && (
                <div className="solve-tab">
                    <div className="challenge-header-info">
                        <h2>{challengesData.title}</h2>
                        <div className="challenge-meta">
                            <span className="difficulty-badge">{challengesData.difficulty}</span>
                            <span className="type-badge">{currentCh?.type.replace('_', ' ')}</span>
                            <span className="challenge-counter">
                                Challenge {currentChallenge + 1} of {challengesData.challenges.length}
                            </span>
                        </div>
                    </div>

                    <div className="challenge-card">
                        <h3 className="challenge-problem">{currentCh?.problem}</h3>

                        {/* Constraints */}
                        <div className="constraints-section">
                            <h4><FaClipboardList /> Constraints & Requirements</h4>
                            <ul className="constraints-list">
                                {currentCh?.constraints.map((constraint, idx) => (
                                    <li key={idx}>{constraint}</li>
                                ))}
                            </ul>
                        </div>

                        {/* User Solution Input */}
                        <div className="solution-input-section">
                            <h4>Your Solution</h4>
                            <textarea
                                className="solution-textarea"
                                placeholder="Type your solution here... Show your work and reasoning."
                                value={userSolutions[currentChallenge] || ''}
                                onChange={handleSolutionChange}
                                rows={8}
                            />
                        </div>

                        {/* Hints */}
                        <div className="hints-section">
                            <h4><FaLightbulb /> Hints</h4>
                            {currentCh?.hints.map((hint, idx) => (
                                <div key={idx} className="hint-item">
                                    {showHints.includes(idx) ? (
                                        <p className="hint-text">{hint}</p>
                                    ) : (
                                        <button
                                            className="show-hint-btn"
                                            onClick={() => handleShowHint(idx)}
                                        >
                                            Show Hint {idx + 1}
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Solution Approach */}
                        {!showSolution && (
                            <button className="show-solution-btn" onClick={handleShowSolution}>
                                Show Solution Approach
                            </button>
                        )}

                        {showSolution && currentCh?.solution_approach && (
                            <div className="solution-box">
                                <strong>Solution Approach:</strong>
                                <p>{currentCh.solution_approach}</p>
                            </div>
                        )}
                    </div>

                    <div className="challenge-navigation">
                        <button
                            onClick={handlePrevious}
                            disabled={currentChallenge === 0}
                            className="nav-btn"
                        >
                            ← Previous
                        </button>

                        <div className="progress-dots">
                            {challengesData.challenges.map((_, idx) => (
                                <span
                                    key={idx}
                                    className={`dot ${idx === currentChallenge ? 'active' : ''} ${userSolutions[idx]?.trim() ? 'answered' : ''}`}
                                    onClick={() => {
                                        setCurrentChallenge(idx);
                                        setShowHints([]);
                                        setShowSolution(false);
                                    }}
                                />
                            ))}
                        </div>

                        {currentChallenge < challengesData.challenges.length - 1 ? (
                            <button onClick={handleNext} className="nav-btn">
                                Next →
                            </button>
                        ) : (
                            <button onClick={handleFinishChallenges} className="submit-btn">
                                Finish & Review
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Review Tab */}
            {tab === 'review' && challengesCompleted && (
                <div className="review-tab">
                    <div className="review-header">
                        <h2>Challenge Review</h2>
                        <div className="completion-stats">
                            <p className="stat-item">
                                <strong>{Object.keys(userSolutions).filter(k => userSolutions[k]?.trim()).length}</strong>
                                <span> / {challengesData.challenges.length} Completed</span>
                            </p>
                        </div>
                    </div>

                    <div className="review-details">
                        <h3>Your Solutions</h3>
                        {challengesData.challenges.map((ch, idx) => {
                            const userSolution = userSolutions[idx];
                            const hasUserSolution = userSolution?.trim().length > 0;

                            return (
                                <div key={idx} className={`review-item ${hasUserSolution ? 'completed' : 'incomplete'}`}>
                                    <div className="review-item-header">
                                        {hasUserSolution ? <FaCheckCircle /> : <FaTimesCircle />}
                                        <h4>Challenge {idx + 1} - {ch.type.replace('_', ' ')}</h4>
                                    </div>
                                    <p className="review-problem">{ch.problem}</p>

                                    <div className="review-constraints">
                                        <strong>Constraints:</strong>
                                        <ul>
                                            {ch.constraints.map((c, cidx) => (
                                                <li key={cidx}>{c}</li>
                                            ))}
                                        </ul>
                                    </div>

                                    {hasUserSolution && (
                                        <div className="user-solution-display">
                                            <strong>Your Solution:</strong>
                                            <p>{userSolution}</p>
                                        </div>
                                    )}

                                    <div className="solution-approach-display">
                                        <strong>Solution Approach:</strong>
                                        <p>{ch.solution_approach}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    <div className="review-actions">
                        <button onClick={handleRetakeChallenges} className="action-btn">
                            <FaRedo /> Retry Challenges
                        </button>
                        <button onClick={downloadChallenges} className="action-btn">
                            <FaDownload /> Download Challenges
                        </button>
                        <button onClick={handleRestart} className="action-btn">
                            Create New Challenges
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default StemChallenge;
