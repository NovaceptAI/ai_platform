import React, { useState } from 'react';
import './QuizScreen.css'; // Ensure this file contains the necessary styles

function QuizScreen({ quiz, onRestart }) {
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState([]);
    const [showResults, setShowResults] = useState(false);
    const [score, setScore] = useState(0);

    const handleAnswer = (answer) => {
        console.log("Answer selected:", answer);
        console.log("Current question:", quiz[currentQuestionIndex]);

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

    if (!quiz) {
        return <div>Loading quiz...</div>;
    }

    if (!Array.isArray(quiz) || quiz.length === 0) {
        console.log("Quiz data:", quiz); // Debugging
        return <div>No quiz data available.</div>;
    }

    if (currentQuestionIndex >= quiz.length) {
        return <div>Invalid question index</div>;
    }

    return (
        <div className="quiz-screen">
            {!showResults ? (
                <div>
                    <h2>Question {currentQuestionIndex + 1} of {quiz.length}</h2>
                    {/* Ensure the question text wraps properly */}
                    <p className="question-text">
                        {quiz[currentQuestionIndex]?.question || "Question not available"}
                    </p>
                    <div className="options">
                        {quiz[currentQuestionIndex]?.options
                            ? Object.entries(quiz[currentQuestionIndex].options).map(([key, value]) => (
                                <button key={key} onClick={() => handleAnswer(key)}>
                                    {key}: {value}
                                </button>
                            ))
                            : <p>Options not available</p>
                        }
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