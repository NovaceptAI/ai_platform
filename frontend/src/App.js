import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import HomePage from './components/HomePage';
import QuizCreator from './components/QuizCreator';
import ChronoAI from './components/Scoolish_MVP1/ChronoAI';
// import DigitalDebate from './components/DigitalDebate';
import ScoolishMVP1 from './components/Scoolish_MVP1/ScoolishMVP1';
import Summarizer from './components/Scoolish_MVP1/Summarizer';
import Segmenter from './components/Scoolish_MVP1/Segmenter';
import TopicModeller from './components/Scoolish_MVP1/TopicModeller';
import StoryVisualizer from './components/Scoolish_MVP1/StoryVisualizer';
import DigitalDebate from './components/Scoolish_MVP1/DigitalDebate';
import DocumentAnalyzer from './components/Scoolish_MVP1/DocumentAnalyzer';
import TreeView from './components/Scoolish_MVP1/TreeView';
import './App.css';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/quiz_creator" element={<QuizCreator />} />
                <Route path="/chrono_ai" element={<ChronoAI />} />
                <Route path="/digital_debate" element={<DigitalDebate />} />
                <Route path="/scoolish_mvp_1" element={<ScoolishMVP1 />} />
                <Route path="/ai_summarizer" element={<Summarizer />} />
                <Route path="/ai_segmenter" element={<Segmenter />} />
                <Route path="/ai_topic_modelling" element={<TopicModeller />} />
                <Route path="/story_visualizer" element={<StoryVisualizer />} />
                <Route path="/document_analyzer" element={<DocumentAnalyzer />} />
                <Route path="/tree-view" component={TreeView} />
                {/* Add routes for other tools here */}
            </Routes>
        </Router>
    );
}

export default App;