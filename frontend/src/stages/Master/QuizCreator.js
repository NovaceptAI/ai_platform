import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaQuestionCircle, FaRocket, FaSyncAlt, FaDownload, FaCopy, FaPlus, FaTrash, FaShareAlt,
  FaWhatsapp, FaTelegramPlane, FaTwitter, FaFacebookF, FaCheck, FaClock, FaRandom, FaPlay, FaCloudUploadAlt
} from 'react-icons/fa';
import '../../stages/StagesHome.css';
import './QuizCreator.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

const API_BASE = (config && config.API_BASE_URL) || process.env.REACT_APP_API_BASE_URL || '';

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const defaultQuestion = () => ({
  id: uid(),
  question: '',
  options: [{ id: uid(), text: '' }, { id: uid(), text: '' }],
  correctIndex: 0,
  explanation: '',
});

export default function InteractiveQuizCreator() {
  const [tab, setTab] = useState('generate'); // generate | build | play
  const [quizTitle, setQuizTitle] = useState('Untitled Quiz');

  // ---------- Knowledge Vault ----------
  const [source, setSource] = useState('vault'); // 'vault' | 'upload'
  const [vaultFiles, setVaultFiles] = useState([]); // [{id, name, stored_name, ...}]
  const [selectedVaultFile, setSelectedVaultFile] = useState(''); // stored_name
  const [uploading, setUploading] = useState(false);

  // ---------- Generate params ----------
  const [numQ, setNumQ] = useState(10);
  const [difficulty, setDifficulty] = useState('medium'); // easy | medium | hard
  const [force, setForce] = useState(false);

  // ---------- Progress ----------
  const [status, setStatus] = useState('idle'); // idle | starting | running | completed | failed
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const pollerRef = useRef(null);

  // ---------- Quiz Model ----------
  const [questions, setQuestions] = useState([defaultQuestion()]);
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);

  // ---------- Auth headers ----------
  const accessToken = (typeof window !== 'undefined' && localStorage.getItem('access_token')) || '';
  const userId = (typeof window !== 'undefined' && (localStorage.getItem('user_id') || 'admin')) || 'admin';
  const headers = useMemo(() => {
    const h = { 'Content-Type': 'application/json', 'X-User-Id': userId || '' };
    if (accessToken) h['Authorization'] = accessToken.startsWith('Bearer ') ? accessToken : `Bearer ${accessToken}`;
    return h;
  }, [accessToken, userId]);

  // ---------- Load vault files ----------
  useEffect(() => {
    (async () => {
      try {
        const res = await axiosInstance.get('/upload/files');
        setVaultFiles(res.data.files || []);
      } catch {
        // silent
      }
    })();
    return () => { if (pollerRef.current) clearInterval(pollerRef.current); };
  }, []);

  // ---------- Upload to Vault ----------
  async function handleUpload(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      // Adjust endpoint if your uploader differs (e.g., '/upload' vs '/upload/file')
      const res = await axiosInstance.post('/upload/file', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const saved = res.data?.file || res.data; // expect {file:{id, name, stored_name}} or similar
      if (!saved) throw new Error('Upload failed');

      // register in local list & select it
      const vf = {
        id: saved.id,
        name: saved.name || file.name,
        stored_name: saved.stored_name || saved.stored_file_name || saved.storedFileName || saved.filename,
      };
      setVaultFiles((prev) => {
        const exists = prev.some(x => x.stored_name === vf.stored_name);
        return exists ? prev : [vf, ...prev];
      });
      setSelectedVaultFile(vf.stored_name);
      setSource('vault');
    } catch (err) {
      setError(err?.message || 'Upload failed');
    } finally {
      setUploading(false);
      // clear the input value so the same file can be re-selected if needed
      e.target.value = '';
    }
  }

  // ---------- Generate Flow ----------
  async function startGenerate() {
    try {
      setError('');
      if (source === 'vault' && !selectedVaultFile) {
        throw new Error('Pick a file from Knowledge Vault or upload one.');
      }

      // resolve file_id if present in the vault list (fallback to fromVault+filename if not)
      const vf = vaultFiles.find(v => v.stored_name === selectedVaultFile);
      const body = {
        user_id: userId,
        n: numQ,
        difficulty,
        force
      };
      if (vf?.id) {
        body.file_id = vf.id;
      } else {
        body.fromVault = true;
        body.filename = selectedVaultFile;
      }

      setStatus('starting');
      setProgress(0);

      const res = await fetch(`${API_BASE}/quiz_creator/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.error || `Failed to start (${res.status})`);

      const progressId = data.progress_id;
      setStatus('running');
      pollProgress(progressId);
    } catch (err) {
      setStatus('failed');
      setError(err.message || 'Failed to start.');
    }
  }

  function pollProgress(progressId) {
    if (pollerRef.current) clearInterval(pollerRef.current);
    pollerRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API_BASE}/quiz_creator/progress/${progressId}`, { headers });
        const j = await r.json();
        setProgress(Number(j.percentage || 0));
        if (j.status === 'completed') {
          clearInterval(pollerRef.current);
          pollerRef.current = null;
          setStatus('completed');
          await fetchResults();
          setTab('build');
        } else if (j.status === 'failed') {
          clearInterval(pollerRef.current);
          pollerRef.current = null;
          setStatus('failed');
          setError('Job failed. Check server logs.');
        } else {
          setStatus('running');
        }
      } catch (e) {
        clearInterval(pollerRef.current);
        pollerRef.current = null;
        setStatus('failed');
        setError('Progress polling failed.');
      }
    }, 1200);
  }

  async function fetchResults() {
    try {
      // Prefer file_id if we have it; otherwise results can accept filename via backend (optional).
      const vf = vaultFiles.find(v => v.stored_name === selectedVaultFile);
      const queryParams = new URLSearchParams();
      if (vf?.id) queryParams.set('file_id', vf.id);
      else queryParams.set('file_id', selectedVaultFile); // backend may resolve stored_name -> id
      queryParams.set('n', String(numQ));
      queryParams.set('difficulty', difficulty);

      const res = await fetch(`${API_BASE}/quiz_creator/results?${queryParams.toString()}`, { headers });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Failed to fetch results (${res.status})`);

      let qs = [];
      let title = data?.quiz?.title || data?.title || `Quiz`;
      if (Array.isArray(data?.quiz?.questions)) qs = normalizeQuestions(data.quiz.questions);
      else if (Array.isArray(data?.questions)) qs = normalizeQuestions(data.questions);
      else qs = [defaultQuestion()];

      setQuizTitle(title);
      setQuestions(qs);
    } catch (err) {
      setError(err.message || 'Failed to fetch results.');
    }
  }

  // ---------- Editor ----------
  function normalizeQuestions(raw) {
    return (raw || []).slice(0, 50).map((q) => ({
      id: uid(),
      question: String(q.question || '').trim(),
      options: (Array.isArray(q.options) && q.options.length ? q.options : ['', '', '', ''])
        .slice(0, 6).map((t) => ({ id: uid(), text: String(t || '') })),
      correctIndex: typeof q.correctIndex === 'number' ? Math.max(0, Math.min(5, q.correctIndex)) : 0,
      explanation: String(q.explanation || '')
    }));
  }

  function addQuestion() { setQuestions((qs) => [...qs, defaultQuestion()]); }
  function removeQuestion(id) { setQuestions((qs) => (qs.length > 1 ? qs.filter((q) => q.id !== id) : qs)); }
  function changeQuestion(id, patch) { setQuestions((qs) => qs.map((q) => (q.id === id ? { ...q, ...patch } : q))); }
  function addOption(qid) {
    setQuestions((qs) =>
      qs.map((q) => (q.id === qid ? { ...q, options: [...q.options, { id: uid(), text: '' }] } : q))
    );
  }
  function removeOption(qid, oid) {
    setQuestions((qs) =>
      qs.map((q) => {
        if (q.id !== qid) return q;
        const next = q.options.filter((o) => o.id !== oid);
        const ci = Math.min(q.correctIndex, Math.max(0, next.length - 1));
        return { ...q, options: next, correctIndex: ci };
      })
    );
  }
  function changeOption(qid, oid, text) {
    setQuestions((qs) =>
      qs.map((q) => q.id === qid
        ? { ...q, options: q.options.map((o) => (o.id === oid ? { ...o, text } : o)) }
        : q
      )
    );
  }

  // ---------- Play ----------
  const [playIndex, setPlayIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [finished, setFinished] = useState(false);
  function startPlay() { setTab('play'); setPlayIndex(0); setAnswers({}); setFinished(false); }
  function selectAnswer(qid, idx) { setAnswers((a) => ({ ...a, [qid]: idx })); }
  function nextQuestion() { if (playIndex < questions.length - 1) setPlayIndex((i) => i + 1); else setFinished(true); }
  const score = useMemo(() => questions.reduce((s, q) => s + (answers[q.id] === q.correctIndex ? 1 : 0), 0), [answers, questions]);

  // ---------- Share ----------
  const PUBLIC_BASE = (config && config.PUBLIC_BASE_URL) || '';
  async function createShareLink() {
    try {
      const payload = { title: quizTitle, questions };
      const res = await fetch(`${API_BASE}/quiz_creator/share`, { method: 'POST', headers, body: JSON.stringify(payload) });
      const data = await res.json();
      if (res.ok && data.share_url) setShareUrl(data.share_url);
      else setShareUrl('');
    } catch {
      setShareUrl('');
      setError('Share endpoint not available. You can still share via text or download JSON.');
    }
  }
  function getShareText() {
    const link = shareUrl || (PUBLIC_BASE ? `${PUBLIC_BASE}/play_quiz` : '');
    const msg = `🎯 *${quizTitle}* — ${questions.length} questions\n` + (finished ? `I scored ${score}/${questions.length}! ` : '') + (link ? `\nPlay here: ${link}` : '');
    return msg.trim();
  }
  const openShare = (url) => window.open(url, '_blank', 'noopener,noreferrer');
  const shareWhatsApp = () => openShare(`https://wa.me/?text=${encodeURIComponent(getShareText())}`);
  const shareTelegram = () => openShare(`https://t.me/share/url?url=${encodeURIComponent(shareUrl || (PUBLIC_BASE || window.location.origin))}&text=${encodeURIComponent(getShareText())}`);
  const shareTwitter = () => openShare(`https://twitter.com/intent/tweet?text=${encodeURIComponent(getShareText())}&url=${encodeURIComponent(shareUrl || (PUBLIC_BASE || window.location.origin))}`);
  const shareFacebook = () => openShare(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl || (PUBLIC_BASE || window.location.origin))}`);
  const copyJSON = () => { navigator.clipboard.writeText(JSON.stringify({ title: quizTitle, questions }, null, 2)).then(() => { setCopied(true); setTimeout(() => setCopied(false), 900); }); };
  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({ title: quizTitle, questions }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a');
    a.download = `${quizTitle.replace(/\s+/g, '_').toLowerCase() || 'quiz'}.json`; a.href = url; a.click();
    URL.revokeObjectURL(url);
  };

  const canStart = useMemo(() => {
    if (status === 'running' || status === 'starting' || uploading) return false;
    if (source === 'vault') return !!selectedVaultFile;
    return true;
  }, [status, uploading, source, selectedVaultFile]);

  return (
    <div className="iq-wrap">
      <header className="iq-header">
        <h1 className="iq-title"><FaQuestionCircle /> Interactive Quiz Creator</h1>
        <p className="iq-subtitle">Pick a document from your Knowledge Vault (or upload one) and generate sharable quizzes.</p>
      </header>

      <section className="iq-card iq-toolbar">
        <div className="iq-tabs">
          <button className={`iq-tab ${tab === 'generate' ? 'active' : ''}`} onClick={() => setTab('generate')}>Generate from document</button>
          <button className={`iq-tab ${tab === 'build' ? 'active' : ''}`} onClick={() => setTab('build')}>Build manually</button>
          <button className={`iq-tab ${tab === 'play' ? 'active' : ''}`} onClick={startPlay}><FaPlay /> Play Quiz</button>
        </div>

        {tab === 'generate' && (
          <div className="iq-generate">
            {/* Source selector */}
            <div className="kv-seg">
              {['vault','upload'].map(m => (
                <button
                  key={m}
                  type="button"
                  className={`seg-btn ${source === m ? 'active' : ''}`}
                  onClick={() => setSource(m)}
                  disabled={status === 'running' || status === 'starting' || uploading}
                >{m === 'vault' ? 'From Vault' : 'Upload'}</button>
              ))}
            </div>

            {source === 'vault' ? (
              <div className="iq-row">
                <label className="iq-label">
                  <span>Knowledge Vault</span>
                  <div className="kv-select-wrap">
                    <select
                      className="iq-input"
                      value={selectedVaultFile}
                      onChange={(e) => setSelectedVaultFile(e.target.value)}
                    >
                      <option value="">Vault: choose file…</option>
                      {vaultFiles.map((vf, idx) => (
                        <option key={idx} value={vf.stored_name}>{vf.name || vf.stored_name}</option>
                      ))}
                    </select>
                    {selectedVaultFile && (
                      <button className="btn-ghost" type="button" onClick={() => setSelectedVaultFile('')}>✕</button>
                    )}
                  </div>
                </label>
              </div>
            ) : (
              <div className="iq-row">
                <label className="iq-label">
                  <span>Upload to Vault</span>
                  <div className="kv-upload">
                    <label className="kv-upload-btn">
                      <FaCloudUploadAlt /> {uploading ? 'Uploading…' : 'Choose file'}
                      <input type="file" onChange={handleUpload} disabled={uploading || status === 'running' || status === 'starting'} />
                    </label>
                    <span className="hint">File is saved to the Knowledge Vault and selectable thereafter.</span>
                  </div>
                </label>
              </div>
            )}

            {/* Generation params */}
            <div className="iq-row">
              <label className="iq-label">
                <span>Questions</span>
                <select className="iq-input" value={numQ} onChange={(e) => setNumQ(Number(e.target.value))}>
                  {[5, 10, 15, 20].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </label>
              <label className="iq-label">
                <span>Difficulty</span>
                <select className="iq-input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </label>
              <label className="iq-check">
                <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
                <span>Regenerate (ignore cached)</span>
              </label>
            </div>

            <div className="iq-actions">
              <button className="btn-primary" onClick={startGenerate} disabled={!canStart}>
                <FaRocket /> {(status === 'running' || status === 'starting') ? 'Working…' : 'Generate'}
              </button>
              <button className="btn-ghost" onClick={fetchResults} disabled={status === 'running' || status === 'starting'}>
                <FaSyncAlt /> Refresh
              </button>
            </div>

            {(status === 'running' || status === 'starting') && (
              <div className="iq-progress">
                <div className="iq-progress-bar" style={{ width: `${progress}%` }} />
                <div className="iq-progress-text">{progress}%</div>
              </div>
            )}

            {error && <div className="iq-error">{error}</div>}
          </div>
        )}
      </section>

      {/* Editor */}
      {tab !== 'play' && (
        <section className="iq-card iq-editor">
          <div className="iq-editor-top">
            <div className="iq-title-edit">
              <span className="muted">Quiz title</span>
              <input className="iq-input big" value={quizTitle} onChange={(e) => setQuizTitle(e.target.value)} />
            </div>
            <div className="iq-editor-actions">
              <button className="btn-ghost" onClick={() => setQuestions((qs) => [...qs, defaultQuestion()])}><FaPlus /> Add Question</button>
              <button className="btn-ghost" onClick={startPlay}><FaPlay /> Preview / Play</button>
            </div>
          </div>

          <div className="iq-qgrid">
            {questions.map((q, idx) => (
              <QuestionEditor
                key={q.id}
                index={idx + 1}
                model={q}
                onRemove={() => setQuestions((qs) => (qs.length > 1 ? qs.filter((x) => x.id !== q.id) : qs))}
                onChange={(id, patch) => setQuestions((qs) => qs.map((x) => (x.id === id ? { ...x, ...patch } : x)))}
                onAddOption={() => setQuestions((qs) => qs.map((x) => (x.id === q.id ? { ...x, options: [...x.options, { id: uid(), text: '' }] } : x)))}
                onRemoveOption={(oid) => setQuestions((qs) => qs.map((x) => {
                  if (x.id !== q.id) return x;
                  const next = x.options.filter((o) => o.id !== oid);
                  const ci = Math.min(x.correctIndex, Math.max(0, next.length - 1));
                  return { ...x, options: next, correctIndex: ci };
                }))}
                onChangeOption={(oid, text) => setQuestions((qs) => qs.map((x) => {
                  if (x.id !== q.id) return x;
                  return { ...x, options: x.options.map((o) => (o.id === oid ? { ...o, text } : o)) };
                }))}
              />
            ))}
          </div>
        </section>
      )}

      {/* Play Mode */}
      {tab === 'play' && (
        <section className="iq-card iq-play">
            {!finished ? (
            <PlayPane
                quizTitle={quizTitle}
                question={questions[Math.min(playIndex, Math.max(questions.length - 1, 0))]}
                index={playIndex}
                total={questions.length}
                chosen={answers[questions[playIndex]?.id]}
                onChoose={(idx) =>
                setAnswers((a) => ({ ...a, [questions[playIndex].id]: idx }))
                }
                onNext={() =>
                playIndex < questions.length - 1
                    ? setPlayIndex((i) => i + 1)
                    : setFinished(true)
                }
                explanation={questions[playIndex]?.explanation}
            />
            ) : (
            <ResultPane
                title={quizTitle}
                score={score}
                total={questions.length}
                onRestart={() => {
                setFinished(false);
                setPlayIndex(0);
                setAnswers({});
                 
                }}
                onBackToGenerate={() => {
          setFinished(false);
          setPlayIndex(0);
          setAnswers({});
          setTab('generate');   // ⟵ jump back to Generate tab
        }}
            />
            )}
        </section>
        )}

      {/* Share & Export */}
      <section className="iq-card iq-share">
        <div className="iq-share-left">
          <h3 className="iq-h3"><FaShareAlt /> Share</h3>
          <div className="iq-share-row">
            <button className="iq-share-btn wa" onClick={() => window.open(`https://wa.me/?text=${encodeURIComponent(getShareText({ finished, score, questions, quizTitle, shareUrl, PUBLIC_BASE: (config && config.PUBLIC_BASE_URL) || '' }))}`, '_blank', 'noopener,noreferrer')}><FaWhatsapp /> WhatsApp</button>
            <button className="iq-share-btn tg" onClick={() => window.open(`https://t.me/share/url?url=${encodeURIComponent(shareUrl || ((config && config.PUBLIC_BASE_URL) || window.location.origin))}&text=${encodeURIComponent(getShareText({ finished, score, questions, quizTitle, shareUrl, PUBLIC_BASE: (config && config.PUBLIC_BASE_URL) || '' }))}`, '_blank', 'noopener,noreferrer')}><FaTelegramPlane /> Telegram</button>
            <button className="iq-share-btn tw" onClick={() => window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(getShareText({ finished, score, questions, quizTitle, shareUrl, PUBLIC_BASE: (config && config.PUBLIC_BASE_URL) || '' }))}&url=${encodeURIComponent(shareUrl || ((config && config.PUBLIC_BASE_URL) || window.location.origin))}`, '_blank', 'noopener,noreferrer')}><FaTwitter /> X (Twitter)</button>
            <button className="iq-share-btn fb" onClick={() => window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl || ((config && config.PUBLIC_BASE_URL) || window.location.origin))}`, '_blank', 'noopener,noreferrer')}><FaFacebookF /> Facebook</button>
          </div>
          <div className="iq-share-row">
            <button className="btn-ghost" onClick={createShareLink}><FaShareAlt /> Create Share Link</button>
            <button className="btn-ghost" onClick={() => { navigator.clipboard.writeText(JSON.stringify({ title: quizTitle, questions }, null, 2)).then(() => { setCopied(true); setTimeout(() => setCopied(false), 900); }); }}><FaCopy /> {copied ? 'Copied!' : 'Copy JSON'}</button>
            <button className="btn-primary" onClick={() => {
              const blob = new Blob([JSON.stringify({ title: quizTitle, questions }, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob); const a = document.createElement('a');
              a.download = `${quizTitle.replace(/\s+/g, '_').toLowerCase() || 'quiz'}.json`; a.href = url; a.click();
              URL.revokeObjectURL(url);
            }}><FaDownload /> Download JSON</button>
          </div>
          {shareUrl && <div className="iq-share-link"><span className="muted">Link:</span> <a href={shareUrl} target="_blank" rel="noreferrer">{shareUrl}</a></div>}
        </div>

        <div className="iq-share-right">
          <div className="iq-stats">
            <div><FaClock /> Suggested time: {Math.max(questions.length * 0.7, 5).toFixed(0)} min</div>
            <div><FaRandom /> Shuffle recommended</div>
          </div>
        </div>
      </section>

      <footer className="iq-footer">
        <Link to="/master" className="cw-back">← Back to Master</Link>
      </footer>
    </div>
  );
}

