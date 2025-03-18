import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import HomePage from './components/HomePage';
import QuizCreator from './components/QuizCreator';
import ChronoAI from './components/ChronoAI';
import DigitalDebate from './components/DigitalDebate';
import './App.css';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/quiz_creator" element={<QuizCreator />} />
                <Route path="/chrono_ai" element={<ChronoAI />} />
                <Route path="/digital_debate" element={<DigitalDebate />} />
                {/* Add routes for other tools here */}
            </Routes>
        </Router>
    );
}

export default App;