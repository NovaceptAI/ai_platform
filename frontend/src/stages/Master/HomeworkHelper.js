import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBook, FaCheckCircle, FaLightbulb, FaPencilAlt, FaChartLine, FaFileAlt } from 'react-icons/fa';
import './HomeworkHelper.css';
import axiosInstance from '../../utils/axiosInstance';

function HomeworkHelper() {
    const navigate = useNavigate();
    
    // State Management
    const [tab, setTab] = useState('generate'); // 'generate' | 'results'
    const [source, setSource] = useState('vault'); // 'vault' | 'upload'
    
    // File Selection
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileIds, setSelectedFileIds] = useState([]);
    const [uploadedFiles, setUploadedFiles] = useState([]);
    
    // Configuration
    const [includeExplanations, setIncludeExplanations] = useState(true);
    const [includeExamples, setIncludeExamples] = useState(true);
    const [includePractice, setIncludePractice] = useState(true);
    const [difficultyLevel, setDifficultyLevel] = useState('medium');
    
    // Progress Tracking
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'completed' | 'error'
    const [progress, setProgress] = useState(0);
    const [progressId, setProgressId] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    
    // Results Data
    const [assistanceData, setAssistanceData] = useState(null);
    const [expandedSections, setExpandedSections] = useState({});

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
            }, 1500);
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

    const selectAllFiles = () => {
        if (source === 'vault') {
            setSelectedFileIds(vaultFiles.map(f => f.id));
        }
    };

    const deselectAllFiles = () => {
        setSelectedFileIds([]);
    };

    const startHomeworkHelper = async () => {
        try {
            setStatus('generating');
            setProgress(0);
            setErrorMessage('');

            const token = localStorage.getItem('access_token');
            const userId = localStorage.getItem('user_id');

            let fileIds = [];
            
            if (source === 'vault') {
                if (selectedFileIds.length === 0) {
                    setErrorMessage('Please select at least one file');
                    setStatus('idle');
                    return;
                }
                fileIds = selectedFileIds;
            } else {
                if (uploadedFiles.length === 0) {
                    setErrorMessage('Please upload at least one file');
                    setStatus('idle');
                    return;
                }
                
                const formData = new FormData();
                uploadedFiles.forEach(file => {
                    formData.append('files', file);
                });

                const uploadResponse = await axiosInstance.post('/upload/upload', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (uploadResponse.data.results && uploadResponse.data.results.length > 0) {
                    fileIds = uploadResponse.data.results
                        .filter(r => r.status === 'success')
                        .map(r => r.file_id);
                }

                if (fileIds.length === 0) {
                    setErrorMessage('File upload failed');
                    setStatus('idle');
                    return;
                }
            }

            const options = {
                include_explanations: includeExplanations,
                include_examples: includeExamples,
                include_practice: includePractice,
                difficulty_level: difficultyLevel
            };

            const response = await axiosInstance.post('/master/homework_helper/start', {
                file_ids: fileIds,
                options: options
            }, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-User-Id': userId
                }
            });

            setProgressId(response.data.progress_id);
            setProgress(10);

        } catch (error) {
            console.error('Error starting homework helper:', error);
            setErrorMessage(error.response?.data?.error || 'Failed to start homework helper');
            setStatus('error');
        }
    };

    const pollProgress = async () => {
        try {
            const token = localStorage.getItem('access_token');
            
            const response = await axiosInstance.get(`/master/homework_helper/progress/${progressId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = response.data;
            setProgress(data.percentage || 0);

            if (data.status === 'completed') {
                setStatus('completed');
                fetchResults();
            } else if (data.status === 'failed') {
                setStatus('error');
                setErrorMessage(data.error_message || 'Homework helper generation failed');
            }

        } catch (error) {
            console.error('Error polling progress:', error);
        }
    };

    const fetchResults = async () => {
        try {
            const token = localStorage.getItem('access_token');
            
            const response = await axiosInstance.get(`/master/homework_helper/results/${progressId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            setAssistanceData(response.data.results);
            setTab('results');

        } catch (error) {
            console.error('Error fetching results:', error);
            setErrorMessage('Failed to fetch results');
        }
    };

    const toggleSection = (section) => {
        setExpandedSections(prev => ({
            ...prev,
            [section]: !prev[section]
        }));
    };

    const resetTool = () => {
        setStatus('idle');
        setProgress(0);
        setProgressId(null);
        setAssistanceData(null);
        setErrorMessage('');
        setSelectedFileIds([]);
        setUploadedFiles([]);
        setExpandedSections({});
        setTab('generate');
    };

    return (
        <div className="homework-helper-container">
            <div className="homework-helper-header">
                <button className="back-button" onClick={() => navigate('/master')}>
                    ← Back to Master Tools
                </button>
                <h1>
                    <FaBook className="header-icon" />
                    Homework Helper
                </h1>
                <p className="subtitle">Get step-by-step explanations, examples, and study guidance</p>
            </div>

            {/* Tab Navigation */}
            <div className="tab-navigation">
                <button 
                    className={tab === 'generate' ? 'tab-button active' : 'tab-button'}
                    onClick={() => setTab('generate')}
                >
                    <FaPencilAlt /> Generate Help
                </button>
                <button 
                    className={tab === 'results' ? 'tab-button active' : 'tab-button'}
                    onClick={() => setTab('results')}
                    disabled={!assistanceData}
                >
                    <FaCheckCircle /> View Results
                </button>
            </div>

            {/* Error Message */}
            {errorMessage && (
                <div className="error-banner">
                    <p>{errorMessage}</p>
                    <button onClick={() => setErrorMessage('')}>×</button>
                </div>
            )}

            {/* Generate Tab */}
            {tab === 'generate' && (
                <div className="generate-section">
                    <div className="config-card">
                        <h2>Configuration</h2>

                        {/* Assistance Options */}
                        <div className="options-group">
                            <h3>Include in Assistance</h3>
                            <div className="checkbox-group">
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={includeExplanations}
                                        onChange={(e) => setIncludeExplanations(e.target.checked)}
                                    />
                                    <span>Concept Explanations</span>
                                </label>
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={includeExamples}
                                        onChange={(e) => setIncludeExamples(e.target.checked)}
                                    />
                                    <span>Example Problems</span>
                                </label>
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={includePractice}
                                        onChange={(e) => setIncludePractice(e.target.checked)}
                                    />
                                    <span>Practice Recommendations</span>
                                </label>
                            </div>
                        </div>

                        {/* Difficulty Level */}
                        <div className="form-group">
                            <label>Difficulty Level</label>
                            <select
                                value={difficultyLevel}
                                onChange={(e) => setDifficultyLevel(e.target.value)}
                                className="difficulty-select"
                            >
                                <option value="easy">Easy</option>
                                <option value="medium">Medium</option>
                                <option value="hard">Hard</option>
                            </select>
                        </div>

                        {/* Source Selection */}
                        <div className="source-selection">
                            <h3>Select Source</h3>
                            <div className="source-buttons">
                                <button
                                    className={source === 'vault' ? 'source-btn active' : 'source-btn'}
                                    onClick={() => setSource('vault')}
                                >
                                    Knowledge Vault
                                </button>
                                <button
                                    className={source === 'upload' ? 'source-btn active' : 'source-btn'}
                                    onClick={() => setSource('upload')}
                                >
                                    Upload Files
                                </button>
                            </div>
                        </div>

                        {/* File Selection */}
                        {source === 'vault' ? (
                            <div className="vault-section">
                                <h3>Select Files from Knowledge Vault</h3>
                                <div className="file-actions">
                                    <button onClick={selectAllFiles} className="action-btn">Select All</button>
                                    <button onClick={deselectAllFiles} className="action-btn">Deselect All</button>
                                    <span className="selected-count">{selectedFileIds.length} selected</span>
                                </div>
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
                                                    type="checkbox"
                                                    checked={selectedFileIds.includes(file.id)}
                                                    onChange={() => toggleFileSelection(file.id)}
                                                />
                                                <FaFileAlt className="file-icon" />
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
                                <h3>Upload Files</h3>
                                <div className="upload-area">
                                    <input
                                        type="file"
                                        multiple
                                        onChange={handleFileUpload}
                                        accept=".pdf,.doc,.docx,.txt"
                                        className="file-input"
                                        id="file-upload"
                                    />
                                    <label htmlFor="file-upload" className="upload-label">
                                        <FaFileAlt size={40} />
                                        <p>Click to upload files</p>
                                        <p className="file-types">PDF, DOC, DOCX, TXT</p>
                                    </label>
                                </div>
                                {uploadedFiles.length > 0 && (
                                    <div className="uploaded-files-list">
                                        <h4>Uploaded Files:</h4>
                                        {uploadedFiles.map((file, idx) => (
                                            <div key={idx} className="uploaded-file-item">
                                                <FaFileAlt />
                                                <span>{file.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Generate Button */}
                        <div className="generate-actions">
                            {status === 'generating' ? (
                                <div className="progress-section">
                                    <div className="progress-bar">
                                        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                                    </div>
                                    <p className="progress-text">Generating homework assistance... {progress}%</p>
                                </div>
                            ) : (
                                <button
                                    className="generate-button"
                                    onClick={startHomeworkHelper}
                                    disabled={status === 'generating'}
                                >
                                    <FaLightbulb /> Generate Homework Help
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Results Tab */}
            {tab === 'results' && assistanceData && (
                <div className="results-section">
                    <div className="results-header">
                        <h2>Homework Assistance</h2>
                        <button className="reset-button" onClick={resetTool}>
                            <FaCheckCircle /> Start New
                        </button>
                    </div>

                    {/* Study Plan Overview */}
                    {assistanceData.study_plan && (
                        <div className="study-plan-card">
                            <h3><FaChartLine /> Study Plan</h3>
                            <div className="study-plan-info">
                                <div className="info-item">
                                    <strong>Estimated Time:</strong> {assistanceData.study_plan.estimated_time}
                                </div>
                                <div className="info-item">
                                    <strong>Recommended Order:</strong> {assistanceData.study_plan.recommended_order?.join(' → ')}
                                </div>
                                <div className="info-item">
                                    <strong>Difficulty Progression:</strong> {assistanceData.study_plan.difficulty_progression}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Concept Explanations */}
                    {assistanceData.homework_assistance?.explanations && assistanceData.homework_assistance.explanations.length > 0 && (
                        <div className="assistance-section">
                            <div 
                                className="section-header"
                                onClick={() => toggleSection('explanations')}
                            >
                                <h3><FaLightbulb /> Concept Explanations ({assistanceData.homework_assistance.explanations.length})</h3>
                                <span className="toggle-icon">{expandedSections.explanations ? '−' : '+'}</span>
                            </div>
                            {expandedSections.explanations && (
                                <div className="section-content">
                                    {assistanceData.homework_assistance.explanations.map((item, idx) => (
                                        <div key={idx} className="explanation-card">
                                            <h4>{item.concept}</h4>
                                            <p className="explanation-text">{item.explanation}</p>
                                            <div className="meta-info">
                                                <span className="difficulty-badge">{item.difficulty}</span>
                                                <span className="time-estimate">{item.estimated_time}</span>
                                                {item.source_file && <span className="source-file">From: {item.source_file}</span>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Example Problems */}
                    {assistanceData.homework_assistance?.examples && assistanceData.homework_assistance.examples.length > 0 && (
                        <div className="assistance-section">
                            <div 
                                className="section-header"
                                onClick={() => toggleSection('examples')}
                            >
                                <h3><FaPencilAlt /> Example Problems ({assistanceData.homework_assistance.examples.length})</h3>
                                <span className="toggle-icon">{expandedSections.examples ? '−' : '+'}</span>
                            </div>
                            {expandedSections.examples && (
                                <div className="section-content">
                                    {assistanceData.homework_assistance.examples.map((item, idx) => (
                                        <div key={idx} className="example-card">
                                            <div className="problem-section">
                                                <h4>Problem:</h4>
                                                <p>{item.problem}</p>
                                            </div>
                                            <div className="solution-section">
                                                <h4>Solution:</h4>
                                                <p>{item.solution}</p>
                                            </div>
                                            <div className="explanation-section">
                                                <h4>Explanation:</h4>
                                                <p>{item.explanation}</p>
                                            </div>
                                            <div className="meta-info">
                                                <span className="difficulty-badge">{item.difficulty}</span>
                                                {item.source_file && <span className="source-file">From: {item.source_file}</span>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Practice Recommendations */}
                    {assistanceData.homework_assistance?.practice_recommendations && assistanceData.homework_assistance.practice_recommendations.length > 0 && (
                        <div className="assistance-section">
                            <div 
                                className="section-header"
                                onClick={() => toggleSection('practice')}
                            >
                                <h3><FaCheckCircle /> Practice Recommendations ({assistanceData.homework_assistance.practice_recommendations.length})</h3>
                                <span className="toggle-icon">{expandedSections.practice ? '−' : '+'}</span>
                            </div>
                            {expandedSections.practice && (
                                <div className="section-content">
                                    {assistanceData.homework_assistance.practice_recommendations.map((item, idx) => (
                                        <div key={idx} className="practice-card">
                                            <h4>{item.topic}</h4>
                                            {item.practice_activities && (
                                                <div className="activities-list">
                                                    <strong>Activities:</strong>
                                                    <ul>
                                                        {item.practice_activities.map((activity, i) => (
                                                            <li key={i}>{activity}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {item.resources && (
                                                <div className="resources-list">
                                                    <strong>Resources:</strong>
                                                    <ul>
                                                        {item.resources.map((resource, i) => (
                                                            <li key={i}>{resource}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            <div className="meta-info">
                                                <span className="time-estimate">{item.time_estimate}</span>
                                                {item.source_file && <span className="source-file">From: {item.source_file}</span>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Study Guidance */}
                    {assistanceData.homework_assistance?.study_guidance && (
                        <div className="assistance-section">
                            <div 
                                className="section-header"
                                onClick={() => toggleSection('guidance')}
                            >
                                <h3><FaBook /> Study Guidance</h3>
                                <span className="toggle-icon">{expandedSections.guidance ? '−' : '+'}</span>
                            </div>
                            {expandedSections.guidance && (
                                <div className="section-content">
                                    <div className="guidance-card">
                                        {assistanceData.homework_assistance.study_guidance.study_approach && (
                                            <div className="guidance-item">
                                                <h4>Study Approach</h4>
                                                <p>{assistanceData.homework_assistance.study_guidance.study_approach}</p>
                                            </div>
                                        )}
                                        {assistanceData.homework_assistance.study_guidance.key_strategies && (
                                            <div className="guidance-item">
                                                <h4>Key Strategies</h4>
                                                <ul>
                                                    {assistanceData.homework_assistance.study_guidance.key_strategies.map((strategy, i) => (
                                                        <li key={i}>{strategy}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {assistanceData.homework_assistance.study_guidance.common_mistakes && (
                                            <div className="guidance-item">
                                                <h4>Common Mistakes to Avoid</h4>
                                                <ul>
                                                    {assistanceData.homework_assistance.study_guidance.common_mistakes.map((mistake, i) => (
                                                        <li key={i}>{mistake}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {assistanceData.homework_assistance.study_guidance.success_tips && (
                                            <div className="guidance-item">
                                                <h4>Success Tips</h4>
                                                <ul>
                                                    {assistanceData.homework_assistance.study_guidance.success_tips.map((tip, i) => (
                                                        <li key={i}>{tip}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Empty Results State */}
            {tab === 'results' && !assistanceData && (
                <div className="empty-state">
                    <FaBook size={64} />
                    <h3>No Results Yet</h3>
                    <p>Generate homework assistance to see results here</p>
                    <button onClick={() => setTab('generate')} className="generate-button">
                        <FaLightbulb /> Generate Help
                    </button>
                </div>
            )}
        </div>
    );
}

export default HomeworkHelper;
