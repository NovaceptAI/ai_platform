import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaFlask, FaAtom, FaDna, FaLightbulb, FaSave, FaPlay, FaRedo } from 'react-icons/fa';
import axiosInstance from '../../utils/axiosInstance';
import './VirtualScienceLab.css';

/**
 * Virtual Science Lab
 *
 * Interactive simulation-based environment for physics, chemistry, and biology experiments.
 * Features AI tutor, digital lab notebook, and real-time simulations.
 */
function VirtualScienceLab() {
  const navigate = useNavigate();

  // Subject and experiment selection
  const [subject, setSubject] = useState('physics'); // physics, chemistry, biology
  const [experimentType, setExperimentType] = useState('');
  const [experimentTitle, setExperimentTitle] = useState('');

  // Simulation state
  const [parameters, setParameters] = useState({});
  const [results, setResults] = useState(null);
  const [trials, setTrials] = useState([]);
  const [currentTrial, setCurrentTrial] = useState(1);

  // Lab notebook
  const [observations, setObservations] = useState('');
  const [conclusions, setConclusions] = useState('');

  // AI Tutor
  const [aiHint, setAiHint] = useState('');
  const [aiFeedback, setAiFeedback] = useState(null);
  const [showHint, setShowHint] = useState(false);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('simulation'); // simulation, notebook, results

  // Saved experiments
  const [savedExperiments, setSavedExperiments] = useState([]);
  const [currentExperimentId, setCurrentExperimentId] = useState(null);

  // Experiment definitions
  const experiments = {
    physics: [
      { type: 'physics_pendulum', name: 'Simple Pendulum', icon: '⏱️' },
      { type: 'physics_projectile', name: 'Projectile Motion', icon: '🎯' },
      { type: 'physics_springs', name: 'Springs & Hooke\'s Law', icon: '🔩' }
    ],
    chemistry: [
      { type: 'chemistry_ph', name: 'pH Calculator', icon: '🧪' },
      { type: 'chemistry_reaction', name: 'Stoichiometry', icon: '⚗️' }
    ],
    biology: [
      { type: 'biology_photosynthesis', name: 'Photosynthesis (Coming Soon)', icon: '🌱', disabled: true }
    ]
  };

  // Load saved experiments on mount
  useEffect(() => {
    fetchSavedExperiments();
  }, []);

  const fetchSavedExperiments = async () => {
    try {
      const response = await axiosInstance.get('/master/science_lab/experiments');
      setSavedExperiments(response.data.experiments || []);
    } catch (err) {
      console.error('Error fetching experiments:', err);
    }
  };

  // Initialize parameters when experiment type changes
  useEffect(() => {
    if (experimentType) {
      setParameters(getDefaultParameters(experimentType));
      setResults(null);
      setTrials([]);
      setCurrentTrial(1);
    }
  }, [experimentType]);

  const getDefaultParameters = (type) => {
    const defaults = {
      physics_pendulum: { length: 1.0, initial_angle: 15, gravity: 9.81 },
      physics_projectile: { initial_velocity: 20, angle: 45, height: 0 },
      physics_springs: { spring_constant: 100, mass: 1, displacement: 0.1 },
      chemistry_ph: { concentration: 0.1, acid_or_base: 'acid', strong_or_weak: 'strong' },
      chemistry_reaction: { reactant_amount: 10, reactant_molar_mass: 18, product_molar_mass: 32, ratio: '2:1' }
    };
    return defaults[type] || {};
  };

  const runSimulation = async () => {
    if (!experimentType) {
      setError('Please select an experiment first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axiosInstance.post('/master/science_lab/simulate', {
        experiment_type: experimentType,
        parameters
      });

      const newResults = response.data.results;
      setResults(newResults);

      // Add to trials
      const newTrial = {
        trial_number: currentTrial,
        parameters: { ...parameters },
        results: newResults,
        timestamp: new Date().toISOString()
      };
      setTrials([...trials, newTrial]);
      setCurrentTrial(currentTrial + 1);

    } catch (err) {
      setError(err?.response?.data?.error || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const getHint = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.post('/master/science_lab/hint', {
        experiment_type: experimentType,
        current_data: { parameters, results, trials }
      });
      setAiHint(response.data.hint);
      setShowHint(true);
    } catch (err) {
      setError('Failed to get hint');
    } finally {
      setLoading(false);
    }
  };

  const getFeedback = async () => {
    if (!observations || !conclusions) {
      setError('Please fill in observations and conclusions first');
      return;
    }

    setLoading(true);
    try {
      const response = await axiosInstance.post('/master/science_lab/feedback', {
        experiment_type: experimentType,
        trials,
        observations,
        conclusions
      });
      setAiFeedback(response.data.feedback);
      setActiveTab('results');
    } catch (err) {
      setError('Failed to get feedback');
    } finally {
      setLoading(false);
    }
  };

  const saveExperiment = async () => {
    if (!experimentTitle) {
      setError('Please enter an experiment title');
      return;
    }

    setLoading(true);
    try {
      const response = await axiosInstance.post('/master/science_lab/save', {
        experiment_id: currentExperimentId,
        experiment_type: experimentType,
        experiment_title: experimentTitle,
        subject,
        initial_parameters: getDefaultParameters(experimentType),
        trial_data: trials,
        observations,
        conclusions,
        status: aiFeedback ? 'completed' : 'in_progress'
      });

      setCurrentExperimentId(response.data.experiment_id);
      await fetchSavedExperiments();
      alert('Experiment saved successfully!');
    } catch (err) {
      setError('Failed to save experiment');
    } finally {
      setLoading(false);
    }
  };

  const resetExperiment = () => {
    setParameters(getDefaultParameters(experimentType));
    setResults(null);
    setTrials([]);
    setCurrentTrial(1);
    setObservations('');
    setConclusions('');
    setAiFeedback(null);
    setAiHint('');
    setShowHint(false);
    setCurrentExperimentId(null);
    setExperimentTitle('');
  };

  const loadExperiment = async (expId) => {
    try {
      const response = await axiosInstance.get(`/master/science_lab/experiments/${expId}`);
      const exp = response.data.experiment;

      setExperimentType(exp.experiment_type);
      setExperimentTitle(exp.experiment_title);
      setSubject(exp.subject);
      setTrials(exp.trial_data || []);
      setObservations(exp.observations || '');
      setConclusions(exp.conclusions || '');
      setAiFeedback(exp.ai_feedback || null);
      setCurrentExperimentId(exp.id);
      setCurrentTrial((exp.trial_data || []).length + 1);
    } catch (err) {
      setError('Failed to load experiment');
    }
  };

  return (
    <div className="science-lab-container">
      {/* Header */}
      <header className="lab-header">
        <button className="back-button" onClick={() => navigate('/master')}>
          ← Back to Master
        </button>
        <h1><FaFlask /> Virtual Science Lab</h1>
        <p className="subtitle">Interactive simulations with AI tutor guidance</p>
      </header>

      <div className="lab-layout">
        {/* Sidebar - Experiment Selection */}
        <aside className="lab-sidebar">
          <div className="sidebar-section">
            <h3>Select Subject</h3>
            <div className="subject-buttons">
              <button
                className={`subject-btn ${subject === 'physics' ? 'active' : ''}`}
                onClick={() => setSubject('physics')}
              >
                <FaAtom /> Physics
              </button>
              <button
                className={`subject-btn ${subject === 'chemistry' ? 'active' : ''}`}
                onClick={() => setSubject('chemistry')}
              >
                <FaFlask /> Chemistry
              </button>
              <button
                className={`subject-btn ${subject === 'biology' ? 'active' : ''}`}
                onClick={() => setSubject('biology')}
              >
                <FaDna /> Biology
              </button>
            </div>
          </div>

          <div className="sidebar-section">
            <h3>Choose Experiment</h3>
            <div className="experiment-list">
              {experiments[subject]?.map((exp) => (
                <button
                  key={exp.type}
                  className={`experiment-item ${experimentType === exp.type ? 'active' : ''} ${exp.disabled ? 'disabled' : ''}`}
                  onClick={() => !exp.disabled && setExperimentType(exp.type)}
                  disabled={exp.disabled}
                >
                  <span className="exp-icon">{exp.icon}</span>
                  <span className="exp-name">{exp.name}</span>
                </button>
              ))}
            </div>
          </div>

          {savedExperiments.length > 0 && (
            <div className="sidebar-section">
              <h3>Saved Experiments</h3>
              <div className="saved-list">
                {savedExperiments.slice(0, 5).map((exp) => (
                  <button
                    key={exp.id}
                    className="saved-item"
                    onClick={() => loadExperiment(exp.id)}
                  >
                    <span>{exp.experiment_title}</span>
                    <small>{exp.subject}</small>
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="lab-main">
          {!experimentType ? (
            <div className="empty-state">
              <FaFlask size={64} />
              <h2>Welcome to the Virtual Science Lab!</h2>
              <p>Select a subject and experiment from the sidebar to get started.</p>
            </div>
          ) : (
            <>
              {/* Experiment Title */}
              <div className="experiment-header">
                <input
                  type="text"
                  placeholder="Enter experiment title..."
                  value={experimentTitle}
                  onChange={(e) => setExperimentTitle(e.target.value)}
                  className="experiment-title-input"
                />
                <div className="header-actions">
                  <button onClick={getHint} className="btn-hint" disabled={loading}>
                    <FaLightbulb /> Get Hint
                  </button>
                  <button onClick={saveExperiment} className="btn-save" disabled={loading}>
                    <FaSave /> Save
                  </button>
                  <button onClick={resetExperiment} className="btn-reset">
                    <FaRedo /> Reset
                  </button>
                </div>
              </div>

              {/* Tabs */}
              <div className="lab-tabs">
                <button
                  className={`tab ${activeTab === 'simulation' ? 'active' : ''}`}
                  onClick={() => setActiveTab('simulation')}
                >
                  🔬 Simulation
                </button>
                <button
                  className={`tab ${activeTab === 'notebook' ? 'active' : ''}`}
                  onClick={() => setActiveTab('notebook')}
                >
                  📓 Lab Notebook
                </button>
                <button
                  className={`tab ${activeTab === 'results' ? 'active' : ''}`}
                  onClick={() => setActiveTab('results')}
                >
                  📊 Results & Feedback
                </button>
              </div>

              {/* AI Hint Modal */}
              {showHint && aiHint && (
                <div className="hint-banner">
                  <div className="hint-content">
                    <FaLightbulb className="hint-icon" />
                    <p>{aiHint}</p>
                  </div>
                  <button onClick={() => setShowHint(false)} className="hint-close">✕</button>
                </div>
              )}

              {error && (
                <div className="error-banner">
                  {error}
                  <button onClick={() => setError('')} className="error-close">✕</button>
                </div>
              )}

              {/* Tab Content */}
              {activeTab === 'simulation' && (
                <SimulationTab
                  experimentType={experimentType}
                  parameters={parameters}
                  setParameters={setParameters}
                  results={results}
                  loading={loading}
                  runSimulation={runSimulation}
                  trials={trials}
                />
              )}

              {activeTab === 'notebook' && (
                <NotebookTab
                  observations={observations}
                  setObservations={setObservations}
                  conclusions={setConclusions}
                  conclusions_value={conclusions}
                  trials={trials}
                  getFeedback={getFeedback}
                  loading={loading}
                />
              )}

              {activeTab === 'results' && (
                <ResultsTab
                  trials={trials}
                  aiFeedback={aiFeedback}
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

// Simulation Tab Component
function SimulationTab({ experimentType, parameters, setParameters, results, loading, runSimulation, trials }) {
  const updateParameter = (key, value) => {
    setParameters({ ...parameters, [key]: parseFloat(value) || value });
  };

  return (
    <div className="tab-content simulation-tab">
      <div className="simulation-grid">
        {/* Parameters Panel */}
        <div className="parameters-panel">
          <h3>Parameters</h3>
          {Object.entries(parameters).map(([key, value]) => (
            <div key={key} className="parameter-row">
              <label>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
              {typeof value === 'string' && !key.includes('ratio') ? (
                <select
                  value={value}
                  onChange={(e) => updateParameter(key, e.target.value)}
                >
                  {key === 'acid_or_base' && (
                    <>
                      <option value="acid">Acid</option>
                      <option value="base">Base</option>
                    </>
                  )}
                  {key === 'strong_or_weak' && (
                    <>
                      <option value="strong">Strong</option>
                      <option value="weak">Weak</option>
                    </>
                  )}
                </select>
              ) : (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => updateParameter(key, e.target.value)}
                />
              )}
            </div>
          ))}

          <button onClick={runSimulation} className="btn-run" disabled={loading}>
            <FaPlay /> Run Simulation
          </button>
        </div>

        {/* Results Panel */}
        <div className="results-panel">
          <h3>Results {results && <span className="trial-badge">Trial #{trials.length}</span>}</h3>
          {results ? (
            <div className="results-grid">
              {Object.entries(results).map(([key, value]) => {
                if (key === 'units' || typeof value === 'object') return null;
                return (
                  <div key={key} className="result-item">
                    <span className="result-label">{key.replace(/_/g, ' ')}:</span>
                    <span className="result-value">{value}</span>
                    {results.units && results.units[key] && (
                      <span className="result-unit">{results.units[key]}</span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="no-results">
              <p>Run a simulation to see results</p>
            </div>
          )}
        </div>
      </div>

      {/* Trials History */}
      {trials.length > 0 && (
        <div className="trials-history">
          <h3>Trial History ({trials.length} trials)</h3>
          <div className="trials-table">
            <table>
              <thead>
                <tr>
                  <th>Trial #</th>
                  <th>Parameters</th>
                  <th>Key Results</th>
                </tr>
              </thead>
              <tbody>
                {trials.map((trial, idx) => (
                  <tr key={idx}>
                    <td>{trial.trial_number}</td>
                    <td>{JSON.stringify(trial.parameters).substring(0, 50)}...</td>
                    <td>{Object.keys(trial.results).slice(0, 2).join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// Notebook Tab Component
function NotebookTab({ observations, setObservations, conclusions, setConclusions, trials, getFeedback, loading }) {
  return (
    <div className="tab-content notebook-tab">
      <div className="notebook-section">
        <h3>📝 Observations</h3>
        <p className="instruction">Record what you observed during your experiments. Be specific and detailed.</p>
        <textarea
          value={observations}
          onChange={(e) => setObservations(e.target.value)}
          placeholder="Example: In Trial 1, when I increased the pendulum length from 1m to 2m, the period increased from 2.01s to 2.84s..."
          rows={8}
        />
      </div>

      <div className="notebook-section">
        <h3>💡 Conclusions</h3>
        <p className="instruction">What did you learn? How do your observations support your conclusions?</p>
        <textarea
          value={conclusions}
          onChange={(e) => setConclusions(e.target.value)}
          placeholder="Example: My experiments show that the period of a pendulum increases with length. This relationship appears to be proportional to the square root of the length..."
          rows={8}
        />
      </div>

      <button
        onClick={getFeedback}
        className="btn-feedback"
        disabled={loading || !observations || !conclusions || trials.length === 0}
      >
        Get AI Feedback on My Work
      </button>

      {trials.length === 0 && (
        <div className="warning-box">
          ⚠️ Run at least one simulation before requesting feedback
        </div>
      )}
    </div>
  );
}

// Results Tab Component
function ResultsTab({ trials, aiFeedback }) {
  return (
    <div className="tab-content results-tab">
      {aiFeedback ? (
        <div className="feedback-container">
          <h2>🎓 AI Tutor Feedback</h2>

          {aiFeedback.strengths && aiFeedback.strengths.length > 0 && (
            <div className="feedback-section strengths">
              <h3>✅ Strengths</h3>
              <ul>
                {aiFeedback.strengths.map((strength, idx) => (
                  <li key={idx}>{strength}</li>
                ))}
              </ul>
            </div>
          )}

          {aiFeedback.areas_for_improvement && aiFeedback.areas_for_improvement.length > 0 && (
            <div className="feedback-section improvements">
              <h3>💪 Areas for Improvement</h3>
              <ul>
                {aiFeedback.areas_for_improvement.map((area, idx) => (
                  <li key={idx}>{area}</li>
                ))}
              </ul>
            </div>
          )}

          {aiFeedback.suggestions && aiFeedback.suggestions.length > 0 && (
            <div className="feedback-section suggestions">
              <h3>💡 Suggestions</h3>
              <ul>
                {aiFeedback.suggestions.map((suggestion, idx) => (
                  <li key={idx}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}

          {aiFeedback.scientific_accuracy && (
            <div className="feedback-section accuracy">
              <h3>🎯 Scientific Accuracy</h3>
              <div className={`accuracy-badge ${aiFeedback.scientific_accuracy}`}>
                {aiFeedback.scientific_accuracy.toUpperCase()}
              </div>
            </div>
          )}

          {aiFeedback.overall_comment && (
            <div className="feedback-section overall">
              <h3>📋 Overall</h3>
              <p>{aiFeedback.overall_comment}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="no-feedback">
          <p>Complete your lab notebook and request feedback to see results here</p>
        </div>
      )}

      {/* Summary of Trials */}
      {trials.length > 0 && (
        <div className="trials-summary">
          <h3>Experiment Summary</h3>
          <p>Total Trials: {trials.length}</p>
          <p>Experiment Type: {trials[0]?.parameters ? Object.keys(trials[0].parameters).join(', ') : 'N/A'}</p>
        </div>
      )}
    </div>
  );
}

export default VirtualScienceLab;
