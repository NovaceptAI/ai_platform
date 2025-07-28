import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';

// Pages Import 
import HomePage from './pages/HomePage';
import Login from './pages/Login'; // Import the Login component

// Stages Import
import Create from './stages/Create/Create';
import Discover from './stages/Discover/Discover';
import Organize from './stages/Organize/Organize';
import Collaborate from './stages/Collaborate/Collaborate';
import Master from './stages/Master/Master';
import Scoolish from './pages/Scoolish'; // Import the StagesHome component

// CSS Import
import './App.css';

// Discover Tools Import
import Summarizer from './stages/Discover/Summarizer';
import Segmenter from './stages/Discover/Segmenter';
import TopicModeller from './stages/Discover/TopicModeller';
import VisualStudyGuideMaker from './stages/Discover/VisualStudyGuideMaker';
import MathProblemVisualizer from './stages/Discover/MathProblemVisualizer';
import TimelineExplorer from './stages/Discover/TimelineExplorer';

// Organize Tools Import


// Master Tools Import
import QuizCreator from './stages/Master/QuizCreator';
import HomeworkHelper from './stages/Master/HomeworkHelper'; // Import Homework Helper

// Create Tools Import
import StoryVisualizer from './stages/Create/StoryVisualizer';

// Collaborate Tools Import
import DigitalDebate from './stages/Collaborate/DigitalDebate';

// AI Tools Import
import ChronoAI from './AI_Tools/ChronoAI';
import DocumentAnalyzer from './AI_Tools/DocumentAnalyzer';
import TreeView from './AI_Tools/TreeView';



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
        <>
    <Routes>
        {/* Pages Routes */}
        <Route path="/login" element={<Login onLogin={handleLogin} />} />
        <Route path="/" element={<PrivateRoute element={<HomePage />} />} />
        
        {/* Discover Tools Routes */}
        <Route path="/summarizer" element={<PrivateRoute element={<Summarizer />} />} />
        <Route path="/segmenter" element={<PrivateRoute element={<Segmenter />} />} />
        <Route path="/topic_modeller" element={<PrivateRoute element={<TopicModeller />} />} />               
        <Route path="/visual_study_guide_maker" element={<PrivateRoute element={<VisualStudyGuideMaker />} />} />
        <Route path="/math_problem_visualizer" element={<PrivateRoute element={<MathProblemVisualizer />} />} />
        <Route path="/timeline_explorer" element={<PrivateRoute element={<TimelineExplorer />} />} />
        
        {/* Organize Tools Routes */}

        {/* Master Tools Routes */}
        <Route path="/quiz_creator" element={<PrivateRoute element={<QuizCreator />} />} />
        <Route path="/homework_helper" element={<PrivateRoute element={<HomeworkHelper />} />} />
        
        {/* Create Tools Routes */}
        <Route path="/story_visualizer" element={<PrivateRoute element={<StoryVisualizer />} />} />

        {/* Collaborate Tools Routes */}
        <Route path="/digital_debate" element={<PrivateRoute element={<DigitalDebate />} />} />
        
        {/* AI Tools Routes */}
        <Route path="/chrono_ai" element={<PrivateRoute element={<ChronoAI />} />} />
        <Route path="/document_analyzer" element={<PrivateRoute element={<DocumentAnalyzer />} />} />
        <Route path="/tree-view" element={<PrivateRoute element={<TreeView />} />} />

        {/* Stages Home Route */}
        <Route path="/scoolish" element={<PrivateRoute element={<Scoolish />} />} />

        {/* Stages Routes */}
        <Route path="/create" element={<PrivateRoute element={<Create />} />} />
        <Route path="/discover" element={<PrivateRoute element={<Discover />} />} />
        <Route path="/organize" element={<PrivateRoute element={<Organize />} />} />
        <Route path="/collaborate" element={<PrivateRoute element={<Collaborate />} />} />
        <Route path="/master" element={<PrivateRoute element={<Master />} />} />
    </Routes>
    {token && (
        <div className="logout-container">
            <button onClick={handleLogout}>Logout</button>
        </div>
    )}
</>
    );
}

export default App;