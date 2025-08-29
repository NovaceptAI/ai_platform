// frontend/src/pages/learningPaths/StartupThinker.js
import React from "react";
import LearningPathLanding from "./LearningPathLanding";

export default function StartupThinker() {
  return (
    <LearningPathLanding
      title="Startup Thinker"
      icon="🚀"
      description="For entrepreneurs and innovators."
      estimatedTime="20–30 min"
      tools={[
        "Idea Generator",
        "Pitch Deck Builder",
        "Competitor Analyzer",
        "Market Trends",
        "Business Model Canvas",
      ]}
    />
  );
}