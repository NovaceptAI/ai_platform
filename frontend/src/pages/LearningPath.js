// frontend/src/pages/LearningPath.js
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./LearningPath.css";
import axiosInstance from "../utils/axiosInstance";

const learningPaths = [
  {
    id: "LP1",
    slug: "curious-explorer",
    title: "Curious Explorer",
    icon: "🔍",
    description: "For first-time users, students, and casual learners.",
    tools: [
      "Summarizer",
      "Learn by Drawing",
      "Homework Helper",
      "Quiz Creator",
      "Comics Converter",
    ],
    estimatedTime: "15–20 min",
  },
  {
    id: "LP2",
    slug: "academic-researcher",
    title: "Academic Researcher",
    icon: "📚",
    description: "For graduate students and researchers.",
    tools: [
      "Summarizer",
      "Entity Resolution",
      "Topic Modelling",
      "Clustering",
      "Chronology",
      "Similarity",
      "Mind Mapping",
    ],
    estimatedTime: "30–40 min",
  },
  {
    id: "LP3",
    slug: "startup-thinker",
    title: "Startup Thinker",
    icon: "🚀",
    description: "For entrepreneurs and innovators.",
    tools: [
      "Idea Generator",
      "Pitch Deck Builder",
      "Competitor Analyzer",
      "Market Trends",
      "Business Model Canvas",
    ],
    estimatedTime: "20–30 min",
  },
];

export default function LearningPath() {
  const [recentActivity, setRecentActivity] = useState(null);

  useEffect(() => {
    // Optional: try to fetch user's recent learning-path progress (stubbed)
    const fetchRecent = async () => {
      try {
        const res = await axiosInstance.get("/progress/recent-learning-path");
        if (res?.data) setRecentActivity(res.data);
      } catch (_) {
        // ignore — keep null if backend not available
        setRecentActivity(null);
      }
    };
    fetchRecent();
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