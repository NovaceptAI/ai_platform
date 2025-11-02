import React, { useState, useEffect } from "react";

export default function LearningPathLanding() {
  const [step, setStep] = useState(1);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);

  // Simulate progress
  useEffect(() => {
    if (step === 2 && progress < 100) {
      const timer = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(timer);
            setTimeout(() => setStep(3), 1000);
            return 100;
          }
          return prev + 20;
        });
      }, 800);
      return () => clearInterval(timer);
    }
  }, [step, progress]);

  // Mock results after process completes
  useEffect(() => {
    if (step === 3) {
      setResults({
        Summarizer: [
          { page: 1, summary: "AI is transforming education with personalization." },
          { page: 2, summary: "Students benefit from adaptive learning paths." },
          { page: 3, summary: "Teachers use AI tools for efficiency." }
        ],
        Segmenter: ["Intro", "Methods", "Results", "Conclusion"],
        TimelineExplorer: [
          { year: 2010, event: "AI enters classrooms" },
          { year: 2020, event: "AI widely adopted in education" }
        ]
      });
    }
  }, [step]);

  return (
    <div className="stage-wrap">
      <h1 className="text-2xl font-bold mb-4">Learning Path Hero</h1>

      {step === 1 && (
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-3">Upload File</h2>
          <input type="file" className="mb-4" />
          <button
            onClick={() => setStep(2)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg"
          >
            Start Process
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-3">Processing...</h2>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className="bg-indigo-600 h-4 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="mt-2 text-sm text-gray-600">{progress}% completed</p>
        </div>
      )}

      {step === 3 && results && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-semibold mb-3">Summarizer Output</h2>
            <table className="min-w-full border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-3 py-2 border">Page</th>
                  <th className="px-3 py-2 border">Summary</th>
                </tr>
              </thead>
              <tbody>
                {results.Summarizer.map((row, idx) => (
                  <tr key={idx}>
                    <td className="border px-3 py-2">{row.page}</td>
                    <td className="border px-3 py-2">{row.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-semibold mb-3">Segmenter Output</h2>
            <ul className="list-disc pl-5 space-y-1">
              {results.Segmenter.map((seg, idx) => (
                <li key={idx}>{seg}</li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-semibold mb-3">Timeline Explorer Output</h2>
            <ul className="space-y-1">
              {results.TimelineExplorer.map((event, idx) => (
                <li key={idx}>
                  <strong>{event.year}:</strong> {event.event}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}