function QuestionEditor({ index, model, onRemove, onChange, onAddOption, onRemoveOption, onChangeOption }) {
  return (
    <div className="iq-qcard">
      <div className="iq-qhead">
        <h4 className="iq-qtitle">Q{index}</h4>
        <button className="iq-remove" onClick={onRemove} title="Remove question"><FaTrash /></button>
      </div>

      <label className="iq-label">
        <span>Question</span>
        <textarea className="iq-input" rows={2} value={model.question} onChange={(e) => onChange(model.id, { question: e.target.value })} placeholder="Type the question…" />
      </label>

      <div className="iq-options">
        {model.options.map((o, i) => (
          <div key={o.id} className={`iq-option ${i === model.correctIndex ? 'correct' : ''}`}>
            <input className="iq-radio" type="radio" name={`correct-${model.id}`} checked={i === model.correctIndex} onChange={() => onChange(model.id, { correctIndex: i })} title="Mark as correct" />
            <input className="iq-input" value={o.text} onChange={(e) => onChangeOption(o.id, e.target.value)} placeholder={`Option ${i + 1}`} />
            <button className="iq-delopt" onClick={() => onRemoveOption(o.id)} title="Delete option"><FaTrash /></button>
          </div>
        ))}
      </div>

      <div className="iq-row">
        <button className="btn-ghost" onClick={onAddOption}><FaPlus /> Add Option</button>
      </div>

      <label className="iq-label">
        <span>Explanation (optional)</span>
        <textarea className="iq-input" rows={2} value={model.explanation} onChange={(e) => onChange(model.id, { explanation: e.target.value })} placeholder="Why is this the right answer?" />
      </label>
    </div>
  );
}

