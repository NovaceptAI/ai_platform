import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import HomePage from './components/HomePage';
import QuizCreator from './components/QuizCreator';
import ChronoAI from './components/Scoolish_MVP1/ChronoAI';
import ScoolishMVP1 from './components/Scoolish_MVP1/ScoolishMVP1';
import Summarizer from './components/Scoolish_MVP1/Summarizer';
import Segmenter from './components/Scoolish_MVP1/Segmenter';
import TopicModeller from './components/Scoolish_MVP1/TopicModeller';
import StoryVisualizer from './components/Scoolish_MVP1/StoryVisualizer';
import DigitalDebate from './components/Scoolish_MVP1/DigitalDebate';
import DocumentAnalyzer from './components/Scoolish_MVP1/DocumentAnalyzer';
import TreeView from './components/Scoolish_MVP1/TreeView';
import Login from './components/Login'; // Import the Login component
import './App.css';

function App() {
    const [token, setToken] = useState(localStorage.getItem('token'));

    const handleLogin = (newToken) => {
        setToken(newToken);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        setToken(null);
    };

    const PrivateRoute = ({ element }) => {
        return token ? element : <Navigate to="/login" />;
    };

    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login onLogin={handleLogin} />} />
                <Route path="/" element={<PrivateRoute element={<HomePage />} />} />
                <Route path="/quiz_creator" element={<PrivateRoute element={<QuizCreator />} />} />
                <Route path="/chrono_ai" element={<PrivateRoute element={<ChronoAI />} />} />
                <Route path="/digital_debate" element={<PrivateRoute element={<DigitalDebate />} />} />
                <Route path="/scoolish_mvp_1" element={<PrivateRoute element={<ScoolishMVP1 />} />} />
                <Route path="/ai_summarizer" element={<PrivateRoute element={<Summarizer />} />} />
                <Route path="/ai_segmenter" element={<PrivateRoute element={<Segmenter />} />} />
                <Route path="/ai_topic_modelling" element={<PrivateRoute element={<TopicModeller />} />} />
                <Route path="/story_visualizer" element={<PrivateRoute element={<StoryVisualizer />} />} />
                <Route path="/document_analyzer" element={<PrivateRoute element={<DocumentAnalyzer />} />} />
                <Route path="/tree-view" element={<PrivateRoute element={<TreeView />} />} />
            </Routes>
            {token && (
                <div className="logout-container">
                    <button onClick={handleLogout}>Logout</button>
                </div>
            )}
        </Router>
    );
}

export default App;