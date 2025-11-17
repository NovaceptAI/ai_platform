import React, { useState, useEffect, useCallback } from 'react';
import './HistoricalTimelineBuilder.css';
import axiosInstance from '../../utils/axiosInstance';
import {
    Clock, Calendar, BookOpen, FileText, Upload, Sparkles,
    Eye, Star, Trash2, Download, ChevronLeft, ChevronRight,
    Search, Filter, Plus, Edit3, History, Globe, Lightbulb
} from 'lucide-react';

function HistoricalTimelineBuilder() {
    // Tab state
    const [activeTab, setActiveTab] = useState('create'); // create, timelines, view

    // Service info
    const [categories, setCategories] = useState([]);

    // Create form state
    const [inputType, setInputType] = useState('text'); // text, document
    const [inputText, setInputText] = useState('');
    const [documentFile, setDocumentFile] = useState(null);
    const [category, setCategory] = useState('history');
    const [timePeriod, setTimePeriod] = useState('');
    const [enhance, setEnhance] = useState(true);

    // Generation state
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [taskId, setTaskId] = useState('');
    const [error, setError] = useState('');
    const [timelineId, setTimelineId] = useState('');

    // Timelines list state
    const [timelines, setTimelines] = useState([]);
    const [isLoadingTimelines, setIsLoadingTimelines] = useState(false);
    const [filterCategory, setFilterCategory] = useState('');

    // View state
    const [viewedTimeline, setViewedTimeline] = useState(null);
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [viewMode, setViewMode] = useState('linear'); // linear, grid

    // Fetch categories on mount
    const fetchCategories = useCallback(async () => {
        try {
            const response = await axiosInstance.get('/timeline_builder/categories');
            setCategories(response.data.categories || []);
        } catch (err) {
            console.error('Error fetching categories:', err);
        }
    }, []);

    const fetchTimelines = useCallback(async () => {
        setIsLoadingTimelines(true);
        try {
            const params = {};
            if (filterCategory) params.category = filterCategory;

            const response = await axiosInstance.get('/timeline_builder/timelines', { params });
            setTimelines(response.data.timelines || []);
        } catch (err) {
            console.error('Error fetching timelines:', err);
        } finally {
            setIsLoadingTimelines(false);
        }
    }, [filterCategory]);

    useEffect(() => {
        fetchCategories();
        fetchTimelines();
    }, [fetchCategories, fetchTimelines]);

    // Poll for timeline completion
    useEffect(() => {
        let interval;
        if (isGenerating && timelineId) {
            interval = setInterval(async () => {
                try {
                    const response = await axiosInstance.get(`/timeline_builder/timeline/${timelineId}`);
                    const data = response.data;

                    if (data.timeline && data.timeline.title !== 'Processing...') {
                        setIsGenerating(false);
                        setProgress(100);
                        setProgressMessage('Timeline created successfully!');
                        setViewedTimeline(data.timeline);
                        setActiveTab('view');
                        fetchTimelines();
                    }
                } catch (err) {
                    console.error('Error polling timeline:', err);
                }
            }, 3000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isGenerating, timelineId]);

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            const allowedTypes = ['application/pdf', 'text/plain',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword'];

            if (!allowedTypes.includes(file.type)) {
                setError('Please upload a PDF, TXT, or DOCX file');
                return;
            }

            if (file.size > 10 * 1024 * 1024) {
                setError('File size must be less than 10MB');
                return;
            }

            setDocumentFile(file);
            setError('');
        }
    };

    const handleCreateTimeline = async () => {
        setError('');

        // Validation
        if (inputType === 'text') {
            if (!inputText || inputText.trim().length < 50) {
                setError('Please enter at least 50 characters of text');
                return;
            }
        } else {
            if (!documentFile) {
                setError('Please select a document to upload');
                return;
            }
        }

        try {
            setIsGenerating(true);
            setProgress(10);
            setProgressMessage('Starting timeline creation...');

            const formData = new FormData();
            formData.append('input_type', inputType);
            formData.append('category', category);
            formData.append('time_period', timePeriod);
            formData.append('enhance', enhance);

            if (inputType === 'text') {
                formData.append('input_text', inputText);
            } else {
                formData.append('document', documentFile);
            }

            const response = await axiosInstance.post('/timeline_builder/create', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            if (response.data.success) {
                setTimelineId(response.data.timeline_id);
                setProgress(30);
                setProgressMessage('Analyzing content and extracting events...');
            } else {
                throw new Error(response.data.error || 'Failed to create timeline');
            }
        } catch (err) {
            console.error('Error creating timeline:', err);
            setError(err.response?.data?.error || err.message || 'Failed to create timeline');
            setIsGenerating(false);
            setProgress(0);
            setProgressMessage('');
        }
    };

    const handleViewTimeline = async (timeline) => {
        try {
            const response = await axiosInstance.get(`/timeline_builder/timeline/${timeline.id}`);
            setViewedTimeline(response.data.timeline);
            setSelectedEvent(null);
            setActiveTab('view');
        } catch (err) {
            console.error('Error loading timeline:', err);
            setError('Failed to load timeline');
        }
    };

    const handleDeleteTimeline = async (timelineId) => {
        if (!window.confirm('Are you sure you want to delete this timeline?')) {
            return;
        }

        try {
            await axiosInstance.delete(`/timeline_builder/timeline/${timelineId}`);
            fetchTimelines();
            if (viewedTimeline?.id === timelineId) {
                setViewedTimeline(null);
                setActiveTab('timelines');
            }
        } catch (err) {
            console.error('Error deleting timeline:', err);
            setError('Failed to delete timeline');
        }
    };

    const handleToggleFavorite = async (timelineId, isFavorite) => {
        try {
            await axiosInstance.put(`/timeline_builder/timeline/${timelineId}`, {
                is_favorite: !isFavorite
            });
            fetchTimelines();
            if (viewedTimeline?.id === timelineId) {
                setViewedTimeline({...viewedTimeline, is_favorite: !isFavorite});
            }
        } catch (err) {
            console.error('Error toggling favorite:', err);
        }
    };

    const handleExportTimeline = async (timelineId) => {
        try {
            const response = await axiosInstance.post(`/timeline_builder/timeline/${timelineId}/export`, {
                format: 'json'
            });

            if (response.data.success) {
                alert('Export started! Check your downloads.');
            }
        } catch (err) {
            console.error('Error exporting timeline:', err);
            setError('Failed to export timeline');
        }
    };

    const handleEnhanceTimeline = async (timelineId) => {
        try {
            const response = await axiosInstance.post(`/timeline_builder/timeline/${timelineId}/enhance`);

            if (response.data.success) {
                alert('Timeline enhancement started! This may take 30-45 seconds.');
                setTimeout(() => {
                    handleViewTimeline({id: timelineId});
                }, 40000);
            }
        } catch (err) {
            console.error('Error enhancing timeline:', err);
            setError('Failed to enhance timeline');
        }
    };

    // Render Create Tab
    const renderCreateTab = () => (
        <div className="create-tab">
            <div className="create-header">
                <div className="header-icon">
                    <Clock size={32} />
                </div>
                <h2>Create Historical Timeline</h2>
                <p>Transform text or documents into interactive chronological timelines</p>
            </div>

            {error && (
                <div className="error-message">
                    <span>{error}</span>
                    <button onClick={() => setError('')}>×</button>
                </div>
            )}

            <div className="input-type-selector">
                <button
                    className={`type-btn ${inputType === 'text' ? 'active' : ''}`}
                    onClick={() => setInputType('text')}
                >
                    <FileText size={20} />
                    <span>Text Input</span>
                </button>
                <button
                    className={`type-btn ${inputType === 'document' ? 'active' : ''}`}
                    onClick={() => setInputType('document')}
                >
                    <Upload size={20} />
                    <span>Document Upload</span>
                </button>
            </div>

            {inputType === 'text' ? (
                <div className="text-input-section">
                    <label>Historical Text or Events</label>
                    <textarea
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        placeholder="Enter historical text, events, project milestones, or any chronological information... (minimum 50 characters)"
                        rows={12}
                    />
                    <div className="char-count">
                        {inputText.length} characters
                    </div>
                </div>
            ) : (
                <div className="document-input-section">
                    <label>Upload Document</label>
                    <div className="file-upload-area">
                        <input
                            type="file"
                            id="document-upload"
                            onChange={handleFileSelect}
                            accept=".pdf,.txt,.docx,.doc"
                            style={{ display: 'none' }}
                        />
                        <label htmlFor="document-upload" className="upload-label">
                            <Upload size={32} />
                            <p>Click to upload or drag and drop</p>
                            <span>PDF, TXT, or DOCX (max 10MB)</span>
                        </label>
                        {documentFile && (
                            <div className="selected-file">
                                <FileText size={20} />
                                <span>{documentFile.name}</span>
                                <button onClick={() => setDocumentFile(null)}>×</button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="options-grid">
                <div className="option-group">
                    <label>Category</label>
                    <select value={category} onChange={(e) => setCategory(e.target.value)}>
                        {categories.map((cat) => (
                            <option key={cat.value} value={cat.value}>
                                {cat.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="option-group">
                    <label>Time Period (Optional)</label>
                    <input
                        type="text"
                        value={timePeriod}
                        onChange={(e) => setTimePeriod(e.target.value)}
                        placeholder="e.g., Ancient Rome, 1940s, 2020-2023"
                    />
                </div>
            </div>

            <div className="enhance-option">
                <label className="checkbox-label">
                    <input
                        type="checkbox"
                        checked={enhance}
                        onChange={(e) => setEnhance(e.target.checked)}
                    />
                    <span>Enhance with AI research (adds historical context and connections)</span>
                </label>
            </div>

            <button
                className="generate-btn"
                onClick={handleCreateTimeline}
                disabled={isGenerating}
            >
                {isGenerating ? (
                    <>
                        <div className="spinner"></div>
                        <span>Creating Timeline...</span>
                    </>
                ) : (
                    <>
                        <Sparkles size={20} />
                        <span>Generate Timeline</span>
                    </>
                )}
            </button>

            {isGenerating && (
                <div className="progress-section">
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                    </div>
                    <p className="progress-message">{progressMessage}</p>
                    <p className="estimated-time">Estimated time: 30-90 seconds</p>
                </div>
            )}
        </div>
    );

    // Render Timelines Tab
    const renderTimelinesTab = () => (
        <div className="timelines-tab">
            <div className="timelines-header">
                <h2>My Timelines</h2>
                <div className="filter-section">
                    <Filter size={18} />
                    <select
                        value={filterCategory}
                        onChange={(e) => {
                            setFilterCategory(e.target.value);
                            fetchTimelines();
                        }}
                    >
                        <option value="">All Categories</option>
                        {categories.map((cat) => (
                            <option key={cat.value} value={cat.value}>
                                {cat.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {isLoadingTimelines ? (
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading timelines...</p>
                </div>
            ) : timelines.length === 0 ? (
                <div className="empty-state">
                    <History size={48} />
                    <p>No timelines yet</p>
                    <button onClick={() => setActiveTab('create')}>
                        <Plus size={18} />
                        Create Your First Timeline
                    </button>
                </div>
            ) : (
                <div className="timelines-grid">
                    {timelines.map((timeline) => (
                        <div key={timeline.id} className="timeline-card">
                            <div className="card-header">
                                <h3>{timeline.title}</h3>
                                <button
                                    className={`favorite-btn ${timeline.is_favorite ? 'active' : ''}`}
                                    onClick={() => handleToggleFavorite(timeline.id, timeline.is_favorite)}
                                >
                                    <Star size={18} fill={timeline.is_favorite ? 'currentColor' : 'none'} />
                                </button>
                            </div>

                            {timeline.description && (
                                <p className="card-description">{timeline.description}</p>
                            )}

                            <div className="card-meta">
                                <span className="category-badge">{timeline.category}</span>
                                <span className="event-count">
                                    <Calendar size={14} />
                                    {timeline.total_events} events
                                </span>
                            </div>

                            {timeline.time_period && (
                                <div className="time-period">
                                    <Clock size={14} />
                                    <span>{timeline.time_period}</span>
                                </div>
                            )}

                            {timeline.key_themes && timeline.key_themes.length > 0 && (
                                <div className="themes">
                                    {timeline.key_themes.slice(0, 3).map((theme, idx) => (
                                        <span key={idx} className="theme-tag">{theme}</span>
                                    ))}
                                </div>
                            )}

                            <div className="card-actions">
                                <button
                                    className="action-btn view"
                                    onClick={() => handleViewTimeline(timeline)}
                                >
                                    <Eye size={16} />
                                    View
                                </button>
                                <button
                                    className="action-btn export"
                                    onClick={() => handleExportTimeline(timeline.id)}
                                >
                                    <Download size={16} />
                                </button>
                                <button
                                    className="action-btn delete"
                                    onClick={() => handleDeleteTimeline(timeline.id)}
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>

                            <div className="card-footer">
                                <span className="created-date">
                                    Created {new Date(timeline.created_at).toLocaleDateString()}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    // Render View Tab
    const renderViewTab = () => {
        if (!viewedTimeline) {
            return (
                <div className="empty-state">
                    <Globe size={48} />
                    <p>No timeline selected</p>
                    <button onClick={() => setActiveTab('timelines')}>
                        Browse Timelines
                    </button>
                </div>
            );
        }

        const sortedEvents = [...(viewedTimeline.events || [])].sort((a, b) => {
            return (a.date || '').localeCompare(b.date || '');
        });

        return (
            <div className="view-tab">
                <div className="view-header">
                    <button className="back-btn" onClick={() => setActiveTab('timelines')}>
                        <ChevronLeft size={20} />
                        Back to Timelines
                    </button>

                    <div className="timeline-title-section">
                        <h2>{viewedTimeline.title}</h2>
                        {viewedTimeline.description && (
                            <p className="timeline-description">{viewedTimeline.description}</p>
                        )}
                    </div>

                    <div className="view-actions">
                        <button
                            className="action-btn"
                            onClick={() => handleToggleFavorite(viewedTimeline.id, viewedTimeline.is_favorite)}
                        >
                            <Star size={18} fill={viewedTimeline.is_favorite ? 'currentColor' : 'none'} />
                        </button>
                        <button
                            className="action-btn"
                            onClick={() => handleEnhanceTimeline(viewedTimeline.id)}
                            title="Enhance with AI research"
                        >
                            <Sparkles size={18} />
                        </button>
                        <button
                            className="action-btn"
                            onClick={() => handleExportTimeline(viewedTimeline.id)}
                        >
                            <Download size={18} />
                        </button>
                    </div>
                </div>

                <div className="timeline-meta-info">
                    {viewedTimeline.time_period && (
                        <div className="meta-item">
                            <Clock size={16} />
                            <span>{viewedTimeline.time_period}</span>
                        </div>
                    )}
                    <div className="meta-item">
                        <Calendar size={16} />
                        <span>{viewedTimeline.total_events} events</span>
                    </div>
                    {viewedTimeline.date_range_start && viewedTimeline.date_range_end && (
                        <div className="meta-item">
                            <span>{viewedTimeline.date_range_start} to {viewedTimeline.date_range_end}</span>
                        </div>
                    )}
                </div>

                {viewedTimeline.key_themes && viewedTimeline.key_themes.length > 0 && (
                    <div className="timeline-themes">
                        <h4>Key Themes:</h4>
                        <div className="themes-list">
                            {viewedTimeline.key_themes.map((theme, idx) => (
                                <span key={idx} className="theme-badge">{theme}</span>
                            ))}
                        </div>
                    </div>
                )}

                {viewedTimeline.key_figures && viewedTimeline.key_figures.length > 0 && (
                    <div className="timeline-figures">
                        <h4>Key Figures:</h4>
                        <div className="figures-list">
                            {viewedTimeline.key_figures.map((figure, idx) => (
                                <span key={idx} className="figure-badge">{figure}</span>
                            ))}
                        </div>
                    </div>
                )}

                <div className="view-mode-selector">
                    <button
                        className={viewMode === 'linear' ? 'active' : ''}
                        onClick={() => setViewMode('linear')}
                    >
                        Linear View
                    </button>
                    <button
                        className={viewMode === 'grid' ? 'active' : ''}
                        onClick={() => setViewMode('grid')}
                    >
                        Grid View
                    </button>
                </div>

                {viewMode === 'linear' ? (
                    <div className="timeline-linear">
                        {sortedEvents.map((event, idx) => (
                            <div
                                key={event.id || idx}
                                className={`timeline-event ${selectedEvent?.id === event.id ? 'selected' : ''}`}
                                onClick={() => setSelectedEvent(selectedEvent?.id === event.id ? null : event)}
                            >
                                <div className="event-marker"></div>
                                <div className="event-content">
                                    <div className="event-date">
                                        <Calendar size={16} />
                                        <span>{event.date}</span>
                                        {event.date_precision && event.date_precision !== 'exact' && (
                                            <span className="precision-badge">{event.date_precision}</span>
                                        )}
                                    </div>
                                    <h3>{event.title}</h3>
                                    {event.category && (
                                        <span className="event-category">{event.category}</span>
                                    )}
                                    <p className="event-description">{event.description}</p>

                                    {selectedEvent?.id === event.id && (
                                        <div className="event-details">
                                            {event.significance && (
                                                <div className="detail-section">
                                                    <h4><Lightbulb size={16} /> Significance</h4>
                                                    <p>{event.significance}</p>
                                                </div>
                                            )}
                                            {event.location && (
                                                <div className="detail-section">
                                                    <h4><Globe size={16} /> Location</h4>
                                                    <p>{event.location}</p>
                                                </div>
                                            )}
                                            {event.people_involved && event.people_involved.length > 0 && (
                                                <div className="detail-section">
                                                    <h4>People Involved</h4>
                                                    <div className="people-list">
                                                        {event.people_involved.map((person, pidx) => (
                                                            <span key={pidx} className="person-badge">{person}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="timeline-grid">
                        {sortedEvents.map((event, idx) => (
                            <div key={event.id || idx} className="event-grid-card">
                                <div className="grid-card-header">
                                    <div className="event-date">
                                        <Calendar size={14} />
                                        <span>{event.date}</span>
                                    </div>
                                    {event.category && (
                                        <span className="event-category">{event.category}</span>
                                    )}
                                </div>
                                <h3>{event.title}</h3>
                                <p className="event-description">{event.description}</p>
                                {event.location && (
                                    <div className="event-location">
                                        <Globe size={12} />
                                        <span>{event.location}</span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="historical-timeline-builder">
            <div className="tabs-container">
                <button
                    className={`tab ${activeTab === 'create' ? 'active' : ''}`}
                    onClick={() => setActiveTab('create')}
                >
                    <Plus size={18} />
                    Create
                </button>
                <button
                    className={`tab ${activeTab === 'timelines' ? 'active' : ''}`}
                    onClick={() => setActiveTab('timelines')}
                >
                    <History size={18} />
                    My Timelines
                </button>
                <button
                    className={`tab ${activeTab === 'view' ? 'active' : ''}`}
                    onClick={() => setActiveTab('view')}
                    style={{ display: viewedTimeline ? 'flex' : 'none' }}
                >
                    <Eye size={18} />
                    View
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'create' && renderCreateTab()}
                {activeTab === 'timelines' && renderTimelinesTab()}
                {activeTab === 'view' && renderViewTab()}
            </div>
        </div>
    );
}

export default HistoricalTimelineBuilder;