function PlayPane({ quizTitle, question, index, total, chosen, onChoose, onNext, explanation }) {
  const isAnswered = typeof chosen === 'number';
  const isCorrect = isAnswered && chosen === question?.correctIndex;
  return (
    <div className="iq-playpane">
      <h3 className="iq-h3">{quizTitle}</h3>
      <div className="iq-play-meta">Question {Math.min(index + 1, total)} of {total}</div>
      <div className="iq-play-q">{question?.question || '—'}</div>
      <div className="iq-play-options">
        {(question?.options || []).map((o, i) => {
          const sel = chosen === i;
          const klass = ['iq-play-opt', sel ? 'selected' : '', isAnswered && i === question.correctIndex ? 'good' : '', isAnswered && sel && i !== question.correctIndex ? 'bad' : ''].join(' ').trim();
          return (
            <button key={o.id || i} className={klass} onClick={() => !isAnswered && onChoose(i)}>
              <span className="iq-opt-dot">{String.fromCharCode(65 + i)}</span>
              <span>{o.text || '—'}</span>
              {isAnswered && i === question.correctIndex && <FaCheck className="iq-check" />}
            </button>
          );
        })}
      </div>
      <div className="iq-play-actions">
        {!isAnswered ? (
          <div className="muted">Choose an answer to continue.</div>
        ) : (
          <>
            {explanation && <div className="iq-explain"><strong>Why:</strong> {explanation}</div>}
            <button className="btn-primary" onClick={onNext}>Next</button>
          </>
        )}
      </div>
    </div>
  );
}

