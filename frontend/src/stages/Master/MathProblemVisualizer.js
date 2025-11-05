import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaCalculator, FaChartLine, FaLightbulb, FaFileAlt, FaPencilAlt, FaCheckCircle } from 'react-icons/fa';
import './MathProblemVisualizer.css';
import axiosInstance from '../../utils/axiosInstance';

function MathProblemVisualizer() {
    const navigate = useNavigate();
    
    // State Management
    const [tab, setTab] = useState('solve'); // 'solve' | 'results'
    const [inputMethod, setInputMethod] = useState('text'); // 'text' | 'document'
    
    // Text Input
    const [problemText, setProblemText] = useState('');
    
    // Document Upload
    const [uploadedFile, setUploadedFile] = useState(null);
    
    // Configuration
    const [difficulty, setDifficulty] = useState('intermediate');
    const [level, setLevel] = useState('school');
    const [showHints, setShowHints] = useState(true);
    const [practiceCount, setPracticeCount] = useState(3);
    const [visualizeTypes, setVisualizeTypes] = useState(['graph', 'number_line', 'geometry']);
    
    // Processing Status
    const [status, setStatus] = useState('idle'); // 'idle' | 'solving' | 'completed' | 'error'
    const [errorMessage, setErrorMessage] = useState('');
    
    // Results Data
    const [solutionData, setSolutionData] = useState(null);
    const [expandedSteps, setExpandedSteps] = useState({});
    const [showHintsInResults, setShowHintsInResults] = useState(true);

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            setUploadedFile(file);
        }
    };

    const toggleVisualizeType = (type) => {
        setVisualizeTypes(prev => 
            prev.includes(type) 
                ? prev.filter(t => t !== type)
                : [...prev, type]
        );
    };

    const solveMathProblem = async () => {
        try {
            setStatus('solving');
            setErrorMessage('');
            setSolutionData(null);

            if (inputMethod === 'text') {
                if (!problemText.trim() || problemText.trim().length < 5) {
                    setErrorMessage('Please enter a math problem (minimum 5 characters)');
                    setStatus('error');
                    return;
                }

                // Solve with text input
                const res = await axiosInstance.post('/master/math_visualizer/solve', {
                    method: 'text',
                    text: problemText.trim(),
                    difficulty,
                    level,
                    show_hints: showHints,
                    practice_count: practiceCount,
                    visualize_types: visualizeTypes
                });

                setSolutionData(res.data);
                setStatus('completed');
                setTab('results');
            } else {
                // Document upload
                if (!uploadedFile) {
                    setErrorMessage('Please upload a document');
                    setStatus('error');
                    return;
                }

                const formData = new FormData();
                formData.append('file', uploadedFile);
                formData.append('method', 'document');
                formData.append('difficulty', difficulty);
                formData.append('level', level);
                formData.append('show_hints', showHints.toString());
                formData.append('practice_count', practiceCount.toString());
                formData.append('visualize_types', visualizeTypes.join(','));

                const res = await axiosInstance.post('/master/math_visualizer/solve', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });

                setSolutionData(res.data);
                setStatus('completed');
                setTab('results');
            }

        } catch (error) {
            console.error('Error solving math problem:', error);
            setErrorMessage(error.response?.data?.error || 'Failed to solve the problem. Please try again.');
            setStatus('error');
        }
    };

    const toggleStep = (stepId) => {
        setExpandedSteps(prev => ({
            ...prev,
            [stepId]: !prev[stepId]
        }));
    };

    const expandAllSteps = () => {
        const allExpanded = {};
        if (solutionData?.steps) {
            solutionData.steps.forEach(step => {
                allExpanded[step.id] = true;
            });
        }
        setExpandedSteps(allExpanded);
    };

    const collapseAllSteps = () => {
        setExpandedSteps({});
    };

    const startNewProblem = () => {
        setProblemText('');
        setUploadedFile(null);
        setSolutionData(null);
        setStatus('idle');
        setErrorMessage('');
        setExpandedSteps({});
        setTab('solve');
    };

    const renderLatex = (text) => {
        // Simple LaTeX rendering - in production, use KaTeX or MathJax
        if (!text) return '';
        return text;
    };

    const renderDiagram = (diagram) => {
        const { type, title, svg, plot } = diagram;

        return (
            <div className="math-diagram" key={title}>
                <h4 className="diagram-title">
                    <FaChartLine /> {title || `${type} visualization`}
                </h4>
                
                {svg && (
                    <div className="diagram-svg" dangerouslySetInnerHTML={{ __html: svg }} />
                )}
                
                {plot && plot.x && plot.y && plot.x.length > 0 && (
                    <div className="diagram-plot">
                        <div className="plot-info">
                            <p><strong>{plot.series_label || 'Data Series'}</strong></p>
                            <p>X-axis: {plot.x_label || 'X'}</p>
                            <p>Y-axis: {plot.y_label || 'Y'}</p>
                            <p>Points: {plot.x.length}</p>
                        </div>
                        <div className="plot-data">
                            {plot.x.slice(0, 10).map((x, i) => (
                                <span key={i} className="plot-point">
                                    ({x.toFixed(2)}, {plot.y[i]?.toFixed(2) || 0})
                                </span>
                            ))}
                            {plot.x.length > 10 && <span>... ({plot.x.length} total points)</span>}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="math-visualizer-container">
            <div className="math-visualizer-header">
                <button className="back-button" onClick={() => navigate('/master')}>
                    ← Back to Master Stage
                </button>
                <h1 className="math-visualizer-title">
                    <FaCalculator /> Math Problem Visualizer
                </h1>
                <p className="math-visualizer-subtitle">
                    Solve math problems with step-by-step visualizations
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="math-tabs">
                <button 
                    className={`math-tab ${tab === 'solve' ? 'active' : ''}`}
                    onClick={() => setTab('solve')}
                >
                    <FaPencilAlt /> Solve Problem
                </button>
                <button 
                    className={`math-tab ${tab === 'results' ? 'active' : ''}`}
                    onClick={() => setTab('results')}
                    disabled={!solutionData}
                >
                    <FaCheckCircle /> View Solution
                </button>
            </div>

            {/* Solve Tab */}
            {tab === 'solve' && (
                <div className="math-solve-section">
                    {/* Input Method Selection */}
                    <div className="input-method-selector">
                        <h3>Input Method</h3>
                        <div className="method-buttons">
                            <button
                                className={`method-btn ${inputMethod === 'text' ? 'active' : ''}`}
                                onClick={() => setInputMethod('text')}
                            >
                                <FaPencilAlt /> Text Input
                            </button>
                            <button
                                className={`method-btn ${inputMethod === 'document' ? 'active' : ''}`}
                                onClick={() => setInputMethod('document')}
                            >
                                <FaFileAlt /> Upload Document
                            </button>
                        </div>
                    </div>

                    {/* Text Input */}
                    {inputMethod === 'text' && (
                        <div className="text-input-section">
                            <h3>Enter Math Problem</h3>
                            <textarea
                                className="problem-input"
                                value={problemText}
                                onChange={(e) => setProblemText(e.target.value)}
                                placeholder="Enter your math problem here... (e.g., 'Solve 2x + 3 = 11', 'Find the derivative of x²+3x', etc.)"
                                rows={6}
                            />
                            <p className="input-hint">
                                {problemText.length} characters {problemText.length < 5 && '(minimum 5 required)'}
                            </p>
                        </div>
                    )}

                    {/* Document Upload */}
                    {inputMethod === 'document' && (
                        <div className="document-upload-section">
                            <h3>Upload Document</h3>
                            <div className="file-upload-area">
                                <input
                                    type="file"
                                    id="math-file-upload"
                                    onChange={handleFileUpload}
                                    accept=".pdf,.docx,.txt"
                                    style={{ display: 'none' }}
                                />
                                <label htmlFor="math-file-upload" className="upload-label">
                                    <FaFileAlt />
                                    {uploadedFile ? (
                                        <span>Selected: {uploadedFile.name}</span>
                                    ) : (
                                        <span>Click to upload PDF, DOCX, or TXT (max 25MB)</span>
                                    )}
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Configuration */}
                    <div className="math-config-section">
                        <h3>Configuration</h3>
                        
                        <div className="config-grid">
                            {/* Difficulty */}
                            <div className="config-item">
                                <label>Difficulty Level</label>
                                <select 
                                    value={difficulty} 
                                    onChange={(e) => setDifficulty(e.target.value)}
                                    className="config-select"
                                >
                                    <option value="beginner">Beginner</option>
                                    <option value="intermediate">Intermediate</option>
                                    <option value="advanced">Advanced</option>
                                </select>
                            </div>

                            {/* Level */}
                            <div className="config-item">
                                <label>Education Level</label>
                                <select 
                                    value={level} 
                                    onChange={(e) => setLevel(e.target.value)}
                                    className="config-select"
                                >
                                    <option value="school">School</option>
                                    <option value="college">College</option>
                                    <option value="olympiad">Olympiad</option>
                                </select>
                            </div>

                            {/* Practice Count */}
                            <div className="config-item">
                                <label>Practice Problems</label>
                                <input
                                    type="number"
                                    min="0"
                                    max="10"
                                    value={practiceCount}
                                    onChange={(e) => setPracticeCount(parseInt(e.target.value) || 0)}
                                    className="config-input"
                                />
                            </div>

                            {/* Show Hints */}
                            <div className="config-item">
                                <label>
                                    <input
                                        type="checkbox"
                                        checked={showHints}
                                        onChange={(e) => setShowHints(e.target.checked)}
                                    />
                                    Show Hints
                                </label>
                            </div>
                        </div>

                        {/* Visualization Types */}
                        <div className="visualize-types-section">
                            <label>Visualization Types</label>
                            <div className="visualize-checkboxes">
                                {['graph', 'number_line', 'geometry', 'flowchart'].map(type => (
                                    <label key={type} className="checkbox-label">
                                        <input
                                            type="checkbox"
                                            checked={visualizeTypes.includes(type)}
                                            onChange={() => toggleVisualizeType(type)}
                                        />
                                        {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Error Display */}
                    {status === 'error' && errorMessage && (
                        <div className="math-error-message">
                            {errorMessage}
                        </div>
                    )}

                    {/* Action Button */}
                    <div className="math-actions">
                        <button
                            className="solve-button"
                            onClick={solveMathProblem}
                            disabled={status === 'solving'}
                        >
                            {status === 'solving' ? (
                                <>
                                    <div className="spinner"></div>
                                    Solving Problem...
                                </>
                            ) : (
                                <>
                                    <FaCalculator /> Solve Problem
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}

            {/* Results Tab */}
            {tab === 'results' && solutionData && (
                <div className="math-results-section">
                    <div className="results-header">
                        <h2>Solution</h2>
                        <div className="results-actions">
                            <button className="action-btn" onClick={expandAllSteps}>
                                Expand All
                            </button>
                            <button className="action-btn" onClick={collapseAllSteps}>
                                Collapse All
                            </button>
                            <button className="action-btn primary" onClick={startNewProblem}>
                                <FaCalculator /> New Problem
                            </button>
                        </div>
                    </div>

                    {/* Problem Statement */}
                    <div className="result-card problem-card">
                        <h3><FaCalculator /> Problem</h3>
                        <p className="problem-text">{solutionData.problem}</p>
                        {solutionData.interpretation && (
                            <p className="interpretation-text">
                                <strong>Interpretation:</strong> {solutionData.interpretation}
                            </p>
                        )}
                        {solutionData.latex?.problem && (
                            <div className="latex-display">
                                <strong>LaTeX:</strong> {renderLatex(solutionData.latex.problem)}
                            </div>
                        )}
                    </div>

                    {/* Final Answer */}
                    <div className="result-card answer-card">
                        <h3><FaCheckCircle /> Final Answer</h3>
                        <p className="final-answer">{solutionData.final_answer}</p>
                        {solutionData.latex?.answer && (
                            <div className="latex-display">
                                <strong>LaTeX:</strong> {renderLatex(solutionData.latex.answer)}
                            </div>
                        )}
                    </div>

                    {/* Formulas Used */}
                    {solutionData.formulas && solutionData.formulas.length > 0 && (
                        <div className="result-card formulas-card">
                            <h3>Key Formulas</h3>
                            <ul className="formulas-list">
                                {solutionData.formulas.map((formula, idx) => (
                                    <li key={idx}>{renderLatex(formula)}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Step-by-Step Solution */}
                    {solutionData.steps && solutionData.steps.length > 0 && (
                        <div className="result-card steps-card">
                            <h3>Step-by-Step Solution</h3>
                            <div className="steps-container">
                                {solutionData.steps.map((step, idx) => (
                                    <div key={step.id} className={`step-item ${expandedSteps[step.id] ? 'expanded' : ''}`}>
                                        <div 
                                            className="step-header"
                                            onClick={() => toggleStep(step.id)}
                                        >
                                            <span className="step-number">Step {idx + 1}</span>
                                            <span className="step-title">{step.title}</span>
                                            <span className="expand-icon">{expandedSteps[step.id] ? '−' : '+'}</span>
                                        </div>
                                        
                                        {expandedSteps[step.id] && (
                                            <div className="step-content">
                                                {showHintsInResults && step.hint && (
                                                    <div className="step-hint">
                                                        <FaLightbulb /> <strong>Hint:</strong> {step.hint}
                                                    </div>
                                                )}
                                                <div className="step-detail">
                                                    {step.detail}
                                                </div>
                                                {step.formula && (
                                                    <div className="step-formula">
                                                        <strong>Formula:</strong> {renderLatex(step.formula)}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Visualizations/Diagrams */}
                    {solutionData.diagrams && solutionData.diagrams.length > 0 && (
                        <div className="result-card diagrams-card">
                            <h3>Visualizations</h3>
                            <div className="diagrams-container">
                                {solutionData.diagrams.map((diagram, idx) => (
                                    <div key={idx}>
                                        {renderDiagram(diagram)}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Verification Checks */}
                    {solutionData.checks && solutionData.checks.length > 0 && (
                        <div className="result-card checks-card">
                            <h3>Verification Checks</h3>
                            <ul className="checks-list">
                                {solutionData.checks.map((check, idx) => (
                                    <li key={idx}><FaCheckCircle /> {check}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Alternative Methods */}
                    {solutionData.alternates && solutionData.alternates.length > 0 && (
                        <div className="result-card alternates-card">
                            <h3>Alternative Approaches</h3>
                            <ul className="alternates-list">
                                {solutionData.alternates.map((alt, idx) => (
                                    <li key={idx}>{alt}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Practice Problems */}
                    {solutionData.practice && solutionData.practice.length > 0 && (
                        <div className="result-card practice-card">
                            <h3>Practice Problems</h3>
                            <div className="practice-container">
                                {solutionData.practice.map((prob, idx) => (
                                    <div key={idx} className="practice-item">
                                        <div className="practice-header">
                                            <span className="practice-number">Problem {idx + 1}</span>
                                            <span className={`practice-difficulty ${prob.difficulty}`}>
                                                {prob.difficulty}
                                            </span>
                                        </div>
                                        <p className="practice-question">{prob.question}</p>
                                        <p className="practice-answer">
                                            <strong>Answer:</strong> {prob.answer}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default MathProblemVisualizer;
