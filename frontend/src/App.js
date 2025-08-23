// App.jsx
import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from "./components/Navbar";
import WebDock from './components/WebDock';
import config from './config';
import { getAuthToken, setAuthToken, clearAuth } from './utils/auth';

// Pages
import HomePage from './pages/HomePage';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Onboarding from './pages/Onboarding';
import Vault from './pages/Vault';
import LearningPath from './pages/LearningPath';
import Scoolish from './pages/Scoolish';

// Stages
import Create from './stages/Create/Create';
import Discover from './stages/Discover/Discover';
import Organize from './stages/Organize/Organize';
import Collaborate from './stages/Collaborate/Collaborate';
import Master from './stages/Master/Master';

// Discover Tools
import Summarizer from './stages/Discover/Summarizer';
import Segmenter from './stages/Discover/Segmenter';
import TopicModeller from './stages/Discover/TopicModeller';
import VisualStudyGuideMaker from './stages/Discover/VisualStudyGuideMaker';
import MathProblemVisualizer from './stages/Discover/MathProblemVisualizer';
import TimelineExplorer from './stages/Discover/TimelineExplorer';

// Master Tools
import QuizCreator from './stages/Master/QuizCreator';
import HomeworkHelper from './stages/Master/HomeworkHelper';

// Create Tools
import StoryVisualizer from './stages/Create/StoryVisualizer';
import CreativeWritingPrompts from './stages/Create/CreativeWritingPrompts';

// Collaborate Tools
import DigitalDebate from './stages/Collaborate/DigitalDebate';

// AI Tools
import ChronoAI from './AI_Tools/ChronoAI';
import DocumentAnalyzer from './AI_Tools/DocumentAnalyzer';
import TreeView from './AI_Tools/TreeView';

import './App.css';
import ChatBot from './components/ChatBot';

function AppRoutes({ token, onLogin, onLogout }) {
  const { pathname, search } = useLocation();
  const showNavbar = token && pathname !== '/login';
  const [dockOpen, setDockOpen] = useState(false);
  const location = useLocation();   // ✅ React Router hook
  const [onboardingStatus, setOnboardingStatus] = useState(null);
  const hideNavbarOn = ["/login", "/signup"]; // pages without navbar
  const isOnboarding = location.pathname.endsWith("/onboarding") || location.pathname.includes("/onboarding");
  const shouldShowNavbar = !hideNavbarOn.includes(location.pathname) && !isOnboarding;
  // Hotkey Ctrl+Shift+K
  React.useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'K' || e.key === 'k')) {
        e.preventDefault();
        setDockOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Global capture of ?token= before any guards/routes
  useEffect(() => {
    const params = new URLSearchParams(search);
    const tokenParam = params.get('token');
    if (tokenParam) {
      setAuthToken(tokenParam);
      onLogin(tokenParam);
      params.delete('token');
      const newSearch = params.toString();
      const newUrl = pathname + (newSearch ? `?${newSearch}` : '');
      window.history.replaceState({}, '', newUrl);
    }
  }, [pathname, search, onLogin]);

  useEffect(() => {
    const fetchState = async () => {
      if (!token) { setOnboardingStatus(null); return; }
      try {
        const res = await fetch(`${config.API_BASE_URL}/onboarding/state`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) { setOnboardingStatus(null); return; }
        const data = await res.json();
        setOnboardingStatus(data.onboarding_status);
      } catch (_) {
        setOnboardingStatus(null);
      }
    };
    fetchState();
  }, [token, pathname]);

  const PrivateRoute = ({ element }) => {
    if (!token) return <Navigate to="/login" replace />;
    if (onboardingStatus === 'pending' && !pathname.endsWith('/onboarding')) {
      return <Navigate to="/onboarding" replace />;
    }
    return element;
  };

  return (
    <>
      {shouldShowNavbar && (
        <Navbar
          onLogout={onLogout}
          onToggleDock={() => setDockOpen((v) => !v)}
        />
      )}

      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login onLogin={(t) => {
          localStorage.setItem('token', t);
          onLogin(t);
        }} />} />

        {/* Protected */}
        <Route path="/" element={<PrivateRoute element={<HomePage />} />} />
        <Route path="/dashboard" element={<PrivateRoute element={<Dashboard />} />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/vault" element={<PrivateRoute element={<Vault />} />} />
        <Route path="/learning-path" element={<PrivateRoute element={<LearningPath />} />} />
        <Route path="/scoolish" element={<PrivateRoute element={<Scoolish />} />} />

        {/* Stages */}
        <Route path="/create" element={<PrivateRoute element={<Create />} />} />
        <Route path="/discover" element={<PrivateRoute element={<Discover />} />} />
        <Route path="/organize" element={<PrivateRoute element={<Organize />} />} />
        <Route path="/collaborate" element={<PrivateRoute element={<Collaborate />} />} />
        <Route path="/master" element={<PrivateRoute element={<Master />} />} />

        {/* Discover Tools */}
        <Route path="/summarizer" element={<PrivateRoute element={<Summarizer />} />} />
        <Route path="/segmenter" element={<PrivateRoute element={<Segmenter />} />} />
        <Route path="/topic_modeller" element={<PrivateRoute element={<TopicModeller />} />} />
        <Route path="/visual_study_guide_maker" element={<PrivateRoute element={<VisualStudyGuideMaker />} />} />
        <Route path="/math_problem_visualizer" element={<PrivateRoute element={<MathProblemVisualizer />} />} />
        <Route path="/timeline_explorer" element={<PrivateRoute element={<TimelineExplorer />} />} />

        {/* Master Tools */}
        <Route path="/quiz_creator" element={<PrivateRoute element={<QuizCreator />} />} />
        <Route path="/homework_helper" element={<PrivateRoute element={<HomeworkHelper />} />} />

        {/* Create Tools */}
        <Route path="/story_visualizer" element={<PrivateRoute element={<StoryVisualizer />} />} />
        <Route path="/creative_writing_prompts" element={<PrivateRoute element={<CreativeWritingPrompts />} />} />

        {/* Collaborate Tools */}
        <Route path="/digital_debate" element={<PrivateRoute element={<DigitalDebate />} />} />

        {/* AI Tools */}
        <Route path="/chrono_ai" element={<PrivateRoute element={<ChronoAI />} />} />
        <Route path="/document_analyzer" element={<PrivateRoute element={<DocumentAnalyzer />} />} />
        <Route path="/tree-view" element={<PrivateRoute element={<TreeView />} />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
      </Routes>
      {/* Global ChatBot */}
      {!(pathname.endsWith('/login') || pathname.endsWith('/signup') || pathname.includes('/onboarding')) && <ChatBot />}

      {token && !(pathname.endsWith('/login') || pathname.endsWith('/signup') || pathname.includes('/onboarding')) && (
        <WebDock isOpen={dockOpen} onClose={() => setDockOpen(false)} />
      )}
    </>
  );
}

export default function App() {
  const [token, setToken] = useState(getAuthToken());

  const handleLogin = (newToken) => {
    setAuthToken(newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    clearAuth();
    setToken(null);
  };

  return <AppRoutes token={token} onLogin={handleLogin} onLogout={handleLogout} />;
}