function getShareText({ finished, score, questions, quizTitle, shareUrl, PUBLIC_BASE }) {
  const link = shareUrl || (PUBLIC_BASE ? `${PUBLIC_BASE}/play_quiz` : '');
  const msg = `🎯 *${quizTitle}* — ${questions.length} questions\n` + (finished ? `I scored ${score}/${questions.length}! ` : '') + (link ? `\nPlay here: ${link}` : '');
  return msg.trim();
}

function ResultPane({ title, score, total, onRestart, onBackToGenerate }) {
  const safeTotal = Math.max(total || 0, 1);
  const safeScore = Math.max(0, Math.min(score || 0, safeTotal));
  const pct = Math.round((safeScore / safeTotal) * 100);

  return (
    <div className="iq-result">
      <h3 className="iq-h3">{title}</h3>
      <div className="iq-score">
        You scored <strong>{safeScore}</strong> / {safeTotal} ({pct}%)
      </div>
      <div className="iq-result-hint muted">
        Share your score or try again to beat it!
      </div>
      <div style={{ marginTop: 10, display: 'flex', gap: 10 }}>
        <button className="btn-primary" onClick={onRestart}>
          Start Again
        </button>
        <button className="btn-ghost" onClick={onBackToGenerate}>
          Back to Generate
        </button>
      </div>
    </div>
  );
}