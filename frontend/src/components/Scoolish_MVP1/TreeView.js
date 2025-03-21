import React from 'react';
import Tree from 'react-d3-tree';
import './TreeView.css';

function TreeView({ location }) {
    const { analysis } = location.state;

    const generateTreeData = (analysis) => {
        if (!analysis || !analysis.topics) return null;

        const treeData = {
            name: analysis.document_title || 'Document',
            children: analysis.topics.map((topic) => ({
                name: topic.title || 'Untitled Topic',
            })),
        };

        console.log('Generated tree data:', treeData); // Debugging: Log the generated tree data
        return [treeData];
    };

    return (
        <div className="tree-view">
            <h1>Document Analysis Tree</h1>
            {analysis && generateTreeData(analysis) && (
                <div className="tree-container" style={{ height: '500px', width: '100%' }}>
                    <Tree
                        data={generateTreeData(analysis)}
                        orientation="vertical"
                        translate={{ x: 400, y: 50 }}
                        pathFunc="elbow"
                        styles={{
                            nodes: {
                                node: {
                                    circle: { fill: '#007bff' },
                                    name: { stroke: '#0056b3', fill: '#ffffff' },
                                    attributes: { stroke: '#cccccc', fill: '#cccccc' },
                                },
                                leafNode: {
                                    circle: { fill: '#007bff' },
                                    name: { stroke: '#0056b3', fill: '#ffffff' },
                                    attributes: { stroke: '#cccccc', fill: '#cccccc' },
                                },
                            },
                            links: {
                                stroke: '#cccccc',
                                strokeWidth: 2,
                            },
                        }}
                    />
                </div>
            )}
        </div>
    );
}

export default TreeView;