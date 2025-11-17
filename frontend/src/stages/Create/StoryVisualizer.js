import React, { useState, useEffect } from 'react';
import './StoryVisualizer.css';
import axiosInstance from '../../utils/axiosInstance';
import { FileText, Image, Eye, Sparkles, Download, X, ChevronLeft, ChevronRight } from 'lucide-react';

function StoryVisualizer() {
    // Tab state
    const [activeTab, setActiveTab] = useState('generate'); // 'generate' | 'explore' | 'review'

    // Generate tab state
    const [sourceType, setSourceType] = useState('vault'); // 'vault' | 'upload'
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileId, setSelectedFileId] = useState('');
    const [uploadedFile, setUploadedFile] = useState(null);
    const [uploadedFileId, setUploadedFileId] = useState('');

    // Configuration
    const [numScenes, setNumScenes] = useState(5);
    const [style, setStyle] = useState('vivid');
    const [forceRegenerate, setForceRegenerate] = useState(false);

    // Progress and results
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [error, setError] = useState('');

    // Results state
    const [scenes, setScenes] = useState([]);
    const [metadata, setMetadata] = useState({});
    const [currentFileId, setCurrentFileId] = useState('');

    // Review state
    const [selectedScene, setSelectedScene] = useState(null);
    const [lightboxOpen, setLightboxOpen] = useState(false);
    const [lightboxImage, setLightboxImage] = useState('');

    // Fetch vault files on mount
    useEffect(() => {
        if (sourceType === 'vault') {
            fetchVaultFiles();
        }
    }, [sourceType]);

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            const files = response.data.files || [];

            // Normalize file structure to match API response
            const normalizedFiles = files.map(file => ({
                id: file.fileId || file.id,
                name: file.name,
                stored_name: file.stored_name
            }));

            setVaultFiles(normalizedFiles);
        } catch (err) {
            console.error('Error fetching vault files:', err);
            setError('Failed to load Knowledge Vault files');
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axiosInstance.post('/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            setUploadedFile(file);
            setUploadedFileId(response.data.file_id);
        } catch (err) {
            setError(err.response?.data?.error || 'Upload failed');
        }
    };

    const handleGenerate = async () => {
        const fileId = sourceType === 'vault' ? selectedFileId : uploadedFileId;

        if (!fileId) {
            setError('Please select or upload a file');
            return;
        }

        setIsGenerating(true);
        setError('');
        setProgress(0);
        setProgressMessage('Starting story visualization...');

        try {
            // Start the task
            const response = await axiosInstance.post('/create/story_visualizer/start', {
                file_ids: [fileId],  // Backend expects an array of file IDs
                user_id: 'admin',
                num_scenes: numScenes,
                style: style,
                generate_images: true,
                options: {
                    story_type: 'educational',
                    narrative_style: 'engaging',
                    audience_level: 'general',
                    creative_elements: true
                }
            });

            const progressId = response.data.progress_id;
            setCurrentFileId(fileId);

            // Poll for progress
            pollProgress(progressId, fileId);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to start visualization');
            setIsGenerating(false);
        }
    };

    const pollProgress = async (progressId, fileId) => {
        const pollInterval = setInterval(async () => {
            try {
                const response = await axiosInstance.get(`/create/story_visualizer/progress/${progressId}`);
                const data = response.data;

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    setProgress(100);
                    setProgressMessage('Visualization complete!');

                    // Fetch results
                    await fetchResults(fileId);

                    setIsGenerating(false);
                    setActiveTab('explore');
                } else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    setError(data.error_message || 'Visualization failed');
                    setIsGenerating(false);
                } else {
                    setProgress(data.percentage || 0);
                    setProgressMessage(data.status === 'in_progress' ? 'Processing...' : 'Pending...');
                }
            } catch (err) {
                clearInterval(pollInterval);
                setError(err.response?.data?.error || 'Polling error');
                setIsGenerating(false);
            }
        }, 2000);
    };

    const fetchResults = async (fileId) => {
        try {
            const response = await axiosInstance.get(`/create/story_visualizer/results?file_id=${fileId}`);
            
            // Extract scene images from the response
            const sceneImages = response.data.scene_images || [];
            setScenes(sceneImages);
            setMetadata(response.data.metadata || {});
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to fetch results');
        }
    };

    const handleViewScene = (scene) => {
        setSelectedScene(scene);
        setActiveTab('review');
    };

    const openLightbox = (imageUrl) => {
        setLightboxImage(imageUrl);
        setLightboxOpen(true);
    };

    const closeLightbox = () => {
        setLightboxOpen(false);
        setLightboxImage('');
    };

    const handleDownloadImage = async (imageUrl, sceneNumber) => {
        try {
            const response = await fetch(imageUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `story-scene-${sceneNumber}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('Download failed:', err);
        }
    };

    const navigateScene = (direction) => {
        if (!selectedScene || scenes.length === 0) return;

        const currentIndex = scenes.findIndex(s => s.scene_number === selectedScene.scene_number);
        let newIndex;

        if (direction === 'prev') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : scenes.length - 1;
        } else {
            newIndex = currentIndex < scenes.length - 1 ? currentIndex + 1 : 0;
        }

        setSelectedScene(scenes[newIndex]);
    };

    return (
        <div className="sv-container">
            {/* Header */}
            <div className="sv-hero">
                <h1>
                    <Image size={40} />
                    Document Visualizer
                </h1>
                <p className="sv-subtitle">Transform document content into clear visual diagrams and illustrations</p>
            </div>

            {/* Tabs */}
            <div className="sv-tabs">
                <button
                    className={`sv-tab ${activeTab === 'generate' ? 'active' : ''}`}
                    onClick={() => setActiveTab('generate')}
                >
                    <Sparkles size={18} />
                    Generate
                </button>
                <button
                    className={`sv-tab ${activeTab === 'explore' ? 'active' : ''}`}
                    disabled={scenes.length === 0}
                    onClick={() => setActiveTab('explore')}
                >
                    <FileText size={18} />
                    Explore Visuals
                </button>
                <button
                    className={`sv-tab ${activeTab === 'review' ? 'active' : ''}`}
                    disabled={!selectedScene}
                    onClick={() => setActiveTab('review')}
                >
                    <Eye size={18} />
                    Review
                </button>
            </div>

            {/* Generate Tab */}
            {activeTab === 'generate' && (
                <div className="sv-section">
                    <h2 className="sv-section-title">Select Document Source</h2>

                    {/* Source selector */}
                    <div className="sv-source-selector">
                        <label className="sv-radio">
                            <input
                                type="radio"
                                value="vault"
                                checked={sourceType === 'vault'}
                                onChange={() => setSourceType('vault')}
                            />
                            <span>Knowledge Vault</span>
                        </label>
                        <label className="sv-radio">
                            <input
                                type="radio"
                                value="upload"
                                checked={sourceType === 'upload'}
                                onChange={() => setSourceType('upload')}
                            />
                            <span>Upload New File</span>
                        </label>
                    </div>

                    {/* File selection */}
                    {sourceType === 'vault' && (
                        <div className="sv-form-group">
                            <label className="sv-label">Select File from Vault</label>
                            <select
                                className="sv-input"
                                value={selectedFileId}
                                onChange={(e) => setSelectedFileId(e.target.value)}
                            >
                                <option value="">Choose a file...</option>
                                {vaultFiles.map((file) => (
                                    <option key={file.id} value={file.id}>
                                        {file.name}
                                    </option>
                                ))}
                            </select>
                            {vaultFiles.length === 0 && (
                                <div className="sv-empty-files">
                                    No files in vault. Upload files first.
                                </div>
                            )}
                        </div>
                    )}

                    {sourceType === 'upload' && (
                        <div className="sv-form-group">
                            <label className="sv-label">Upload Document File</label>
                            <input
                                type="file"
                                className="sv-input"
                                accept=".pdf,.txt,.doc,.docx"
                                onChange={handleFileUpload}
                            />
                            {uploadedFile && (
                                <div className="sv-uploaded-list">
                                    <div className="sv-uploaded-item">
                                        <span>{uploadedFile.name}</span>
                                        <span className="sv-file-size">
                                            {(uploadedFile.size / 1024).toFixed(1)} KB
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Configuration */}
                    <h2 className="sv-section-title">Visualization Configuration</h2>

                    <div className="sv-config">
                        <div className="sv-form-group">
                            <label className="sv-label">
                                Number of Visualizations: {numScenes}
                            </label>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                value={numScenes}
                                onChange={(e) => setNumScenes(parseInt(e.target.value))}
                                className="sv-slider"
                            />
                        </div>

                        <div className="sv-form-group">
                            <label className="sv-label">Diagram Style</label>
                            <select
                                className="sv-input"
                                value={style}
                                onChange={(e) => setStyle(e.target.value)}
                            >
                                <option value="vivid">Vivid (Clear & Colorful Educational Diagrams)</option>
                                <option value="natural">Natural (Professional & Technical Illustrations)</option>
                            </select>
                        </div>
                    </div>

                    <label className="sv-checkbox">
                        <input
                            type="checkbox"
                            checked={forceRegenerate}
                            onChange={(e) => setForceRegenerate(e.target.checked)}
                        />
                        Force regenerate (ignore cached results)
                    </label>

                    {/* Actions */}
                    <div className="sv-actions">
                        <button
                            className="btn-primary"
                            onClick={handleGenerate}
                            disabled={isGenerating || (!selectedFileId && !uploadedFileId)}
                        >
                            <Sparkles size={20} />
                            {isGenerating ? 'Generating...' : 'Generate Visualizations'}
                        </button>
                    </div>

                    {/* Progress */}
                    {isGenerating && (
                        <div className="sv-progress-container">
                            <div className="sv-progress-bar">
                                <div
                                    className="sv-progress-fill"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                            <div className="sv-progress-text">
                                {progress}% - {progressMessage}
                            </div>
                        </div>
                    )}

                    {/* Error */}
                    {error && <div className="sv-error">{error}</div>}
                </div>
            )}

            {/* Explore Tab */}
            {activeTab === 'explore' && (
                <div className="sv-section">
                    <div className="sv-section-header">
                        <h2 className="sv-section-title">Visualization Gallery</h2>
                        <div className="sv-header-info">
                            {scenes.length} visualizations • {style} style
                        </div>
                    </div>

                    {scenes.length === 0 ? (
                        <div className="sv-empty">
                            No visualizations generated yet. Go to Generate tab to create visualizations.
                        </div>
                    ) : (
                        <div className="sv-grid">
                            {scenes.map((scene) => (
                                <div key={scene.scene_number} className="sv-card">
                                    <div className="sv-card-image-wrapper">
                                        <img
                                            src={scene.image_url}
                                            alt={scene.title}
                                            className="sv-card-image"
                                            onClick={() => openLightbox(scene.image_url)}
                                        />
                                        <div className="sv-card-overlay">
                                            <button
                                                className="sv-overlay-btn"
                                                onClick={() => openLightbox(scene.image_url)}
                                            >
                                                <Eye size={20} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="sv-card-body">
                                        <div className="sv-scene-number">
                                            Visualization {scene.scene_number}
                                        </div>
                                        <h3 className="sv-card-title">{scene.title}</h3>
                                        <p className="sv-card-description">
                                            {scene.description.substring(0, 100)}...
                                        </p>
                                        <div className="sv-card-actions">
                                            <button
                                                className="btn-ghost btn-sm"
                                                onClick={() => handleViewScene(scene)}
                                            >
                                                View Details
                                            </button>
                                            <button
                                                className="btn-ghost btn-sm"
                                                onClick={() => handleDownloadImage(scene.image_url, scene.scene_number)}
                                            >
                                                <Download size={16} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Review Tab */}
            {activeTab === 'review' && selectedScene && (
                <div className="sv-section">
                    <div className="sv-review-card">
                        <div className="sv-review-header">
                            <h2 className="sv-section-title">
                                Visualization {selectedScene.scene_number}: {selectedScene.title}
                            </h2>
                            <div className="sv-review-nav">
                                <button
                                    className="btn-ghost btn-sm"
                                    onClick={() => navigateScene('prev')}
                                >
                                    <ChevronLeft size={18} />
                                    Previous
                                </button>
                                <button
                                    className="btn-ghost btn-sm"
                                    onClick={() => navigateScene('next')}
                                >
                                    Next
                                    <ChevronRight size={18} />
                                </button>
                            </div>
                        </div>

                        <div className="sv-review-image-container">
                            <img
                                src={selectedScene.image_url}
                                alt={selectedScene.title}
                                className="sv-review-image"
                                onClick={() => openLightbox(selectedScene.image_url)}
                            />
                        </div>

                        <div className="sv-review-content">
                            <h3>Content Description</h3>
                            <p className="sv-review-description">
                                {selectedScene.description}
                            </p>

                            {selectedScene.revised_prompt && (
                                <>
                                    <h3>Visualization Prompt</h3>
                                    <p className="sv-review-prompt">
                                        {selectedScene.revised_prompt}
                                    </p>
                                </>
                            )}
                        </div>

                        <div className="sv-review-actions">
                            <button
                                className="btn-ghost"
                                onClick={() => setActiveTab('explore')}
                            >
                                Back to Gallery
                            </button>
                            <button
                                className="btn-primary"
                                onClick={() => handleDownloadImage(selectedScene.image_url, selectedScene.scene_number)}
                            >
                                <Download size={20} />
                                Download Image
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Lightbox */}
            {lightboxOpen && (
                <div className="sv-lightbox" onClick={closeLightbox}>
                    <button className="sv-lightbox-close" onClick={closeLightbox}>
                        <X size={32} />
                    </button>
                    <img
                        src={lightboxImage}
                        alt="Visualization"
                        className="sv-lightbox-image"
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
            )}
        </div>
    );
}

export default StoryVisualizer;
