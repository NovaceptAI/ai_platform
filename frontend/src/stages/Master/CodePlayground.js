import React, { useState, useEffect, useRef } from 'react';
import './CodePlayground.css';
import axiosInstance from '../../utils/axiosInstance';

// Simple turtle graphics simulator for the browser
class TurtleSimulator {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.commands = [];
    this.reset();
  }

  reset() {
    this.x = this.canvas.width / 2;
    this.y = this.canvas.height / 2;
    this.angle = 0; // 0 degrees is pointing right
    this.penDown = true;
    this.color = '#8b5cf6'; // Purple
    this.commands = [];
    
    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Draw turtle
    this.drawTurtle();
  }

  forward(distance) {
    const startX = this.x;
    const startY = this.y;
    
    const radians = (this.angle * Math.PI) / 180;
    this.x += distance * Math.cos(radians);
    this.y += distance * Math.sin(radians);
    
    if (this.penDown) {
      this.ctx.strokeStyle = this.color;
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(startX, startY);
      this.ctx.lineTo(this.x, this.y);
      this.ctx.stroke();
    }
    
    this.commands.push({ type: 'forward', distance });
    this.drawTurtle();
  }

  backward(distance) {
    this.forward(-distance);
    this.commands.push({ type: 'backward', distance });
  }

  right(angle) {
    this.angle += angle;
    this.commands.push({ type: 'right', angle });
    this.drawTurtle();
  }

  left(angle) {
    this.angle -= angle;
    this.commands.push({ type: 'left', angle });
    this.drawTurtle();
  }

  penup() {
    this.penDown = false;
    this.commands.push({ type: 'penup' });
  }

  pendown() {
    this.penDown = true;
    this.commands.push({ type: 'pendown' });
  }

  setColor(newColor) {
    this.color = newColor;
    this.commands.push({ type: 'color', color: newColor });
  }

  circle(radius) {
    this.ctx.strokeStyle = this.color;
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.arc(this.x, this.y, Math.abs(radius), 0, 2 * Math.PI);
    this.ctx.stroke();
    this.commands.push({ type: 'circle', radius });
  }

  goto(x, y) {
    this.x = x;
    this.y = y;
    this.commands.push({ type: 'goto', x, y });
    this.drawTurtle();
  }

  home() {
    this.x = this.canvas.width / 2;
    this.y = this.canvas.height / 2;
    this.angle = 0;
    this.commands.push({ type: 'home' });
    this.drawTurtle();
  }

  drawTurtle() {
    // Draw a small triangle to represent the turtle
    const size = 10;
    const radians = (this.angle * Math.PI) / 180;
    
    this.ctx.save();
    this.ctx.translate(this.x, this.y);
    this.ctx.rotate(radians);
    
    this.ctx.fillStyle = '#ef4444';
    this.ctx.beginPath();
    this.ctx.moveTo(size, 0);
    this.ctx.lineTo(-size, -size/2);
    this.ctx.lineTo(-size, size/2);
    this.ctx.closePath();
    this.ctx.fill();
    
    this.ctx.restore();
  }

  getCommands() {
    return this.commands;
  }
}

