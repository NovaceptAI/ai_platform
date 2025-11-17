import React, { useState, useEffect } from 'react';
import './AIArtCreatorForKids.css';
import axiosInstance from '../../utils/axiosInstance';
import {
    Sparkles, Palette, Heart, Image as ImageIcon, Eye, Star,
    ChevronLeft, ChevronRight, Download, Trash2, BookOpen,
    Wand2, PlusCircle, Grid, Edit3
} from 'lucide-react';

function AIArtCreatorForKids() {
    // Tab state
    const [activeTab, setActiveTab] = useState('create'); // create, results, gallery, view

    // Service info
    const [styles, setStyles] = useState([]);
    const [palettes, setPalettes] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [magicWords, setMagicWords] = useState({});

    // Create form state
    const [promptText, setPromptText] = useState('');
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [ageGroup, setAgeGroup] = useState('8-10');
    const [artStyle, setArtStyle] = useState('cartoon');
    const [colorPalette, setColorPalette] = useState('rainbow');
    const [numVariations, setNumVariations] = useState(2);
    const [showTemplates, setShowTemplates] = useState(true);
    const [showMagicWords, setShowMagicWords] = useState(false);

    // Generation state
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [taskId, setTaskId] = useState('');
    const [error, setError] = useState('');

    // Results state
    const [generatedArt, setGeneratedArt] = useState(null);
    const [currentVariation, setCurrentVariation] = useState(0);
    const [artTitle, setArtTitle] = useState('My Artwork');
    const [artStory, setArtStory] = useState('');
    const [characterName, setCharacterName] = useState('');
    const [collectionName, setCollectionName] = useState('');

    // Gallery state
    const [gallery, setGallery] = useState([]);
    const [collections, setCollections] = useState([]);
    const [filterFavorites, setFilterFavorites] = useState(false);
    const [filterCollection, setFilterCollection] = useState('');
    const [isLoadingGallery, setIsLoadingGallery] = useState(false);

    // View state
    const [viewedArt, setViewedArt] = useState(null);

    // Fetch service data on mount
    useEffect(() => {
        fetchServiceInfo();
        fetchGallery();
        fetchCollections();
    }, []);

    // Poll progress during generation
    useEffect(() => {
        let interval;
        if (isGenerating && taskId) {
            interval = setInterval(async () => {
                try {
                    const response = await axiosInstance.get(`/ai_art_creator_for_kids/progress/${taskId}`);
                    const data = response.data;

                    setProgress(data.progress || 0);
                    setProgressMessage(data.status || '');

                    if (data.state === 'SUCCESS') {
                        setIsGenerating(false);
                        setProgress(100);
                        setProgressMessage('Your magical artwork is ready!');

                        // Set results
                        setGeneratedArt(data.result);
                        setArtTitle('My Artwork');
                        setArtStory('');
                        setActiveTab('results');

                        // Refresh gallery
                        fetchGallery();
                        fetchCollections();
                    } else if (data.state === 'FAILURE') {
                        setIsGenerating(false);
                        setError(data.error || 'Generation failed');
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
    }, [isGenerating, taskId]);

    const fetchServiceInfo = async () => {
        try {
            // Fetch styles
            const stylesRes = await axiosInstance.get('/ai_art_creator_for_kids/styles');
            setStyles(stylesRes.data.styles || []);

            // Fetch palettes
            const palettesRes = await axiosInstance.get('/ai_art_creator_for_kids/palettes');
            setPalettes(palettesRes.data.palettes || []);

            // Fetch templates
            const templatesRes = await axiosInstance.get('/ai_art_creator_for_kids/templates');
            setTemplates(templatesRes.data.templates || []);

            // Fetch magic words
            const magicRes = await axiosInstance.get('/ai_art_creator_for_kids/magic-words');
            setMagicWords(magicRes.data.magic_words || {});
        } catch (err) {
            console.error('Error fetching service info:', err);
        }
    };

    const fetchGallery = async () => {
        setIsLoadingGallery(true);
        try {
            const params = {};
            if (filterFavorites) params.is_favorite = true;
            if (filterCollection) params.collection_name = filterCollection;

            const response = await axiosInstance.get('/ai_art_creator_for_kids/gallery', { params });
            setGallery(response.data.artworks || []);
        } catch (err) {
            console.error('Error fetching gallery:', err);
        } finally {
            setIsLoadingGallery(false);
        }
    };

    const fetchCollections = async () => {
        try {
            const response = await axiosInstance.get('/ai_art_creator_for_kids/collections');
            setCollections(response.data.collections || []);
        } catch (err) {
            console.error('Error fetching collections:', err);
        }
    };

    const handleTemplateSelect = (template) => {
        setSelectedTemplate(template);
        setPromptText(template.examples[0]);
        setShowTemplates(false);
    };

    const handleMagicWordClick = (word) => {
        setPromptText(prev => prev ? `${prev} ${word}` : word);
    };

    const handleGenerate = async () => {
        setError('');

        if (promptText.trim().length < 5) {
            setError('Please describe what you want to create!');
            return;
        }

        setIsGenerating(true);
        setProgress(0);
        setProgressMessage('Starting to create your art...');

        try {
            const response = await axiosInstance.post('/ai_art_creator_for_kids/generate', {
                prompt_text: promptText,
                age_group: ageGroup,
                art_style: artStyle,
                color_palette: colorPalette,
                num_variations: numVariations
            });

            setTaskId(response.data.task_id);
        } catch (err) {
            console.error('Error starting generation:', err);
            setError(err.response?.data?.error || 'Failed to start generation');
            setIsGenerating(false);
        }
    };

    const handleSaveArt = async () => {
        if (!generatedArt || !generatedArt.art_id) {
            setError('No artwork to save');
            return;
        }

        try {
            await axiosInstance.put(`/ai_art_creator_for_kids/art/${generatedArt.art_id}`, {
                title: artTitle,
                story_text: artStory,
                character_name: characterName,
                collection_name: collectionName
            });

            setError('');
            alert('Artwork saved successfully!');
            fetchGallery();
            fetchCollections();
        } catch (err) {
            console.error('Error saving artwork:', err);
            setError('Failed to save artwork details');
        }
    };

    const handleViewArt = async (artId) => {
        try {
            const response = await axiosInstance.get(`/ai_art_creator_for_kids/art/${artId}`);
            setViewedArt(response.data.artwork);
            setActiveTab('view');
        } catch (err) {
            console.error('Error viewing artwork:', err);
            setError('Failed to load artwork');
        }
    };

    const handleToggleFavorite = async (artId, isFavorite) => {
        try {
            await axiosInstance.put(`/ai_art_creator_for_kids/art/${artId}`, {
                is_favorite: !isFavorite
            });
            fetchGallery();
        } catch (err) {
            console.error('Error toggling favorite:', err);
        }
    };

    const handleDeleteArt = async (artId) => {
        if (!window.confirm('Are you sure you want to delete this artwork?')) {
            return;
        }

        try {
            await axiosInstance.delete(`/ai_art_creator_for_kids/art/${artId}`);
            fetchGallery();
            fetchCollections();
            alert('Artwork deleted successfully!');
        } catch (err) {
            console.error('Error deleting artwork:', err);
            alert('Failed to delete artwork');
        }
    };

    const handleDownloadImage = (imageUrl, title) => {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = `${title.replace(/[^a-z0-9]/gi, '_')}.jpg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // ==================== Render Functions ====================

    const renderCreateTab = () => (
        <div className="art-create-tab">
            <h2>Create Your Magical Artwork!</h2>

            {/* Age Group Selection */}
            <div className="age-group-section">
                <label>How old are you?</label>
                <div className="age-buttons">
                    {['5-7', '8-10', '11-14'].map(age => (
                        <button
                            key={age}
                            className={`age-btn ${ageGroup === age ? 'active' : ''}`}
                            onClick={() => setAgeGroup(age)}
                        >
                            {age} years
                        </button>
                    ))}
                </div>
            </div>

            {/* Templates */}
            {showTemplates && (
                <div className="templates-section">
                    <div className="section-header">
                        <h3>Choose a Fun Idea!</h3>
                        <button onClick={() => setShowTemplates(false)} className="hide-btn">
                            Skip
                        </button>
                    </div>
                    <div className="templates-grid">
                        {templates.map(template => (
                            <div
                                key={template.id}
                                className="template-card"
                                onClick={() => handleTemplateSelect(template)}
                            >
                                <div className="template-icon">{template.icon}</div>
                                <h4>{template.title}</h4>
                                <p className="template-example">{template.examples[0]}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Prompt Input */}
            <div className="prompt-section">
                <label>Describe What You Want to Create</label>
                <textarea
                    className="prompt-input"
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    placeholder="A magical unicorn flying through a rainbow forest..."
                    rows={4}
                    maxLength={500}
                />
                <div className="char-count">{promptText.length}/500</div>

                {/* Magic Words */}
                <button
                    className="magic-words-toggle"
                    onClick={() => setShowMagicWords(!showMagicWords)}
                >
                    <Wand2 size={16} />
                    {showMagicWords ? 'Hide Magic Words' : 'Show Magic Words'}
                </button>

                {showMagicWords && (
                    <div className="magic-words-section">
                        {Object.entries(magicWords).map(([category, words]) => (
                            <div key={category} className="magic-category">
                                <div className="category-name">{category.replace('_', ' ')}</div>
                                <div className="magic-words">
                                    {words.slice(0, 8).map((word, idx) => (
                                        <button
                                            key={idx}
                                            className="magic-word"
                                            onClick={() => handleMagicWordClick(word)}
                                        >
                                            {word}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Art Style Selection */}
            <div className="style-section">
                <label>Choose Your Art Style</label>
                <div className="styles-grid">
                    {styles.map(style => (
                        <button
                            key={style.id}
                            className={`style-card ${artStyle === style.id ? 'active' : ''}`}
                            onClick={() => setArtStyle(style.id)}
                        >
                            <span className="style-icon">{style.icon}</span>
                            <div className="style-name">{style.name}</div>
                            <div className="style-desc">{style.description}</div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Color Palette Selection */}
            <div className="palette-section">
                <label>Choose Your Colors</label>
                <div className="palettes-grid">
                    {palettes.map(palette => (
                        <button
                            key={palette.id}
                            className={`palette-card ${colorPalette === palette.id ? 'active' : ''}`}
                            onClick={() => setColorPalette(palette.id)}
                        >
                            <div className="palette-colors">
                                {palette.colors.slice(0, 5).map((color, idx) => (
                                    <div
                                        key={idx}
                                        className="color-swatch"
                                        style={{ backgroundColor: color }}
                                    />
                                ))}
                            </div>
                            <div className="palette-name">{palette.name}</div>
                            <div className="palette-desc">{palette.description}</div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Number of Variations */}
            <div className="variations-section">
                <label>How Many Versions? (1-4)</label>
                <div className="variations-buttons">
                    {[1, 2, 3, 4].map(num => (
                        <button
                            key={num}
                            className={`variation-btn ${numVariations === num ? 'active' : ''}`}
                            onClick={() => setNumVariations(num)}
                        >
                            {num}
                        </button>
                    ))}
                </div>
            </div>

            {/* Generate Button */}
            <button
                className="generate-btn"
                onClick={handleGenerate}
                disabled={isGenerating || promptText.trim().length < 5}
            >
                <Sparkles size={20} />
                Create My Magical Art!
            </button>

            {/* Progress */}
            {isGenerating && (
                <div className="progress-section">
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${progress}%` }} />
                    </div>
                    <div className="progress-message">{progressMessage}</div>
                </div>
            )}

            {/* Error */}
            {error && <div className="error-message">{error}</div>}
        </div>
    );

    const renderResultsTab = () => {
        if (!generatedArt) {
            return (
                <div className="results-empty">
                    <Sparkles size={64} />
                    <h3>No Artwork Yet!</h3>
                    <p>Create your first magical artwork to see it here.</p>
                    <button onClick={() => setActiveTab('create')}>Create Art</button>
                </div>
            );
        }

        const images = generatedArt.images || [];
        const currentImage = images[currentVariation];

        return (
            <div className="art-results-tab">
                <h2>Your Magical Artwork! ✨</h2>

                {/* Image Display */}
                <div className="result-display">
                    {images.length > 1 && (
                        <button
                            className="nav-btn left"
                            onClick={() => setCurrentVariation(Math.max(0, currentVariation - 1))}
                            disabled={currentVariation === 0}
                        >
                            <ChevronLeft size={24} />
                        </button>
                    )}

                    <div className="result-image-container">
                        <img
                            src={currentImage?.image_url}
                            alt={artTitle}
                            className="result-image"
                        />
                        <div className="variation-indicator">
                            Version {currentVariation + 1} of {images.length}
                        </div>
                    </div>

                    {images.length > 1 && (
                        <button
                            className="nav-btn right"
                            onClick={() => setCurrentVariation(Math.min(images.length - 1, currentVariation + 1))}
                            disabled={currentVariation === images.length - 1}
                        >
                            <ChevronRight size={24} />
                        </button>
                    )}
                </div>

                {/* Thumbnails */}
                {images.length > 1 && (
                    <div className="thumbnails">
                        {images.map((img, idx) => (
                            <img
                                key={idx}
                                src={img.thumbnail_url || img.image_url}
                                alt={`Version ${idx + 1}`}
                                className={`thumbnail ${currentVariation === idx ? 'active' : ''}`}
                                onClick={() => setCurrentVariation(idx)}
                            />
                        ))}
                    </div>
                )}

                {/* Details Form */}
                <div className="details-section">
                    <h3>Tell Us About Your Art!</h3>

                    <div className="form-row">
                        <label>Title</label>
                        <input
                            type="text"
                            value={artTitle}
                            onChange={(e) => setArtTitle(e.target.value)}
                            placeholder="My Magical Artwork"
                            maxLength={100}
                        />
                    </div>

                    <div className="form-row">
                        <label>Write a Story (Optional)</label>
                        <textarea
                            value={artStory}
                            onChange={(e) => setArtStory(e.target.value)}
                            placeholder="Once upon a time..."
                            rows={4}
                            maxLength={1000}
                        />
                    </div>

                    <div className="form-row">
                        <label>Character Name (Optional)</label>
                        <input
                            type="text"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            placeholder="Sparkle the Unicorn"
                            maxLength={50}
                        />
                    </div>

                    <div className="form-row">
                        <label>Collection (Optional)</label>
                        <input
                            type="text"
                            value={collectionName}
                            onChange={(e) => setCollectionName(e.target.value)}
                            placeholder="My Magical Animals"
                            maxLength={50}
                            list="collections-list"
                        />
                        <datalist id="collections-list">
                            {collections.map((col, idx) => (
                                <option key={idx} value={col} />
                            ))}
                        </datalist>
                    </div>

                    <div className="action-buttons">
                        <button className="save-btn" onClick={handleSaveArt}>
                            <Star size={16} />
                            Save Details
                        </button>
                        <button
                            className="download-btn"
                            onClick={() => handleDownloadImage(currentImage?.image_url, artTitle)}
                        >
                            <Download size={16} />
                            Download
                        </button>
                        <button className="create-more-btn" onClick={() => setActiveTab('create')}>
                            <PlusCircle size={16} />
                            Create More
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    const renderGalleryTab = () => (
        <div className="art-gallery-tab">
            <div className="gallery-header">
                <h2>My Art Gallery</h2>

                <div className="gallery-filters">
                    <button
                        className={`filter-btn ${filterFavorites ? 'active' : ''}`}
                        onClick={() => {
                            setFilterFavorites(!filterFavorites);
                            setTimeout(fetchGallery, 100);
                        }}
                    >
                        <Heart size={16} fill={filterFavorites ? 'currentColor' : 'none'} />
                        Favorites
                    </button>

                    <select
                        value={filterCollection}
                        onChange={(e) => {
                            setFilterCollection(e.target.value);
                            setTimeout(fetchGallery, 100);
                        }}
                        className="collection-filter"
                    >
                        <option value="">All Collections</option>
                        {collections.map((col, idx) => (
                            <option key={idx} value={col}>{col}</option>
                        ))}
                    </select>
                </div>
            </div>

            {isLoadingGallery ? (
                <div className="loading">Loading your artwork...</div>
            ) : gallery.length === 0 ? (
                <div className="empty-gallery">
                    <Palette size={64} />
                    <h3>No Artwork Yet!</h3>
                    <p>Start creating magical art to build your gallery.</p>
                    <button onClick={() => setActiveTab('create')}>
                        <Sparkles size={16} />
                        Create Art
                    </button>
                </div>
            ) : (
                <div className="gallery-grid">
                    {gallery.map(art => (
                        <div key={art.id} className="art-card">
                            <div
                                className="art-thumbnail"
                                onClick={() => handleViewArt(art.id)}
                            >
                                {art.thumbnail_url ? (
                                    <img src={art.thumbnail_url} alt={art.title} />
                                ) : (
                                    <div className="placeholder-thumb">
                                        <ImageIcon size={48} />
                                    </div>
                                )}
                            </div>

                            <div className="art-info">
                                <h3>{art.title}</h3>
                                <div className="art-meta">
                                    <span>{art.num_variations} version{art.num_variations > 1 ? 's' : ''}</span>
                                    <span>{art.art_style}</span>
                                </div>
                                {art.collection_name && (
                                    <div className="collection-badge">{art.collection_name}</div>
                                )}
                            </div>

                            <div className="art-actions">
                                <button
                                    className={`favorite-btn ${art.is_favorite ? 'active' : ''}`}
                                    onClick={() => handleToggleFavorite(art.id, art.is_favorite)}
                                >
                                    <Heart size={16} fill={art.is_favorite ? 'currentColor' : 'none'} />
                                </button>
                                <button onClick={() => handleViewArt(art.id)}>
                                    <Eye size={16} />
                                </button>
                                <button onClick={() => handleDeleteArt(art.id)}>
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
        if (!viewedArt) {
            return (
                <div className="view-empty">
                    <p>No artwork selected</p>
                    <button onClick={() => setActiveTab('gallery')}>Back to Gallery</button>
                </div>
            );
        }

        const images = viewedArt.images || [];

        return (
            <div className="art-view-tab">
                <div className="view-header">
                    <button className="back-btn" onClick={() => setActiveTab('gallery')}>
                        <ChevronLeft size={16} />
                        Back to Gallery
                    </button>
                    <h2>{viewedArt.title}</h2>
                </div>

                <div className="view-images">
                    {images.map((img, idx) => (
                        <div key={idx} className="view-image-container">
                            <h4>Version {img.variation_num}</h4>
                            <img src={img.image_url} alt={`Version ${img.variation_num}`} className="view-image" />
                            <button
                                className="download-img-btn"
                                onClick={() => handleDownloadImage(img.image_url, `${viewedArt.title}_v${img.variation_num}`)}
                            >
                                <Download size={16} />
                                Download
                            </button>
                        </div>
                    ))}
                </div>

                {viewedArt.story_text && (
                    <div className="story-section">
                        <h3><BookOpen size={20} /> My Story</h3>
                        <p>{viewedArt.story_text}</p>
                    </div>
                )}

                <div className="art-details">
                    <div className="detail-item">
                        <strong>Style:</strong> {viewedArt.art_style}
                    </div>
                    <div className="detail-item">
                        <strong>Colors:</strong> {viewedArt.color_palette}
                    </div>
                    <div className="detail-item">
                        <strong>Age Group:</strong> {viewedArt.age_group}
                    </div>
                    {viewedArt.character_name && (
                        <div className="detail-item">
                            <strong>Character:</strong> {viewedArt.character_name}
                        </div>
                    )}
                    {viewedArt.collection_name && (
                        <div className="detail-item">
                            <strong>Collection:</strong> {viewedArt.collection_name}
                        </div>
                    )}
                </div>
            </div>
        );
    };

    // ==================== Main Render ====================

    return (
        <div className="ai_art_creator_for_kids">
            <div className="art-header">
                <h1>
                    <Palette size={32} />
                    AI Art Creator for Kids
                </h1>
                <p className="description">Create magical artwork with AI!</p>
            </div>

            {/* Tabs */}
            <div className="tabs">
                <button
                    className={`tab ${activeTab === 'create' ? 'active' : ''}`}
                    onClick={() => setActiveTab('create')}
                >
                    <Sparkles size={16} />
                    Create
                </button>
                <button
                    className={`tab ${activeTab === 'results' ? 'active' : ''}`}
                    onClick={() => setActiveTab('results')}
                    disabled={!generatedArt}
                >
                    <Star size={16} />
                    Results
                </button>
                <button
                    className={`tab ${activeTab === 'gallery' ? 'active' : ''}`}
                    onClick={() => {
                        setActiveTab('gallery');
                        fetchGallery();
                    }}
                >
                    <Grid size={16} />
                    Gallery
                </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'create' && renderCreateTab()}
            {activeTab === 'results' && renderResultsTab()}
            {activeTab === 'gallery' && renderGalleryTab()}
            {activeTab === 'view' && renderViewTab()}
        </div>
    );
}

export default AIArtCreatorForKids;
