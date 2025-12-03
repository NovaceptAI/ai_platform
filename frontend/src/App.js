// App.jsx
import React, { useEffect, useState, lazy, Suspense } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from "./components/Navbar";
import WebDock from './components/WebDock';
import config from './config';
import { getAuthToken, setAuthToken, clearAuth } from './utils/auth';
import './App.css';

// Loading component for Suspense fallback
const PageLoader = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    fontSize: '1.2rem',
    color: '#667eea'
  }}>
    Loading...
  </div>
);

// Pages - Lazy loaded
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Onboarding = lazy(() => import('./pages/Onboarding'));
const Vault = lazy(() => import('./pages/Vault'));
const LearningPath = lazy(() => import('./pages/LearningPath'));
const Scoolish = lazy(() => import('./pages/Scoolish'));

// Stages - Lazy loaded
const Create = lazy(() => import('./stages/Create/Create'));
const Discover = lazy(() => import('./stages/Discover/Discover'));
const Organize = lazy(() => import('./stages/Organize/Organize'));
const Collaborate = lazy(() => import('./stages/Collaborate/Collaborate'));
const Master = lazy(() => import('./stages/Master/Master'));

// Discover Tools - Lazy loaded
const Summarizer = lazy(() => import('./stages/Discover/Summarizer'));
const Segmenter = lazy(() => import('./stages/Discover/Segmenter'));
const TopicModeller = lazy(() => import('./stages/Discover/TopicModeller'));
const VisualStudyGuideMaker = lazy(() => import('./stages/Discover/VisualStudyGuideMaker'));
const MathProblemVisualizer = lazy(() => import('./stages/Master/MathProblemVisualizer'));
const TimelineExplorer = lazy(() => import('./stages/Discover/TimelineExplorer'));
const EvidenceExtractor = lazy(() => import('./stages/Discover/EvidenceExtractor'));
const ReadabilityAnalyzer = lazy(() => import('./stages/Discover/ReadabilityAnalyzer'));

// Master Tools - Lazy loaded
const QuizCreator = lazy(() => import('./stages/Master/QuizCreator'));
const HomeworkHelper = lazy(() => import('./stages/Master/HomeworkHelper'));
const LanguageLab = lazy(() => import('./stages/Master/LanguageLab'));
const CodePlayground = lazy(() => import('./stages/Master/CodePlayground'));
const Flashcards = lazy(() => import('./stages/Master/Flashcards'));
const StemChallenge = lazy(() => import('./stages/Master/StemChallenge'));
const EthicalAITutor = lazy(() => import('./stages/Master/EthicalAITutor'));
const VirtualScienceLab = lazy(() => import('./stages/Master/VirtualScienceLab'));

// Create Tools - Lazy loaded
const StoryVisualizer = lazy(() => import('./stages/Create/StoryVisualizer'));
const CreativeWritingPrompts = lazy(() => import('./stages/Create/CreativeWritingPrompts'));
const DataStoryBuilder = lazy(() => import('./stages/Create/DataStoryBuilder'));
const Story_to_comics_converterTool = lazy(() => import('./stages/Create/StoryToComics'));
const LearnByDrawing = lazy(() => import('./stages/Create/LearnByDrawing'));
const AI3DModelBuilder = lazy(() => import('./stages/Create/AI3DModelBuilder'));
const Interactive_comic_strip_builderTool = lazy(() => import('./stages/Create/interactive-comic-strip-builder'));
const Ai_presentation_builderTool = lazy(() => import('./stages/Create/AIPresentationBuilder'));

// Knowledge Data Tools - Lazy loaded
const HistoricalTimelineBuilder = lazy(() => import('./stages/KnowledgeData/HistoricalTimelineBuilder'));
const AIArtCreatorForKids = lazy(() => import('./stages/Create/AIArtCreatorForKids'));

// Collaborate Tools - Lazy loaded
const DigitalDebate = lazy(() => import('./stages/Collaborate/DigitalDebate'));
const CollaborativeMindMap = lazy(() => import('./stages/Collaborate/CollaborativeMindMap'));

// Organize Tools - Lazy loaded
const Clusters = lazy(() => import('./stages/Organize/Clusters'));
const Collections = lazy(() => import('./stages/Organize/Collections'));
const ConceptGraphs = lazy(() => import('./stages/Organize/ConceptGraphs'));
const SavedViews = lazy(() => import('./stages/Organize/SavedViews'));
const Tags = lazy(() => import('./stages/Organize/Tags'));

