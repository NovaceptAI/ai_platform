// frontend/src/pages/learningPaths/AcademicResearcher.js
import React from "react";
import LearningPathLanding from "./LearningPathLanding";

export default function AcademicResearcher() {
  return (
    <LearningPathLanding
      title="Academic Researcher"
      icon="📚"
      description="For graduate students and researchers."
      estimatedTime="30–40 min"
      tools={[
        "Summarizer",
        "Entity Resolution",
        "Topic Modelling",
        "Clustering",
        "Chronology",
        "Similarity",
        "Mind Mapping",
      ]}
    />
  );
}