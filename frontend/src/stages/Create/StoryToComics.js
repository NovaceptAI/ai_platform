import React, { useState, useEffect } from 'react';
import './StoryToComics.css';
import axiosInstance from '../../utils/axiosInstance';
import { BookOpen, Upload, FileText, Sparkles, Eye, Download, X, ChevronLeft, ChevronRight, MessageSquare, Trash2 } from 'lucide-react';

function StoryToComics() {
    // Tab state
    const [activeTab, setActiveTab] = useState('gallery'); // 'create' | 'gallery' | 'view'

    // Source type
    const [sourceType, setSourceType] = useState('vault'); // 'vault' | 'upload' | 'text'

    // Vault files
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileIds, setSelectedFileIds] = useState([]);

    // Upload
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [uploadedFileIds, setUploadedFileIds] = useState([]);

    // Text prompt
    const [textPrompt, setTextPrompt] = useState('');

    // Configuration
    const [numPanels, setNumPanels] = useState(6);
    const [style, setStyle] = useState('vivid');

    // Progress and results
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [error, setError] = useState('');

    // Gallery state
    const [comics, setComics] = useState([]);
    const [isLoadingGallery, setIsLoadingGallery] = useState(false);
    const [selectedComic, setSelectedComic] = useState(null);
    const [selectedPanel, setSelectedPanel] = useState(null);

    // Lightbox
    const [lightboxOpen, setLightboxOpen] = useState(false);
    const [lightboxImage, setLightboxImage] = useState('');

    // Fetch gallery on mount
    useEffect(() => {
        fetchGallery();
    }, []);

    // Fetch vault files when needed
    useEffect(() => {
        if (sourceType === 'vault') {
            fetchVaultFiles();
        }
    }, [sourceType]);

    const fetchGallery = async () => {
        setIsLoadingGallery(true);
        try {
            const response = await axiosInstance.get('/create/story_to_comics/gallery');
            const comicsData = response.data.comics || [];
            setComics(comicsData);
        } catch (err) {
            console.error('Error fetching gallery:', err);
            // Don't set error state on mount, just log it
        } finally {
            setIsLoadingGallery(false);
        }
    };

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            const files = response.data.files || [];

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
        const files = Array.from(e.target.files).slice(0, 3); // Max 3 files
        if (files.length === 0) return;

        const uploadPromises = files.map(async (file) => {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await axiosInstance.post('/upload', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });

                return {
                    file: file,
                    id: response.data.file_id
                };
            } catch (err) {
                console.error('Upload error:', err);
                return null;
            }
        });

        const results = await Promise.all(uploadPromises);
        const successfulUploads = results.filter(r => r !== null);

        setUploadedFiles(successfulUploads.map(r => r.file));
        setUploadedFileIds(successfulUploads.map(r => r.id));
    };

    const toggleFileSelection = (fileId) => {
        setSelectedFileIds(prev => {
            if (prev.includes(fileId)) {
                return prev.filter(id => id !== fileId);
            } else {
                if (prev.length >= 3) {
                    setError('Maximum 3 files can be selected');
                    return prev;
                }
                return [...prev, fileId];
            }
        });
        setError('');
    };

    const handleGenerate = async () => {
        // Validate input based on source type
        let file_ids = [];
        let text_prompt = '';

        if (sourceType === 'vault') {
            if (selectedFileIds.length === 0) {
                setError('Please select at least one file from vault');
                return;
            }
            file_ids = selectedFileIds;
        } else if (sourceType === 'upload') {
            if (uploadedFileIds.length === 0) {
                setError('Please upload at least one file');
                return;
            }
            file_ids = uploadedFileIds;
        } else { // text
            if (textPrompt.trim().length < 50) {
                setError('Text prompt must be at least 50 characters');
                return;
            }
            text_prompt = textPrompt;
        }

        setIsGenerating(true);
        setError('');
        setProgress(0);
        setProgressMessage('Starting comic creation...');

        try {
            // Start the task (user_id will be extracted from JWT token by backend)
            const response = await axiosInstance.post('/create/story_to_comics/start', {
                source_type: sourceType,
                file_ids: file_ids,
                text_prompt: text_prompt,
                num_panels: numPanels,
                style: style,
                generate_images: true
            });

            const progressId = response.data.progress_id;

            // Poll for progress
            pollProgress(progressId);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to start comic creation');
            setIsGenerating(false);
        }
    };

    const pollProgress = async (progressId) => {
        const pollInterval = setInterval(async () => {
            try {
                const response = await axiosInstance.get(`/create/story_to_comics/progress/${progressId}`);
                const data = response.data;

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    setProgress(100);
                    setProgressMessage('Comic creation complete!');

                    // Reload gallery to show new comic
                    await fetchGallery();

                    setIsGenerating(false);
                    setActiveTab('gallery');
                } else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    setError(data.error_message || 'Comic creation failed');
                    setIsGenerating(false);
                } else {
                    setProgress(data.percentage || 0);
                    setProgressMessage(data.status === 'in_progress' ? 'Creating comic panels...' : 'Pending...');
                }
            } catch (err) {
                clearInterval(pollInterval);
                setError(err.response?.data?.error || 'Polling error');
                setIsGenerating(false);
            }
        }, 2000);
    };

    const handleViewComic = async (comic) => {
        try {
            // Fetch full comic details with all panels
            const response = await axiosInstance.get(`/create/story_to_comics/comics/${comic.id}`);
            const fullComic = response.data;

            setSelectedComic(fullComic);
            if (fullComic.panels && fullComic.panels.length > 0) {
                setSelectedPanel(fullComic.panels[0]);
            }
            setActiveTab('view');
        } catch (err) {
            console.error('Error fetching comic details:', err);
            setError('Failed to load comic details');
        }
    };

    const handleDeleteComic = async (comicId, event) => {
        // Prevent event bubbling
        if (event) {
            event.stopPropagation();
        }

        if (!window.confirm('Are you sure you want to delete this comic? This action cannot be undone.')) {
            return;
        }

        try {
            await axiosInstance.delete(`/create/story_to_comics/comics/${comicId}`);

            // Reload gallery
            await fetchGallery();

            // If viewing the deleted comic, go back to gallery
            if (selectedComic && selectedComic.id === comicId) {
                setSelectedComic(null);
                setSelectedPanel(null);
                setActiveTab('gallery');
            }
        } catch (err) {
            console.error('Error deleting comic:', err);
            setError(err.response?.data?.error || 'Failed to delete comic');
        }
    };

    const navigatePanel = (direction) => {
        if (!selectedComic || !selectedPanel) return;

        const panels = selectedComic.panels;
        const currentIndex = panels.findIndex(p => p.panel_number === selectedPanel.panel_number);

        let newIndex;
        if (direction === 'prev') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : panels.length - 1;
        } else {
            newIndex = currentIndex < panels.length - 1 ? currentIndex + 1 : 0;
        }

        setSelectedPanel(panels[newIndex]);
    };

    const openLightbox = (imageUrl) => {
        setLightboxImage(imageUrl);
        setLightboxOpen(true);
    };

    const closeLightbox = () => {
        setLightboxOpen(false);
        setLightboxImage('');
    };

    const handleDownloadImage = async (imageUrl, panelNumber) => {
        try {
            const response = await fetch(imageUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `comic-panel-${panelNumber}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('Download failed:', err);
        }
    };

    return (
        <div className="stc-container">
            {/* Header */}
            <div className="stc-hero">
                <h1>
                    <BookOpen size={40} />
                    Story to Comics Creator
                </h1>
                <p className="stc-subtitle">Transform stories into engaging comic strips with AI-generated panels</p>
            </div>

            {/* Tabs */}
            <div className="stc-tabs">
                <button
                    className={`stc-tab ${activeTab === 'create' ? 'active' : ''}`}
                    onClick={() => setActiveTab('create')}
                    disabled={isGenerating}
                >
                    <Sparkles size={18} />
                    Create
                </button>
                <button
                    className={`stc-tab ${activeTab === 'gallery' ? 'active' : ''}`}
                    onClick={() => setActiveTab('gallery')}
                >
                    <FileText size={18} />
                    Gallery {comics.length > 0 && `(${comics.length})`}
                </button>
                <button
                    className={`stc-tab ${activeTab === 'view' ? 'active' : ''}`}
                    disabled={!selectedComic}
                    onClick={() => setActiveTab('view')}
                >
                    <Eye size={18} />
                    View Comic
                </button>
            </div>

            {/* Create Tab */}
            {activeTab === 'create' && (
                <div className="stc-section">
                    <h2 className="stc-section-title">Select Story Source</h2>

                    {/* Source selector */}
                    <div className="stc-source-selector">
                        <label className="stc-radio">
                            <input
                                type="radio"
                                value="vault"
                                checked={sourceType === 'vault'}
                                onChange={() => setSourceType('vault')}
                            />
                            <span>Knowledge Vault</span>
                        </label>
                        <label className="stc-radio">
                            <input
                                type="radio"
                                value="upload"
                                checked={sourceType === 'upload'}
                                onChange={() => setSourceType('upload')}
                            />
                            <span>Upload Files</span>
                        </label>
                        <label className="stc-radio">
                            <input
                                type="radio"
                                value="text"
                                checked={sourceType === 'text'}
                                onChange={() => setSourceType('text')}
                            />
                            <span>Text Prompt</span>
                        </label>
                    </div>

                    {/* Vault selection */}
                    {sourceType === 'vault' && (
                        <div className="stc-form-group">
                            <label className="stc-label">Select Files from Vault (Max 3)</label>
                            <div className="stc-file-list">
                                {vaultFiles.length === 0 ? (
                                    <div className="stc-empty-files">
                                        No files in vault. Upload files first.
                                    </div>
                                ) : (
                                    vaultFiles.map((file) => (
                                        <div
                                            key={file.id}
                                            className={`stc-file-item ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
                                            onClick={() => toggleFileSelection(file.id)}
                                        >
                                            <FileText size={18} />
                                            <span className="stc-file-name">{file.name}</span>
                                            {selectedFileIds.includes(file.id) && (
                                                <span className="stc-selected-badge"></span>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                            {selectedFileIds.length > 0 && (
                                <div className="stc-selected-count">
                                    {selectedFileIds.length} file{selectedFileIds.length !== 1 ? 's' : ''} selected
                                </div>
                            )}
                        </div>
                    )}

                    {/* Upload */}
                    {sourceType === 'upload' && (
                        <div className="stc-form-group">
                            <label className="stc-label">Upload Story Files (Max 3)</label>
                            <input
                                type="file"
                                className="stc-input"
                                accept=".pdf,.txt,.doc,.docx"
                                multiple
                                onChange={handleFileUpload}
                            />
                            {uploadedFiles.length > 0 && (
                                <div className="stc-uploaded-list">
                                    {uploadedFiles.map((file, index) => (
                                        <div key={index} className="stc-uploaded-item">
                                            <FileText size={18} />
                                            <span>{file.name}</span>
                                            <span className="stc-file-size">
                                                {(file.size / 1024).toFixed(1)} KB
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Text prompt */}
                    {sourceType === 'text' && (
                        <div className="stc-form-group">
                            <label className="stc-label">Enter Your Story (Min 50 characters)</label>
                            <textarea
                                className="stc-textarea"
                                rows="8"
                                placeholder="Once upon a time in a land far away..."
                                value={textPrompt}
                                onChange={(e) => setTextPrompt(e.target.value)}
                            />
                            <div className="stc-char-count">
                                {textPrompt.length} characters {textPrompt.length < 50 && `(${50 - textPrompt.length} more needed)`}
                            </div>
                        </div>
                    )}

                    {/* Configuration */}
                    <h2 className="stc-section-title">Comic Configuration</h2>

                    <div className="stc-config">
                        <div className="stc-form-group">
                            <label className="stc-label">
                                Number of Panels: {numPanels}
                            </label>
                            <input
                                type="range"
                                min="3"
                                max="12"
                                value={numPanels}
                                onChange={(e) => setNumPanels(parseInt(e.target.value))}
                                className="stc-slider"
                            />
                        </div>

                        <div className="stc-form-group">
                            <label className="stc-label">Comic Style</label>
                            <select
                                className="stc-input"
                                value={style}
                                onChange={(e) => setStyle(e.target.value)}
                            >
                                <option value="vivid">Vivid (Bold Comic Book Style)</option>
                                <option value="natural">Natural (Realistic Graphic Novel)</option>
                            </select>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="stc-actions">
                        <button
                            className="btn-primary"
                            onClick={handleGenerate}
                            disabled={isGenerating}
                        >
                            <Sparkles size={20} />
                            {isGenerating ? 'Creating Comic...' : 'Create Comic'}
                        </button>
                    </div>

                    {/* Progress */}
                    {isGenerating && (
                        <div className="stc-progress-container">
                            <div className="stc-progress-bar">
                                <div
                                    className="stc-progress-fill"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                            <div className="stc-progress-text">
                                {progress}% - {progressMessage}
                            </div>
                        </div>
                    )}

                    {/* Error */}
                    {error && <div className="stc-error">{error}</div>}
                </div>
            )}

            {/* Gallery Tab */}
            {activeTab === 'gallery' && (
                <div className="stc-section">
                    <div className="stc-section-header">
                        <h2 className="stc-section-title">Comic Gallery</h2>
                        <div className="stc-header-info">
                            {comics.length} comic{comics.length !== 1 ? 's' : ''} created
                        </div>
                    </div>

                    {/* Creating overlay */}
                    {isGenerating && (
                        <div className="stc-creating-overlay">
                            <div className="stc-creating-message">
                                <Sparkles size={32} />
                                <p>Creating new comic...</p>
                                <div className="stc-progress-bar">
                                    <div
                                        className="stc-progress-fill"
                                        style={{ width: `${progress}%` }}
                                    />
                                </div>
                                <div className="stc-progress-text">
                                    {progress}% - {progressMessage}
                                </div>
                            </div>
                        </div>
                    )}

                    {isLoadingGallery ? (
                        <div className="stc-empty">
                            Loading gallery...
                        </div>
                    ) : comics.length === 0 ? (
                        <div className="stc-empty">
                            No comics created yet. Go to Create tab to make your first comic!
                        </div>
                    ) : (
                        <div className="stc-comics-grid">
                            {comics.map((comic) => (
                                <div key={comic.id} className="stc-comic-card">
                                    <div className="stc-comic-header">
                                        <h3 className="stc-comic-title">
                                            {comic.title || 'Comic Story'}
                                        </h3>
                                        <div className="stc-comic-meta">
                                            {comic.total_panels} panels • {comic.style}
                                            {comic.source_file_name && ` • ${comic.source_file_name}`}
                                            {comic.source_type === 'text' && ' • Text Prompt'}
                                        </div>
                                    </div>

                                    {/* Preview thumbnail */}
                                    {comic.thumbnail_url && (
                                        <div className="stc-comic-preview">
                                            <img
                                                src={comic.thumbnail_url}
                                                alt="Comic preview"
                                                className="stc-preview-image"
                                            />
                                        </div>
                                    )}

                                    <div className="stc-comic-actions">
                                        <button
                                            className="btn-primary btn-sm"
                                            onClick={() => handleViewComic(comic)}
                                        >
                                            <Eye size={16} />
                                            View Comic
                                        </button>
                                        <button
                                            className="btn-ghost btn-sm"
                                            onClick={(e) => handleDeleteComic(comic.id, e)}
                                            style={{ color: '#dc2626' }}
                                        >
                                            <Trash2 size={16} />
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* View Comic Tab */}
            {activeTab === 'view' && selectedComic && selectedPanel && (
                <div className="stc-section">
                    <div className="stc-comic-viewer">
                        <div className="stc-viewer-header">
                            <h2 className="stc-section-title">
                                {selectedComic.title || 'Comic Story'}
                            </h2>
                            <div className="stc-panel-nav">
                                <button
                                    className="btn-ghost btn-sm"
                                    onClick={() => navigatePanel('prev')}
                                >
                                    <ChevronLeft size={18} />
                                    Previous
                                </button>
                                <span className="stc-panel-indicator">
                                    Panel {selectedPanel.panel_number} of {selectedComic.panels?.length || 0}
                                </span>
                                <button
                                    className="btn-ghost btn-sm"
                                    onClick={() => navigatePanel('next')}
                                >
                                    Next
                                    <ChevronRight size={18} />
                                </button>
                            </div>
                        </div>

                        {/* Panel Image */}
                        {selectedPanel.image_url && (
                            <div className="stc-panel-image-container">
                                <img
                                    src={selectedPanel.image_url}
                                    alt={selectedPanel.title}
                                    className="stc-panel-image"
                                    onClick={() => openLightbox(selectedPanel.image_url)}
                                />
                            </div>
                        )}

                        {/* Panel Details */}
                        <div className="stc-panel-details">
                            <h3 className="stc-panel-title">{selectedPanel.title}</h3>

                            {selectedPanel.scene_description && (
                                <div className="stc-detail-section">
                                    <h4>Scene</h4>
                                    <p>{selectedPanel.scene_description}</p>
                                </div>
                            )}

                            {selectedPanel.dialogue && selectedPanel.dialogue.length > 0 && (
                                <div className="stc-detail-section">
                                    <h4><MessageSquare size={18} /> Dialogue</h4>
                                    <div className="stc-dialogue-list">
                                        {selectedPanel.dialogue.map((line, idx) => (
                                            <div key={idx} className="stc-dialogue-item">
                                                {line}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {selectedPanel.narration && (
                                <div className="stc-detail-section">
                                    <h4>Narration</h4>
                                    <p className="stc-narration">{selectedPanel.narration}</p>
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="stc-viewer-actions">
                            <button
                                className="btn-ghost"
                                onClick={() => setActiveTab('gallery')}
                            >
                                Back to Gallery
                            </button>
                            {selectedPanel.image_url && (
                                <button
                                    className="btn-primary"
                                    onClick={() => handleDownloadImage(selectedPanel.image_url, selectedPanel.panel_number)}
                                >
                                    <Download size={20} />
                                    Download Panel
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Lightbox */}
            {lightboxOpen && (
                <div className="stc-lightbox" onClick={closeLightbox}>
                    <button className="stc-lightbox-close" onClick={closeLightbox}>
                        <X size={32} />
                    </button>
                    <img
                        src={lightboxImage}
                        alt="Comic panel"
                        className="stc-lightbox-image"
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
            )}
        </div>
    );
}

export default StoryToComics;
