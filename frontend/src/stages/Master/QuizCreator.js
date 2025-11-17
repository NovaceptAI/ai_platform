import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBook, FaCheckCircle, FaTimesCircle, FaRedo, FaDownload, FaPlay, FaCog } from 'react-icons/fa';
import './QuizCreator.css';
import axiosInstance from '../../utils/axiosInstance';

function QuizCreator() {
    const navigate = useNavigate();
    
    // State Management
    const [tab, setTab] = useState('generate'); // 'generate' | 'take-quiz' | 'results'
    const [source, setSource] = useState('vault'); // 'vault' | 'upload'
    
    // File Selection
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileIds, setSelectedFileIds] = useState([]);
    const [uploadedFiles, setUploadedFiles] = useState([]);
    
    // Quiz Configuration
    const [numQuestions, setNumQuestions] = useState(10);
    const [difficulty, setDifficulty] = useState('medium');
    
    // Progress Tracking
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'completed' | 'error'
    const [progress, setProgress] = useState(0);
    const [progressId, setProgressId] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    
    // Quiz Data
    const [quizData, setQuizData] = useState(null);
    const [currentQuestion, setCurrentQuestion] = useState(0);
    const [userAnswers, setUserAnswers] = useState({});
    const [showExplanation, setShowExplanation] = useState(false);
    const [quizCompleted, setQuizCompleted] = useState(false);
    const [score, setScore] = useState(0);

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

    const startQuizGeneration = async () => {
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
                // Use first selected file (can be enhanced for multiple files)
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

                const uploadResponse = await axiosInstance.post('/upload', formData, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'multipart/form-data'
                    }
                });

                fileId = uploadResponse.data.file_id;
            }

            // Start quiz generation
            const response = await axiosInstance.post('/master/quiz_creator/start', {
                file_id: fileId,
                user_id: userId,
                n: numQuestions,
                difficulty: difficulty
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
            console.error('Error starting quiz generation:', error);
            setErrorMessage(error.response?.data?.error || 'Failed to start quiz generation');
            setStatus('error');
        }
    };

    const fetchQuizResults = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const userId = localStorage.getItem('user_id');
            const fileId = selectedFileIds[0]; // Using first selected file

            const response = await axiosInstance.get('/master/quiz_creator/results', {
                params: {
                    file_id: fileId,
                    n: numQuestions,
                    difficulty: difficulty
                },
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-User-Id': userId
                }
            });

            setQuizData(response.data.quiz);
            setTab('take-quiz');
        } catch (error) {
            console.error('Error fetching quiz results:', error);
            setErrorMessage('Failed to fetch quiz');
            setStatus('error');
        }
    };

    const pollProgress = async () => {
        if (!progressId) return;
        
        try {
            const token = localStorage.getItem('access_token');
            const response = await axiosInstance.get(`/master/quiz_creator/progress/${progressId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const { status: taskStatus, percentage } = response.data;
            setProgress(percentage || 0);

            if (taskStatus === 'completed') {
                setStatus('completed');
                await fetchQuizResults();
            } else if (taskStatus === 'failed') {
                setStatus('error');
                setErrorMessage('Quiz generation failed');
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    };

    const handleAnswerSelect = (questionIndex, optionIndex) => {
        if (quizCompleted) return;
        
        setUserAnswers(prev => ({
            ...prev,
            [questionIndex]: optionIndex
        }));
        setShowExplanation(false);
    };

    const handleNext = () => {
        if (currentQuestion < quizData.questions.length - 1) {
            setCurrentQuestion(prev => prev + 1);
            setShowExplanation(false);
        }
    };

    const handlePrevious = () => {
        if (currentQuestion > 0) {
            setCurrentQuestion(prev => prev - 1);
            setShowExplanation(false);
        }
    };

    const handleShowExplanation = () => {
        setShowExplanation(true);
    };

    const handleSubmitQuiz = () => {
        // Calculate score
        let correct = 0;
        quizData.questions.forEach((q, idx) => {
            if (userAnswers[idx] === q.correctIndex) {
                correct++;
            }
        });
        
        setScore(correct);
        setQuizCompleted(true);
        setTab('results');
    };

    const handleRestart = () => {
        setTab('generate');
        setStatus('idle');
        setProgress(0);
        setProgressId(null);
        setQuizData(null);
        setCurrentQuestion(0);
        setUserAnswers({});
        setShowExplanation(false);
        setQuizCompleted(false);
        setScore(0);
        setErrorMessage('');
    };

    const handleRetakeQuiz = () => {
        setTab('take-quiz');
        setCurrentQuestion(0);
        setUserAnswers({});
        setShowExplanation(false);
        setQuizCompleted(false);
        setScore(0);
    };

    const downloadQuiz = () => {
        const quizExport = {
            title: quizData.title,
            difficulty: quizData.difficulty,
            questions: quizData.questions.map((q, idx) => ({
                number: idx + 1,
                question: q.question,
                options: q.options,
                correctAnswer: q.options[q.correctIndex],
                explanation: q.explanation
            }))
        };

        const blob = new Blob([JSON.stringify(quizExport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `quiz_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const currentQ = quizData?.questions[currentQuestion];
    const isAnswered = userAnswers[currentQuestion] !== undefined;
    const isCorrect = isAnswered && userAnswers[currentQuestion] === currentQ?.correctIndex;

    return (
        <div className="quiz-creator-container">
            <div className="quiz-creator-header">
                <button className="back-button" onClick={() => navigate('/master')}>
                    ← Back to Master
                </button>
                <h1><FaBook /> Quiz Creator</h1>
                <p className="subtitle">Generate interactive quizzes from your documents</p>
            </div>

            {/* Tab Navigation */}
            <div className="quiz-tabs">
                <button 
                    className={`quiz-tab ${tab === 'generate' ? 'active' : ''}`}
                    onClick={() => setTab('generate')}
                    disabled={status === 'generating'}
                >
                    <FaCog /> Generate Quiz
                </button>
                <button 
                    className={`quiz-tab ${tab === 'take-quiz' ? 'active' : ''}`}
                    onClick={() => setTab('take-quiz')}
                    disabled={!quizData || quizCompleted}
                >
                    <FaPlay /> Take Quiz
                </button>
                <button 
                    className={`quiz-tab ${tab === 'results' ? 'active' : ''}`}
                    onClick={() => setTab('results')}
                    disabled={!quizCompleted}
                >
                    <FaCheckCircle /> Results
                </button>
            </div>

            {/* Generate Tab */}
            {tab === 'generate' && (
                <div className="generate-tab">
                    {status === 'idle' && (
                        <>
                            {/* Quiz Configuration */}
                            <div className="quiz-config-section">
                                <h2>Quiz Configuration</h2>
                                <div className="config-grid">
                                    <div className="config-item">
                                        <label>Number of Questions</label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="50"
                                            value={numQuestions}
                                            onChange={(e) => setNumQuestions(Math.min(50, Math.max(1, parseInt(e.target.value) || 10)))}
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
                                onClick={startQuizGeneration}
                                disabled={(source === 'vault' && selectedFileIds.length === 0) || 
                                         (source === 'upload' && uploadedFiles.length === 0)}
                            >
                                <FaPlay /> Generate Quiz
                            </button>
                        </>
                    )}

                    {status === 'generating' && (
                        <div className="progress-section">
                            <h2>Generating Quiz...</h2>
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                            </div>
                            <p className="progress-text">{progress}% complete</p>
                        </div>
                    )}

                    {status === 'completed' && (
                        <div className="success-message">
                            <FaCheckCircle /> Quiz generated successfully! Switch to "Take Quiz" tab.
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

            {/* Take Quiz Tab */}
            {tab === 'take-quiz' && quizData && (
                <div className="take-quiz-tab">
                    <div className="quiz-header-info">
                        <h2>{quizData.title}</h2>
                        <div className="quiz-meta">
                            <span className="difficulty-badge">{quizData.difficulty}</span>
                            <span className="question-counter">
                                Question {currentQuestion + 1} of {quizData.questions.length}
                            </span>
                        </div>
                    </div>

                    <div className="question-card">
                        <h3 className="question-text">{currentQ?.question}</h3>
                        
                        <div className="options-list">
                            {currentQ?.options.map((option, idx) => {
                                const isSelected = userAnswers[currentQuestion] === idx;
                                const isCorrectOption = idx === currentQ.correctIndex;
                                const showCorrect = showExplanation && isCorrectOption;
                                const showWrong = showExplanation && isSelected && !isCorrectOption;

                                return (
                                    <button
                                        key={idx}
                                        className={`option-btn ${isSelected ? 'selected' : ''} ${showCorrect ? 'correct' : ''} ${showWrong ? 'wrong' : ''}`}
                                        onClick={() => handleAnswerSelect(currentQuestion, idx)}
                                        disabled={showExplanation}
                                    >
                                        <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                                        <span className="option-text">{option}</span>
                                        {showCorrect && <FaCheckCircle className="check-icon" />}
                                        {showWrong && <FaTimesCircle className="wrong-icon" />}
                                    </button>
                                );
                            })}
                        </div>

                        {isAnswered && !showExplanation && (
                            <button className="show-explanation-btn" onClick={handleShowExplanation}>
                                Show Explanation
                            </button>
                        )}

                        {showExplanation && currentQ?.explanation && (
                            <div className={`explanation-box ${isCorrect ? 'correct' : 'incorrect'}`}>
                                <strong>{isCorrect ? 'Correct!' : 'Incorrect'}</strong>
                                <p>{currentQ.explanation}</p>
                            </div>
                        )}
                    </div>

                    <div className="quiz-navigation">
                        <button 
                            onClick={handlePrevious} 
                            disabled={currentQuestion === 0}
                            className="nav-btn"
                        >
                            ← Previous
                        </button>
                        
                        <div className="progress-dots">
                            {quizData.questions.map((_, idx) => (
                                <span 
                                    key={idx}
                                    className={`dot ${idx === currentQuestion ? 'active' : ''} ${userAnswers[idx] !== undefined ? 'answered' : ''}`}
                                    onClick={() => setCurrentQuestion(idx)}
                                />
                            ))}
                        </div>

                        {currentQuestion < quizData.questions.length - 1 ? (
                            <button onClick={handleNext} className="nav-btn">
                                Next →
                            </button>
                        ) : (
                            <button onClick={handleSubmitQuiz} className="submit-btn">
                                Submit Quiz
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Results Tab */}
            {tab === 'results' && quizCompleted && (
                <div className="results-tab">
                    <div className="results-header">
                        <h2>Quiz Results</h2>
                        <div className="score-circle">
                            <div className="score-number">{Math.round((score / quizData.questions.length) * 100)}%</div>
                            <div className="score-text">{score} / {quizData.questions.length}</div>
                        </div>
                    </div>

                    <div className="results-summary">
                        <div className="summary-item correct">
                            <FaCheckCircle />
                            <span>{score} Correct</span>
                        </div>
                        <div className="summary-item incorrect">
                            <FaTimesCircle />
                            <span>{quizData.questions.length - score} Incorrect</span>
                        </div>
                    </div>

                    <div className="results-details">
                        <h3>Question Review</h3>
                        {quizData.questions.map((q, idx) => {
                            const userAnswer = userAnswers[idx];
                            const isCorrect = userAnswer === q.correctIndex;
                            
                            return (
                                <div key={idx} className={`result-item ${isCorrect ? 'correct' : 'incorrect'}`}>
                                    <div className="result-header">
                                        {isCorrect ? <FaCheckCircle /> : <FaTimesCircle />}
                                        <h4>Question {idx + 1}</h4>
                                    </div>
                                    <p className="result-question">{q.question}</p>
                                    <div className="result-answers">
                                        <p><strong>Your answer:</strong> {q.options[userAnswer]}</p>
                                        {!isCorrect && (
                                            <p className="correct-answer">
                                                <strong>Correct answer:</strong> {q.options[q.correctIndex]}
                                            </p>
                                        )}
                                    </div>
                                    {q.explanation && (
                                        <p className="result-explanation"><strong>Explanation:</strong> {q.explanation}</p>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    <div className="results-actions">
                        <button onClick={handleRetakeQuiz} className="action-btn">
                            <FaRedo /> Retake Quiz
                        </button>
                        <button onClick={downloadQuiz} className="action-btn">
                            <FaDownload /> Download Quiz
                        </button>
                        <button onClick={handleRestart} className="action-btn">
                            Create New Quiz
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default QuizCreator;
