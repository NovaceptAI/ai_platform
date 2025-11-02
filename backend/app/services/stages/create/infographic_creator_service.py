import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class InfographicCreatorService(AIServiceBase):
    """
    Service for creating infographic designs from document content.
    Transforms text-based analysis into visual information graphics.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "infographic_creator"
        
    def get_service_info(self) -> Dict[str, Any]:
        """Return information about the infographic creator service."""
        return {
            "service_name": self.service_name,
            "description": "Service for creating visual infographics from document analysis",
            "capabilities": [
                "data_visualization",
                "layout_design", 
                "color_scheme_generation",
                "icon_recommendations"
            ],
            "supported_styles": [
                "modern", "minimal", "colorful", "professional", "academic"
            ],
            "version": "1.0.0"
        }
        
    def create_infographic(self, file_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an infographic design from file content.
        
        Args:
            file_data: Dictionary containing file content and metadata
            options: Optional configuration for infographic creation
            
        Returns:
            Dict containing infographic design specification and elements
        """
        try:
            log.info(f"[InfographicCreator] Creating infographic for file: {file_data.get('file_name', 'Unknown')}")
            
            config = options or {
                "style": "modern",
                "color_scheme": "blue_gradient",
                "layout": "vertical",
                "include_charts": True,
                "complexity": "medium"
            }
            
            # Extract content for infographic creation
            content = self._prepare_content(file_data)
            
            # Generate infographic components
            infographic = {}
            
            # 1. Create overall design layout
            layout = self._create_layout_design(content, config)
            infographic["layout"] = layout
            
            # 2. Generate header section
            header = self._create_header_section(content, config)
            infographic["header"] = header
            
            # 3. Create data visualization sections
            if config.get("include_charts", True):
                visualizations = self._create_data_visualizations(content, config)
                infographic["visualizations"] = visualizations
            
            # 4. Generate key statistics section
            statistics = self._create_statistics_section(content, config)
            infographic["statistics"] = statistics
            
            # 5. Create key points section
            key_points = self._create_key_points_section(content, config)
            infographic["key_points"] = key_points
            
            # 6. Add footer with sources
            footer = self._create_footer_section(content, config)
            infographic["footer"] = footer
            
            # 7. Define color palette and styling
            styling = self._create_styling_guide(config)
            infographic["styling"] = styling
            
            result = {
                "infographic": infographic,
                "metadata": {
                    "style": config.get("style", "modern"),
                    "layout": config.get("layout", "vertical"),
                    "color_scheme": config.get("color_scheme", "blue_gradient"),
                    "total_sections": len([k for k in infographic.keys() if k != "styling"]),
                    "complexity": config.get("complexity", "medium")
                },
                "design_specs": {
                    "recommended_size": self._get_recommended_size(config),
                    "export_formats": ["PNG", "PDF", "SVG"],
                    "software_compatibility": ["Canva", "Adobe Illustrator", "Figma"],
                    "accessibility": {
                        "color_contrast": "WCAG AA compliant",
                        "font_size": "minimum 12pt",
                        "alt_text_required": True
                    }
                },
                "creation_tips": {
                    "hierarchy": "Use size and color to establish visual hierarchy",
                    "whitespace": "Include adequate white space for readability",
                    "consistency": "Maintain consistent styling throughout",
                    "balance": "Balance text and visual elements"
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[InfographicCreator] Created infographic with {len(infographic)} sections")
            return result
            
        except Exception as e:
            log.error(f"[InfographicCreator] Error creating infographic: {e}")
            raise
    
    def _prepare_content(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and extract content for infographic creation."""
        
        content = {
            "text": file_data.get("content", ""),
            "summary": file_data.get("summary", ""),
            "topics": file_data.get("topics", []),
            "entities": file_data.get("entities", {}),
            "key_points": file_data.get("key_points", []),
            "file_name": file_data.get("file_name", "Unknown Document")
        }
        
        return content
    
    def _create_layout_design(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create overall layout design for the infographic."""
        
        layout_type = config.get("layout", "vertical")
        
        if layout_type == "vertical":
            layout = {
                "type": "vertical",
                "sections": [
                    {"name": "header", "height": "15%", "position": "top"},
                    {"name": "statistics", "height": "20%", "position": "upper"},
                    {"name": "visualizations", "height": "35%", "position": "middle"},
                    {"name": "key_points", "height": "25%", "position": "lower"},
                    {"name": "footer", "height": "5%", "position": "bottom"}
                ],
                "dimensions": {"width": 800, "height": 1200}
            }
        elif layout_type == "horizontal":
            layout = {
                "type": "horizontal",
                "sections": [
                    {"name": "header", "width": "100%", "position": "top"},
                    {"name": "left_panel", "width": "30%", "position": "left"},
                    {"name": "center_panel", "width": "40%", "position": "center"},
                    {"name": "right_panel", "width": "30%", "position": "right"}
                ],
                "dimensions": {"width": 1200, "height": 800}
            }
        else:
            layout = {
                "type": "grid",
                "sections": [
                    {"name": "header", "grid": "1,1,4,1"},
                    {"name": "stat1", "grid": "1,2,2,1"},
                    {"name": "stat2", "grid": "3,2,2,1"},
                    {"name": "main_visual", "grid": "1,3,4,2"},
                    {"name": "footer", "grid": "1,5,4,1"}
                ],
                "dimensions": {"width": 1000, "height": 1000}
            }
        
        return layout
    
    def _create_header_section(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create header section for the infographic."""
        
        # Generate compelling title
        title = self._generate_infographic_title(content)
        
        header = {
            "title": {
                "text": title,
                "font_size": "large",
                "font_weight": "bold",
                "alignment": "center"
            },
            "subtitle": {
                "text": f"Analysis of {content.get('file_name', 'Document')}",
                "font_size": "medium",
                "font_weight": "normal",
                "alignment": "center"
            },
            "background": {
                "type": "gradient",
                "primary_color": "#3B82F6",
                "secondary_color": "#1E40AF"
            },
            "decorative_elements": [
                {"type": "icon", "name": "document", "position": "left"},
                {"type": "line", "style": "decorative", "position": "bottom"}
            ]
        }
        
        return header
    
    def _create_data_visualizations(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create data visualization specifications."""
        
        visualizations = []
        topics = content.get("topics", [])
        
        # Create topic distribution chart
        if len(topics) > 1:
            topic_chart = {
                "type": "bar_chart",
                "title": "Key Topics Distribution",
                "data": [
                    {"label": str(topic)[:20], "value": 100 - (i * 15), "color": f"hsl({i * 60}, 70%, 50%)"}
                    for i, topic in enumerate(topics[:5])
                ],
                "position": {"x": 50, "y": 200},
                "size": {"width": 300, "height": 200}
            }
            visualizations.append(topic_chart)
        
        # Create key points timeline
        key_points = content.get("key_points", [])
        if len(key_points) > 2:
            timeline = {
                "type": "timeline",
                "title": "Key Insights Flow",
                "data": [
                    {
                        "step": i + 1,
                        "text": str(kp.get("text", kp))[:50] + "..." if len(str(kp.get("text", kp))) > 50 else str(kp.get("text", kp)),
                        "icon": "insight"
                    }
                    for i, kp in enumerate(key_points[:4])
                ],
                "position": {"x": 400, "y": 200},
                "size": {"width": 350, "height": 200}
            }
            visualizations.append(timeline)
        
        # Create entity relationship diagram
        entities = content.get("entities", {})
        if entities:
            entity_viz = {
                "type": "network_diagram",
                "title": "Concept Relationships",
                "data": {
                    "nodes": [
                        {"id": entity, "label": str(entity)[:15], "type": category}
                        for category, entity_list in entities.items()
                        for entity in (entity_list if isinstance(entity_list, list) else [entity_list])
                    ][:8],
                    "connections": [
                        {"from": 0, "to": 1, "strength": "medium"},
                        {"from": 1, "to": 2, "strength": "high"}
                    ]
                },
                "position": {"x": 50, "y": 450},
                "size": {"width": 700, "height": 200}
            }
            visualizations.append(entity_viz)
        
        return visualizations
    
    def _create_statistics_section(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create statistics section with key numbers."""
        
        # Calculate basic statistics
        text_length = len(content.get("text", ""))
        word_count = len(content.get("text", "").split())
        topics_count = len(content.get("topics", []))
        key_points_count = len(content.get("key_points", []))
        
        statistics = {
            "layout": "horizontal_cards",
            "stats": [
                {
                    "label": "Total Words",
                    "value": f"{word_count:,}",
                    "icon": "text",
                    "color": "#10B981",
                    "background": "#F0FDF4"
                },
                {
                    "label": "Key Topics",
                    "value": str(topics_count),
                    "icon": "topics",
                    "color": "#3B82F6",
                    "background": "#EFF6FF"
                },
                {
                    "label": "Main Insights",
                    "value": str(key_points_count),
                    "icon": "insights",
                    "color": "#F59E0B",
                    "background": "#FFFBEB"
                },
                {
                    "label": "Analysis Depth",
                    "value": "High" if word_count > 1000 else "Medium" if word_count > 500 else "Basic",
                    "icon": "depth",
                    "color": "#8B5CF6",
                    "background": "#F5F3FF"
                }
            ]
        }
        
        return statistics
    
    def _create_key_points_section(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create key points section with visual highlights."""
        
        key_points = content.get("key_points", [])
        
        key_points_section = {
            "title": "Key Insights",
            "layout": "icon_list",
            "items": []
        }
        
        icons = ["star", "lightbulb", "check", "arrow", "target", "chart"]
        
        for i, kp in enumerate(key_points[:6]):
            if isinstance(kp, dict):
                text = kp.get("text", "")
            else:
                text = str(kp)
            
            if text and len(text) > 5:
                key_points_section["items"].append({
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "icon": icons[i % len(icons)],
                    "color": f"hsl({i * 60}, 60%, 45%)",
                    "emphasis": "medium" if i < 3 else "low"
                })
        
        return key_points_section
    
    def _create_footer_section(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create footer section with source information."""
        
        footer = {
            "source": {
                "text": f"Source: {content.get('file_name', 'Document Analysis')}",
                "font_size": "small",
                "alignment": "left"
            },
            "date": {
                "text": f"Created: {datetime.utcnow().strftime('%Y-%m-%d')}",
                "font_size": "small",
                "alignment": "right"
            },
            "branding": {
                "text": "Generated by AI Analysis Platform",
                "font_size": "small",
                "alignment": "center",
                "style": "italic"
            },
            "background_color": "#F8F9FA"
        }
        
        return footer
    
    def _create_styling_guide(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create styling guide for consistent design."""
        
        style = config.get("style", "modern")
        color_scheme = config.get("color_scheme", "blue_gradient")
        
        # Define color palettes
        color_palettes = {
            "blue_gradient": {
                "primary": "#3B82F6",
                "secondary": "#1E40AF", 
                "accent": "#60A5FA",
                "text": "#1F2937",
                "background": "#FFFFFF"
            },
            "green_natural": {
                "primary": "#10B981",
                "secondary": "#059669",
                "accent": "#34D399",
                "text": "#1F2937",
                "background": "#F9FAFB"
            },
            "purple_creative": {
                "primary": "#8B5CF6",
                "secondary": "#7C3AED",
                "accent": "#A78BFA",
                "text": "#1F2937",
                "background": "#FFFFFF"
            }
        }
        
        # Define typography
        typography = {
            "heading_font": "Inter, sans-serif" if style == "modern" else "Georgia, serif",
            "body_font": "Inter, sans-serif",
            "font_sizes": {
                "large": "24px",
                "medium": "16px", 
                "small": "12px"
            }
        }
        
        styling = {
            "color_palette": color_palettes.get(color_scheme, color_palettes["blue_gradient"]),
            "typography": typography,
            "spacing": {
                "section_margin": "20px",
                "element_padding": "10px",
                "text_line_height": "1.5"
            },
            "effects": {
                "border_radius": "8px" if style == "modern" else "0px",
                "shadow": "0 2px 4px rgba(0,0,0,0.1)" if style == "modern" else "none",
                "gradient_angle": "135deg"
            }
        }
        
        return styling
    
    def _generate_infographic_title(self, content: Dict[str, Any]) -> str:
        """Generate an engaging title for the infographic."""
        
        topics = content.get("topics", [])
        file_name = content.get("file_name", "Document")
        
        if topics:
            main_topic = str(topics[0])
            if len(main_topic) > 30:
                main_topic = main_topic[:30] + "..."
            return f"Understanding {main_topic}"
        else:
            return f"Analysis of {file_name}"
    
    def _get_recommended_size(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Get recommended size based on layout."""
        
        layout = config.get("layout", "vertical")
        
        sizes = {
            "vertical": {"width": "800px", "height": "1200px", "aspect_ratio": "2:3"},
            "horizontal": {"width": "1200px", "height": "800px", "aspect_ratio": "3:2"},
            "grid": {"width": "1000px", "height": "1000px", "aspect_ratio": "1:1"}
        }
        
        return sizes.get(layout, sizes["vertical"])
    
    def generate_infographic(self, file_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate infographic from file data - main method called by tasks
        
        Args:
            file_data: Dictionary containing file content and metadata
            options: Optional configuration for infographic generation
            
        Returns:
            Dict containing complete infographic specification
        """
        try:
            log.info(f"[InfographicCreator] Generating infographic for file: {file_data.get('file_id', 'unknown')}")
            
            # Use create_infographic method as the main implementation
            result = self.create_infographic(file_data, options)
            
            # Add additional metadata for task processing
            result.update({
                'generation_method': 'automated',
                'processing_status': 'completed',
                'file_id': file_data.get('file_id'),
                'export_ready': True
            })
            
            return result
            
        except Exception as e:
            log.error(f"[InfographicCreator] Error generating infographic: {e}")
            raise
    
    def process_template(self, template_id: str, file_ids: List[str], customizations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a specific template with multiple files
        
        Args:
            template_id: ID of the template to use
            file_ids: List of file IDs to process
            customizations: Template customizations
            
        Returns:
            Dict containing processed template result
        """
        try:
            log.info(f"[InfographicCreator] Processing template {template_id} with {len(file_ids)} files")
            
            # Mock template processing - in real implementation this would load actual templates
            templates = {
                'modern_summary': {
                    'name': 'Modern Summary',
                    'layout': 'vertical',
                    'style': 'modern',
                    'sections': ['header', 'key_stats', 'main_content', 'footer']
                },
                'data_focused': {
                    'name': 'Data Focused',
                    'layout': 'grid',
                    'style': 'professional',
                    'sections': ['header', 'charts', 'statistics', 'insights']
                },
                'minimal_clean': {
                    'name': 'Minimal & Clean',
                    'layout': 'horizontal',
                    'style': 'minimal',
                    'sections': ['title', 'content', 'summary']
                }
            }
            
            template = templates.get(template_id, templates['modern_summary'])
            
            # Process each file with the template
            processed_files = []
            for file_id in file_ids:
                file_data = {'file_id': file_id, 'content': f'Sample content for {file_id}'}
                
                # Apply template configuration
                template_options = {
                    'style': template['style'],
                    'layout': template['layout'],
                    'template_sections': template['sections']
                }
                
                # Merge with customizations
                if customizations:
                    template_options.update(customizations)
                
                file_result = self.generate_infographic(file_data, template_options)
                file_result['template_applied'] = template_id
                processed_files.append(file_result)
            
            result = {
                'template_id': template_id,
                'template_name': template['name'],
                'files_processed': len(processed_files),
                'customizations_applied': customizations or {},
                'results': processed_files,
                'batch_metadata': {
                    'consistent_styling': True,
                    'template_version': '1.0',
                    'processing_time': datetime.utcnow().isoformat()
                }
            }
            
            log.info(f"[InfographicCreator] Successfully processed template {template_id}")
            return result
            
        except Exception as e:
            log.error(f"[InfographicCreator] Error processing template: {e}")
            raise
    
    def export_infographic(self, infographic_id: str, export_format: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export infographic to specified format
        
        Args:
            infographic_id: ID of the infographic to export
            export_format: Export format (PNG, PDF, SVG, JPG)
            options: Export options (resolution, quality, etc.)
            
        Returns:
            Dict containing export result and download information
        """
        try:
            log.info(f"[InfographicCreator] Exporting infographic {infographic_id} to {export_format}")
            
            # Default export options
            if options is None:
                options = {}
            
            resolution = options.get('resolution', '300dpi')
            quality = options.get('quality', 'high')
            
            # Format-specific configurations
            format_configs = {
                'PNG': {
                    'extension': '.png',
                    'mime_type': 'image/png',
                    'supports_transparency': True,
                    'recommended_use': 'Web display, presentations'
                },
                'PDF': {
                    'extension': '.pdf',
                    'mime_type': 'application/pdf',
                    'supports_vector': True,
                    'recommended_use': 'Print, professional documents'
                },
                'SVG': {
                    'extension': '.svg',
                    'mime_type': 'image/svg+xml',
                    'supports_vector': True,
                    'recommended_use': 'Web, scalable graphics'
                },
                'JPG': {
                    'extension': '.jpg',
                    'mime_type': 'image/jpeg',
                    'supports_compression': True,
                    'recommended_use': 'Web, social media'
                }
            }
            
            format_upper = export_format.upper()
            config = format_configs.get(format_upper, format_configs['PNG'])
            
            # Simulate export process
            import random
            file_size_kb = random.randint(500, 3000)
            
            result = {
                'infographic_id': infographic_id,
                'export_format': format_upper,
                'file_extension': config['extension'],
                'mime_type': config['mime_type'],
                'file_size_kb': file_size_kb,
                'file_size_formatted': f"{file_size_kb}KB",
                'resolution': resolution,
                'quality': quality,
                'export_options': options,
                'format_features': {
                    key: value for key, value in config.items() 
                    if key.startswith('supports_') or key == 'recommended_use'
                },
                'download_info': {
                    'download_url': f"/api/infographic/{infographic_id}/download?format={export_format.lower()}",
                    'filename': f"infographic_{infographic_id}{config['extension']}",
                    'expires_at': datetime.utcnow().isoformat(),
                    'access_token': f"token_{infographic_id}_{format_upper.lower()}"
                },
                'metadata': {
                    'exported_at': datetime.utcnow().isoformat(),
                    'export_version': '1.0',
                    'created_by': 'infographic_creator_service'
                }
            }
            
            log.info(f"[InfographicCreator] Successfully exported {infographic_id} to {export_format}")
            return result
            
        except Exception as e:
            log.error(f"[InfographicCreator] Error exporting infographic: {e}")
            raise