function CodePlayground() {
  const [activeTab, setActiveTab] = useState('turtle');
  
  // Turtle Graphics State
  const [sessionId, setSessionId] = useState(null);
  const [selectedChallenge, setSelectedChallenge] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState('');
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [challenge, setChallenge] = useState(null);
  const [stats, setStats] = useState({ executions: 0, hints_used: 0 });
  const [hintText, setHintText] = useState('');
  const [isGettingHint, setIsGettingHint] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [gameState, setGameState] = useState('select'); // 'select', 'coding', 'completed'
  const [finalStats, setFinalStats] = useState(null);
  const [error, setError] = useState('');
  
  const canvasRef = useRef(null);
  const turtleRef = useRef(null);
  const codeEditorRef = useRef(null);

  // Load challenges on mount
  useEffect(() => {
    console.log('Component mounted, loading challenges...');
    // Set default challenges immediately for faster UX
    setDefaultChallenges();
    // Then try to load from API
    loadChallenges();
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl/Cmd + Enter to run code
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && gameState === 'coding') {
        e.preventDefault();
        handleRunCode();
      }
      // Ctrl/Cmd + H for hint
      if ((e.ctrlKey || e.metaKey) && e.key === 'h' && gameState === 'coding' && !isGettingHint) {
        e.preventDefault();
        handleGetHint();
      }
      // Ctrl/Cmd + R to reset canvas
      if ((e.ctrlKey || e.metaKey) && e.key === 'r' && gameState === 'coding') {
        e.preventDefault();
        handleResetCanvas();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameState, code, isGettingHint]);

  const loadChallenges = async () => {
    try {
      const response = await axiosInstance.get('/master/code_playground/turtle/challenges');
      console.log('Challenges loaded:', response.data.challenges);
      setChallenges(response.data.challenges);
    } catch (err) {
      console.error('Error loading challenges:', err);
      // Set default challenges if API fails
      setDefaultChallenges();
    }
  };

  const setDefaultChallenges = () => {
    // Fallback challenges if API fails
    const defaultChallenges = [
      { id: 'draw_square', name: 'Draw a Square', description: 'Use turtle commands to draw a perfect square', difficulty: 'easy' },
      { id: 'draw_triangle', name: 'Draw a Triangle', description: 'Create an equilateral triangle', difficulty: 'easy' },
      { id: 'draw_star', name: 'Draw a Star', description: 'Draw a 5-pointed star', difficulty: 'medium' },
      { id: 'spiral', name: 'Create a Spiral', description: 'Draw a beautiful spiral pattern', difficulty: 'medium' },
      { id: 'rainbow_circle', name: 'Rainbow Circles', description: 'Draw multiple colorful circles', difficulty: 'hard' },
      { id: 'custom', name: 'Free Drawing', description: 'Create your own masterpiece!', difficulty: 'any' }
    ];
    setChallenges(defaultChallenges);
  };

  const handleSelectChallenge = async (challengeId) => {
    try {
      console.log('Starting challenge:', challengeId, 'with language:', language);
      setError('');
      
      const response = await axiosInstance.post('/master/code_playground/turtle/start', {
        challenge_id: challengeId,
        language: language
      });

      console.log('Response status:', response.status);
      console.log('Challenge started successfully:', response.data);
      
      setSessionId(response.data.session_id);
      setChallenge(response.data.challenge);
      setCode(response.data.starter_code);
      setGameState('coding');
      setStats({ executions: 0, hints_used: 0 });
      setHintText('');
      setValidationResult(null);
      
      // Initialize canvas
      setTimeout(() => {
        if (canvasRef.current) {
          turtleRef.current = new TurtleSimulator(canvasRef.current);
          console.log('Turtle simulator initialized');
        } else {
          console.error('Canvas ref not available');
        }
      }, 100);
      
    } catch (err) {
      console.error('Error in handleSelectChallenge:', err);
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleRunCode = async () => {
    if (!code.trim()) return;
    
    try {
      setIsRunning(true);
      setOutput('');
      setError('');
      setValidationResult(null);
      
      // Reset turtle
      if (turtleRef.current) {
        turtleRef.current.reset();
      }
      
      // Execute code
      try {
        executeTurtleCode(code);
        setOutput('✓ Code executed successfully!');
        
        // Get commands and validate
        const commands = turtleRef.current.getCommands();
        await validateSolution(commands);
        
        // Track execution
        await axiosInstance.post('/master/code_playground/turtle/execute', {
          session_id: sessionId,
          code: code,
          language: language
        });
        
        setStats(prev => ({ ...prev, executions: prev.executions + 1 }));
        
      } catch (err) {
        setError(err.message);
        setOutput(`✗ Error: ${err.message}`);
      }
      
    } finally {
      setIsRunning(false);
    }
  };

  const executeTurtleCode = (codeToRun) => {
    const turtle = turtleRef.current;
    if (!turtle) throw new Error('Canvas not initialized');
    
    // Create safe execution context
    const safeContext = {
      forward: (d) => turtle.forward(d),
      backward: (d) => turtle.backward(d),
      right: (a) => turtle.right(a),
      left: (a) => turtle.left(a),
      penup: () => turtle.penup(),
      pendown: () => turtle.pendown(),
      color: (c) => turtle.setColor(c),
      circle: (r) => turtle.circle(r),
      goto: (x, y) => turtle.goto(x, y),
      home: () => turtle.home(),
      console: { log: () => {} } // Prevent console spam
    };
    
    // Create function from code
    try {
      if (language === 'python') {
        // Convert Python-style code to JavaScript
        let jsCode = codeToRun
          .replace(/def\s+(\w+)\s*\((.*?)\):/g, 'function $1($2) {')
          .replace(/for\s+(\w+)\s+in\s+range\((\d+)\):/g, 'for (let $1 = 0; $1 < $2; $1++) {')
          .replace(/^\s*#.*$/gm, '') // Remove comments
          .split('\n')
          .map(line => {
            const indent = line.match(/^\s*/)[0].length;
            if (indent > 0 && line.trim() && !line.trim().startsWith('}')) {
              return line;
            }
            return line;
          })
          .join('\n');
        
        // Execute
        const func = new Function(...Object.keys(safeContext), jsCode);
        func(...Object.values(safeContext));
      } else {
        // JavaScript execution
        const func = new Function(...Object.keys(safeContext), codeToRun);
        func(...Object.values(safeContext));
      }
    } catch (err) {
      throw new Error(err.message);
    }
  };

  const validateSolution = async (commands) => {
    try {
      const response = await axiosInstance.post('/master/code_playground/turtle/validate', {
        session_id: sessionId,
        code: code,
        output: commands
      });

      setValidationResult(response.data);
    } catch (err) {
      console.error('Validation error:', err);
    }
  };

  const handleGetHint = async () => {
    try {
      setIsGettingHint(true);
      setError('');
      
      const response = await axiosInstance.post('/master/code_playground/turtle/hint', {
        session_id: sessionId,
        code: code,
        error_message: error || undefined
      });

      setHintText(response.data.hint);
      setStats(prev => ({ ...prev, hints_used: response.data.hints_used }));
      
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setIsGettingHint(false);
    }
  };

  const handleResetCanvas = () => {
    if (turtleRef.current) {
      turtleRef.current.reset();
      setOutput('Canvas reset');
      setValidationResult(null);
    }
  };

  const handleEndSession = async () => {
    try {
      const response = await axiosInstance.post('/master/code_playground/turtle/end', {
        session_id: sessionId
      });

      setFinalStats(response.data);
      setGameState('completed');
      
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleNewChallenge = () => {
    setGameState('select');
    setSessionId(null);
    setChallenge(null);
    setCode('');
    setOutput('');
    setHintText('');
    setValidationResult(null);
    setFinalStats(null);
    setStats({ executions: 0, hints_used: 0 });
  };

  const renderChallengeSelect = () => (
    <div className="cp-select-container">
      <div className="cp-language-selector">
        <label>Choose your language:</label>
        <div className="cp-lang-buttons">
          <button
            className={`cp-lang-button ${language === 'python' ? 'cp-lang-active' : ''}`}
            onClick={() => setLanguage('python')}
          >
            🐍 Python
          </button>
          <button
            className={`cp-lang-button ${language === 'javascript' ? 'cp-lang-active' : ''}`}
            onClick={() => setLanguage('javascript')}
          >
            ⚡ JavaScript
          </button>
        </div>
      </div>

      <div className="cp-challenges-grid">
        <h2>Choose a Challenge</h2>
        {challenges.length === 0 ? (
          <div className="cp-loading" style={{gridColumn: '1 / -1', textAlign: 'center', padding: '40px'}}>
            <p>Loading challenges...</p>
          </div>
        ) : (
          challenges.map((ch) => (
            <div
              key={ch.id}
              className={`cp-challenge-card cp-difficulty-${ch.difficulty}`}
              onClick={() => {
                console.log('CLICK DETECTED! Challenge ID:', ch.id);
                handleSelectChallenge(ch.id);
              }}
            >
              <div className="cp-challenge-icon">
                {ch.id === 'draw_square' && '⬜'}
                {ch.id === 'draw_triangle' && '🔺'}
                {ch.id === 'draw_star' && '⭐'}
                {ch.id === 'spiral' && '🌀'}
                {ch.id === 'rainbow_circle' && '🌈'}
                {ch.id === 'custom' && '🎨'}
              </div>
              <h3>{ch.name}</h3>
              <p>{ch.description}</p>
              <span className="cp-difficulty-badge">{ch.difficulty}</span>
            </div>
          ))
        )}
      </div>

      {error && <div className="cp-error">{error}</div>}
    </div>
  );

  const renderCodingScreen = () => (
    <div className="cp-coding-container">
      <div className="cp-coding-header">
        <div className="cp-challenge-info">
          <h2>🎯 {challenge?.name}</h2>
          <p>{challenge?.description}</p>
        </div>
        <div className="cp-stats-row">
          <div className="cp-stat-badge">
            <span className="cp-stat-label">Runs:</span>
            <span className="cp-stat-value">{stats.executions}</span>
          </div>
          <div className="cp-stat-badge">
            <span className="cp-stat-label">Hints:</span>
            <span className="cp-stat-value">{stats.hints_used}</span>
          </div>
        </div>
      </div>

      {challenge?.instructions && (
        <div className="cp-instructions">
          <h3>📝 Instructions</h3>
          <ul>
            {challenge.instructions.map((inst, idx) => (
              <li key={idx}>{inst}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="cp-workspace">
        <div className="cp-editor-panel">
          <div className="cp-editor-header">
            <span>Code Editor</span>
            <span className="cp-lang-indicator">{language}</span>
          </div>
          <textarea
            ref={codeEditorRef}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="cp-code-editor"
            spellCheck="false"
            placeholder={`Write your ${language} code here...`}
          />
          <div className="cp-editor-actions">
            <button
              onClick={handleRunCode}
              className="cp-run-button"
              disabled={isRunning}
              title="Ctrl/Cmd + Enter"
            >
              {isRunning ? '⏳ Running...' : '▶️ Run Code (Ctrl+Enter)'}
            </button>
            <button
              onClick={handleResetCanvas}
              className="cp-reset-button"
              title="Ctrl/Cmd + R"
            >
              🔄 Reset (Ctrl+R)
            </button>
            <button
              onClick={handleGetHint}
              className="cp-hint-button"
              disabled={isGettingHint}
              title="Ctrl/Cmd + H"
            >
              {isGettingHint ? '💭 Thinking...' : '💡 Hint (Ctrl+H)'}
            </button>
          </div>

          {output && (
            <div className={`cp-output ${error ? 'cp-output-error' : 'cp-output-success'}`}>
              {output}
            </div>
          )}

          {hintText && (
            <div className="cp-hint-display">
              <div className="cp-hint-icon">💡</div>
              <div className="cp-hint-content">{hintText}</div>
            </div>
          )}

          {validationResult && (
            <div className={`cp-validation ${validationResult.valid ? 'cp-validation-success' : 'cp-validation-pending'}`}>
              <div className="cp-validation-message">
                {validationResult.message}
              </div>
              {validationResult.feedback && validationResult.feedback.length > 0 && (
                <ul className="cp-validation-feedback">
                  {validationResult.feedback.map((fb, idx) => (
                    <li key={idx}>{fb}</li>
                  ))}
                </ul>
              )}
              {validationResult.completed && (
                <button onClick={handleEndSession} className="cp-complete-button">
                  🎉 Complete Challenge
                </button>
              )}
            </div>
          )}
        </div>

        <div className="cp-canvas-panel">
          <div className="cp-canvas-header">
            <span>🐢 Turtle Canvas</span>
          </div>
          <canvas
            ref={canvasRef}
            width={500}
            height={500}
            className="cp-canvas"
          />
          <div className="cp-canvas-tip">
            The red triangle is your turtle! 🐢
          </div>
        </div>
      </div>

      <div className="cp-bottom-actions">
        <button onClick={handleNewChallenge} className="cp-back-button">
          ← Back to Challenges
        </button>
      </div>
    </div>
  );

  const renderCompletedScreen = () => (
    <div className="cp-completed-container">
      <div className="cp-completed-card">
        <div className="cp-trophy">🏆</div>
        <h2>Challenge Completed!</h2>
        
        {finalStats && (
          <>
            <div className="cp-final-stats">
              <div className="cp-final-stat">
                <span className="cp-final-stat-label">Challenge:</span>
                <span className="cp-final-stat-value">{challenge?.name}</span>
              </div>
              <div className="cp-final-stat">
                <span className="cp-final-stat-label">Time Spent:</span>
                <span className="cp-final-stat-value">{Math.floor(finalStats.statistics.duration_seconds / 60)}m {finalStats.statistics.duration_seconds % 60}s</span>
              </div>
              <div className="cp-final-stat">
                <span className="cp-final-stat-label">Code Runs:</span>
                <span className="cp-final-stat-value">{finalStats.statistics.executions}</span>
              </div>
              <div className="cp-final-stat">
                <span className="cp-final-stat-label">Hints Used:</span>
                <span className="cp-final-stat-value">{finalStats.statistics.hints_used}</span>
              </div>
            </div>

            {finalStats.achievements && finalStats.achievements.length > 0 && (
              <div className="cp-achievements">
                <h3>🎖️ Achievements Unlocked</h3>
                {finalStats.achievements.map((achievement, idx) => (
                  <div key={idx} className="cp-achievement">
                    <div className="cp-achievement-name">{achievement.name}</div>
                    <div className="cp-achievement-desc">{achievement.description}</div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        <button onClick={handleNewChallenge} className="cp-new-challenge-button">
          Try Another Challenge
        </button>
      </div>
    </div>
  );

  return (
    <div className="code-playground-container">
      <div className="cp-header">
        <h1 className="cp-title">
          <span className="cp-title-icon">👨‍💻</span>
          Code Playground for Kids
        </h1>
        <p className="cp-subtitle">Learn programming through fun, interactive challenges!</p>
      </div>

      <div className="cp-tabs">
        <button 
          className={`cp-tab ${activeTab === 'turtle' ? 'cp-tab-active' : ''}`}
          onClick={() => setActiveTab('turtle')}
        >
          <span className="cp-tab-icon">🐢</span>
          Turtle Graphics
        </button>
        <button 
          className={`cp-tab ${activeTab === 'blocks' ? 'cp-tab-active' : ''}`}
          onClick={() => setActiveTab('blocks')}
          disabled
        >
          <span className="cp-tab-icon">🧩</span>
          Block Coding (Coming Soon)
        </button>
      </div>

      <div className="cp-content">
        {activeTab === 'turtle' && (
          <>
            {gameState === 'select' && renderChallengeSelect()}
            {gameState === 'coding' && renderCodingScreen()}
            {gameState === 'completed' && renderCompletedScreen()}
          </>
        )}
        {activeTab === 'blocks' && (
          <div className="cp-coming-soon">
            <div className="cp-coming-soon-icon">🚧</div>
            <h2>Block-Based Coding Coming Soon!</h2>
            <p>Drag and drop blocks to create programs.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default CodePlayground;
