import React, { useState } from 'react';
import './QuizScreen.css';

function QuizScreen({ quiz, onRestart }) {
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState([]);
    const [showResults, setShowResults] = useState(false);
    const [score, setScore] = useState(0);

    const handleAnswer = (answer) => {
        const newAnswers = [...answers, answer];
        setAnswers(newAnswers);

        if (answer === quiz[currentQuestionIndex].correct_answer) {
            setScore(score + 1);
        }

        if (currentQuestionIndex < quiz.length - 1) {
            setCurrentQuestionIndex(currentQuestionIndex + 1);
        } else {
            setShowResults(true);
        }
    };

    if (!quiz || !Array.isArray(quiz) || quiz.length === 0) {
        return <div>No quiz data available.</div>;
    }

    return (
        <div className="quiz-screen">
            {!showResults ? (
                <div>
                    <h2>Question {currentQuestionIndex + 1} of {quiz.length}</h2>
                    <p>{quiz[currentQuestionIndex].question}</p>
                    <div className="options">
                        {Object.entries(quiz[currentQuestionIndex].options).map(([key, value]) => (
                            <button key={key} onClick={() => handleAnswer(key)}>
                                {key}: {value}
                            </button>
                        ))}
                    </div>
                </div>
            ) : (
                <div>
                    <h2>Quiz Completed!</h2>
                    <p>Your score: {score} out of {quiz.length}</p>
                    <div className="results">
                        {quiz.map((q, index) => (
                            <div key={index} className={`result ${answers[index] === q.correct_answer ? 'correct' : 'incorrect'}`}>
                                <p>{q.question}</p>
                                <p>Your answer: {answers[index]}</p>
                                <p>Correct answer: {q.correct_answer}</p>
                            </div>
                        ))}
                    </div>
                    <button onClick={onRestart} className="restart-button">Restart Quiz</button>
                </div>
            )}
        </div>
    );
}

export default QuizScreen;