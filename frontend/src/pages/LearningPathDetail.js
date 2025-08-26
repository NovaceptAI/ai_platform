import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axiosInstance from '../utils/axiosInstance';
import FileSelector from '../components/FileSelector';
import { computeProjectCompletion } from '../utils/toolCompletion';
import './LearningPath.css';

const TOOL_ROUTE_MAP = {
  'Summarizer': { path: '/summarizer', synonyms: ['summarizer'] },
  'Quiz Creator': { path: '/quiz_creator', synonyms: ['quiz', 'quiz creator', 'quiz_creator'] },
  'Homework Helper': { path: '/homework_helper', synonyms: ['homework', 'homework helper'] },
  'Study Guide': { path: '/visual_study_guide_maker', synonyms: ['study guide', 'visual study guide', 'study_guide'] },
  'Entity Resolution': { path: '/segmenter', synonyms: ['entity resolution', 'entity', 'segmenter', 'segments'] },
  'Topic Modelling': { path: '/topic_modeller', synonyms: ['topic model', 'topic modelling', 'topic modeller', 'topics'] },
  'Chronology': { path: '/chrono_ai', synonyms: ['chronology'] },
  'Document Analyzer': { path: '/document_analyzer', synonyms: ['document analyzer', 'doc_analysis', 'document analysis', 'doc analysis'] },
  'Report Export': { path: '/ai_presentation_builder', synonyms: ['report', 'presentation', 'export', 'report_export'] },
  'Segments': { path: '/segmenter', synonyms: ['segments', 'segmenter', 'segment'] },
  'Clustering': { path: undefined, synonyms: ['clustering', 'cluster'] },
  'Similarity': { path: undefined, synonyms: ['similarity', 'similar'] },
  'Concept Map': { path: '/tree-view', synonyms: ['concept map', 'mind map', 'tree', 'mind mapping'] },
  'Presentation Builder': { path: '/ai_presentation_builder', synonyms: ['presentation builder', 'presentation', 'ai_presentation_builder'] }
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
  const [running, setRunning] = useState(false);
  const [resultsByTool, setResultsByTool] = useState({});

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

  const userIdHeader = async () => {
    try {
      const me = await axiosInstance.get('/users/me');
      return me?.data?.id;
    } catch {
      return undefined;
    }
  };

  const ensureFileId = async (filename) => {
    // Many start endpoints accept either file_id or filename; prefer filename and let backend resolve.
    return filename;
  };

  const runTool = async (toolLabel) => {
    if (!selectedFile) return alert('Please select or upload a file first.');
    setRunning(true);
    const uid = await userIdHeader();
    const commonBody = { filename: selectedFile, stored_name: selectedFile, user_id: uid, force: false };
    try {
      let startResp, progressResp, resultsResp;
      if (toolLabel === 'Summarizer') {
        startResp = await axiosInstance.post('/summarizer/summarize_file', { filename: selectedFile, fromVault: true });
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/summarizer/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/summarizer/get_summary/${progressResp.data.file_id}`);
      } else if (toolLabel === 'Quiz Creator') {
        startResp = await axiosInstance.post('/quiz_creator/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/quiz_creator/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/quiz_creator/results?filename=${encodeURIComponent(selectedFile)}`);
      } else if (toolLabel === 'Homework Helper') {
        // No long-running progress; return a placeholder guidance result
        resultsResp = { data: { message: 'Use Homework Helper to ask questions about your material.' } };
      } else if (toolLabel === 'Study Guide') {
        const body = { method: 'document', fromVault: true, filename: selectedFile };
        resultsResp = await axiosInstance.post('/study_guide/generate_visual_study_guide', body);
      } else if (toolLabel === 'Entity Resolution' || toolLabel === 'Segments') {
        startResp = await axiosInstance.post('/segmenter/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/segmenter/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/segmenter/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Topic Modelling') {
        startResp = await axiosInstance.post('/modeller/topics/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/modeller/topics/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/modeller/topics/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Chronology') {
        startResp = await axiosInstance.post('/chronology/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/chronology/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/chronology/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Document Analyzer') {
        startResp = await axiosInstance.post('/doc_analysis/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/doc_analysis/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/doc_analysis/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Report Export') {
        startResp = await axiosInstance.post('/report_export/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/report_export/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/report_export/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Clustering') {
        startResp = await axiosInstance.post('/clustering/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/clustering/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/clustering/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Similarity') {
        startResp = await axiosInstance.post('/similarity/start', commonBody);
        const pid = startResp.data.progress_id;
        progressResp = await axiosInstance.get(`/similarity/progress/${pid}`);
        resultsResp = await axiosInstance.get(`/similarity/results?file_id=${encodeURIComponent(progressResp.data.file_id)}`);
      } else if (toolLabel === 'Concept Map') {
        // use TreeView page normally; here we return a placeholder
        resultsResp = { data: { message: 'Open Concept Map to view and edit your map.' } };
      } else if (toolLabel === 'Presentation Builder') {
        // link-out only; placeholder
        resultsResp = { data: { message: 'Open Presentation Builder to create slides.' } };
      }

      // Refresh overview after a run
      try {
        const r = await axiosInstance.get('/tools/overview');
        setOverviewItems(r?.data?.items || overviewItems);
      } catch {}

      if (resultsResp) {
        setResultsByTool(prev => ({ ...prev, [toolLabel]: resultsResp.data }));
      }
    } catch (e) {
      setResultsByTool(prev => ({ ...prev, [toolLabel]: { error: e?.response?.data?.error || 'Failed to run tool' } }));
    } finally {
      setRunning(false);
    }
  };

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
                <button className="lp-button primary" disabled={running} onClick={() => runTool(tool.label)}>Run</button>
                {tool.available ? (
                  <button className="lp-button" onClick={() => navigate(tool.path)}>Open</button>
                ) : (
                  <button className="lp-button" disabled>Coming soon</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-section">
        <h2 className="lp-section-title">Results</h2>
        {!Object.keys(resultsByTool).length && <p className="lp-section-desc">Run a tool to see its results here.</p>}
        {Object.entries(resultsByTool).map(([label, data]) => (
          <div key={label} className="tool-card" style={{ marginBottom: '1rem' }}>
            <div className="tool-card-top">
              <h3 className="tool-card-title">{label}</h3>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', background: '#f8fafc', padding: '0.75rem', borderRadius: 8, maxHeight: 360, overflow: 'auto' }}>
              {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
            </pre>
          </div>
        ))}
      </section>

      <footer className="lp-section" style={{ paddingTop: 0 }}>
        <p className="lp-section-desc">Need a different combo? <Link to="/learning-path">Pick another path</Link> or create a custom flow.</p>
      </footer>
    </div>
  );
}