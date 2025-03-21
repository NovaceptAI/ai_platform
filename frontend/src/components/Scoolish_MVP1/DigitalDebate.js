import React, { useState } from 'react';
import './DigitalDebate.css';
import config from '../../config.js'; // Adjust the import path as needed

function DigitalDebate() {
    const [topic, setTopic] = useState('');
    const [debate, setDebate] = useState(null);
    const [forStudentScore, setForStudentScore] = useState('');
    const [againstStudentScore, setAgainstStudentScore] = useState('');
    const [scoreResult, setScoreResult] = useState(null);
    const [error, setError] = useState('');

    const handleTopicChange = (e) => {
        setTopic(e.target.value);
    };

    const handleForStudentScoreChange = (e) => {
        setForStudentScore(e.target.value);
    };

    const handleAgainstStudentScoreChange = (e) => {
        setAgainstStudentScore(e.target.value);
    };

    const handleCreateDebate = async (e) => {
        e.preventDefault();
        setError('');
        setDebate(null);

        try {
            const response = await fetch(`${config.API_BASE_URL}/digital_debate/create_debate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic }),
            });

            const data = await response.json();
            if (response.ok) {
                setDebate(data);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while creating the debate.');
        }
    };

    const handleScoreDebate = async (e) => {
        e.preventDefault();
        setError('');
        setScoreResult(null);

        try {
            const response = await fetch(`${config.API_BASE_URL}/digital_debate/score_debate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ for_student_score: forStudentScore, against_student_score: againstStudentScore }),
            });

            const data = await response.json();
            if (response.ok) {
                setScoreResult(data);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('An error occurred while scoring the debate.');
        }
    };

    return (
        <div className="digital-debate">
            <h1>Digital Debate</h1>
            <form onSubmit={handleCreateDebate}>
                <input
                    type="text"
                    value={topic}
                    onChange={handleTopicChange}
                    placeholder="Enter debate topic"
                />
                <button type="submit">Create Debate</button>
            </form>
            {error && <p className="error">{error}</p>}
            {debate && (
                <div className="debate">
                    <h2>Debate on: {debate.topic}</h2>
                    <p><strong>For:</strong> {debate.for_arguments}</p>
                    <p><strong>Against:</strong> {debate.against_arguments}</p>
                </div>
            )}
            {debate && (
                <form onSubmit={handleScoreDebate}>
                    <input
                        type="number"
                        value={forStudentScore}
                        onChange={handleForStudentScoreChange}
                        placeholder="For Student Score"
                        min="0"
                        max="100"
                    />
                    <input
                        type="number"
                        value={againstStudentScore}
                        onChange={handleAgainstStudentScoreChange}
                        placeholder="Against Student Score"
                        min="0"
                        max="100"
                    />
                    <button type="submit">Score Debate</button>
                </form>
            )}
            {scoreResult && (
                <div className="score-result">
                    <h2>Debate Result</h2>
                    <p><strong>For Student Score:</strong> {scoreResult.for_student_score}</p>
                    <p><strong>Against Student Score:</strong> {scoreResult.against_student_score}</p>
                    <p><strong>Result:</strong> {scoreResult.result}</p>
                </div>
            )}
        </div>
    );
}

export default DigitalDebate;