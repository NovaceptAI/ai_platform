"""
AI 3D Model Builder Service

Stage 2: Enhanced text-to-3D using procedural generation, AI guidance, and real mesh creation.
Generates 3D models from text descriptions using ChatGPT for composition
and trimesh for actual 3D geometry creation with GLB/OBJ/STL export.
"""

import logging
import json
import numpy as np
import trimesh
from typing import Dict, List, Any, Optional
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from stl import mesh as stl_mesh
from app.services.ai_service_base import AIServiceBase

logger = logging.getLogger(__name__)


class AI3DModelBuilderService(AIServiceBase):
    """Service for generating 3D models using AI guidance."""

    def __init__(self):
        super().__init__()
        self.service_name = "AI3DModelBuilder"
        self.model_name = "gpt-4"

    # ==================== Service Info ====================

    def get_service_info(self) -> Dict[str, Any]:
        """Return service metadata."""
        return {
            'service_name': 'AI3DModelBuilder',
            'description': 'Generate interactive 3D models from text descriptions',
            'version': '2.0',
            'stage': 2,
            'capabilities': [
                'text_to_3d',
                'style_variation',
                'multi_format_export',
                'preview_rendering',
                'procedural_generation',
                'real_mesh_creation',
                'interactive_3d_viewer',
                'glb_obj_stl_export'
            ],
            'supported_styles': [s['id'] for s in self.get_available_styles()],
            'complexity_levels': ['simple', 'medium', 'detailed'],
            'export_formats': ['glb', 'obj', 'stl'],
            'max_shapes': 20
        }

    def get_available_styles(self) -> List[Dict[str, Any]]:
        """Get available 3D styles."""
        return [
            {
                'id': 'realistic',
                'name': 'Realistic',
                'description': 'Photorealistic 3D models with detailed textures',
                'icon': '🎨'
            },
            {
                'id': 'cartoon',
                'name': 'Cartoon',
                'description': 'Stylized cartoon-like 3D models',
                'icon': '🎪'
            },
            {
                'id': 'low_poly',
                'name': 'Low Poly',
                'description': 'Geometric low-polygon art style',
                'icon': '🔷'
            },
            {
                'id': 'clay',
                'name': 'Clay',
                'description': 'Soft clay sculpture appearance',
                'icon': '🏺'
            },
            {
                'id': 'wireframe',
                'name': 'Wireframe',
                'description': 'Technical wireframe visualization',
                'icon': '📐'
            }
        ]

    # ==================== Prompt Analysis ====================

    def analyze_3d_prompt(self, prompt_text: str, complexity: str) -> Dict[str, Any]:
        """
        Analyze user prompt to extract 3D object details.

        Args:
            prompt_text: User's description
            complexity: simple|medium|detailed

        Returns:
            Dict with object_type, category, features, etc.
        """
        try:
            analysis_prompt = f"""
            Analyze this 3D object description and extract key information for 3D model generation.

            Prompt: "{prompt_text}"
            Target complexity: {complexity}

            Return a JSON object with:
            {{
                "object_type": "short type (e.g., car, chair, robot)",
                "category": "one of: objects, vehicles, buildings, nature, characters, food",
                "key_features": ["feature1", "feature2", "feature3"],
                "primary_shapes": ["cube", "sphere", "cylinder"],
                "color_scheme": {{"primary": "#RRGGBB", "secondary": "#RRGGBB"}},
                "scale_estimate": {{"width": 1.0, "height": 1.0, "depth": 1.0}},
                "suggested_complexity": "simple|medium|detailed"
            }}

            Examples of primary_shapes: cube, sphere, cylinder, cone, torus
            """

            response = self._query_ai_service(analysis_prompt, max_tokens=600, temperature=0.3)

            # Parse JSON response
            try:
                # Clean response and parse
                response_clean = response.strip()
                if response_clean.startswith('```json'):
                    response_clean = response_clean.split('```json')[1].split('```')[0].strip()
                elif response_clean.startswith('```'):
                    response_clean = response_clean.split('```')[1].split('```')[0].strip()

                analysis = json.loads(response_clean)
                
                logger.info(f"Prompt analysis successful: {analysis.get('object_type', 'unknown')}")
                return analysis

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON analysis: {str(e)}, using defaults")
                return self._get_default_analysis(prompt_text)

        except Exception as e:
            logger.error(f"Error analyzing prompt: {str(e)}")
            return self._get_default_analysis(prompt_text)

    def _get_default_analysis(self, prompt_text: str) -> Dict[str, Any]:
        """Return default analysis if AI fails."""
        return {
            'object_type': 'object',
            'category': 'objects',
            'key_features': [prompt_text[:50]],
            'primary_shapes': ['cube', 'sphere'],
            'color_scheme': {'primary': '#888888', 'secondary': '#CCCCCC'},
            'scale_estimate': {'width': 1.0, 'height': 1.0, 'depth': 1.0},
            'suggested_complexity': 'simple'
        }

    # ==================== Geometry Generation ====================

    def generate_3d_geometry(
        self,
        prompt: str,
        object_type: str,
        complexity: str,
        style: str
    ) -> Dict[str, Any]:
        """
        Generate 3D geometry data.
        
        Stage 1: Uses AI to generate shape composition, then creates procedural geometry.
        """
        try:
            logger.info(f"Generating geometry for: {object_type} ({complexity}, {style})")

            # Determine number of shapes based on complexity
            max_shapes = {
                'simple': 5,
                'medium': 10,
                'detailed': 15
            }.get(complexity, 5)

            # Use ChatGPT to generate shape composition
            composition_prompt = f"""
            Create a 3D model composition for: "{prompt}"
            
            Object type: {object_type}
            Complexity: {complexity}
            Style: {style}
            Maximum shapes: {max_shapes}

            Generate a JSON array of 3D shapes to compose this object.
            Each shape should have:
            {{
                "type": "cube|sphere|cylinder|cone|torus",
                "position": [x, y, z],
                "scale": [width, height, depth],
                "rotation": [x_deg, y_deg, z_deg],
                "color": "#RRGGBB",
                "name": "descriptive name"
            }}

            Position should be relative to origin (0,0,0).
            Scale values should be reasonable (0.1 to 5.0).
            Return ONLY the JSON array, no explanations.
            
            Example:
            [
                {{"type": "cube", "position": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0], "color": "#FF0000", "name": "body"}},
                {{"type": "sphere", "position": [0, 1, 0], "scale": [0.5, 0.5, 0.5], "rotation": [0, 0, 0], "color": "#0000FF", "name": "head"}}
            ]
            """

            response = self._query_ai_service(composition_prompt, max_tokens=1500, temperature=0.6)

            # Parse shapes
            shapes = self._parse_shapes_response(response, max_shapes)

            logger.info(f"Generated {len(shapes)} shapes for composition")

            return {
                'geometry': {
                    'shapes': shapes,
                    'bounding_box': self._calculate_bounding_box(shapes)
                },
                'shape_count': len(shapes),
                'complexity': complexity,
                'style': style
            }

        except Exception as e:
            logger.error(f"Error generating geometry: {str(e)}")
            # Return fallback simple geometry
            return self._get_fallback_geometry(object_type)

    def _parse_shapes_response(self, response: str, max_shapes: int) -> List[Dict[str, Any]]:
        """Parse ChatGPT response into shape list."""
        try:
            # Clean response
            response_clean = response.strip()
            if response_clean.startswith('```json'):
                response_clean = response_clean.split('```json')[1].split('```')[0].strip()
            elif response_clean.startswith('```'):
                response_clean = response_clean.split('```')[1].split('```')[0].strip()

            shapes = json.loads(response_clean)

            # Validate and normalize shapes
            valid_shapes = []
            valid_types = ['cube', 'sphere', 'cylinder', 'cone', 'torus']

            for shape in shapes[:max_shapes]:
                if shape.get('type') in valid_types:
                    # Ensure all required fields exist
                    normalized_shape = {
                        'type': shape.get('type', 'cube'),
                        'position': shape.get('position', [0, 0, 0]),
                        'scale': shape.get('scale', [1, 1, 1]),
                        'rotation': shape.get('rotation', [0, 0, 0]),
                        'color': shape.get('color', '#888888'),
                        'name': shape.get('name', f'shape_{len(valid_shapes)}')
                    }
                    valid_shapes.append(normalized_shape)

            return valid_shapes if valid_shapes else self._get_fallback_shapes()

        except Exception as e:
            logger.warning(f"Failed to parse shapes: {str(e)}, using fallback")
            return self._get_fallback_shapes()

    def _get_fallback_shapes(self) -> List[Dict[str, Any]]:
        """Return simple fallback shapes."""
        return [
            {
                'type': 'cube',
                'position': [0, 0, 0],
                'scale': [1, 1, 1],
                'rotation': [0, 0, 0],
                'color': '#4A90E2',
                'name': 'body'
            }
        ]

    def _get_fallback_geometry(self, object_type: str) -> Dict[str, Any]:
        """Return fallback geometry."""
        shapes = self._get_fallback_shapes()
        return {
            'geometry': {
                'shapes': shapes,
                'bounding_box': {'min': [-1, -1, -1], 'max': [1, 1, 1]}
            },
            'shape_count': len(shapes),
            'complexity': 'simple',
            'style': 'realistic'
        }

    def _calculate_bounding_box(self, shapes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate bounding box for all shapes."""
        if not shapes:
            return {'min': [0, 0, 0], 'max': [0, 0, 0], 'dimensions': [0, 0, 0]}

        min_vals = [float('inf')] * 3
        max_vals = [float('-inf')] * 3

        for shape in shapes:
            pos = shape.get('position', [0, 0, 0])
            scale = shape.get('scale', [1, 1, 1])

            for i in range(3):
                min_vals[i] = min(min_vals[i], pos[i] - scale[i] / 2)
                max_vals[i] = max(max_vals[i], pos[i] + scale[i] / 2)

        dimensions = [max_vals[i] - min_vals[i] for i in range(3)]

        return {
            'min': min_vals,
            'max': max_vals,
            'dimensions': dimensions
        }

    # ==================== Mesh Creation (Placeholder) ====================

    def create_mesh_from_geometry(
        self,
        geometry: Dict[str, Any],
        style: str
    ) -> Dict[str, Any]:
        """
        Create actual 3D mesh from geometry data using trimesh.

        Stage 2: Creates real 3D meshes by combining primitive shapes
        based on AI-generated composition.
        """
        shapes = geometry.get('shapes', [])

        if not shapes:
            logger.warning("No shapes provided, creating default cube")
            shapes = [{'type': 'cube', 'position': [0, 0, 0], 'scale': [1, 1, 1], 'color': [0.5, 0.5, 0.5]}]

        meshes = []

        for shape_data in shapes:
            try:
                shape_type = shape_data.get('type', 'cube').lower()
                position = shape_data.get('position', [0, 0, 0])
                scale = shape_data.get('scale', [1, 1, 1])
                color = shape_data.get('color', [0.7, 0.7, 0.7])

                # Create primitive mesh based on type
                if shape_type == 'cube' or shape_type == 'box':
                    mesh = trimesh.primitives.Box(extents=[scale[0], scale[1], scale[2]])
                elif shape_type == 'sphere':
                    radius = max(scale) / 2
                    mesh = trimesh.primitives.Sphere(radius=radius, subdivisions=3)
                elif shape_type == 'cylinder':
                    mesh = trimesh.primitives.Cylinder(radius=scale[0]/2, height=scale[1], sections=32)
                elif shape_type == 'cone':
                    mesh = trimesh.primitives.Cone(radius=scale[0]/2, height=scale[1], sections=32)
                elif shape_type == 'torus':
                    # Torus is not a basic primitive, use cylinder as fallback
                    mesh = trimesh.primitives.Cylinder(radius=scale[0]/2, height=scale[1]/4, sections=32)
                else:
                    # Default to box
                    mesh = trimesh.primitives.Box(extents=[scale[0], scale[1], scale[2]])

                # Apply position transform
                translation_matrix = trimesh.transformations.translation_matrix(position)
                mesh.apply_transform(translation_matrix)

                # Set color (convert to 0-255 range)
                try:
                    color_255 = [int(c * 255) for c in color] + [255]  # Add alpha
                    mesh.visual.vertex_colors = color_255
                except:
                    pass

                meshes.append(mesh)

            except Exception as e:
                logger.error(f"Error creating shape {shape_type}: {str(e)}")
                continue

        # Combine all meshes into one
        if len(meshes) > 1:
            combined_mesh = trimesh.util.concatenate(meshes)
        elif len(meshes) == 1:
            combined_mesh = meshes[0]
        else:
            # Fallback: create a default cube
            combined_mesh = trimesh.primitives.Box(extents=[1, 1, 1])

        # Get actual vertex and face counts
        vertex_count = len(combined_mesh.vertices)
        face_count = len(combined_mesh.faces)

        logger.info(f"Created mesh with {vertex_count} vertices and {face_count} faces")

        return {
            'mesh': combined_mesh,  # Actual trimesh object
            'metadata': {
                'vertex_count': vertex_count,
                'face_count': face_count,
                'bounds': combined_mesh.bounds.tolist(),
                'shapes': shapes,
                'style': style
            }
        }

    # ==================== Preview Rendering (Placeholder) ====================

    def render_preview_images(
        self,
        mesh_data: Dict[str, Any],
        angles: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Render preview images from different angles.

        Stage 1: Generates simple placeholder images with PIL showing model info.
        Stage 2: Will use actual 3D rendering with pyrender.
        """
        try:
            shapes = mesh_data['metadata'].get('shapes', [])
            style = mesh_data['metadata'].get('style', 'realistic')

            preview_images = []

            logger.info(f"Generating {len(angles)} placeholder preview images")

            # Generate simple placeholder image for each angle
            for angle in angles:
                image_bytes = self._create_placeholder_image(shapes, angle, style)

                preview_images.append({
                    'angle': angle,
                    'image_bytes': image_bytes,
                    'width': 800,
                    'height': 600
                })

                logger.info(f"Generated placeholder image for {angle} view")

            return preview_images

        except Exception as e:
            logger.error(f"Error rendering previews: {str(e)}")
            return []

    def _create_placeholder_image(
        self,
        shapes: List[Dict[str, Any]],
        angle: str,
        style: str
    ) -> bytes:
        """
        Create a simple placeholder image using PIL.

        Args:
            shapes: List of shape definitions
            angle: View angle (front, side, top, perspective)
            style: Visual style

        Returns:
            Image as PNG bytes
        """
        # Create image
        width, height = 800, 600

        # Color schemes based on style
        color_schemes = {
            'realistic': {'bg': '#F0F4F8', 'text': '#2C3E50', 'accent': '#3498DB'},
            'cartoon': {'bg': '#FFF9E6', 'text': '#E67E22', 'accent': '#F39C12'},
            'low_poly': {'bg': '#E8F5E9', 'text': '#27AE60', 'accent': '#2ECC71'},
            'clay': {'bg': '#FBE9E7', 'text': '#D35400', 'accent': '#E67E22'},
            'wireframe': {'bg': '#ECF0F1', 'text': '#34495E', 'accent': '#95A5A6'}
        }

        colors = color_schemes.get(style, color_schemes['realistic'])

        # Create image with background color
        img = Image.new('RGB', (width, height), colors['bg'])
        draw = ImageDraw.Draw(img)

        # Draw simple geometric representation
        center_x, center_y = width // 2, height // 2

        # Draw shapes based on angle
        for i, shape in enumerate(shapes[:5]):  # Limit to 5 shapes
            shape_type = shape.get('type', 'cube')
            color = shape.get('color', colors['accent'])

            # Offset based on index
            offset_x = (i - 2) * 80
            offset_y = (i - 2) * 40 if angle == 'perspective' else 0

            x = center_x + offset_x
            y = center_y + offset_y

            # Draw shape based on type
            if shape_type == 'sphere':
                draw.ellipse([x-40, y-40, x+40, y+40], fill=color, outline='#34495E', width=2)
            elif shape_type == 'cylinder':
                draw.rectangle([x-30, y-50, x+30, y+50], fill=color, outline='#34495E', width=2)
            elif shape_type == 'cone':
                draw.polygon([(x, y-50), (x-40, y+50), (x+40, y+50)], fill=color, outline='#34495E', width=2)
            else:  # cube/default
                draw.rectangle([x-40, y-40, x+40, y+40], fill=color, outline='#34495E', width=2)

        # Add text
        try:
            # Try to use a nice font, fall back to default if not available
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw title
        title = f"{style.upper()} - {angle.upper()} VIEW"
        draw.text((50, 50), title, fill=colors['text'], font=font_large)

        # Draw shape count
        shape_count_text = f"{len(shapes)} shapes"
        draw.text((50, height - 80), shape_count_text, fill=colors['text'], font=font_small)

        # Draw "Preview" watermark
        draw.text((width - 200, height - 80), "Stage 1 Preview", fill=colors['accent'], font=font_small)

        # Convert to PNG bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG', optimize=True)
        img_bytes.seek(0)

        return img_bytes.getvalue()

    def _create_model_description(self, shapes: List[Dict[str, Any]], style: str) -> str:
        """Create text description of model for preview generation."""
        shape_names = [s.get('name', s.get('type', 'shape')) for s in shapes]
        return f"3D {style} model composed of {', '.join(shape_names[:3])}"

    # ==================== Export (Placeholder) ====================

    def export_3d_model(
        self,
        mesh_data: Dict[str, Any],
        formats: List[str]
    ) -> Dict[str, bytes]:
        """
        Export 3D model to various formats using trimesh.

        Stage 2: Exports actual 3D mesh to GLB, OBJ, and STL formats.
        """
        export_files = {}
        mesh = mesh_data.get('mesh')

        if mesh is None:
            logger.error("No mesh found in mesh_data, cannot export")
            return export_files

        for fmt in formats:
            try:
                if fmt == 'glb':
                    # Export to GLB (binary glTF)
                    glb_data = mesh.export(file_type='glb')
                    export_files['glb'] = glb_data
                    logger.info("Exported to GLB format")

                elif fmt == 'obj':
                    # Export to OBJ
                    obj_data = mesh.export(file_type='obj')
                    export_files['obj'] = obj_data
                    logger.info("Exported to OBJ format")

                elif fmt == 'stl':
                    # Export to STL
                    stl_data = mesh.export(file_type='stl')
                    export_files['stl'] = stl_data
                    logger.info("Exported to STL format")

            except Exception as e:
                logger.error(f"Error exporting to {fmt}: {str(e)}")
                continue

        logger.info(f"Successfully exported model to {len(export_files)} formats")
        return export_files

    # ==================== Helper Methods ====================

    def _query_ai_service(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> str:
        """Query AI service with a prompt."""
        try:
            messages = [
                {"role": "system", "content": "You are an expert 3D modeler who understands geometric composition and can describe 3D objects precisely."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_openai_call(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response

        except Exception as e:
            logger.error(f"Error querying AI service: {str(e)}")
            return "{}"
