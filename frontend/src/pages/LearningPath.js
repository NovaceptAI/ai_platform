// frontend/src/pages/LearningPath.js
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./LearningPath.css";
import axiosInstance from "../utils/axiosInstance";

const learningPaths = [
  {
    id: "LP1",
    slug: "deep-reading-investigation",
    title: "Deep Reading & Investigation",
    icon: "🔬",
    description: "For comprehensive document analysis and understanding.",
    tools: [
      "Summarizer",
      "Segmenter",
      "Chronology",
      "Sentiment Analysis",
      "Topic Modelling",
      "Timeline Explorer",
    ],
    estimatedTime: "30–45 min",
  },
  {
    id: "LP2",
    slug: "timeline-path",
    title: "Timeline Path",
    icon: "📅",
    description: "Master chronological analysis and historical understanding.",
    tools: [
      "Timeline Explorer",
      "Chronology",
      "Evidence Extractor",
      "Document Analysis",
    ],
    estimatedTime: "25–35 min",
  },
  {
    id: "LP3",
    slug: "codecraft-systems-thinking",
    title: "CodeCraft & Systems Thinking",
    icon: "💻",
    description: "Learn programming concepts and computational thinking.",
    tools: [
      "Code Playground",
      "STEM Challenge",
      "Math Visualizer",
      "Science Lab",
    ],
    estimatedTime: "40–60 min",
  },
  {
    id: "LP4",
    slug: "stem-fundamentals",
    title: "STEM Fundamentals",
    icon: "🔬",
    description: "Build foundational knowledge in science, technology, engineering, and math.",
    tools: [
      "Math Visualizer",
      "Science Lab",
      "STEM Challenge",
      "Visual Study Guide",
    ],
    estimatedTime: "35–50 min",
  },
  {
    id: "LP5",
    slug: "language-learning",
    title: "Language Learning",
    icon: "🌍",
    description: "Develop language skills through interactive exercises and practice.",
    tools: [
      "Language Lab",
      "Flashcards",
      "Reading Analysis",
      "Quiz Creator",
    ],
    estimatedTime: "30–40 min",
  },
  {
    id: "LP6",
    slug: "creative-arts-media",
    title: "Creative Arts & Media",
    icon: "🎨",
    description: "Express creativity through storytelling, art, and visual media.",
    tools: [
      "Story Visualizer",
      "Story to Comics",
      "AI Art Creator",
      "Interactive Comic Builder",
    ],
    estimatedTime: "35–50 min",
  },
];

export default function LearningPath() {
  const [recentActivity, setRecentActivity] = useState(null);

  useEffect(() => {
    // TODO: Implement backend endpoint /api/progress/recent-learning-path to fetch user's recent learning path
    // For now, keep recentActivity as null (feature disabled until backend is ready)
    
    // Commenting out the API call to avoid 400 errors in production
    // const fetchRecent = async () => {
    //   try {
    //     const res = await axiosInstance.get("/progress/recent-learning-path");
    //     if (res?.data) setRecentActivity(res.data);
    //   } catch (_) {
    //     setRecentActivity(null);
    //   }
    // };
    // fetchRecent();
  }, []);

  return (
    <div className="lp-page">
      <header className="lp-header">
        <h1>Learning Paths</h1>
        <p className="lp-subtitle">
          Pick a guided journey. Each path bundles tools with clear steps.
        </p>
      </header>

      {recentActivity && (
        <section className="lp-recent">
          <h3>Resume</h3>
          <div className="lp-recent-card">
            <div>
              <div className="lp-recent-title">{recentActivity.title}</div>
              <div className="lp-recent-progress">
                {recentActivity.progress || 0}% complete
              </div>
            </div>
            <Link
              className="lp-button primary"
              to={`/learning-path/${recentActivity.slug || "curious-explorer"}`}
            >
              Continue
            </Link>
          </div>
        </section>
      )}

      <div className="lp-grid">
        {learningPaths.map((lp) => (
          <div key={lp.id} className="lp-card">
            <div className="lp-card-head">
              <span className="lp-icon">{lp.icon}</span>
              <h2 className="lp-title">{lp.title}</h2>
            </div>
            <p className="lp-desc">{lp.description}</p>
            <div className="lp-tools-wrap">
              {lp.tools.map((tool, idx) => (
                <span key={idx} className="lp-tool-chip">
                  {tool}
                </span>
              ))}
            </div>
            <p className="lp-time">🕒 {lp.estimatedTime}</p>
            <div className="lp-actions">
              <Link className="lp-button" to={`/learning-path/${lp.slug}`}>
                View Path
              </Link>
              <Link className="lp-button primary" to={`/learning-path/${lp.slug}`}>
                Start / Resume
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}