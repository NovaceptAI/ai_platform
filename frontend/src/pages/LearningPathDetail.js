import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axiosInstance from '../utils/axiosInstance';
import FileSelector from '../components/FileSelector';
import { computeProjectCompletion } from '../utils/toolCompletion';
import './LearningPath.css';

const TOOL_ROUTE_MAP = {
  'Summarizer': { path: '/summarizer', synonyms: ['summarizer'] },
  'Quiz Creator': { path: '/quiz_creator', synonyms: ['quiz', 'quiz creator'] },
  'Homework Helper': { path: '/homework_helper', synonyms: ['homework', 'homework helper'] },
  'Study Guide': { path: '/visual_study_guide_maker', synonyms: ['study guide', 'visual study guide'] },
  'Entity Resolution': { path: '/segmenter', synonyms: ['entity resolution', 'entity', 'segmenter'] },
  'Topic Modelling': { path: '/topic_modeller', synonyms: ['topic model', 'topic modelling', 'topic modeller'] },
  'Chronology': { path: '/chrono_ai', synonyms: ['chronology', 'chrono', 'timeline'] },
  'Document Analyzer': { path: '/document_analyzer', synonyms: ['document analyzer', 'analyzer'] },
  'Report Export': { path: '/ai_presentation_builder', synonyms: ['report', 'presentation', 'export'] },
  'Segments': { path: '/segmenter', synonyms: ['segments', 'segmenter', 'segment'] },
  'Clustering': { path: undefined, synonyms: ['clustering', 'cluster'] },
  'Similarity': { path: undefined, synonyms: ['similarity', 'similar'] },
  'Concept Map': { path: '/tree-view', synonyms: ['concept map', 'mind map', 'tree'] },
  'Presentation Builder': { path: '/ai_presentation_builder', synonyms: ['presentation', 'builder'] }
};

const PATHS = {
  LP1: {
    id: 'LP1',
    title: 'Curious Explorer Path',
    icon: '🔍',
    audience: 'Students',
    description: 'Start light: summarize content, test yourself, get help with homework, and craft a study guide.',
    tools: ['Summarizer', 'Quiz Creator', 'Homework Helper', 'Study Guide']
  },
  LP2: {
    id: 'LP2',
    title: 'Academic Researcher Path',
    icon: '📚',
    audience: 'Researchers',
    description: 'Dive deeper: summarize, disambiguate entities, extract topics, build timelines, analyze documents, and export reports.',
    tools: ['Summarizer', 'Entity Resolution', 'Topic Modelling', 'Chronology', 'Document Analyzer', 'Report Export']
  },
  LP3: {
    id: 'LP3',
    title: 'Startup Thinker Path',
    icon: '🚀',
    audience: 'Entrepreneurs',
    description: 'Move fast: segment content, cluster ideas, explore similarity, map concepts, and build presentations.',
    tools: ['Summarizer', 'Segments', 'Clustering', 'Similarity', 'Concept Map', 'Presentation Builder']
  }
};

function guessProgressForLabel(items, label) {
  if (!Array.isArray(items) || items.length === 0) return 0;
  const synonyms = (TOOL_ROUTE_MAP[label]?.synonyms || [label]).map(s => s.toLowerCase());
  for (const it of items) {
    const toolName = String(it.tool || '').toLowerCase();
    if (synonyms.some(s => toolName === s || toolName.includes(s))) {
      return Number(it.percentage || 0);
    }
  }
  return 0;
}

export default function LearningPathDetail() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState('');
  const [overviewItems, setOverviewItems] = useState([]);

  const cfg = PATHS[pathId] || PATHS['LP1'];

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await axiosInstance.get('/tools/overview');
        if (mounted && r?.data?.items) setOverviewItems(r.data.items);
      } catch (_) {
        // no-op
      }
    })();
    return () => { mounted = false; };
  }, [pathId]);

  const toolCards = useMemo(() => {
    return cfg.tools.map((label) => {
      const map = TOOL_ROUTE_MAP[label] || {};
      const progress = guessProgressForLabel(overviewItems, label);
      return {
        label,
        path: map.path,
        available: Boolean(map.path),
        progress
      };
    });
  }, [cfg, overviewItems]);

  const overallProgress = useMemo(() => {
    return computeProjectCompletion(toolCards.map(t => ({ percentage: t.progress })));
  }, [toolCards]);

  const firstOpenablePath = useMemo(() => {
    const incomplete = toolCards.find(t => t.available && t.progress < 100);
    if (incomplete) return incomplete.path;
    const anyAvailable = toolCards.find(t => t.available);
    return anyAvailable ? anyAvailable.path : null;
  }, [toolCards]);

  return (
    <div className="lp-container">
      <div className="lp-breadcrumb">
        <button className="lp-button" onClick={() => navigate('/learning-path')}>← Back</button>
      </div>

      <header className="lp-header" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="lp-icon" aria-hidden>{cfg.icon}</span>
          <div>
            <h1 className="lp-title" style={{ textAlign: 'left', margin: 0 }}>{cfg.title}</h1>
            <p className="lp-subtitle" style={{ textAlign: 'left', margin: 0 }}>{cfg.description}</p>
          </div>
        </div>
        <div className="lp-summary">
          <div className="lp-summary-row">
            <span>Audience</span>
            <strong>{cfg.audience}</strong>
          </div>
          <div className="lp-summary-row">
            <span>Overall Progress</span>
            <strong>{overallProgress}%</strong>
          </div>
          <div>
            <button
              className="lp-button primary"
              disabled={!firstOpenablePath}
              onClick={() => firstOpenablePath && navigate(firstOpenablePath)}
            >
              {overallProgress === 0 ? 'Start Path' : (overallProgress < 100 ? 'Resume Path' : 'Review Tools')}
            </button>
          </div>
        </div>
      </header>

      <section className="lp-section">
        <h2 className="lp-section-title">Upload files</h2>
        <p className="lp-section-desc">Upload or select files from your Knowledge Vault. Tools in this path will use your selected materials.</p>
        <div style={{ maxWidth: 560 }}>
          <FileSelector onFileReady={(fname) => setSelectedFile(fname)} />
          {selectedFile && (
            <p className="lp-selected-file">Selected file: <strong>{selectedFile}</strong></p>
          )}
        </div>
      </section>

      <section className="lp-section">
        <h2 className="lp-section-title">Your tools</h2>
        <div className="lp-tool-grid">
          {toolCards.map(tool => (
            <div key={tool.label} className="tool-card">
              <div className="tool-card-top">
                <h3 className="tool-card-title">{tool.label}</h3>
                <span className="tool-card-pct">{tool.progress}%</span>
              </div>
              <div className="tool-progress">
                <div className="tool-progress-bar" style={{ width: `${tool.progress}%` }} />
              </div>
              <div className="tool-card-actions">
                {tool.available ? (
                  <button className="lp-button primary" onClick={() => navigate(tool.path)}>Open</button>
                ) : (
                  <button className="lp-button" disabled>Coming soon</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="lp-section" style={{ paddingTop: 0 }}>
        <p className="lp-section-desc">Need a different combo? <Link to="/learning-path">Pick another path</Link> or create a custom flow.</p>
      </footer>
    </div>
  );
}