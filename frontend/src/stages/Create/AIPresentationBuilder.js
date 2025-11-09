import React, { useState, useEffect } from 'react';
import './AIPresentationBuilder.css';
import axiosInstance from '../../utils/axiosInstance';
import {
    Presentation, Upload, FileText, Sparkles, Eye, Download,
    X, ChevronLeft, ChevronRight, Image as ImageIcon,
    Check, Square, CheckSquare, Palette, Trash2
} from 'lucide-react';

function AIPresentationBuilder() {
    // Tab state: create (Stage 1), review (Stage 2), gallery, view
    const [activeTab, setActiveTab] = useState('create');
    const [stage, setStage] = useState(1); // 1 = content generation, 2 = finalize with images

    // Source type
    const [sourceType, setSourceType] = useState('vault'); // 'vault' | 'upload' | 'text'

    // Vault files
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFileId, setSelectedFileId] = useState('');

    // Upload
    const [uploadedFile, setUploadedFile] = useState(null);
    const [uploadedFileId, setUploadedFileId] = useState('');

    // Text prompt
    const [textPrompt, setTextPrompt] = useState('');

    // Configuration
    const [totalSlides, setTotalSlides] = useState(10);
    const [selectedTheme, setSelectedTheme] = useState('professional_blue');
    const [themes, setThemes] = useState([]);

    // Stage 1 results
    const [generatedPresentation, setGeneratedPresentation] = useState(null);
    const [slides, setSlides] = useState([]);
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

    // Stage 2 configuration
    const [imageStyle, setImageStyle] = useState('professional'); // 'professional' | 'creative'
    const [slidesForImages, setSlidesForImages] = useState([]);

    // Progress and results
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [error, setError] = useState('');
    const [currentProgressId, setCurrentProgressId] = useState('');

    // Gallery state
    const [presentations, setPresentations] = useState([]);
    const [isLoadingGallery, setIsLoadingGallery] = useState(false);
    const [selectedPresentation, setSelectedPresentation] = useState(null);

    // Fetch themes, gallery on mount
    useEffect(() => {
        fetchThemes();
        fetchGallery();
    }, []);

    // Fetch vault files when needed
    useEffect(() => {
        if (sourceType === 'vault') {
            fetchVaultFiles();
        }
    }, [sourceType]);

    // Poll progress during generation
    useEffect(() => {
        let interval;
        if (isGenerating && currentProgressId) {
            interval = setInterval(async () => {
                try {
                    const response = await axiosInstance.get(`/ai-presentation-builder/progress/${currentProgressId}`);
                    const data = response.data;

                    setProgress(data.percentage || 0);

                    if (data.status === 'completed') {
                        setIsGenerating(false);
                        setProgress(100);

                        if (stage === 1) {
                            // Stage 1 completed - show review tab
                            setProgressMessage('Presentation content generated! Review your slides and select images.');
                            const presentationId = data.result?.presentation_id;

                            // Fetch the presentation details
                            if (presentationId) {
                                const presResponse = await axiosInstance.get(`/ai-presentation-builder/presentations/${presentationId}`);
                                setGeneratedPresentation(presResponse.data);
                                setSlides(presResponse.data.slides_data || []);
                                setActiveTab('review');
                            }
                        } else {
                            // Stage 2 completed - show success and refresh gallery
                            setProgressMessage('Presentation finalized! You can now download your PowerPoint.');
                            await fetchGallery();
                            setActiveTab('gallery');
                        }
                    } else if (data.status === 'failed') {
                        setIsGenerating(false);
                        setError(data.error_message || 'Generation failed');
                        setProgressMessage('');
                    } else {
                        setProgressMessage(stage === 1 ? 'Generating slide content...' : 'Creating images and PowerPoint...');
                    }
                } catch (err) {
                    console.error('Error polling progress:', err);
                }
            }, 2000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isGenerating, currentProgressId, stage]);

    const fetchThemes = async () => {
        try {
            const response = await axiosInstance.get('/ai-presentation-builder/themes');
            setThemes(response.data.themes || []);
        } catch (err) {
            console.error('Error fetching themes:', err);
        }
    };

    const fetchGallery = async () => {
        setIsLoadingGallery(true);
        try {
            const response = await axiosInstance.get('/ai-presentation-builder/gallery');
            setPresentations(response.data.presentations || []);
        } catch (err) {
            console.error('Error fetching gallery:', err);
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
            setError('');
        } catch (err) {
            console.error('Upload error:', err);
            setError('Failed to upload file');
        }
    };

    const handleGenerateContent = async () => {
        // Stage 1: Generate slide content
        setError('');

        let file_id = '';
        let text_prompt = '';

        if (sourceType === 'vault') {
            if (!selectedFileId) {
                setError('Please select a file from vault');
                return;
            }
            file_id = selectedFileId;
        } else if (sourceType === 'upload') {
            if (!uploadedFileId) {
                setError('Please upload a file');
                return;
            }
            file_id = uploadedFileId;
        } else if (sourceType === 'text') {
            if (textPrompt.trim().length < 20) {
                setError('Please enter at least 20 characters for the topic');
                return;
            }
            text_prompt = textPrompt.trim();
        }

        setIsGenerating(true);
        setProgress(0);
        setProgressMessage('Starting content generation...');
        setStage(1);

        try {
            const response = await axiosInstance.post('/ai-presentation-builder/generate-content', {
                source_type: sourceType,
                file_id: file_id || undefined,
                text_prompt: text_prompt,
                total_slides: totalSlides,
                theme: selectedTheme
            });

            setCurrentProgressId(response.data.progress_id);
        } catch (err) {
            console.error('Error starting generation:', err);
            setError(err.response?.data?.error || 'Failed to start generation');
            setIsGenerating(false);
            setProgressMessage('');
        }
    };

    const handleFinalize = async () => {
        // Stage 2: Generate images and create PPTX
        if (!generatedPresentation) {
            setError('No presentation to finalize');
            return;
        }

        setError('');
        setIsGenerating(true);
        setProgress(0);
        setProgressMessage('Generating images and creating PowerPoint...');
        setStage(2);

        try {
            const response = await axiosInstance.post('/ai-presentation-builder/finalize', {
                presentation_id: generatedPresentation.id,
                image_style: imageStyle,
                slides_for_images: slidesForImages
            });

            setCurrentProgressId(response.data.progress_id);
        } catch (err) {
            console.error('Error starting finalization:', err);
            setError(err.response?.data?.error || 'Failed to start finalization');
            setIsGenerating(false);
            setProgressMessage('');
        }
    };

    const toggleSlideImage = (slideNumber) => {
        setSlidesForImages(prev => {
            if (prev.includes(slideNumber)) {
                return prev.filter(n => n !== slideNumber);
            } else {
                return [...prev, slideNumber];
            }
        });
    };

    const handleDownload = async (presentationId) => {
        try {
            const response = await axiosInstance.get(
                `/ai-presentation-builder/presentations/${presentationId}/download`,
                { responseType: 'blob' }
            );

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            // Extract filename from Content-Disposition header or use default
            const contentDisposition = response.headers['content-disposition'];
            let filename = 'presentation.pptx';
            if (contentDisposition) {
                // Match both quoted and unquoted filenames
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
            console.error('Error downloading presentation:', err);
            setError('Failed to download presentation');
        }
    };

    const handleDelete = async (presentationId) => {
        if (!window.confirm('Are you sure you want to delete this presentation?')) {
            return;
        }

        try {
            await axiosInstance.delete(`/ai-presentation-builder/presentations/${presentationId}`);
            await fetchGallery();
            if (selectedPresentation?.id === presentationId) {
                setSelectedPresentation(null);
            }
        } catch (err) {
            console.error('Error deleting presentation:', err);
            setError('Failed to delete presentation');
        }
    };

    const viewPresentation = async (presentationId) => {
        try {
            const response = await axiosInstance.get(`/ai-presentation-builder/presentations/${presentationId}`);
            setSelectedPresentation(response.data);
            setActiveTab('view');
        } catch (err) {
            console.error('Error fetching presentation:', err);
            setError('Failed to load presentation');
        }
    };

    const renderCreateTab = () => (
        <div className="presentation-create-tab">
            <h2>Create New Presentation</h2>

            {/* Source Type Selection */}
            <div className="source-selector">
                <button
                    className={`source-btn ${sourceType === 'vault' ? 'active' : ''}`}
                    onClick={() => setSourceType('vault')}
                >
                    <FileText size={20} />
                    <span>Knowledge Vault</span>
                </button>
                <button
                    className={`source-btn ${sourceType === 'upload' ? 'active' : ''}`}
                    onClick={() => setSourceType('upload')}
                >
                    <Upload size={20} />
                    <span>Upload Document</span>
                </button>
                <button
                    className={`source-btn ${sourceType === 'text' ? 'active' : ''}`}
                    onClick={() => setSourceType('text')}
                >
                    <Sparkles size={20} />
                    <span>Enter Topic</span>
                </button>
            </div>

            {/* Source Input */}
            <div className="source-input">
                {sourceType === 'vault' && (
                    <div className="vault-section">
                        <label>Select File from Knowledge Vault:</label>
                        <select
                            value={selectedFileId}
                            onChange={(e) => setSelectedFileId(e.target.value)}
                            className="vault-select"
                        >
                            <option value="">-- Select a file --</option>
                            {vaultFiles.map(file => (
                                <option key={file.id} value={file.id}>
                                    {file.name}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {sourceType === 'upload' && (
                    <div className="upload-section">
                        <label>Upload Document:</label>
                        <input
                            type="file"
                            onChange={handleFileUpload}
                            accept=".pdf,.txt,.doc,.docx"
                            className="file-input"
                        />
                        {uploadedFile && (
                            <p className="uploaded-file">Uploaded: {uploadedFile.name}</p>
                        )}
                    </div>
                )}

                {sourceType === 'text' && (
                    <div className="text-section">
                        <label>Enter Presentation Topic:</label>
                        <textarea
                            value={textPrompt}
                            onChange={(e) => setTextPrompt(e.target.value)}
                            placeholder="Enter your presentation topic or outline (at least 20 characters)..."
                            rows={6}
                            className="text-input"
                        />
                        <p className="char-count">{textPrompt.length} characters</p>
                    </div>
                )}
            </div>

            {/* Configuration */}
            <div className="config-section">
                <div className="config-row">
                    <label>Number of Slides (5-20):</label>
                    <input
                        type="number"
                        min="5"
                        max="20"
                        value={totalSlides}
                        onChange={(e) => setTotalSlides(parseInt(e.target.value) || 10)}
                        className="slides-input"
                    />
                </div>

                <div className="config-row">
                    <label>Presentation Theme:</label>
                    <select
                        value={selectedTheme}
                        onChange={(e) => setSelectedTheme(e.target.value)}
                        className="theme-select"
                    >
                        {themes.map(theme => (
                            <option key={theme.id} value={theme.id}>
                                {theme.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Generate Button */}
            <button
                className="generate-btn"
                onClick={handleGenerateContent}
                disabled={isGenerating}
            >
                <Sparkles size={20} />
                {isGenerating ? 'Generating...' : 'Generate Presentation'}
            </button>

            {/* Progress */}
            {isGenerating && (
                <div className="progress-section">
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                    </div>
                    <p className="progress-message">{progressMessage}</p>
                </div>
            )}

            {/* Error */}
            {error && <div className="error-message">{error}</div>}
        </div>
    );

    const renderReviewTab = () => {
        if (!generatedPresentation || !slides.length) {
            return (
                <div className="review-empty">
                    <p>No presentation to review. Generate content first!</p>
                    <button onClick={() => setActiveTab('create')}>Create Presentation</button>
                </div>
            );
        }

        const currentSlide = slides[currentSlideIndex];

        return (
            <div className="presentation-review-tab">
                <h2>Review & Select Images</h2>
                <p className="review-instructions">
                    Review your slides and select which ones should have AI-generated images.
                </p>

                {/* Slide Navigation */}
                <div className="slide-navigation">
                    <button
                        onClick={() => setCurrentSlideIndex(Math.max(0, currentSlideIndex - 1))}
                        disabled={currentSlideIndex === 0}
                        className="nav-btn"
                    >
                        <ChevronLeft size={20} />
                    </button>

                    <span className="slide-counter">
                        Slide {currentSlideIndex + 1} of {slides.length}
                    </span>

                    <button
                        onClick={() => setCurrentSlideIndex(Math.min(slides.length - 1, currentSlideIndex + 1))}
                        disabled={currentSlideIndex === slides.length - 1}
                        className="nav-btn"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>

                {/* Slide Card */}
                <div className="slide-card">
                    <div className="slide-header">
                        <h3>{currentSlide.title}</h3>
                        <button
                            className={`image-toggle-btn ${slidesForImages.includes(currentSlide.slide_number) ? 'selected' : ''}`}
                            onClick={() => toggleSlideImage(currentSlide.slide_number)}
                        >
                            {slidesForImages.includes(currentSlide.slide_number) ? (
                                <>
                                    <CheckSquare size={18} />
                                    <span>Image Selected</span>
                                </>
                            ) : (
                                <>
                                    <Square size={18} />
                                    <span>Add Image</span>
                                </>
                            )}
                        </button>
                    </div>

                    {currentSlide.subtitle && (
                        <p className="slide-subtitle">{currentSlide.subtitle}</p>
                    )}

                    <div className="slide-content">
                        {currentSlide.content_type === 'bullets' && Array.isArray(currentSlide.content) && (
                            <ul className="bullet-list">
                                {currentSlide.content.map((bullet, idx) => (
                                    <li key={idx}>{bullet}</li>
                                ))}
                            </ul>
                        )}

                        {currentSlide.content_type === 'paragraph' && (
                            <p className="paragraph-content">{currentSlide.content}</p>
                        )}
                    </div>

                    {currentSlide.suggested_image && (
                        <p className="suggested-image">
                            <ImageIcon size={16} /> Suggested image: {currentSlide.suggested_image}
                        </p>
                    )}
                </div>

                {/* Image Style Selection */}
                <div className="image-style-section">
                    <label>Image Style:</label>
                    <div className="style-buttons">
                        <button
                            className={`style-btn ${imageStyle === 'professional' ? 'active' : ''}`}
                            onClick={() => setImageStyle('professional')}
                        >
                            Professional
                        </button>
                        <button
                            className={`style-btn ${imageStyle === 'creative' ? 'active' : ''}`}
                            onClick={() => setImageStyle('creative')}
                        >
                            Creative
                        </button>
                    </div>
                </div>

                {/* Finalize Button */}
                <div className="finalize-section">
                    <p className="images-selected">
                        {slidesForImages.length} slide{slidesForImages.length !== 1 ? 's' : ''} selected for images
                    </p>
                    <button
                        className="finalize-btn"
                        onClick={handleFinalize}
                        disabled={isGenerating}
                    >
                        <Palette size={20} />
                        {isGenerating ? 'Creating...' : 'Create PowerPoint'}
                    </button>
                </div>

                {/* Progress */}
                {isGenerating && (
                    <div className="progress-section">
                        <div className="progress-bar">
                            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                        </div>
                        <p className="progress-message">{progressMessage}</p>
                    </div>
                )}

                {/* Error */}
                {error && <div className="error-message">{error}</div>}
            </div>
        );
    };

    const renderGalleryTab = () => (
        <div className="presentation-gallery-tab">
            <h2>Your Presentations</h2>

            {isLoadingGallery ? (
                <p className="loading">Loading presentations...</p>
            ) : presentations.length === 0 ? (
                <div className="empty-gallery">
                    <Presentation size={64} />
                    <p>No presentations yet</p>
                    <button onClick={() => setActiveTab('create')}>Create Your First Presentation</button>
                </div>
            ) : (
                <div className="presentations-grid">
                    {presentations.map(pres => (
                        <div key={pres.id} className="presentation-card">
                            <div className="card-thumbnail">
                                {pres.thumbnail_url ? (
                                    <img src={pres.thumbnail_url} alt={pres.title} />
                                ) : (
                                    <div className="placeholder-thumbnail">
                                        <Presentation size={48} />
                                    </div>
                                )}
                            </div>
                            <div className="card-info">
                                <h3>{pres.title}</h3>
                                <p className="card-meta">{pres.total_slides} slides " {pres.theme}</p>
                                {pres.has_pptx && (
                                    <span className="pptx-badge">PPTX Ready</span>
                                )}
                            </div>
                            <div className="card-actions">
                                <button
                                    onClick={() => viewPresentation(pres.id)}
                                    className="action-btn view-btn"
                                >
                                    <Eye size={16} />
                                    View
                                </button>
                                {pres.has_pptx && (
                                    <button
                                        onClick={() => handleDownload(pres.id)}
                                        className="action-btn download-btn"
                                    >
                                        <Download size={16} />
                                        Download
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDelete(pres.id)}
                                    className="action-btn delete-btn"
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
        if (!selectedPresentation) {
            return (
                <div className="view-empty">
                    <p>No presentation selected</p>
                    <button onClick={() => setActiveTab('gallery')}>Back to Gallery</button>
                </div>
            );
        }

        return (
            <div className="presentation-view-tab">
                <div className="view-header">
                    <button onClick={() => setActiveTab('gallery')} className="back-btn">
                        <ChevronLeft size={20} />
                        Back to Gallery
                    </button>
                    <h2>{selectedPresentation.title}</h2>
                    {selectedPresentation.pptx_url && (
                        <button
                            onClick={() => handleDownload(selectedPresentation.id)}
                            className="download-btn"
                        >
                            <Download size={20} />
                            Download PPTX
                        </button>
                    )}
                </div>

                <div className="slides-preview">
                    {selectedPresentation.slides_data && selectedPresentation.slides_data.map((slide, idx) => (
                        <div key={idx} className="preview-slide">
                            <h4>Slide {slide.slide_number}: {slide.title}</h4>
                            {slide.azure_image_url && (
                                <img src={slide.azure_image_url} alt={`Slide ${slide.slide_number}`} className="slide-image" />
                            )}
                            {slide.content_type === 'bullets' && Array.isArray(slide.content) && (
                                <ul>
                                    {slide.content.map((bullet, i) => (
                                        <li key={i}>{bullet}</li>
                                    ))}
                                </ul>
                            )}
                            {slide.content_type === 'paragraph' && (
                                <p>{slide.content}</p>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    return (
        <div className="ai-presentation-builder">
            <div className="presentation-header">
                <h1>
                    <Presentation size={32} />
                    AI Presentation Builder
                </h1>
                <p className="description">Create professional PowerPoint presentations from documents or topics</p>
            </div>

            <div className="tabs">
                <button
                    className={`tab ${activeTab === 'create' ? 'active' : ''}`}
                    onClick={() => setActiveTab('create')}
                >
                    Create
                </button>
                <button
                    className={`tab ${activeTab === 'review' ? 'active' : ''}`}
                    onClick={() => setActiveTab('review')}
                    disabled={!generatedPresentation}
                >
                    Review & Finalize
                </button>
                <button
                    className={`tab ${activeTab === 'gallery' ? 'active' : ''}`}
                    onClick={() => setActiveTab('gallery')}
                >
                    Gallery
                </button>
                {selectedPresentation && (
                    <button
                        className={`tab ${activeTab === 'view' ? 'active' : ''}`}
                        onClick={() => setActiveTab('view')}
                    >
                        View
                    </button>
                )}
            </div>

            <div className="tab-content">
                {activeTab === 'create' && renderCreateTab()}
                {activeTab === 'review' && renderReviewTab()}
                {activeTab === 'gallery' && renderGalleryTab()}
                {activeTab === 'view' && renderViewTab()}
            </div>
        </div>
    );
}

export default AIPresentationBuilder;