// AI Tools - Lazy loaded
const ChronoAI = lazy(() => import('./tools/ChronoAI'));
const DocumentAnalyzer = lazy(() => import('./tools/DocumentAnalyzer'));
const TreeView = lazy(() => import('./tools/TreeView'));

// Learning Paths - Lazy loaded
const CuriousExplorer = lazy(() => import('./pages/learningPaths/CuriousExplorer'));
const AcademicResearcher = lazy(() => import('./pages/learningPaths/AcademicResearcher'));
const StartupThinker = lazy(() => import('./pages/learningPaths/StartupThinker'));
const DeepReadingInvestigation = lazy(() => import('./pages/learningPaths/DeepReadingInvestigation'));
const TestLearningPath = lazy(() => import('./pages/learningPaths/TestLearningPath'));

// Project pages - Lazy loaded
const ProjectDashboard = lazy(() => import('./pages/ProjectDashboard'));
const ProjectWorkspace = lazy(() => import('./pages/ProjectWorkspace'));
const ResearchWorkspace = lazy(() => import('./pages/ResearchWorkspace'));

// Scoolish Flow - Lazy loaded
const ScoolishFlow = lazy(() => import('./pages/ScoolishFlow'));
const KnowledgeTree = lazy(() => import("./pages/KnowledgeTree"));

// ChatBot - Lazy loaded
const ChatBot = lazy(() => import('./components/ChatBot'));

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

      <Suspense fallback={<PageLoader />}>
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
          <Route path="/evidence_extractor" element={<PrivateRoute element={<EvidenceExtractor />} />} />
          <Route path="/readability_analyzer" element={<PrivateRoute element={<ReadabilityAnalyzer />} />} />
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
          <Route path="/virtual_science_lab" element={<PrivateRoute element={<VirtualScienceLab />} />} />

          {/* Create Tools */}
          <Route path="/story_visualizer" element={<PrivateRoute element={<StoryVisualizer />} />} />
          <Route path="/creative_writing_prompts" element={<PrivateRoute element={<CreativeWritingPrompts />} />} />
          <Route path="/data_story_builder" element={<PrivateRoute element={<DataStoryBuilder />} />} />
          <Route path="/learn_by_drawing" element={<PrivateRoute element={<LearnByDrawing />} />} />
          <Route path="/three_d_model_builder" element={<PrivateRoute element={<AI3DModelBuilder />} />} />
          <Route path="/interactive_comic_strip_builder" element={<PrivateRoute element={<Interactive_comic_strip_builderTool />} />} />
          <Route path="/ai_presentation_builder" element={<PrivateRoute element={<Ai_presentation_builderTool />} />} />
          <Route path="/ai_art_creator_for_kids" element={<PrivateRoute element={<AIArtCreatorForKids />} />} />
          <Route path="/story_to_comics" element={<PrivateRoute element={<Story_to_comics_converterTool />} />} />

          {/* Knowledge Data Tools */}
          <Route path="/historical_timeline_builder" element={<PrivateRoute element={<HistoricalTimelineBuilder />} />} />

          {/* Organize Tools */}
          <Route path="/clusters" element={<PrivateRoute element={<Clusters />} />} />
          <Route path="/collections" element={<PrivateRoute element={<Collections />} />} />
          <Route path="/concept_graphs" element={<PrivateRoute element={<ConceptGraphs />} />} />
          <Route path="/saved_views" element={<PrivateRoute element={<SavedViews />} />} />
          <Route path="/tags_routes" element={<PrivateRoute element={<Tags />} />} />

          {/* Collaborate Tools */}
          <Route path="/digital_debate" element={<PrivateRoute element={<DigitalDebate />} />} />
          <Route path="/collaborative_mind_mapping" element={<PrivateRoute element={<CollaborativeMindMap />} />} />

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

          {/* Research Workspace route */}
          <Route path="/research/:id" element={<PrivateRoute element={<ResearchWorkspace />} />} />

          <Route path="/scoolish-flow" element={<PrivateRoute element={<ScoolishFlow />} />} />
          <Route path="/knowledge-graph" element={<KnowledgeTree />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
        </Routes>
      </Suspense>

      {/* Global ChatBot - Lazy loaded */}
      {!(pathname.endsWith('/login') || pathname.endsWith('/signup') || pathname.includes('/onboarding')) && (
        <Suspense fallback={null}>
          <ChatBot />
        </Suspense>
      )}

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
