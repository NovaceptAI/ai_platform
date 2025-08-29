// frontend/src/pages/learningPaths/CuriousExplorer.js
import React from "react";
import LearningPathLanding from "./LearningPathLanding";

export default function CuriousExplorer() {
  return (
    <LearningPathLanding
      title="Curious Explorer"
      icon="🔍"
      description="For first-time users, students, and casual learners."
      estimatedTime="15–20 min"
      tools={[
        "Summarizer",
        "Learn by Drawing",
        "Homework Helper",
        "Quiz Creator",
        "Comics Converter",
      ]}
    />
  );
}