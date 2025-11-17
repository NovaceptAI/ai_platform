import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaLayerGroup, FaCheckCircle, FaTimesCircle, FaRedo, FaDownload, FaBrain, FaStar, FaArrowLeft, FaArrowRight } from 'react-icons/fa';
import './Flashcards.css';
import axiosInstance from '../../utils/axiosInstance';

function Flashcards() {
    const navigate = useNavigate();
    
    // State Management
    const [tab, setTab] = useState('generate'); // 'generate' | 'study' | 'results'
    const [source, setSource] = useState('vault'); // 'vault' | 'upload'
    
    // File Selection
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileIds, setSelectedFileIds] = useState([]);
    const [uploadedFiles, setUploadedFiles] = useState([]);
    
    // Flashcard Configuration
    const [maxCards, setMaxCards] = useState(20);
    const [difficulty, setDifficulty] = useState('medium');
    const [includeDefinitions, setIncludeDefinitions] = useState(true);
    const [includeConcepts, setIncludeConcepts] = useState(true);
    const [includeFacts, setIncludeFacts] = useState(true);
    
    // Progress Tracking
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'completed' | 'error'
    const [progress, setProgress] = useState(0);
    const [progressId, setProgressId] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    
    // Flashcard Data
    const [flashcardsData, setFlashcardsData] = useState(null);
    const [currentCardIndex, setCurrentCardIndex] = useState(0);
    const [isFlipped, setIsFlipped] = useState(false);
    const [studyProgress, setStudyProgress] = useState({
        known: 0,
        learning: 0,
        difficult: 0
    });
    const [cardStatuses, setCardStatuses] = useState({});
    const [sessionStats, setSessionStats] = useState({
        cardsStudied: 0,
        timeStarted: null,
        accuracy: 0
    });

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
    }, [status, progressId]);

    // Keyboard shortcuts for study mode
    useEffect(() => {
        if (tab === 'study' && flashcardsData) {
            const handleKeyPress = (e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                    e.preventDefault();
                    handleFlipCard();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    handleNextCard();
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    handlePreviousCard();
                } else if (e.key === '1') {
                    e.preventDefault();
                    handleCardRating('difficult');
                } else if (e.key === '2') {
                    e.preventDefault();
                    handleCardRating('learning');
                } else if (e.key === '3') {
                    e.preventDefault();
                    handleCardRating('known');
                }
            };

            window.addEventListener('keydown', handleKeyPress);
            return () => window.removeEventListener('keydown', handleKeyPress);
        }
    }, [tab, flashcardsData, isFlipped, currentCardIndex]);

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

    const startFlashcardGeneration = async () => {
        try {
            setStatus('generating');
            setProgress(0);
            setErrorMessage('');

            let fileIds = [];
            let filesToPreprocess = [];

            if (source === 'vault') {
                if (selectedFileIds.length === 0) {
                    setErrorMessage('Please select at least one file');
                    setStatus('idle');
                    return;
                }
                fileIds = selectedFileIds;

                // Check prerequisites for vault files
                const prerequisitesResponse = await axiosInstance.post('/files/check_prerequisites', {
                    file_ids: fileIds,
                    required: ['summary', 'topics', 'analysis']
                });

                const { needs_preprocessing } = prerequisitesResponse.data;

                // If some files need preprocessing, store them with their missing data
                if (needs_preprocessing && needs_preprocessing.length > 0) {
                    filesToPreprocess = needs_preprocessing;
                    setErrorMessage(`Preparing ${needs_preprocessing.length} file(s) for flashcard generation...`);
                }
            } else if (source === 'upload') {
                if (uploadedFiles.length === 0) {
                    setErrorMessage('Please upload at least one file');
                    setStatus('idle');
                    return;
                }

                // Upload files first
                const formData = new FormData();
                uploadedFiles.forEach(file => {
                    formData.append('files', file);
                });

                const uploadResponse = await axiosInstance.post('/upload/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });

                // Extract file IDs from successful uploads
                // The upload endpoint returns an array of results with 'file_id' field
                const successfulUploads = (uploadResponse.data.results || [])
                    .filter(result => result.status === 'success' || result.status === 'duplicate')
                    .map(result => result.file_id);

                fileIds = successfulUploads;

                // For newly uploaded files, add all preprocessing steps
                const newFiles = (uploadResponse.data.results || [])
                    .filter(result => result.status === 'success')
                    .map(result => ({
                        file_id: result.file_id,
                        file_name: result.original_name,
                        stored_name: result.stored_as,
                        missing: ['summary', 'topics', 'analysis']
                    }));

                if (newFiles.length > 0) {
                    filesToPreprocess = [...filesToPreprocess, ...newFiles];
                    setErrorMessage(`Preparing ${newFiles.length} newly uploaded file(s)...`);
                }
            }

            // Run preprocessing for files that need it
            if (filesToPreprocess.length > 0) {
                setErrorMessage(`Preparing ${filesToPreprocess.length} file(s). Progress will start after Summarizing, finding topics and performing analysis.`);

                // Process each file
                for (const fileInfo of filesToPreprocess) {
                    const { file_id, missing, file_name, stored_name } = fileInfo;

                    try {
                        console.log(`Preprocessing ${file_name || file_id}: missing ${missing.join(', ')}`);

                        // 1. Run Summarization if missing
                        if (missing.includes('summary')) {
                            // Summarizer expects stored_file_name, not file_id
                            const summaryResponse = await axiosInstance.post('/summarizer/summarize_file', {
                                filename: stored_name || file_id,
                                fromVault: true
                            });

                            if (summaryResponse.data.progress_id) {
                                await pollPreprocessingProgress(summaryResponse.data.progress_id, 'summarization');
                            }
                        }

                        // 2. Run Topics Extraction if missing
                        if (missing.includes('topics')) {
                            const topicsResponse = await axiosInstance.post('/modeller/topics/start', {
                                file_id: file_id,
                                force: false
                            }, {
                                headers: { 'X-User-Id': 'admin' }
                            });

                            if (topicsResponse.data.progress_id) {
                                await pollPreprocessingProgress(topicsResponse.data.progress_id, 'topics');
                            }
                        }

                        // 3. Run Document Analysis if missing
                        if (missing.includes('analysis')) {
                            const docAnalysisResponse = await axiosInstance.post('/doc_analysis/start', {
                                file_id: file_id,
                                user_id: 'admin',
                                force: false
                            });

                            if (docAnalysisResponse.data.progress_id) {
                                await pollPreprocessingProgress(docAnalysisResponse.data.progress_id, 'document analysis');
                            }
                        }
                    } catch (preprocessError) {
                        console.error(`Preprocessing failed for file ${file_id}:`, preprocessError);
                        // Continue with other files even if one fails
                    }
                }

                // Clear the preprocessing message
                setErrorMessage('');
            }

            // Start flashcard generation
            const response = await axiosInstance.post('/master/flashcards/start', {
                file_ids: fileIds,
                options: {
                    max_cards: maxCards,
                    difficulty: difficulty,
                    include_definitions: includeDefinitions,
                    include_concepts: includeConcepts,
                    include_facts: includeFacts
                }
            });

            setProgressId(response.data.progress_id);
            setProgress(10);

        } catch (error) {
            console.error('Error starting flashcard generation:', error);
            setErrorMessage(error.response?.data?.error || 'Failed to start flashcard generation');
            setStatus('error');
        }
    };

    const pollPreprocessingProgress = async (progressId, stepName) => {
        return new Promise((resolve, reject) => {
            const maxAttempts = 100; // Maximum 5 minutes (100 * 3s)
            let attempts = 0;

            const interval = setInterval(async () => {
                attempts++;

                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    reject(new Error(`${stepName} timed out`));
                    return;
                }

                try {
                    // Determine the correct endpoint based on step name
                    let endpoint = '';
                    if (stepName === 'summarization') {
                        endpoint = `/summarizer/progress/${progressId}`;
                    } else if (stepName === 'topics') {
                        endpoint = `/modeller/topics/progress/${progressId}`;
                    } else if (stepName === 'document analysis') {
                        endpoint = `/doc_analysis/progress/${progressId}`;
                    }

                    const response = await axiosInstance.get(endpoint);
                    const { percentage = 0, status } = response.data || {};

                    if (status === 'completed' || status === 'done' || percentage >= 100) {
                        clearInterval(interval);
                        resolve();
                    } else if (status === 'failed' || status === 'canceled') {
                        clearInterval(interval);
                        reject(new Error(`${stepName} failed`));
                    }
                } catch (error) {
                    // Continue polling on errors
                    console.warn(`Polling error for ${stepName}:`, error);
                }
            }, 3000); // Poll every 3 seconds
        });
    };

    const pollProgress = async () => {
        try {
            const response = await axiosInstance.get(`/master/flashcards/progress/${progressId}`);
            const { percentage, status: progressStatus } = response.data;

            setProgress(percentage);

            if (progressStatus === 'completed') {
                setStatus('completed');
                await fetchFlashcardsResults();
            } else if (progressStatus === 'failed') {
                setStatus('error');
                setErrorMessage('Flashcard generation failed');
            }

        } catch (error) {
            console.error('Error polling progress:', error);
        }
    };

    const fetchFlashcardsResults = async () => {
        try {
            const fileIdsParam = selectedFileIds.join(',');
            const response = await axiosInstance.get('/master/flashcards/results', {
                params: { file_ids: fileIdsParam }
            });

            if (response.data.results && response.data.results.length > 0) {
                const latestResult = response.data.results[0];
                setFlashcardsData(latestResult);
                setTab('study');
                setCurrentCardIndex(0);
                setIsFlipped(false);
                setSessionStats({
                    ...sessionStats,
                    timeStarted: new Date()
                });
            }

        } catch (error) {
            console.error('Error fetching flashcards results:', error);
            setErrorMessage('Failed to fetch flashcards');
        }
    };

    const handleFlipCard = () => {
        setIsFlipped(!isFlipped);
    };

    const handleNextCard = () => {
        if (flashcardsData && currentCardIndex < flashcardsData.flashcards.length - 1) {
            setCurrentCardIndex(currentCardIndex + 1);
            setIsFlipped(false);
        }
    };

    const handlePreviousCard = () => {
        if (currentCardIndex > 0) {
            setCurrentCardIndex(currentCardIndex - 1);
            setIsFlipped(false);
        }
    };

    const handleCardRating = (rating) => {
        const cardId = flashcardsData.flashcards[currentCardIndex].id;
        
        setCardStatuses(prev => ({
            ...prev,
            [cardId]: rating
        }));

        setStudyProgress(prev => ({
            ...prev,
            [rating]: prev[rating] + 1
        }));

        setSessionStats(prev => ({
            ...prev,
            cardsStudied: prev.cardsStudied + 1
        }));

        // Auto-advance to next card
        setTimeout(() => {
            handleNextCard();
        }, 300);
    };

    const handleRestart = () => {
        setCurrentCardIndex(0);
        setIsFlipped(false);
        setCardStatuses({});
        setStudyProgress({ known: 0, learning: 0, difficult: 0 });
        setSessionStats({
            cardsStudied: 0,
            timeStarted: new Date(),
            accuracy: 0
        });
    };

    const handleBackToGenerate = () => {
        setTab('generate');
        setStatus('idle');
        setProgress(0);
        setFlashcardsData(null);
        setSelectedFileIds([]);
        setUploadedFiles([]);
    };

    const exportFlashcards = () => {
        if (!flashcardsData) return;

        const dataStr = JSON.stringify(flashcardsData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `flashcards_${Date.now()}.json`;
        link.click();
    };

    // Render Functions
    const renderGenerateTab = () => (
        <div className="fc-generate-container">
            <div className="fc-header">
                <h2>📚 Flashcard Generator</h2>
                <p>Create interactive flashcards from your documents for effective studying</p>
            </div>

            {/* Source Selection */}
            <div className="fc-source-selector">
                <button
                    className={`fc-source-btn ${source === 'vault' ? 'active' : ''}`}
                    onClick={() => setSource('vault')}
                >
                    <FaLayerGroup /> Knowledge Vault
                </button>
                <button
                    className={`fc-source-btn ${source === 'upload' ? 'active' : ''}`}
                    onClick={() => setSource('upload')}
                >
                    📤 Upload Files
                </button>
            </div>

            {/* File Selection */}
            {source === 'vault' && (
                <div className="fc-file-selection">
                    <h3>Select Files from Knowledge Vault</h3>
                    <div className="fc-file-grid">
                        {vaultFiles.length === 0 ? (
                            <p className="fc-no-files">No files in vault. Upload files first!</p>
                        ) : (
                            vaultFiles.map(file => (
                                <div
                                    key={file.id}
                                    className={`fc-file-card ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                                    onClick={() => toggleFileSelection(file.id)}
                                >
                                    <div className="fc-file-icon">📄</div>
                                    <div className="fc-file-name">{file.name}</div>
                                    {selectedFileIds.includes(file.id) && (
                                        <div className="fc-file-checkmark"><FaCheckCircle /></div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                    <p className="fc-selected-count">
                        {selectedFileIds.length} file(s) selected
                    </p>
                </div>
            )}

            {source === 'upload' && (
                <div className="fc-upload-section">
                    <h3>Upload Documents</h3>
                    <input
                        type="file"
                        multiple
                        accept=".pdf,.doc,.docx,.txt"
                        onChange={handleFileUpload}
                        className="fc-file-input"
                    />
                    {uploadedFiles.length > 0 && (
                        <div className="fc-uploaded-list">
                            {uploadedFiles.map((file, idx) => (
                                <div key={idx} className="fc-uploaded-item">
                                    📎 {file.name}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Configuration */}
            <div className="fc-config-section">
                <h3>Flashcard Settings</h3>
                
                <div className="fc-config-grid">
                    <div className="fc-config-item">
                        <label>Maximum Cards</label>
                        <input
                            type="number"
                            min="5"
                            max="50"
                            value={maxCards}
                            onChange={(e) => setMaxCards(parseInt(e.target.value))}
                            className="fc-input"
                        />
                    </div>

                    <div className="fc-config-item">
                        <label>Difficulty</label>
                        <select
                            value={difficulty}
                            onChange={(e) => setDifficulty(e.target.value)}
                            className="fc-select"
                        >
                            <option value="easy">Easy</option>
                            <option value="medium">Medium</option>
                            <option value="hard">Hard</option>
                        </select>
                    </div>
                </div>

                <div className="fc-config-checkboxes">
                    <label className="fc-checkbox-label">
                        <input
                            type="checkbox"
                            checked={includeDefinitions}
                            onChange={(e) => setIncludeDefinitions(e.target.checked)}
                        />
                        Include Definitions
                    </label>
                    <label className="fc-checkbox-label">
                        <input
                            type="checkbox"
                            checked={includeConcepts}
                            onChange={(e) => setIncludeConcepts(e.target.checked)}
                        />
                        Include Concepts
                    </label>
                    <label className="fc-checkbox-label">
                        <input
                            type="checkbox"
                            checked={includeFacts}
                            onChange={(e) => setIncludeFacts(e.target.checked)}
                        />
                        Include Facts
                    </label>
                </div>
            </div>

            {/* Error Message */}
            {errorMessage && (
                <div className="fc-error-message">
                    <FaTimesCircle /> {errorMessage}
                </div>
            )}

            {/* Progress Bar */}
            {status === 'generating' && (
                <div className="fc-progress-container">
                    <div className="fc-progress-bar">
                        <div
                            className="fc-progress-fill"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <p className="fc-progress-text">Generating flashcards... {progress}%</p>
                </div>
            )}

            {/* Generate Button */}
            <button
                className="fc-generate-btn"
                onClick={startFlashcardGeneration}
                disabled={status === 'generating' || (source === 'vault' && selectedFileIds.length === 0)}
            >
                {status === 'generating' ? (
                    <>⏳ Generating...</>
                ) : (
                    <>🎯 Generate Flashcards</>
                )}
            </button>
        </div>
    );

    const renderStudyTab = () => {
        if (!flashcardsData || !flashcardsData.flashcards || flashcardsData.flashcards.length === 0) {
            return (
                <div className="fc-no-data">
                    <p>No flashcards available. Generate some first!</p>
                    <button onClick={handleBackToGenerate} className="fc-back-btn">
                        Back to Generator
                    </button>
                </div>
            );
        }

        const currentCard = flashcardsData.flashcards[currentCardIndex];
        const totalCards = flashcardsData.flashcards.length;
        const progressPercent = ((currentCardIndex + 1) / totalCards) * 100;

        return (
            <div className="fc-study-container">
                <div className="fc-study-header">
                    <button onClick={handleBackToGenerate} className="fc-back-btn">
                        <FaArrowLeft /> Back
                    </button>
                    <h2>Study Mode</h2>
                    <button onClick={exportFlashcards} className="fc-export-btn">
                        <FaDownload /> Export
                    </button>
                </div>

                {/* Progress Stats */}
                <div className="fc-study-stats">
                    <div className="fc-stat-item">
                        <span className="fc-stat-label">Progress</span>
                        <span className="fc-stat-value">{currentCardIndex + 1} / {totalCards}</span>
                    </div>
                    <div className="fc-stat-item fc-stat-known">
                        <span className="fc-stat-label">Known</span>
                        <span className="fc-stat-value">{studyProgress.known}</span>
                    </div>
                    <div className="fc-stat-item fc-stat-learning">
                        <span className="fc-stat-label">Learning</span>
                        <span className="fc-stat-value">{studyProgress.learning}</span>
                    </div>
                    <div className="fc-stat-item fc-stat-difficult">
                        <span className="fc-stat-label">Difficult</span>
                        <span className="fc-stat-value">{studyProgress.difficult}</span>
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="fc-study-progress-bar">
                    <div
                        className="fc-study-progress-fill"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>

                {/* Flashcard */}
                <div className="fc-card-container">
                    <div className={`fc-card ${isFlipped ? 'flipped' : ''}`} onClick={handleFlipCard}>
                        <div className="fc-card-inner">
                            <div className="fc-card-front">
                                <div className="fc-card-type-badge">{currentCard.type}</div>
                                <div className="fc-card-content">
                                    {currentCard.front}
                                </div>
                                <div className="fc-card-hint">Click to reveal answer</div>
                            </div>
                            <div className="fc-card-back">
                                <div className="fc-card-type-badge">{currentCard.type}</div>
                                <div className="fc-card-content">
                                    {currentCard.back}
                                </div>
                                <div className="fc-card-tags">
                                    {currentCard.tags && currentCard.tags.map((tag, idx) => (
                                        <span key={idx} className="fc-tag">#{tag}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <div className="fc-navigation">
                    <button
                        onClick={handlePreviousCard}
                        disabled={currentCardIndex === 0}
                        className="fc-nav-btn"
                    >
                        <FaArrowLeft /> Previous
                    </button>
                    
                    <button onClick={handleFlipCard} className="fc-flip-btn">
                        {isFlipped ? '🔄 Flip Back' : '🔄 Flip Card'}
                    </button>

                    <button
                        onClick={handleNextCard}
                        disabled={currentCardIndex >= totalCards - 1}
                        className="fc-nav-btn"
                    >
                        Next <FaArrowRight />
                    </button>
                </div>

                {/* Rating Buttons (shown when flipped) */}
                {isFlipped && (
                    <div className="fc-rating-section">
                        <p className="fc-rating-prompt">How well did you know this?</p>
                        <div className="fc-rating-buttons">
                            <button
                                onClick={() => handleCardRating('difficult')}
                                className="fc-rating-btn fc-rating-difficult"
                            >
                                <FaTimesCircle /> Difficult (1)
                            </button>
                            <button
                                onClick={() => handleCardRating('learning')}
                                className="fc-rating-btn fc-rating-learning"
                            >
                                <FaBrain /> Learning (2)
                            </button>
                            <button
                                onClick={() => handleCardRating('known')}
                                className="fc-rating-btn fc-rating-known"
                            >
                                <FaCheckCircle /> Known (3)
                            </button>
                        </div>
                    </div>
                )}

                {/* Keyboard Shortcuts Help */}
                <div className="fc-shortcuts-help">
                    <p><strong>Keyboard Shortcuts:</strong></p>
                    <p>Space/Enter: Flip card | ← →: Navigate | 1/2/3: Rate difficulty</p>
                </div>

                {/* Restart Button */}
                <button onClick={handleRestart} className="fc-restart-btn">
                    <FaRedo /> Restart Session
                </button>
            </div>
        );
    };

    return (
        <div className="flashcards-container">
            {/* Tab Navigation */}
            <div className="fc-tabs">
                <button
                    className={`fc-tab ${tab === 'generate' ? 'active' : ''}`}
                    onClick={() => setTab('generate')}
                >
                    📝 Generate
                </button>
                <button
                    className={`fc-tab ${tab === 'study' ? 'active' : ''}`}
                    onClick={() => setTab('study')}
                    disabled={!flashcardsData}
                >
                    📖 Study
                </button>
            </div>

            {/* Tab Content */}
            <div className="fc-content">
                {tab === 'generate' && renderGenerateTab()}
                {tab === 'study' && renderStudyTab()}
            </div>
        </div>
    );
}

export default Flashcards;
