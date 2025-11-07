// App.jsx
import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from "./components/Navbar";
import WebDock from './components/WebDock';
import config from './config';
import { getAuthToken, setAuthToken, clearAuth } from './utils/auth';

// Pages
// import HomePage from './pages/HomePage';
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
import MathProblemVisualizer from './stages/Master/MathProblemVisualizer';
import TimelineExplorer from './stages/Discover/TimelineExplorer';

// Master Tools
import QuizCreator from './stages/Master/QuizCreator';
import HomeworkHelper from './stages/Master/HomeworkHelper';
import LanguageLab from './stages/Master/LanguageLab';
import CodePlayground from './stages/Master/CodePlayground';
import Flashcards from './stages/Master/Flashcards';
import StemChallenge from './stages/Master/StemChallenge';
import EthicalAITutor from './stages/Master/EthicalAITutor';

// Create Tools
import StoryVisualizer from './stages/Create/StoryVisualizer';
import CreativeWritingPrompts from './stages/Create/CreativeWritingPrompts';
import Data_story_builderTool from './stages/Create/data-story-builder';
import Story_to_comics_converterTool from './stages/Create/story-to-comics-converter';
import Learn_by_drawingTool from './stages/Create/learn-by-drawing';
import Three_d_model_builderTool from './stages/Create/three-d-model-builder';
import Interactive_comic_strip_builderTool from './stages/Create/interactive-comic-strip-builder';
import Ai_presentation_builderTool from './stages/Create/ai-presentation-builder';
import Ai_art_creator_for_kidsTool from './stages/Create/ai-art-creator-for-kids';

// Collaborate Tools
import DigitalDebate from './stages/Collaborate/DigitalDebate';

// Organize Tools
import Clusters from './stages/Organize/Clusters';
import Collections from './stages/Organize/Collections';
import ConceptGraphs from './stages/Organize/ConceptGraphs';
import SavedViews from './stages/Organize/SavedViews';
import Tags from './stages/Organize/Tags';

// AI Tools
import ChronoAI from './tools/ChronoAI';
import DocumentAnalyzer from './tools/DocumentAnalyzer';
import TreeView from './tools/TreeView';

// Learning Paths
import CuriousExplorer from './pages/learningPaths/CuriousExplorer';
import AcademicResearcher from './pages/learningPaths/AcademicResearcher';
import StartupThinker from './pages/learningPaths/StartupThinker';
import DeepReadingInvestigation from './pages/learningPaths/DeepReadingInvestigation';
import TestLearningPath from './pages/learningPaths/TestLearningPath';

import ProjectDashboard from './pages/ProjectDashboard';
import ProjectWorkspace from './pages/ProjectWorkspace';

import './App.css';
import ChatBot from './components/ChatBot';

// Scoolish Flow
import ScoolishFlow from './pages/ScoolishFlow';
import KnowledgeTree from "./pages/KnowledgeTree";

