import React, { useEffect, useRef, useState } from 'react';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
import { zoom } from 'd3-zoom';
import { select } from 'd3-selection';

const ForceGraph = ({ nodes, edges, onNodeClick }) => {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const simulationRef = useRef(null);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Handle resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (!nodes || nodes.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const { width, height } = dimensions;

    // Set canvas size
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Clone nodes and edges to avoid mutating props
    const graphNodes = nodes.map(d => ({ ...d }));
    const graphEdges = edges.map(d => ({ ...d }));

    // Create force simulation
    const simulation = forceSimulation(graphNodes)
      .force('link', forceLink(graphEdges)
        .id(d => d.id)
        .distance(d => {
          // Adjust link distance based on edge weight
          const weight = d.weight || 1;
          return 100 / Math.sqrt(weight);
        })
      )
      .force('charge', forceManyBody()
        .strength(-300)
        .distanceMax(400)
      )
      .force('center', forceCenter(width / 2, height / 2))
      .force('collision', forceCollide().radius(d => {
        // Larger radius for nodes with more connections
        const connections = edges.filter(e => e.source === d.id || e.target === d.id).length;
        return Math.max(20, Math.sqrt(connections) * 5);
      }));

    simulationRef.current = simulation;

    // Node colors by type
    const getNodeColor = (type) => {
      switch (type?.toLowerCase()) {
        case 'entity': return '#3b82f6'; // blue
        case 'topic': return '#10b981'; // green
        case 'concept': return '#f59e0b'; // amber
        default: return '#6366f1'; // indigo
      }
    };

    // Draw function
    const draw = () => {
      const { x, y, k } = transformRef.current;

      // Clear canvas
      ctx.save();
      ctx.clearRect(0, 0, width, height);
      ctx.translate(x, y);
      ctx.scale(k, k);

      // Draw edges
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
      ctx.lineWidth = 1;
      graphEdges.forEach(edge => {
        const source = typeof edge.source === 'object' ? edge.source : graphNodes.find(n => n.id === edge.source);
        const target = typeof edge.target === 'object' ? edge.target : graphNodes.find(n => n.id === edge.target);
        
        if (source && target) {
          // Line width based on weight
          const weight = edge.weight || 1;
          ctx.lineWidth = Math.max(0.5, Math.min(weight / 5, 3));
          
          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
        }
      });

      // Draw nodes
      graphNodes.forEach(node => {
        const connections = edges.filter(e => e.source === node.id || e.target === node.id).length;
        const radius = Math.max(5, Math.min(Math.sqrt(connections) * 3, 15));

        // Node circle with gradient
        const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, radius);
        const color = getNodeColor(node.type);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, color + 'cc');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        // Node border
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Node label for important nodes
        if (connections > 5 || node.frequency > 10) {
          ctx.fillStyle = '#1e293b';
          ctx.font = '10px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          const text = node.name.length > 20 ? node.name.substring(0, 17) + '...' : node.name;
          
          // Text background
          const metrics = ctx.measureText(text);
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          ctx.fillRect(
            node.x - metrics.width / 2 - 3,
            node.y + radius + 2,
            metrics.width + 6,
            14
          );
          
          // Text
          ctx.fillStyle = '#1e293b';
          ctx.fillText(text, node.x, node.y + radius + 9);
        }
      });

      ctx.restore();
    };

    // Simulation tick
    simulation.on('tick', draw);

    // Zoom behavior
    const zoomBehavior = zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        transformRef.current = event.transform;
        draw();
      });

    select(canvas).call(zoomBehavior);

    // Mouse interaction
    let hoveredNode = null;

    const getNodeAtPosition = (x, y) => {
      const { x: tx, y: ty, k } = transformRef.current;
      const canvasX = (x - tx) / k;
      const canvasY = (y - ty) / k;

      return graphNodes.find(node => {
        const connections = edges.filter(e => e.source === node.id || e.target === node.id).length;
        const radius = Math.max(5, Math.min(Math.sqrt(connections) * 3, 15));
        const dx = node.x - canvasX;
        const dy = node.y - canvasY;
        return Math.sqrt(dx * dx + dy * dy) < radius;
      });
    };

    const handleMouseMove = (event) => {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const node = getNodeAtPosition(x, y);
      
      if (node !== hoveredNode) {
        hoveredNode = node;
        canvas.style.cursor = node ? 'pointer' : 'grab';
        
        // Highlight hovered node and connected edges
        if (node) {
          draw();
          const { x: tx, y: ty, k } = transformRef.current;
          
          ctx.save();
          ctx.translate(tx, ty);
          ctx.scale(k, k);

          // Highlight connected edges
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 2;
          graphEdges.forEach(edge => {
            const source = typeof edge.source === 'object' ? edge.source : graphNodes.find(n => n.id === edge.source);
            const target = typeof edge.target === 'object' ? edge.target : graphNodes.find(n => n.id === edge.target);
            
            if ((source?.id === node.id || target?.id === node.id) && source && target) {
              ctx.beginPath();
              ctx.moveTo(source.x, source.y);
              ctx.lineTo(target.x, target.y);
              ctx.stroke();
            }
          });

          // Highlight node
          const connections = edges.filter(e => e.source === node.id || e.target === node.id).length;
          const radius = Math.max(5, Math.min(Math.sqrt(connections) * 3, 15));
          
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI);
          ctx.stroke();

          ctx.restore();
        }
      }
    };

    const handleClick = (event) => {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const node = getNodeAtPosition(x, y);
      if (node && onNodeClick) {
        onNodeClick(node);
      }
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleClick);

    // Cleanup
    return () => {
      simulation.stop();
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleClick);
    };
  }, [nodes, edges, dimensions, onNodeClick]);

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%' }}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          cursor: 'grab',
          borderRadius: '8px',
          background: '#1e293b'
        }}
      />
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        background: 'rgba(30, 41, 59, 0.9)',
        color: '#fff',
        padding: '8px 12px',
        borderRadius: '6px',
        fontSize: '12px',
        pointerEvents: 'none'
      }}>
        🖱️ Drag to pan • Scroll to zoom • Click nodes for details
      </div>
    </div>
  );
};

export default ForceGraph;
