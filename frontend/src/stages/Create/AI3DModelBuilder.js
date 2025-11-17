import React, { useState, useEffect, useRef } from 'react';
import './AI3DModelBuilder.css';
import axiosInstance from '../../utils/axiosInstance';
import Model3DViewer from './Model3DViewer';
import {
    Box, Sparkles, Eye, Download, Trash2, X,
    ChevronLeft, ChevronRight, Palette, Grid3x3,
    RotateCcw, ZoomIn, ZoomOut, Maximize2
} from 'lucide-react';

function AI3DModelBuilder() {
    // Tab state
    const [activeTab, setActiveTab] = useState('create'); // create, gallery, view

    // Input state
    const [promptText, setPromptText] = useState('');
    const [title, setTitle] = useState('My 3D Model');
    const [complexityLevel, setComplexityLevel] = useState('simple');
    const [selectedStyle, setSelectedStyle] = useState('realistic');
    const [styles, setStyles] = useState([]);

    // Generation state
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [error, setError] = useState('');
    const [currentProgressId, setCurrentProgressId] = useState('');

    // Gallery state
    const [models, setModels] = useState([]);
    const [isLoadingGallery, setIsLoadingGallery] = useState(false);
    const [selectedModel, setSelectedModel] = useState(null);

    // 3D Viewer state
    const viewerRef = useRef(null);
    const [viewerMode, setViewerMode] = useState('3d'); // '3d' or '2d' (preview images)
    const [autoRotate, setAutoRotate] = useState(true);
    const [showGrid, setShowGrid] = useState(false);
    const [currentAngle, setCurrentAngle] = useState(0); // for 2D preview images

    // Categories for prompts
    const categories = [
        { id: 'objects', name: 'Objects', icon: '🎁', examples: ['coffee mug', 'wooden chair', 'desk lamp'] },
        { id: 'vehicles', name: 'Vehicles', icon: '🚗', examples: ['sports car', 'airplane', 'sailboat'] },
        { id: 'buildings', name: 'Buildings', icon: '🏛️', examples: ['modern house', 'castle', 'tower'] },
        { id: 'nature', name: 'Nature', icon: '🌳', examples: ['pine tree', 'flower', 'mountain'] },
        { id: 'characters', name: 'Characters', icon: '🤖', examples: ['robot', 'cute animal', 'fantasy creature'] },
        { id: 'food', name: 'Food', icon: '🍕', examples: ['pizza slice', 'birthday cake', 'apple'] }
    ];

    // Fetch styles on mount
    useEffect(() => {
        fetchStyles();
        fetchGallery();
    }, []);

    // Poll progress during generation
    useEffect(() => {
        let interval;
        if (isGenerating && currentProgressId) {
            interval = setInterval(async () => {
                try {
                    const response = await axiosInstance.get(`/stages/create/ai_3d_model_builder/progress/${currentProgressId}`);
                    const data = response.data;

                    setProgress(data.percentage || 0);

                    if (data.status === 'completed') {
                        setIsGenerating(false);
                        setProgress(100);
                        setProgressMessage('3D model generated successfully!');

                        // Get the model details
                        if (data.result && data.result.model_id) {
                            const modelResponse = await axiosInstance.get(`/stages/create/ai_3d_model_builder/models/${data.result.model_id}`);
                            setSelectedModel(modelResponse.data);
                            setActiveTab('view');
                        }

                        await fetchGallery();
                    } else if (data.status === 'failed') {
                        setIsGenerating(false);
                        setError(data.error_message || 'Generation failed');
                        setProgressMessage('');
                    } else {
                        setProgressMessage('Generating 3D model...');
                    }
                } catch (err) {
                    console.error('Error polling progress:', err);
                }
            }, 2000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isGenerating, currentProgressId]);

    const fetchStyles = async () => {
        try {
            const response = await axiosInstance.get('/stages/create/ai_3d_model_builder/styles');
            setStyles(response.data.styles || []);
        } catch (err) {
            console.error('Error fetching styles:', err);
        }
    };

    const fetchGallery = async () => {
        setIsLoadingGallery(true);
        try {
            const response = await axiosInstance.get('/stages/create/ai_3d_model_builder/gallery');
            setModels(response.data.models || []);
        } catch (err) {
            console.error('Error fetching gallery:', err);
        } finally {
            setIsLoadingGallery(false);
        }
    };

    const handleGenerate = async () => {
        setError('');

        if (promptText.trim().length < 10) {
            setError('Please enter at least 10 characters for the description');
            return;
        }

        setIsGenerating(true);
        setProgress(0);
        setProgressMessage('Starting 3D model generation...');

        try {
            const response = await axiosInstance.post('/stages/create/ai_3d_model_builder/generate', {
                prompt_text: promptText.trim(),
                complexity_level: complexityLevel,
                style: selectedStyle,
                title: title.trim()
            });

            setCurrentProgressId(response.data.progress_id);
        } catch (err) {
            console.error('Error starting generation:', err);
            setError(err.response?.data?.error || 'Failed to start generation');
            setIsGenerating(false);
            setProgressMessage('');
        }
    };

    const handleDownload = async (modelId, format = 'glb') => {
        try {
            const response = await axiosInstance.get(
                `/stages/create/ai_3d_model_builder/models/${modelId}/download?format=${format}`,
                { responseType: 'blob' }
            );

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            const contentDisposition = response.headers['content-disposition'];
            let filename = `model.${format}`;
            if (contentDisposition) {
                const quotedMatch = contentDisposition.match(/filename="([^"]+)"/);
                const unquotedMatch = contentDisposition.match(/filename=([^;]+)/);
                if (quotedMatch) {
                    filename = quotedMatch[1];
                } else if (unquotedMatch) {
                    filename = unquotedMatch[1].trim();
                }
            }

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Error downloading model:', err);
            setError('Failed to download model');
        }
    };

    const handleDelete = async (modelId) => {
        if (!window.confirm('Are you sure you want to delete this 3D model?')) {
            return;
        }

        try {
            await axiosInstance.delete(`/stages/create/ai_3d_model_builder/models/${modelId}`);
            await fetchGallery();
            if (selectedModel?.id === modelId) {
                setSelectedModel(null);
                setActiveTab('gallery');
            }
        } catch (err) {
            console.error('Error deleting model:', err);
            setError('Failed to delete model');
        }
    };

    const viewModel = async (modelId) => {
        try {
            const response = await axiosInstance.get(`/stages/create/ai_3d_model_builder/models/${modelId}`);
            setSelectedModel(response.data);
            setActiveTab('view');
        } catch (err) {
            console.error('Error fetching model:', err);
            setError('Failed to load model');
        }
    };

    const setPromptFromExample = (example) => {
        setPromptText(example);
    };

    const renderCreateTab = () => (
        <div className="model-create-tab">
            <h2>Create 3D Model from Text</h2>
            <p className="create-instructions">
                Describe the 3D object you want to create, and AI will generate it for you.
            </p>

            {/* Prompt Input */}
            <div className="prompt-section">
                <label>Describe Your 3D Object</label>
                <textarea
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    placeholder="a red sports car with sleek aerodynamic design..."
                    rows={5}
                    maxLength={500}
                    className="prompt-textarea"
                />
                <div className="char-count">{promptText.length}/500 characters</div>
            </div>

            {/* Quick Examples by Category */}
            <div className="examples-section">
                <label>Quick Examples</label>
                <div className="categories-grid">
                    {categories.map(cat => (
                        <div key={cat.id} className="category-card">
                            <div className="category-header">
                                <span className="category-icon">{cat.icon}</span>
                                <span className="category-name">{cat.name}</span>
                            </div>
                            <div className="category-examples">
                                {cat.examples.map((example, idx) => (
                                    <button
                                        key={idx}
                                        className="example-btn"
                                        onClick={() => setPromptFromExample(example)}
                                    >
                                        {example}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Title Input */}
            <div className="title-section">
                <label>Model Title</label>
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="My 3D Model"
                    maxLength={100}
                    className="title-input"
                />
            </div>

            {/* Complexity Level */}
            <div className="complexity-section">
                <label>Detail Level</label>
                <div className="complexity-buttons">
                    {['simple', 'medium', 'detailed'].map(level => (
                        <button
                            key={level}
                            className={`complexity-btn ${complexityLevel === level ? 'active' : ''}`}
                            onClick={() => setComplexityLevel(level)}
                        >
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                        </button>
                    ))}
                </div>
                <p className="complexity-hint">
                    {complexityLevel === 'simple' && 'Fast generation with basic shapes (5-8 shapes)'}
                    {complexityLevel === 'medium' && 'Balanced detail and generation time (8-12 shapes)'}
                    {complexityLevel === 'detailed' && 'High detail with complex geometry (12-15 shapes)'}
                </p>
            </div>

            {/* Style Selection */}
            <div className="style-section">
                <label>3D Style</label>
                <div className="styles-grid">
                    {styles.map(style => (
                        <button
                            key={style.id}
                            className={`style-card ${selectedStyle === style.id ? 'active' : ''}`}
                            onClick={() => setSelectedStyle(style.id)}
                        >
                            <span className="style-icon">{style.icon}</span>
                            <div className="style-name">{style.name}</div>
                            <div className="style-desc">{style.description}</div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Generate Button */}
            <button
                className="generate-btn"
                onClick={handleGenerate}
                disabled={isGenerating || promptText.length < 10}
            >
                <Sparkles size={20} />
                {isGenerating ? 'Generating...' : 'Generate 3D Model'}
            </button>

            {/* Progress */}
            {isGenerating && (
                <div className="progress-section">
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                    </div>
                    <p className="progress-message">{progressMessage}</p>
                    <p className="progress-percent">{progress}%</p>
                </div>
            )}

            {/* Error */}
            {error && <div className="error-message">{error}</div>}
        </div>
    );

    const renderGalleryTab = () => (
        <div className="model-gallery-tab">
            <h2>Your 3D Models</h2>

            {isLoadingGallery ? (
                <p className="loading">Loading models...</p>
            ) : models.length === 0 ? (
                <div className="empty-gallery">
                    <Box size={64} />
                    <p>No 3D models yet</p>
                    <button onClick={() => setActiveTab('create')}>Create Your First Model</button>
                </div>
            ) : (
                <div className="models-grid">
                    {models.map(model => (
                        <div key={model.id} className="model-card">
                            <div className="card-thumbnail">
                                {model.thumbnail_url ? (
                                    <img src={model.thumbnail_url} alt={model.title} />
                                ) : (
                                    <div className="placeholder-thumbnail">
                                        <Box size={48} />
                                    </div>
                                )}
                                <div className="card-overlay">
                                    <button
                                        onClick={() => viewModel(model.id)}
                                        className="overlay-btn"
                                    >
                                        <Eye size={20} />
                                    </button>
                                </div>
                            </div>
                            <div className="card-info">
                                <h3>{model.title}</h3>
                                <p className="card-meta">
                                    {model.style} • {model.complexity_level}
                                </p>
                                <p className="card-details">
                                    {model.vertex_count?.toLocaleString()} vertices
                                </p>
                            </div>
                            <div className="card-actions">
                                <button
                                    onClick={() => handleDownload(model.id, 'glb')}
                                    className="action-btn download-btn"
                                    title="Download GLB"
                                >
                                    <Download size={16} />
                                    GLB
                                </button>
                                <button
                                    onClick={() => handleDownload(model.id, 'obj')}
                                    className="action-btn download-btn"
                                    title="Download OBJ"
                                >
                                    <Download size={16} />
                                    OBJ
                                </button>
                                <button
                                    onClick={() => handleDelete(model.id)}
                                    className="action-btn delete-btn"
                                    title="Delete"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    const renderViewTab = () => {
        if (!selectedModel) {
            return (
                <div className="view-empty">
                    <p>No model selected</p>
                    <button onClick={() => setActiveTab('gallery')}>Back to Gallery</button>
                </div>
            );
        }

        const previewImages = selectedModel.preview_images || [];

        return (
            <div className="model-view-tab">
                <div className="view-header">
                    <button onClick={() => setActiveTab('gallery')} className="back-btn">
                        <ChevronLeft size={20} />
                        Back to Gallery
                    </button>
                    <h2>{selectedModel.title}</h2>
                    <div className="view-actions">
                        <button
                            onClick={() => handleDownload(selectedModel.id, 'glb')}
                            className="download-btn"
                        >
                            <Download size={20} />
                            Download GLB
                        </button>
                        <button
                            onClick={() => handleDownload(selectedModel.id, 'obj')}
                            className="download-btn"
                        >
                            <Download size={20} />
                            Download OBJ
                        </button>
                        <button
                            onClick={() => handleDownload(selectedModel.id, 'stl')}
                            className="download-btn"
                        >
                            <Download size={20} />
                            Download STL
                        </button>
                    </div>
                </div>

                <div className="view-content">
                    {/* Model Viewer */}
                    <div className="model-viewer-container">
                        <div className="viewer-header">
                            <h3>3D Preview</h3>
                            <div className="viewer-mode-toggle">
                                <button
                                    className={`mode-btn ${viewerMode === '3d' ? 'active' : ''}`}
                                    onClick={() => setViewerMode('3d')}
                                    title="Interactive 3D View"
                                >
                                    <Grid3x3 size={16} />
                                    3D View
                                </button>
                                {previewImages.length > 0 && (
                                    <button
                                        className={`mode-btn ${viewerMode === '2d' ? 'active' : ''}`}
                                        onClick={() => setViewerMode('2d')}
                                        title="2D Preview Images"
                                    >
                                        <Eye size={16} />
                                        2D View
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="viewer-canvas">
                            {viewerMode === '3d' ? (
                                selectedModel.model_files?.glb_url ? (
                                    <Model3DViewer
                                        modelUrl={selectedModel.model_files.glb_url}
                                        modelFormat="glb"
                                        autoRotate={autoRotate}
                                        showGrid={showGrid}
                                        backgroundColor="#1a1a1a"
                                        cameraPosition={[3, 2, 5]}
                                    />
                                ) : (
                                    <div className="no-3d-model">
                                        <Box size={64} />
                                        <p>3D model file not available</p>
                                        <small>GLB format required for 3D view</small>
                                    </div>
                                )
                            ) : (
                                <>
                                    {previewImages.length > 0 && (
                                        <div className="angle-selector">
                                            {previewImages.map((preview, idx) => (
                                                <button
                                                    key={idx}
                                                    className={`angle-btn ${currentAngle === idx ? 'active' : ''}`}
                                                    onClick={() => setCurrentAngle(idx)}
                                                >
                                                    {preview.angle}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                    {previewImages.length > 0 && previewImages[currentAngle] ? (
                                        <img
                                            src={previewImages[currentAngle].url}
                                            alt={`${selectedModel.title} - ${previewImages[currentAngle].angle} view`}
                                            className="preview-image"
                                        />
                                    ) : (
                                        <div className="no-preview">
                                            <Box size={64} />
                                            <p>No preview available</p>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                        <div className="viewer-controls">
                            <button
                                className={`control-btn ${autoRotate ? 'active' : ''}`}
                                onClick={() => setAutoRotate(!autoRotate)}
                                title="Toggle Auto Rotate"
                            >
                                <RotateCcw size={18} />
                            </button>
                            <button
                                className={`control-btn ${showGrid ? 'active' : ''}`}
                                onClick={() => setShowGrid(!showGrid)}
                                title="Toggle Grid"
                            >
                                <Grid3x3 size={18} />
                            </button>
                        </div>
                    </div>

                    {/* Model Info */}
                    <div className="model-info-panel">
                        <h3>Model Information</h3>

                        <div className="info-group">
                            <label>Prompt</label>
                            <p className="info-value">{selectedModel.prompt_text}</p>
                        </div>

                        <div className="info-group">
                            <label>Style</label>
                            <p className="info-value">{selectedModel.style}</p>
                        </div>

                        <div className="info-group">
                            <label>Complexity</label>
                            <p className="info-value">{selectedModel.complexity_level}</p>
                        </div>

                        <div className="info-group">
                            <label>Object Type</label>
                            <p className="info-value">{selectedModel.object_type || 'N/A'}</p>
                        </div>

                        <div className="info-group">
                            <label>Category</label>
                            <p className="info-value">{selectedModel.category || 'N/A'}</p>
                        </div>

                        <div className="info-group">
                            <label>Statistics</label>
                            <div className="stats-grid">
                                <div className="stat-item">
                                    <span className="stat-label">Vertices</span>
                                    <span className="stat-value">{selectedModel.vertex_count?.toLocaleString() || '0'}</span>
                                </div>
                                <div className="stat-item">
                                    <span className="stat-label">Faces</span>
                                    <span className="stat-value">{selectedModel.polygon_count?.toLocaleString() || '0'}</span>
                                </div>
                                <div className="stat-item">
                                    <span className="stat-label">File Size</span>
                                    <span className="stat-value">
                                        {selectedModel.file_size_bytes
                                            ? `${(selectedModel.file_size_bytes / 1024).toFixed(1)} KB`
                                            : 'N/A'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="info-group">
                            <label>Created</label>
                            <p className="info-value">
                                {selectedModel.created_at
                                    ? new Date(selectedModel.created_at).toLocaleString()
                                    : 'N/A'}
                            </p>
                        </div>

                        <div className="info-group">
                            <label>Available Formats</label>
                            <div className="formats-list">
                                {selectedModel.model_files?.glb_url && <span className="format-badge">GLB</span>}
                                {selectedModel.model_files?.obj_url && <span className="format-badge">OBJ</span>}
                                {selectedModel.model_files?.stl_url && <span className="format-badge">STL</span>}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="ai-3d-model-builder">
            <div className="model-header">
                <h1>
                    <Box size={32} />
                    AI 3D Model Builder
                </h1>
                <p className="description">Create 3D models from text descriptions using AI</p>
            </div>

            <div className="tabs">
                <button
                    className={`tab ${activeTab === 'create' ? 'active' : ''}`}
                    onClick={() => setActiveTab('create')}
                >
                    <Sparkles size={18} />
                    Create
                </button>
                <button
                    className={`tab ${activeTab === 'gallery' ? 'active' : ''}`}
                    onClick={() => setActiveTab('gallery')}
                >
                    <Grid3x3 size={18} />
                    Gallery
                </button>
                {selectedModel && (
                    <button
                        className={`tab ${activeTab === 'view' ? 'active' : ''}`}
                        onClick={() => setActiveTab('view')}
                    >
                        <Eye size={18} />
                        View
                    </button>
                )}
            </div>

            <div className="tab-content">
                {activeTab === 'create' && renderCreateTab()}
                {activeTab === 'gallery' && renderGalleryTab()}
                {activeTab === 'view' && renderViewTab()}
            </div>
        </div>
    );
}

export default AI3DModelBuilder;