function AppRoutes({ token, onLogin, onLogout }) {
  const { pathname, search } = useLocation();
  const showNavbar = token && pathname !== '/login';
  const [dockOpen, setDockOpen] = useState(false);
  const location = useLocation();   // ✅ React Router hook
  const [onboardingStatus, setOnboardingStatus] = useState(null);
  const hideNavbarOn = ["/login", "/signup"]; // pages without navbar
  const isOnboarding = location.pathname.endsWith("/onboarding") || location.pathname.includes("/onboarding");
  const shouldShowNavbar = !hideNavbarOn.includes(location.pathname) && !isOnboarding;
  
  console.log('🔍 AppRoutes Debug:', {
    pathname,
    hasToken: !!token,
    onboardingStatus,
    search
  });
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
    console.log('PrivateRoute Debug:', {
      pathname,
      hasToken: !!token,
      onboardingStatus,
      componentName: element?.type?.name || element?.type?.displayName || 'Unknown'
    });
    
    if (!token) {
      console.log('❌ No token, redirecting to login');
      return <Navigate to="/login" replace />;
    }
    if (onboardingStatus === 'pending' && !pathname.endsWith('/onboarding')) {
      console.log('❌ Onboarding pending, redirecting to onboarding');
      return <Navigate to="/onboarding" replace />;
    }
    console.log('✅ PrivateRoute: Rendering component');
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
        <Route path="/" element={<PrivateRoute element={<Dashboard />} />} />
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
        <Route path="/language_lab" element={<PrivateRoute element={<LanguageLab />} />} />
        <Route path="/code_playground" element={<PrivateRoute element={<CodePlayground />} />} />
        <Route path="/flashcard_creator" element={<PrivateRoute element={<Flashcards />} />} />
        <Route path="/stem_challenge" element={<PrivateRoute element={<StemChallenge />} />} />
        <Route path="/ethical_ai_tutor" element={<PrivateRoute element={<EthicalAITutor />} />} />

        {/* Create Tools */}
        <Route path="/story_visualizer" element={<PrivateRoute element={<StoryVisualizer />} />} />
        <Route path="/creative_writing_prompts" element={<PrivateRoute element={<CreativeWritingPrompts />} />} />
        <Route path="/data_story_builder" element={<PrivateRoute element={<Data_story_builderTool />} />} />
        <Route path="/learn_by_drawing" element={<PrivateRoute element={<Learn_by_drawingTool />} />} />
        <Route path="/three_d_model_builder" element={<PrivateRoute element={<Three_d_model_builderTool />} />} />
        <Route path="/interactive_comic_strip_builder" element={<PrivateRoute element={<Interactive_comic_strip_builderTool />} />} />
        <Route path="/ai_presentation_builder" element={<PrivateRoute element={<Ai_presentation_builderTool />} />} />
        <Route path="/ai_art_creator_for_kids" element={<PrivateRoute element={<Ai_art_creator_for_kidsTool />} />} />
        <Route path="/story_to_comics" element={<PrivateRoute element={<Story_to_comics_converterTool />} />} />

        {/* Organize Tools */}
        <Route path="/clusters" element={<PrivateRoute element={<Clusters />} />} />
        <Route path="/collections" element={<PrivateRoute element={<Collections />} />} />
        <Route path="/concept_graphs" element={<PrivateRoute element={<ConceptGraphs />} />} />
        <Route path="/saved_views" element={<PrivateRoute element={<SavedViews />} />} />
        <Route path="/tags_routes" element={<PrivateRoute element={<Tags />} />} />

        {/* Collaborate Tools */}
        <Route path="/digital_debate" element={<PrivateRoute element={<DigitalDebate />} />} />

        {/* Learning Paths - moved up for better matching */}
        <Route path="/learning-path/curious-explorer" element={<PrivateRoute element={<CuriousExplorer />} />} />
        <Route path="/learning-path/academic-researcher" element={<PrivateRoute element={<AcademicResearcher />} />} />
        <Route path="/learning-path/startup-thinker" element={<PrivateRoute element={<StartupThinker />} />} />
        <Route path="/learning-path/deep-reading-investigation" element={<PrivateRoute element={<DeepReadingInvestigation />} />} />
        <Route path="/learning-path/test" element={<PrivateRoute element={<TestLearningPath />} />} />

        {/* AI Tools */}
        <Route path="/chrono_ai" element={<PrivateRoute element={<ChronoAI />} />} />
        <Route path="/document_analyzer" element={<PrivateRoute element={<DocumentAnalyzer />} />} />
        <Route path="/tree-view" element={<PrivateRoute element={<TreeView />} />} />

        <Route path="/project/new" element={<PrivateRoute element={<ProjectDashboard />} />} />
        <Route path="/project/:id/edit" element={<PrivateRoute element={<ProjectDashboard />} />} />
        {/* New route for the workspace */}
        <Route path="/project/:id/workspace" element={<PrivateRoute element={<ProjectWorkspace />} />} />

        <Route path="/scoolish-flow" element={<PrivateRoute element={<ScoolishFlow />} />} />
        <Route path="/knowledge-graph" element={<KnowledgeTree />} />

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