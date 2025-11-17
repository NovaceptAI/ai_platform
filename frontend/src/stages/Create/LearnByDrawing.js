import React, { useState, useEffect, useRef, useCallback } from 'react';
import './LearnByDrawing.css';
import axiosInstance from '../../utils/axiosInstance';
import * as fabricModule from 'fabric';
import {
    Pencil, Eraser, Circle, Square, Trash2, Upload,
    Sparkles, Eye, BookOpen, ChevronLeft, Award
} from 'lucide-react';

// Access fabric classes from the module
const fabric = fabricModule;

function LearnByDrawing() {
    // Error state for canvas initialization
    const [loadError, setLoadError] = useState(null);

    // Tab state
    const [activeTab, setActiveTab] = useState('draw'); // draw, gallery, view

    // Canvas state
    const canvasRef = useRef(null);
    const fabricCanvasRef = useRef(null);
    const [canvasSize] = useState({ width: 1000, height: 700 });

    // Drawing state
    const [drawingMode, setDrawingMode] = useState('pen'); // pen, eraser, fill, shape
    const [brushSize, setBrushSize] = useState(5);
    const [currentColor, setCurrentColor] = useState('#000000');

    // Form state
    const [topic, setTopic] = useState('water_cycle');
    const [ageGroup, setAgeGroup] = useState('8-10');
    const [title, setTitle] = useState('My Drawing');

    // Topics data
    const [topics, setTopics] = useState([]);

    // Analysis state
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [taskId, setTaskId] = useState('');
    const [error, setError] = useState('');

    // Results state
    const [analysisResult, setAnalysisResult] = useState(null);

    // Gallery state
    const [gallery, setGallery] = useState([]);
    const [isLoadingGallery, setIsLoadingGallery] = useState(false);
    const [, setSelectedDrawing] = useState(null);

    // Colors palette
    const colorPalette = [
        '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
        '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080',
        '#FFC0CB', '#A52A2A', '#808080', '#C0C0C0', '#FFD700',
        '#00FF7F', '#4169E1', '#FF1493', '#32CD32', '#FF4500'
    ];

    // Initialize Fabric.js canvas - runs ONCE when component mounts
    useEffect(() => {
        // Only initialize when on draw tab
        if (activeTab !== 'draw') {
            return;
        }

        // Prevent double initialization
        if (fabricCanvasRef.current) {
            console.log('Canvas already initialized');
            return;
        }

        // Use a small delay to ensure canvas element is in the DOM
        const timer = setTimeout(() => {
            // Double-check canvas element exists
            if (!canvasRef.current) {
                console.error('Canvas ref is still null after delay');
                setLoadError('Canvas element not found in DOM');
                return;
            }

            try {
                console.log('Initializing Fabric canvas...', canvasRef.current);

                // Check if fabric is available
                if (!fabric || !fabric.Canvas) {
                    throw new Error('Fabric.js is not loaded');
                }

                // Fabric v6: Set dimensions on the HTML canvas element first
                const canvasEl = canvasRef.current;
                canvasEl.width = canvasSize.width;
                canvasEl.height = canvasSize.height;

                // Initialize Fabric Canvas
                const canvas = new fabric.Canvas(canvasEl);

                // Set background color
                canvas.backgroundColor = '#FFFFFF';
                canvas.renderAll();

                // Enable drawing mode
                canvas.isDrawingMode = true;

                // Configure brush - use a safer approach for Fabric v6
                const PencilBrush = fabric.PencilBrush;
                if (PencilBrush) {
                    canvas.freeDrawingBrush = new PencilBrush(canvas);
                    canvas.freeDrawingBrush.width = brushSize;
                    canvas.freeDrawingBrush.color = currentColor;
                }

                fabricCanvasRef.current = canvas;
                console.log('Fabric canvas initialized successfully', canvas);
            } catch (error) {
                console.error('Error initializing Fabric canvas:', error);
                setLoadError(error.message);
            }
        }, 100); // Small delay to ensure DOM is ready

        return () => {
            clearTimeout(timer);
            // Don't dispose here - we want to keep the canvas alive
        };
    }, []); // Empty dependency array - run only once

    // Cleanup only on unmount
    useEffect(() => {
        return () => {
            if (fabricCanvasRef.current) {
                console.log('Component unmounting - cleaning up Fabric canvas');
                fabricCanvasRef.current.dispose();
                fabricCanvasRef.current = null;
            }
        };
    }, []);

    // Define fetch functions BEFORE useEffects that use them
    const fetchTopics = useCallback(async () => {
        try {
            const response = await axiosInstance.get('/learn_by_drawing/topics');
            setTopics(response.data.topics || []);
        } catch (err) {
            console.error('Error fetching topics:', err);
        }
    }, []);

    const fetchGallery = useCallback(async () => {
        setIsLoadingGallery(true);
        try {
            const response = await axiosInstance.get('/learn_by_drawing/gallery');
            setGallery(response.data.drawings || []);
        } catch (err) {
            console.error('Error fetching gallery:', err);
        } finally {
            setIsLoadingGallery(false);
        }
    }, []);

    // Update canvas drawing settings
    useEffect(() => {
        if (!fabricCanvasRef.current) return;

        const canvas = fabricCanvasRef.current;

        try {
            if (drawingMode === 'pen') {
                canvas.isDrawingMode = true;
                // Wait for brush to be initialized
                if (canvas.freeDrawingBrush) {
                    canvas.freeDrawingBrush.width = brushSize;
                    canvas.freeDrawingBrush.color = currentColor;
                }
            } else if (drawingMode === 'eraser') {
                canvas.isDrawingMode = true;
                // Wait for brush to be initialized
                if (canvas.freeDrawingBrush) {
                    canvas.freeDrawingBrush.width = brushSize * 2;
                    canvas.freeDrawingBrush.color = '#FFFFFF';
                }
            } else {
                canvas.isDrawingMode = false;
            }
        } catch (error) {
            console.error('Error updating canvas settings:', error);
        }
    }, [drawingMode, brushSize, currentColor]);

    // Fetch topics on mount
    useEffect(() => {
        fetchTopics();
        fetchGallery();
    }, [fetchTopics, fetchGallery]);

    // Poll progress during analysis
    useEffect(() => {
        let interval;
        if (isAnalyzing && taskId) {
            interval = setInterval(async () => {
                try {
                    const response = await axiosInstance.get(`/learn_by_drawing/progress/dummy?task_id=${taskId}`);
                    const data = response.data;

                    setProgress(data.progress || 0);
                    setProgressMessage(data.status || '');

                    if (data.state === 'SUCCESS') {
                        setIsAnalyzing(false);
                        setProgress(100);
                        setProgressMessage('Analysis complete!');
                        setAnalysisResult(data.result.drawing);
                        setActiveTab('view');
                        fetchGallery();
                    } else if (data.state === 'FAILURE') {
                        setIsAnalyzing(false);
                        setError(data.error || 'Analysis failed');
                        setProgressMessage('');
                    }
                } catch (err) {
                    console.error('Error polling progress:', err);
                }
            }, 2000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isAnalyzing, taskId, fetchGallery]);

    const clearCanvas = () => {
        if (fabricCanvasRef.current) {
            fabricCanvasRef.current.clear();
            fabricCanvasRef.current.backgroundColor = '#FFFFFF';
            fabricCanvasRef.current.renderAll();
        }
    };

    const addShape = (shapeType) => {
        if (!fabricCanvasRef.current) return;

        const canvas = fabricCanvasRef.current;
        let shape;

        if (shapeType === 'circle') {
            shape = new fabric.Circle({
                radius: 50,
                fill: currentColor,
                left: 100,
                top: 100
            });
        } else if (shapeType === 'rectangle') {
            shape = new fabric.Rect({
                width: 100,
                height: 80,
                fill: currentColor,
                left: 100,
                top: 100
            });
        }

        canvas.add(shape);
        canvas.setActiveObject(shape);
        canvas.renderAll();
    };

    const handleAnalyze = async () => {
        if (!fabricCanvasRef.current) return;

        setError('');
        setIsAnalyzing(true);
        setProgress(0);
        setProgressMessage('Starting analysis...');

        try {
            // Export canvas to image
            const imageData = fabricCanvasRef.current.toDataURL({
                format: 'png',
                quality: 1
            });

            const response = await axiosInstance.post('/learn_by_drawing/analyze', {
                image_data: imageData,
                topic: topic,
                age_group: ageGroup,
                title: title,
                canvas_width: canvasSize.width,
                canvas_height: canvasSize.height
            });

            setTaskId(response.data.task_id);
        } catch (err) {
            console.error('Error starting analysis:', err);
            setError(err.response?.data?.error || 'Failed to start analysis');
            setIsAnalyzing(false);
            setProgressMessage('');
        }
    };

    const handleImageUpload = (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const img = await fabric.FabricImage.fromURL(e.target.result);
                const canvas = fabricCanvasRef.current;

                // Scale image to fit canvas
                const scale = Math.min(
                    canvasSize.width / img.width,
                    canvasSize.height / img.height
                );

                img.scale(scale);
                canvas.clear();
                canvas.backgroundColor = '#FFFFFF';
                canvas.add(img);
                canvas.centerObject(img);
                canvas.renderAll();
            } catch (err) {
                console.error('Error loading image:', err);
            }
        };
        reader.readAsDataURL(file);
    };

    const viewDrawing = (drawing) => {
        setSelectedDrawing(drawing);
        setAnalysisResult(drawing);
        setActiveTab('view');
    };

    const deleteDrawing = async (drawingId) => {
        if (!window.confirm('Delete this drawing?')) return;

        try {
            await axiosInstance.delete(`/learn_by_drawing/drawings/${drawingId}`);
            fetchGallery();
        } catch (err) {
            console.error('Error deleting drawing:', err);
        }
    };

    // Render Draw Tab
    const renderDrawTab = () => (
        <div className="draw-tab">
            <div className="draw-container">
                <div className="draw-sidebar">
                    <h3>Drawing Tools</h3>

                    {/* Tool Selection */}
                    <div className="tool-group">
                        <label>Tool</label>
                        <div className="tool-buttons">
                            <button
                                className={`tool-btn ${drawingMode === 'pen' ? 'active' : ''}`}
                                onClick={() => setDrawingMode('pen')}
                                title="Pen"
                            >
                                <Pencil size={20} />
                            </button>
                            <button
                                className={`tool-btn ${drawingMode === 'eraser' ? 'active' : ''}`}
                                onClick={() => setDrawingMode('eraser')}
                                title="Eraser"
                            >
                                <Eraser size={20} />
                            </button>
                            <button
                                className={`tool-btn ${drawingMode === 'shape' ? 'active' : ''}`}
                                onClick={() => setDrawingMode('shape')}
                                title="Shapes"
                            >
                                <Circle size={20} />
                            </button>
                        </div>
                    </div>

                    {/* Brush Size */}
                    <div className="tool-group">
                        <label>Brush Size</label>
                        <div className="size-buttons">
                            <button
                                className={`size-btn ${brushSize === 2 ? 'active' : ''}`}
                                onClick={() => setBrushSize(2)}
                            >
                                S
                            </button>
                            <button
                                className={`size-btn ${brushSize === 5 ? 'active' : ''}`}
                                onClick={() => setBrushSize(5)}
                            >
                                M
                            </button>
                            <button
                                className={`size-btn ${brushSize === 10 ? 'active' : ''}`}
                                onClick={() => setBrushSize(10)}
                            >
                                L
                            </button>
                        </div>
                    </div>

                    {/* Colors */}
                    <div className="tool-group">
                        <label>Color</label>
                        <div className="color-palette">
                            {colorPalette.map((color) => (
                                <button
                                    key={color}
                                    className={`color-btn ${currentColor === color ? 'active' : ''}`}
                                    style={{ backgroundColor: color }}
                                    onClick={() => setCurrentColor(color)}
                                    title={color}
                                />
                            ))}
                        </div>
                    </div>

                    {/* Shapes */}
                    {drawingMode === 'shape' && (
                        <div className="tool-group">
                            <label>Add Shape</label>
                            <div className="shape-buttons">
                                <button onClick={() => addShape('circle')}>
                                    <Circle size={20} /> Circle
                                </button>
                                <button onClick={() => addShape('rectangle')}>
                                    <Square size={20} /> Rectangle
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="tool-group">
                        <label>Actions</label>
                        <button className="action-btn" onClick={clearCanvas}>
                            <Trash2 size={16} /> Clear Canvas
                        </button>
                        <label htmlFor="image-upload" className="action-btn upload-btn">
                            <Upload size={16} /> Upload Image
                        </label>
                        <input
                            id="image-upload"
                            type="file"
                            accept="image/*"
                            onChange={handleImageUpload}
                            style={{ display: 'none' }}
                        />
                    </div>
                </div>

                <div className="draw-main">
                    <div className="draw-settings">
                        <div className="setting-item">
                            <label>Topic</label>
                            <select value={topic} onChange={(e) => setTopic(e.target.value)}>
                                {topics.map((t) => (
                                    <option key={t.id} value={t.id}>
                                        {t.icon} {t.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="setting-item">
                            <label>Age Group</label>
                            <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
                                <option value="5-7">5-7 years</option>
                                <option value="8-10">8-10 years</option>
                                <option value="11-13">11-13 years</option>
                                <option value="14+">14+ years</option>
                            </select>
                        </div>

                        <div className="setting-item">
                            <label>Title</label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="My Drawing"
                            />
                        </div>
                    </div>

                    <div className="canvas-container">
                        <canvas ref={canvasRef} />
                    </div>

                    {error && <div className="error-message">{error}</div>}

                    {isAnalyzing && (
                        <div className="progress-container">
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${progress}%` }} />
                            </div>
                            <p>{progressMessage}</p>
                        </div>
                    )}

                    <button
                        className="analyze-btn"
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                    >
                        <Sparkles size={20} />
                        {isAnalyzing ? 'Analyzing...' : 'Analyze My Drawing'}
                    </button>
                </div>
            </div>
        </div>
    );

    // Render Gallery Tab
    const renderGalleryTab = () => (
        <div className="gallery-tab">
            <h2>My Drawings Gallery</h2>
            {isLoadingGallery ? (
                <p>Loading...</p>
            ) : gallery.length === 0 ? (
                <div className="empty-gallery">
                    <BookOpen size={64} />
                    <p>No drawings yet. Start creating!</p>
                </div>
            ) : (
                <div className="gallery-grid">
                    {gallery.map((drawing) => (
                        <div key={drawing.id} className="gallery-card">
                            <img src={drawing.drawing_image_url} alt={drawing.title} />
                            <div className="card-content">
                                <h3>{drawing.title}</h3>
                                <p className="topic">{drawing.topic.replace('_', ' ')}</p>
                                <div className="card-stats">
                                    <span className="score">Score: {drawing.accuracy_score}/10</span>
                                    {drawing.badges_earned?.length > 0 && (
                                        <span className="badges">
                                            <Award size={14} /> {drawing.badges_earned.length}
                                        </span>
                                    )}
                                </div>
                                <div className="card-actions">
                                    <button onClick={() => viewDrawing(drawing)}>
                                        <Eye size={16} /> View
                                    </button>
                                    <button onClick={() => deleteDrawing(drawing.id)}>
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    // Render View Tab
    const renderViewTab = () => {
        if (!analysisResult) {
            return (
                <div className="view-empty">
                    <p>No drawing selected</p>
                    <button onClick={() => setActiveTab('gallery')}>Go to Gallery</button>
                </div>
            );
        }

        return (
            <div className="view-tab">
                <button className="back-btn" onClick={() => setActiveTab('gallery')}>
                    <ChevronLeft size={20} /> Back
                </button>

                <div className="view-content">
                    <div className="view-image">
                        <img src={analysisResult.drawing_image_url} alt={analysisResult.title} />
                        <h2>{analysisResult.title}</h2>
                    </div>

                    <div className="view-analysis">
                        <div className="analysis-section">
                            <h3>AI Feedback</h3>
                            <p>{analysisResult.feedback_text}</p>
                        </div>

                        <div className="analysis-section">
                            <h3>Accuracy Score</h3>
                            <div className="score-display">
                                {analysisResult.accuracy_score}/10
                            </div>
                        </div>

                        <div className="analysis-section">
                            <h3>Detected Objects</h3>
                            <div className="tags">
                                {analysisResult.detected_objects?.map((obj, idx) => (
                                    <span key={idx} className="tag">{obj}</span>
                                ))}
                            </div>
                        </div>

                        {analysisResult.suggestions?.length > 0 && (
                            <div className="analysis-section">
                                <h3>Suggestions</h3>
                                <ul>
                                    {analysisResult.suggestions.map((s, idx) => (
                                        <li key={idx}>{s}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {analysisResult.fun_fact && (
                            <div className="analysis-section fun-fact">
                                <h3>Fun Fact!</h3>
                                <p>{analysisResult.fun_fact}</p>
                            </div>
                        )}

                        {analysisResult.badges_earned?.length > 0 && (
                            <div className="analysis-section badges">
                                <h3>Badges Earned!</h3>
                                <div className="badge-list">
                                    {analysisResult.badges_earned.map((badge, idx) => (
                                        <span key={idx} className="badge">
                                            <Award size={16} /> {badge}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    // Show error state if canvas failed to load
    if (loadError) {
        return (
            <div className="learn-by-drawing">
                <div className="header">
                    <h1>
                        <Pencil size={32} />
                        Learn by Drawing
                    </h1>
                    <div className="error-message">
                        <p>Failed to load drawing canvas: {loadError}</p>
                        <p>Please refresh the page or contact support.</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="learn-by-drawing">
            <div className="header">
                <h1>
                    <Pencil size={32} />
                    Learn by Drawing
                </h1>
                <p className="description">Draw concepts and learn with AI feedback</p>
            </div>

            <div className="tabs">
                <button
                    className={`tab ${activeTab === 'draw' ? 'active' : ''}`}
                    onClick={() => setActiveTab('draw')}
                >
                    <Pencil size={18} />
                    Draw
                </button>
                <button
                    className={`tab ${activeTab === 'gallery' ? 'active' : ''}`}
                    onClick={() => setActiveTab('gallery')}
                >
                    <BookOpen size={18} />
                    Gallery
                </button>
                <button
                    className={`tab ${activeTab === 'view' ? 'active' : ''}`}
                    onClick={() => setActiveTab('view')}
                    style={{ display: analysisResult ? 'flex' : 'none' }}
                >
                    <Eye size={18} />
                    View
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'draw' && renderDrawTab()}
                {activeTab === 'gallery' && renderGalleryTab()}
                {activeTab === 'view' && renderViewTab()}
            </div>
        </div>
    );
}

export default LearnByDrawing;
