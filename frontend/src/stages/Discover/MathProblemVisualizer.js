import React, { useState } from 'react';
import './MathProblemVisualizer.css'; // Add CSS for styling
import config from '../../config'; // Import API base URL from config

function MathProblemVisualizer() {
    const [problem, setProblem] = useState(''); // State to store the math problem
    const [solution, setSolution] = useState(null); // State to store the solution
    const [visualization, setVisualization] = useState(null); // State to store the visualization
    const [error, setError] = useState(null); // State to handle errors
    const [loading, setLoading] = useState(false); // State to handle loading

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null); // Clear any previous errors
        setSolution(null); // Clear any previous solution
        setVisualization(null); // Clear any previous visualization
        setLoading(true); // Set loading state

        try {
            const response = await fetch(`${config.API_BASE_URL}/math_problem_visualizer/visualize_math_problem`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ problem }),
            });

            const result = await response.json();
            if (response.ok) {
                setSolution(result.solution); // Store the solution
                setVisualization(result.visualization); // Store the visualization
            } else {
                setError(result.error || 'Failed to visualize the math problem.');
            }
        } catch (error) {
            console.error('Failed to fetch:', error);
            setError('An unexpected error occurred. Please try again.');
        } finally {
            setLoading(false); // Reset loading state
        }
    };

    const handleRestart = () => {
        setProblem('');
        setSolution(null);
        setVisualization(null);
        setError(null);
    };

    return (
        <div className="math-problem-visualizer">
            {!solution && !visualization ? (
                <div>
                    <h1>Math Problem Visualizer</h1>
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="problem">Enter a Math Problem:</label>
                        <textarea
                            id="problem"
                            value={problem}
                            onChange={(e) => setProblem(e.target.value)}
                            placeholder="Enter a math problem (e.g., x^2 + 5x + 6 = 0)"
                            required
                        />
                        <button type="submit" disabled={loading}>
                            {loading ? 'Visualizing...' : 'Visualize'}
                        </button>
                    </form>
                    {error && <p className="error">{error}</p>}
                </div>
            ) : (
                <div className="visualization-screen">
                    <h2>Solution</h2>
                    <ul>
                        {solution.map((step, index) => (
                            <li key={index}>{step}</li>
                        ))}
                    </ul>
                    <h2>Visualization</h2>
                    {visualization && (
                        <img
                            src={visualization}
                            alt="Math Problem Visualization"
                            className="visualization-image"
                        />
                    )}
                    <button onClick={handleRestart}>Visualize Another Problem</button>
                </div>
            )}
        </div>
    );
}

export default MathProblemVisualizer;