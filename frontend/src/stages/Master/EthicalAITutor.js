import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBrain, FaCheckCircle, FaTimesCircle, FaRedo, FaDownload, FaPlay, FaCog, FaUsers, FaBalanceScale } from 'react-icons/fa';
import './EthicalAITutor.css';
import axiosInstance from '../../utils/axiosInstance';

function EthicalAITutor() {
    const navigate = useNavigate();

    // State Management
    const [tab, setTab] = useState('generate'); // 'generate' | 'explore' | 'review'
    const [source, setSource] = useState('vault'); // 'vault' | 'upload'

    // File Selection
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileIds, setSelectedFileIds] = useState([]);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    // Scenario Configuration
    const [numScenarios, setNumScenarios] = useState(5);
    const [difficulty, setDifficulty] = useState('medium');
    const [scenarioType, setScenarioType] = useState('mixed');

    // Progress Tracking
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'completed' | 'error'
    const [progress, setProgress] = useState(0);
    const [progressId, setProgressId] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');

    // Scenario Data
    const [scenariosData, setScenariosData] = useState(null);
    const [currentScenario, setCurrentScenario] = useState(0);
    const [showConsiderations, setShowConsiderations] = useState(false);
    const [showApproach, setShowApproach] = useState(false);
    const [userResponses, setUserResponses] = useState({});
    const [scenariosCompleted, setScenariosCompleted] = useState(false);

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

    const startScenarioGeneration = async () => {
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

            // Start scenario generation
            const response = await axiosInstance.post('/master/ethical_ai_tutor/start', {
                file_id: fileId,
                user_id: userId,
                num_scenarios: numScenarios,
                difficulty: difficulty,
                scenario_type: scenarioType
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
            console.error('Error starting scenario generation:', error);
            setErrorMessage(error.response?.data?.error || 'Failed to start scenario generation');
            setStatus('error');
        }
    };

    const fetchScenarioResults = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const userId = localStorage.getItem('user_id');
            const fileId = selectedFileIds[0];

            const response = await axiosInstance.get('/master/ethical_ai_tutor/results', {
                params: {
                    file_id: fileId,
                    num_scenarios: numScenarios,
                    difficulty: difficulty,
                    scenario_type: scenarioType
                },
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-User-Id': userId
                }
            });

            setScenariosData(response.data.scenarios_set);
            setTab('explore');
        } catch (error) {
            console.error('Error fetching scenario results:', error);
            setErrorMessage('Failed to fetch scenarios');
            setStatus('error');
        }
    };

    const pollProgress = async () => {
        if (!progressId) return;

        try {
            const token = localStorage.getItem('access_token');
            const response = await axiosInstance.get(`/master/ethical_ai_tutor/progress/${progressId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const { status: taskStatus, percentage } = response.data;
            setProgress(percentage || 0);

            if (taskStatus === 'completed') {
                setStatus('completed');
                await fetchScenarioResults();
            } else if (taskStatus === 'failed') {
                setStatus('error');
                setErrorMessage('Scenario generation failed');
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    };

    const handleShowConsiderations = () => {
        setShowConsiderations(true);
    };

    const handleShowApproach = () => {
        setShowApproach(true);
    };

    const handleResponseChange = (e) => {
        setUserResponses(prev => ({
            ...prev,
            [currentScenario]: e.target.value
        }));
    };

    const handleNext = () => {
        if (currentScenario < scenariosData.scenarios.length - 1) {
            setCurrentScenario(prev => prev + 1);
            setShowConsiderations(false);
            setShowApproach(false);
        }
    };

    const handlePrevious = () => {
        if (currentScenario > 0) {
            setCurrentScenario(prev => prev - 1);
            setShowConsiderations(false);
            setShowApproach(false);
        }
    };

    const handleFinishScenarios = () => {
        setScenariosCompleted(true);
        setTab('review');
    };

    const handleRestart = () => {
        setTab('generate');
        setStatus('idle');
        setProgress(0);
        setProgressId(null);
        setScenariosData(null);
        setCurrentScenario(0);
        setShowConsiderations(false);
        setShowApproach(false);
        setUserResponses({});
        setScenariosCompleted(false);
        setErrorMessage('');
    };

    const handleRetakeScenarios = () => {
        setTab('explore');
        setCurrentScenario(0);
        setShowConsiderations(false);
        setShowApproach(false);
        setUserResponses({});
        setScenariosCompleted(false);
    };

    const downloadScenarios = () => {
        const scenarioExport = {
            title: scenariosData.title,
            difficulty: scenariosData.difficulty,
            scenario_type: scenariosData.scenario_type,
            scenarios: scenariosData.scenarios.map((sc, idx) => ({
                number: idx + 1,
                type: sc.type,
                scenario: sc.scenario,
                stakeholders: sc.stakeholders,
                ethical_considerations: sc.ethical_considerations,
                discussion_questions: sc.discussion_questions,
                recommended_approach: sc.recommended_approach,
                user_response: userResponses[idx] || ''
            }))
        };

        const blob = new Blob([JSON.stringify(scenarioExport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ethical_ai_scenarios_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const currentSc = scenariosData?.scenarios[currentScenario];
    const hasResponse = userResponses[currentScenario]?.trim().length > 0;

    return (
        <div className="ethical-ai-container">
            <div className="ethical-ai-header">
                <button className="back-button" onClick={() => navigate('/master')}>
                    ← Back to Master
                </button>
                <h1><FaBrain /> Ethical AI Tutor</h1>
                <p className="subtitle">Explore ethical dilemmas and decision-making in AI systems</p>
            </div>

            {/* Tab Navigation */}
            <div className="ethical-tabs">
                <button
                    className={`ethical-tab ${tab === 'generate' ? 'active' : ''}`}
                    onClick={() => setTab('generate')}
                    disabled={status === 'generating'}
                >
                    <FaCog /> Generate Scenarios
                </button>
                <button
                    className={`ethical-tab ${tab === 'explore' ? 'active' : ''}`}
                    onClick={() => setTab('explore')}
                    disabled={!scenariosData || scenariosCompleted}
                >
                    <FaPlay /> Explore Scenarios
                </button>
                <button
                    className={`ethical-tab ${tab === 'review' ? 'active' : ''}`}
                    onClick={() => setTab('review')}
                    disabled={!scenariosCompleted}
                >
                    <FaBalanceScale /> Review
                </button>
            </div>

            {/* Generate Tab */}
            {tab === 'generate' && (
                <div className="generate-tab">
                    {status === 'idle' && (
                        <>
                            {/* Scenario Configuration */}
                            <div className="scenario-config-section">
                                <h2>Scenario Configuration</h2>
                                <div className="config-grid">
                                    <div className="config-item">
                                        <label>Number of Scenarios</label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="10"
                                            value={numScenarios}
                                            onChange={(e) => setNumScenarios(Math.min(10, Math.max(1, parseInt(e.target.value) || 5)))}
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
                                        <label>Scenario Type</label>
                                        <select value={scenarioType} onChange={(e) => setScenarioType(e.target.value)}>
                                            <option value="mixed">Mixed</option>
                                            <option value="bias_fairness">Bias & Fairness</option>
                                            <option value="privacy_security">Privacy & Security</option>
                                            <option value="transparency_accountability">Transparency & Accountability</option>
                                            <option value="safety_reliability">Safety & Reliability</option>
                                            <option value="social_impact">Social Impact</option>
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
                                onClick={startScenarioGeneration}
                                disabled={(source === 'vault' && selectedFileIds.length === 0) ||
                                         (source === 'upload' && uploadedFiles.length === 0)}
                            >
                                <FaPlay /> Generate Scenarios
                            </button>
                        </>
                    )}

                    {status === 'generating' && (
                        <div className="progress-section">
                            <h2>Generating Ethical AI Scenarios...</h2>
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                            </div>
                            <p className="progress-text">{progress}% complete</p>
                        </div>
                    )}

                    {status === 'completed' && (
                        <div className="success-message">
                            <FaCheckCircle /> Scenarios generated successfully! Switch to "Explore Scenarios" tab.
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

            {/* Explore Tab */}
            {tab === 'explore' && scenariosData && (
                <div className="explore-tab">
                    <div className="scenario-header-info">
                        <h2>{scenariosData.title}</h2>
                        <div className="scenario-meta">
                            <span className="difficulty-badge">{scenariosData.difficulty}</span>
                            <span className="type-badge">{currentSc?.type.replace(/_/g, ' ')}</span>
                            <span className="scenario-counter">
                                Scenario {currentScenario + 1} of {scenariosData.scenarios.length}
                            </span>
                        </div>
                    </div>

                    <div className="scenario-card">
                        <h3 className="scenario-description">{currentSc?.scenario}</h3>

                        {/* Stakeholders */}
                        <div className="stakeholders-section">
                            <h4><FaUsers /> Stakeholders</h4>
                            <ul className="stakeholders-list">
                                {currentSc?.stakeholders.map((stakeholder, idx) => (
                                    <li key={idx}>{stakeholder}</li>
                                ))}
                            </ul>
                        </div>

                        {/* Discussion Questions */}
                        <div className="questions-section">
                            <h4>Discussion Questions</h4>
                            <ul className="questions-list">
                                {currentSc?.discussion_questions.map((question, idx) => (
                                    <li key={idx}>{question}</li>
                                ))}
                            </ul>
                        </div>

                        {/* User Response Input */}
                        <div className="response-input-section">
                            <h4>Your Response</h4>
                            <textarea
                                className="response-textarea"
                                placeholder="Share your thoughts on the ethical considerations and how you would approach this scenario..."
                                value={userResponses[currentScenario] || ''}
                                onChange={handleResponseChange}
                                rows={8}
                            />
                        </div>

                        {/* Ethical Considerations */}
                        {!showConsiderations && (
                            <button className="show-considerations-btn" onClick={handleShowConsiderations}>
                                Show Ethical Considerations
                            </button>
                        )}

                        {showConsiderations && currentSc?.ethical_considerations && (
                            <div className="considerations-box">
                                <strong>Key Ethical Considerations:</strong>
                                <ul>
                                    {currentSc.ethical_considerations.map((consideration, idx) => (
                                        <li key={idx}>{consideration}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Recommended Approach */}
                        {showConsiderations && !showApproach && (
                            <button className="show-approach-btn" onClick={handleShowApproach}>
                                Show Recommended Approach
                            </button>
                        )}

                        {showApproach && currentSc?.recommended_approach && (
                            <div className="approach-box">
                                <strong>Recommended Approach:</strong>
                                <p>{currentSc.recommended_approach}</p>
                            </div>
                        )}
                    </div>

                    <div className="scenario-navigation">
                        <button
                            onClick={handlePrevious}
                            disabled={currentScenario === 0}
                            className="nav-btn"
                        >
                            ← Previous
                        </button>

                        <div className="progress-dots">
                            {scenariosData.scenarios.map((_, idx) => (
                                <span
                                    key={idx}
                                    className={`dot ${idx === currentScenario ? 'active' : ''} ${userResponses[idx]?.trim() ? 'answered' : ''}`}
                                    onClick={() => {
                                        setCurrentScenario(idx);
                                        setShowConsiderations(false);
                                        setShowApproach(false);
                                    }}
                                />
                            ))}
                        </div>

                        {currentScenario < scenariosData.scenarios.length - 1 ? (
                            <button onClick={handleNext} className="nav-btn">
                                Next →
                            </button>
                        ) : (
                            <button onClick={handleFinishScenarios} className="submit-btn">
                                Finish & Review
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Review Tab */}
            {tab === 'review' && scenariosCompleted && (
                <div className="review-tab">
                    <div className="review-header">
                        <h2>Scenario Review</h2>
                        <div className="completion-stats">
                            <p className="stat-item">
                                <strong>{Object.keys(userResponses).filter(k => userResponses[k]?.trim()).length}</strong>
                                <span> / {scenariosData.scenarios.length} Responded</span>
                            </p>
                        </div>
                    </div>

                    <div className="review-details">
                        <h3>Your Responses</h3>
                        {scenariosData.scenarios.map((sc, idx) => {
                            const userResponse = userResponses[idx];
                            const hasUserResponse = userResponse?.trim().length > 0;

                            return (
                                <div key={idx} className={`review-item ${hasUserResponse ? 'completed' : 'incomplete'}`}>
                                    <div className="review-item-header">
                                        {hasUserResponse ? <FaCheckCircle /> : <FaTimesCircle />}
                                        <h4>Scenario {idx + 1} - {sc.type.replace(/_/g, ' ')}</h4>
                                    </div>
                                    <p className="review-scenario">{sc.scenario}</p>

                                    <div className="review-stakeholders">
                                        <strong>Stakeholders:</strong>
                                        <ul>
                                            {sc.stakeholders.map((s, sidx) => (
                                                <li key={sidx}>{s}</li>
                                            ))}
                                        </ul>
                                    </div>

                                    {hasUserResponse && (
                                        <div className="user-response-display">
                                            <strong>Your Response:</strong>
                                            <p>{userResponse}</p>
                                        </div>
                                    )}

                                    <div className="considerations-display">
                                        <strong>Ethical Considerations:</strong>
                                        <ul>
                                            {sc.ethical_considerations.map((c, cidx) => (
                                                <li key={cidx}>{c}</li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div className="approach-display">
                                        <strong>Recommended Approach:</strong>
                                        <p>{sc.recommended_approach}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    <div className="review-actions">
                        <button onClick={handleRetakeScenarios} className="action-btn">
                            <FaRedo /> Revisit Scenarios
                        </button>
                        <button onClick={downloadScenarios} className="action-btn">
                            <FaDownload /> Download Scenarios
                        </button>
                        <button onClick={handleRestart} className="action-btn">
                            Create New Scenarios
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default EthicalAITutor;
