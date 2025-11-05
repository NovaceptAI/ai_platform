import React, { useState, useEffect, useRef } from 'react';
import './LanguageLab.css';
import axiosInstance from '../../utils/axiosInstance';

function LanguageLab() {
  const [activeTab, setActiveTab] = useState('word-builder');
  
  // Word Builder State
  const [gameState, setGameState] = useState('setup'); // 'setup', 'playing', 'finished'
  const [sessionId, setSessionId] = useState(null);
  const [difficulty, setDifficulty] = useState('medium');
  const [timeLimit, setTimeLimit] = useState(300);
  const [minWordLength, setMinWordLength] = useState(3);
  const [startingWord, setStartingWord] = useState('');
  const [currentWord, setCurrentWord] = useState('');
  const [inputWord, setInputWord] = useState('');
  const [wordChain, setWordChain] = useState([]);
  const [score, setScore] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(300);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [lastResult, setLastResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isGettingHint, setIsGettingHint] = useState(false);
  const [hintText, setHintText] = useState('');
  const [gameStats, setGameStats] = useState(null);
  const [error, setError] = useState('');
  
  const timerRef = useRef(null);
  const inputRef = useRef(null);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl/Cmd + H for hint
      if ((e.ctrlKey || e.metaKey) && e.key === 'h' && gameState === 'playing' && !isGettingHint) {
        e.preventDefault();
        handleGetHint();
      }
      // Ctrl/Cmd + Q to quit/end game
      if ((e.ctrlKey || e.metaKey) && e.key === 'q' && gameState === 'playing') {
        e.preventDefault();
        handleEndGame();
      }
      // Enter to start game (when on setup screen)
      if (e.key === 'Enter' && gameState === 'setup') {
        e.preventDefault();
        handleStartGame();
      }
      // Enter to play again (when on finished screen)
      if (e.key === 'Enter' && gameState === 'finished') {
        e.preventDefault();
        handlePlayAgain();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameState, isGettingHint]);

  // Timer effect
  useEffect(() => {
    if (gameState === 'playing' && timeRemaining > 0) {
      timerRef.current = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            handleEndGame();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [gameState, timeRemaining]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStartGame = async () => {
    try {
      setError('');
      
      const response = await axiosInstance.post('/master/language_lab/word-builder/start', {
        difficulty,
        time_limit: timeLimit,
        min_word_length: minWordLength
      });

      setSessionId(response.data.session_id);
      setStartingWord(response.data.starting_word);
      setCurrentWord(response.data.starting_word);
      setWordChain([response.data.starting_word]);
      setScore(0);
      setTimeRemaining(response.data.time_limit);
      setHintsUsed(0);
      setHintText('');
      setLastResult(null);
      setGameState('playing');
      
      // Focus input
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
      
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSubmitWord = async (e) => {
    e.preventDefault();
    
    if (!inputWord.trim()) return;
    
    try {
      setIsValidating(true);
      setError('');
      setHintText('');
      
      const response = await axiosInstance.post('/master/language_lab/word-builder/validate', {
        session_id: sessionId,
        previous_word: currentWord,
        new_word: inputWord.toLowerCase().trim(),
        chain: wordChain
      });

      setLastResult(response.data);
      
      if (response.data.valid) {
        setCurrentWord(inputWord.toLowerCase().trim());
        setWordChain([...wordChain, inputWord.toLowerCase().trim()]);
        setScore(response.data.points);
        setInputWord('');
      } else {
        // Keep input to allow correction
        setTimeout(() => {
          setLastResult(null);
        }, 3000);
      }
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsValidating(false);
    }
  };

  const handleGetHint = async () => {
    try {
      setIsGettingHint(true);
      setError('');
      
      const response = await axiosInstance.post('/master/language_lab/word-builder/hint', {
        session_id: sessionId,
        current_word: currentWord,
        used_words: wordChain,
        min_length: minWordLength
      });

      setHintText(response.data.hint);
      setHintsUsed(response.data.hints_used);
      
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setIsGettingHint(false);
    }
  };

  const handleEndGame = async () => {
    if (!sessionId) return;
    
    try {
      setError('');
      
      const response = await axiosInstance.post('/master/language_lab/word-builder/end', {
        session_id: sessionId
      });

      setGameStats(response.data);
      setGameState('finished');
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const handlePlayAgain = () => {
    setGameState('setup');
    setSessionId(null);
    setStartingWord('');
    setCurrentWord('');
    setInputWord('');
    setWordChain([]);
    setScore(0);
    setTimeRemaining(timeLimit);
    setHintsUsed(0);
    setLastResult(null);
    setHintText('');
    setGameStats(null);
    setError('');
  };

  const renderSetupScreen = () => (
    <div className="ll-setup-container">
      <div className="ll-setup-card">
        <div className="ll-game-icon">🎮</div>
        <h2>Word Builder: Morpho Quest</h2>
        <p className="ll-game-description">
          Build the longest word chain by changing one letter at a time! 
          Each word must be a valid dictionary word and differ by exactly one letter.
        </p>
        
        <div className="ll-setup-form">
          <div className="ll-form-group">
            <label>Difficulty</label>
            <div className="ll-radio-group">
              <label className="ll-radio-label">
                <input 
                  type="radio" 
                  name="difficulty" 
                  value="easy" 
                  checked={difficulty === 'easy'}
                  onChange={(e) => setDifficulty(e.target.value)}
                />
                <span>Easy</span>
              </label>
              <label className="ll-radio-label">
                <input 
                  type="radio" 
                  name="difficulty" 
                  value="medium" 
                  checked={difficulty === 'medium'}
                  onChange={(e) => setDifficulty(e.target.value)}
                />
                <span>Medium</span>
              </label>
              <label className="ll-radio-label">
                <input 
                  type="radio" 
                  name="difficulty" 
                  value="hard" 
                  checked={difficulty === 'hard'}
                  onChange={(e) => setDifficulty(e.target.value)}
                />
                <span>Hard</span>
              </label>
            </div>
          </div>

          <div className="ll-form-group">
            <label>Time Limit</label>
            <select 
              value={timeLimit} 
              onChange={(e) => setTimeLimit(parseInt(e.target.value))}
              className="ll-select"
            >
              <option value="60">1 minute</option>
              <option value="180">3 minutes</option>
              <option value="300">5 minutes</option>
              <option value="600">10 minutes</option>
              <option value="900">15 minutes</option>
            </select>
          </div>

          <div className="ll-form-group">
            <label>Minimum Word Length</label>
            <select 
              value={minWordLength} 
              onChange={(e) => setMinWordLength(parseInt(e.target.value))}
              className="ll-select"
            >
              <option value="2">2 letters</option>
              <option value="3">3 letters</option>
              <option value="4">4 letters</option>
              <option value="5">5 letters</option>
            </select>
          </div>

          {error && <div className="ll-error">{error}</div>}

          <button 
            className="ll-start-button"
            onClick={handleStartGame}
          >
            Start Game <span className="ll-shortcut-hint">(Press Enter)</span>
          </button>
        </div>

        <div className="ll-rules">
          <h3>Rules</h3>
          <ul>
            <li>Change exactly one letter at a time (substitute, add, or remove)</li>
            <li>Each word must be a valid English dictionary word</li>
            <li>No repeating words in the same game</li>
            <li>Hints are available but reduce your score</li>
            <li>Longer words and word chains earn bonus points</li>
          </ul>
          
          <h3>Keyboard Shortcuts</h3>
          <ul>
            <li><strong>Enter:</strong> Submit word / Start game / Play again</li>
            <li><strong>Ctrl/Cmd + H:</strong> Get hint</li>
            <li><strong>Ctrl/Cmd + Q:</strong> End game</li>
          </ul>
        </div>
      </div>
    </div>
  );

  const renderGameScreen = () => (
    <div className="ll-game-container">
      <div className="ll-game-header">
        <div className="ll-stat-box">
          <div className="ll-stat-label">Score</div>
          <div className="ll-stat-value">{score}</div>
        </div>
        <div className="ll-stat-box">
          <div className="ll-stat-label">Chain Length</div>
          <div className="ll-stat-value">{wordChain.length}</div>
        </div>
        <div className="ll-stat-box">
          <div className="ll-stat-label">Time</div>
          <div className={`ll-stat-value ${timeRemaining < 60 ? 'll-time-warning' : ''}`}>
            {formatTime(timeRemaining)}
          </div>
        </div>
        <div className="ll-stat-box">
          <div className="ll-stat-label">Hints Used</div>
          <div className="ll-stat-value">{hintsUsed}</div>
        </div>
      </div>

      <div className="ll-game-board">
        <div className="ll-word-chain-section">
          <h3>Word Chain</h3>
          <div className="ll-word-chain">
            {wordChain.map((word, index) => (
              <div key={index} className="ll-chain-word">
                <span className="ll-chain-number">{index + 1}</span>
                <span className="ll-chain-text">{word}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="ll-input-section">
          <div className="ll-current-word-display">
            <span className="ll-label">Current Word:</span>
            <span className="ll-current-word">{currentWord}</span>
          </div>

          <form onSubmit={handleSubmitWord} className="ll-word-form">
            <input
              ref={inputRef}
              type="text"
              value={inputWord}
              onChange={(e) => setInputWord(e.target.value)}
              placeholder="Enter next word..."
              className="ll-word-input"
              disabled={isValidating}
              autoFocus
            />
            <button 
              type="submit" 
              className="ll-submit-button"
              disabled={isValidating || !inputWord.trim()}
            >
              {isValidating ? 'Checking...' : 'Submit'}
            </button>
          </form>

          {lastResult && (
            <div className={`ll-result ${lastResult.valid ? 'll-result-valid' : 'll-result-invalid'}`}>
              {lastResult.valid ? (
                <>
                  <div className="ll-result-icon">✓</div>
                  <div className="ll-result-content">
                    <div className="ll-result-title">Valid Word!</div>
                    <div className="ll-result-points">+{lastResult.points_earned} points</div>
                    {lastResult.word_info && (
                      <div className="ll-word-info">
                        <div className="ll-word-meaning">{lastResult.word_info.definition}</div>
                        {lastResult.word_info.example && (
                          <div className="ll-word-example">
                            <strong>Example:</strong> {lastResult.word_info.example}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="ll-result-icon">✗</div>
                  <div className="ll-result-content">
                    <div className="ll-result-title">Invalid!</div>
                    <div className="ll-result-reason">{lastResult.reason}</div>
                  </div>
                </>
              )}
            </div>
          )}

          {hintText && (
            <div className="ll-hint-box">
              <div className="ll-hint-icon">💡</div>
              <div className="ll-hint-content">
                <div className="ll-hint-title">Hint (Score Penalty: -20%)</div>
                <div className="ll-hint-text">{hintText}</div>
              </div>
            </div>
          )}

          {error && <div className="ll-error">{error}</div>}

          <div className="ll-action-buttons">
            <button 
              onClick={handleGetHint}
              className="ll-hint-button"
              disabled={isGettingHint}
              title="Ctrl/Cmd + H"
            >
              {isGettingHint ? '🔄 Getting Hint...' : '💡 Get Hint (Ctrl+H)'}
            </button>
            <button 
              onClick={handleEndGame}
              className="ll-end-button"
              title="Ctrl/Cmd + Q"
            >
              End Game (Ctrl+Q)
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderFinishedScreen = () => (
    <div className="ll-finished-container">
      <div className="ll-finished-card">
        <div className="ll-trophy-icon">🏆</div>
        <h2>Game Over!</h2>
        
        {gameStats && (
          <>
            <div className="ll-final-score">
              <div className="ll-final-score-label">Final Score</div>
              <div className="ll-final-score-value">{gameStats.total_score}</div>
            </div>

            <div className="ll-stats-grid">
              <div className="ll-stat-item">
                <div className="ll-stat-item-label">Words Created</div>
                <div className="ll-stat-item-value">{gameStats.statistics.words_created}</div>
              </div>
              <div className="ll-stat-item">
                <div className="ll-stat-item-label">Longest Word</div>
                <div className="ll-stat-item-value">{gameStats.statistics.longest_word} ({gameStats.statistics.longest_word_length} letters)</div>
              </div>
              <div className="ll-stat-item">
                <div className="ll-stat-item-label">Average Length</div>
                <div className="ll-stat-item-value">{gameStats.statistics.average_word_length.toFixed(1)} letters</div>
              </div>
              <div className="ll-stat-item">
                <div className="ll-stat-item-label">Hints Used</div>
                <div className="ll-stat-item-value">{gameStats.statistics.hints_used}</div>
              </div>
              <div className="ll-stat-item">
                <div className="ll-stat-item-label">Time Taken</div>
                <div className="ll-stat-item-value">{Math.floor(gameStats.statistics.time_taken / 60)}m {gameStats.statistics.time_taken % 60}s</div>
              </div>
            </div>

            {gameStats.achievements && gameStats.achievements.length > 0 && (
              <div className="ll-achievements">
                <h3>🎖️ Achievements Unlocked</h3>
                <div className="ll-achievement-list">
                  {gameStats.achievements.map((achievement, index) => (
                    <div key={index} className="ll-achievement-item">
                      <div className="ll-achievement-name">{achievement.name}</div>
                      <div className="ll-achievement-desc">{achievement.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="ll-word-chain-final">
              <h3>Your Word Chain</h3>
              <div className="ll-chain-final-list">
                {wordChain.map((word, index) => (
                  <span key={index} className="ll-chain-final-word">
                    {word}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        <button 
          className="ll-play-again-button"
          onClick={handlePlayAgain}
        >
          Play Again <span className="ll-shortcut-hint">(Press Enter)</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="language-lab-container">
      <div className="ll-header">
        <h1 className="ll-title">
          <span className="ll-title-icon">🌍</span>
          Language Learning Lab
        </h1>
        <p className="ll-subtitle">Master languages through interactive games and challenges</p>
      </div>

      <div className="ll-tabs">
        <button 
          className={`ll-tab ${activeTab === 'word-builder' ? 'll-tab-active' : ''}`}
          onClick={() => setActiveTab('word-builder')}
        >
          <span className="ll-tab-icon">🎮</span>
          Word Builder
        </button>
        <button 
          className={`ll-tab ${activeTab === 'game2' ? 'll-tab-active' : ''}`}
          onClick={() => setActiveTab('game2')}
          disabled
        >
          <span className="ll-tab-icon">🎯</span>
          Game 2 (Coming Soon)
        </button>
      </div>

      <div className="ll-content">
        {activeTab === 'word-builder' && (
          <>
            {gameState === 'setup' && renderSetupScreen()}
            {gameState === 'playing' && renderGameScreen()}
            {gameState === 'finished' && renderFinishedScreen()}
          </>
        )}
        {activeTab === 'game2' && (
          <div className="ll-coming-soon">
            <div className="ll-coming-soon-icon">🚧</div>
            <h2>Coming Soon!</h2>
            <p>More exciting language games are on the way.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default LanguageLab;
