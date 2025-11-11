import React, { Suspense, useRef, useEffect, useState } from 'react';
import { Canvas, useLoader, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import * as THREE from 'three';

// Component to render GLB model
function GLBModel({ url, autoRotate }) {
    const gltf = useLoader(GLTFLoader, url);
    const meshRef = useRef();

    useFrame((state, delta) => {
        if (autoRotate && meshRef.current) {
            meshRef.current.rotation.y += delta * 0.5;
        }
    });

    useEffect(() => {
        if (meshRef.current) {
            // Center the model
            const box = new THREE.Box3().setFromObject(meshRef.current);
            const center = box.getCenter(new THREE.Vector3());
            meshRef.current.position.sub(center);

            // Scale to fit
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 2 / maxDim;
            meshRef.current.scale.setScalar(scale);
        }
    }, []);

    return <primitive ref={meshRef} object={gltf.scene} />;
}

// Component to render OBJ model
function OBJModel({ url, autoRotate }) {
    const obj = useLoader(OBJLoader, url);
    const meshRef = useRef();

    useFrame((state, delta) => {
        if (autoRotate && meshRef.current) {
            meshRef.current.rotation.y += delta * 0.5;
        }
    });

    useEffect(() => {
        if (meshRef.current) {
            // Center the model
            const box = new THREE.Box3().setFromObject(meshRef.current);
            const center = box.getCenter(new THREE.Vector3());
            meshRef.current.position.sub(center);

            // Scale to fit
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 2 / maxDim;
            meshRef.current.scale.setScalar(scale);

            // Add material if missing
            meshRef.current.traverse((child) => {
                if (child.isMesh && !child.material) {
                    child.material = new THREE.MeshStandardMaterial({
                        color: 0x808080,
                        roughness: 0.5,
                        metalness: 0.3
                    });
                }
            });
        }
    }, [obj]);

    return <primitive ref={meshRef} object={obj} />;
}

// Fallback placeholder 3D model (procedural geometry)
function PlaceholderModel({ autoRotate }) {
    const meshRef = useRef();

    useFrame((state, delta) => {
        if (autoRotate && meshRef.current) {
            meshRef.current.rotation.y += delta * 0.5;
            meshRef.current.rotation.x += delta * 0.2;
        }
    });

    return (
        <group ref={meshRef}>
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="#4A90E2" roughness={0.3} metalness={0.7} />
            </mesh>
            <mesh position={[0, 0.8, 0]}>
                <sphereGeometry args={[0.4, 32, 32]} />
                <meshStandardMaterial color="#E24A4A" roughness={0.2} metalness={0.5} />
            </mesh>
        </group>
    );
}

// Loading fallback
function LoadingPlaceholder() {
    const meshRef = useRef();

    useFrame((state, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.y += delta;
        }
    });

    return (
        <mesh ref={meshRef}>
            <torusGeometry args={[1, 0.3, 16, 100]} />
            <meshStandardMaterial color="#888888" wireframe />
        </mesh>
    );
}

// Main 3D Viewer Component
function Model3DViewer({
    modelUrl,
    modelFormat = 'glb',
    autoRotate = true,
    showGrid = false,
    backgroundColor = '#1a1a1a',
    cameraPosition = [3, 2, 5]
}) {
    const [error, setError] = useState(null);

    const renderModel = () => {
        if (!modelUrl) {
            return <PlaceholderModel autoRotate={autoRotate} />;
        }

        try {
            if (modelFormat === 'glb') {
                return <GLBModel url={modelUrl} autoRotate={autoRotate} />;
            } else if (modelFormat === 'obj') {
                return <OBJModel url={modelUrl} autoRotate={autoRotate} />;
            } else {
                return <PlaceholderModel autoRotate={autoRotate} />;
            }
        } catch (err) {
            console.error('Error loading model:', err);
            setError(err.message);
            return <PlaceholderModel autoRotate={autoRotate} />;
        }
    };

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            {error && (
                <div style={{
                    position: 'absolute',
                    top: 10,
                    left: 10,
                    background: 'rgba(255, 0, 0, 0.8)',
                    color: 'white',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    zIndex: 1000,
                    fontSize: '12px'
                }}>
                    Error loading model: {error}
                </div>
            )}
            <Canvas
                style={{ background: backgroundColor }}
                gl={{ antialias: true, alpha: false }}
            >
                <PerspectiveCamera makeDefault position={cameraPosition} fov={50} />

                {/* Lighting */}
                <ambientLight intensity={0.5} />
                <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
                <directionalLight position={[-10, -10, -5]} intensity={0.3} />
                <pointLight position={[0, 5, 0]} intensity={0.5} />

                {/* Environment for reflections */}
                <Environment preset="studio" />

                {/* Grid helper */}
                {showGrid && <gridHelper args={[10, 10]} />}

                {/* Model */}
                <Suspense fallback={<LoadingPlaceholder />}>
                    {renderModel()}
                </Suspense>

                {/* Controls */}
                <OrbitControls
                    enablePan={true}
                    enableZoom={true}
                    enableRotate={true}
                    minDistance={1}
                    maxDistance={20}
                    autoRotate={false}  // We handle auto-rotate in the model component
                />
            </Canvas>
        </div>
    );
}

export default Model3DViewer;
