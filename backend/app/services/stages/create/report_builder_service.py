"""
Report Builder Service for Create Stage Learning Path.

This service generates structured research reports from document analysis with professional formatting.
Supports various report types including academic, business, technical, and executive summaries.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

logger = logging.getLogger(__name__)


class ReportBuilderService(AIServiceBase):
    """Service for generating structured research reports from document content."""
    
    def __init__(self):
        super().__init__()
        self.service_name = "ReportBuilder"
    
    def generate_report(self, file, report_type: str = "research", format_style: str = "academic", 
                       length: str = "medium", include_citations: bool = True) -> Dict[str, Any]:
        """
        Generate a structured research report from file content.
        
        Args:
            file: UploadedFile object containing the document to analyze
            report_type: Type of report (research, business, technical, executive, survey)
            format_style: Formatting style (academic, professional, technical, executive)
            length: Report length (short, medium, comprehensive)
            include_citations: Whether to include citations and references
            
        Returns:
            Dictionary containing the structured report
        """
        try:
            logger.info(f"Generating {report_type} report for file: {file.filename}")
            
            # Extract and analyze content
            content = self._extract_file_content(file)
            if not content:
                raise ValueError(f"Could not extract content from {file.filename}")
            
            # Create report structure based on type and style
            report_structure = self._create_report_structure(report_type, format_style, length)
            
            # Generate each section of the report
            report_sections = {}
            
            # Executive Summary / Abstract
            report_sections['executive_summary'] = self._generate_executive_summary(
                content, report_type, length
            )
            
            # Introduction
            report_sections['introduction'] = self._generate_introduction(
                content, report_type, format_style
            )
            
            # Main body sections (varies by report type)
            report_sections['main_sections'] = self._generate_main_sections(
                content, report_type, format_style, length
            )
            
            # Analysis and findings
            report_sections['analysis'] = self._generate_analysis_section(
                content, report_type, format_style
            )
            
            # Conclusions and recommendations
            report_sections['conclusions'] = self._generate_conclusions(
                content, report_type, format_style
            )
            
            # References and citations (if requested)
            if include_citations:
                report_sections['references'] = self._generate_references_section(
                    content, format_style
                )
            
            # Appendices (for comprehensive reports)
            if length == "comprehensive":
                report_sections['appendices'] = self._generate_appendices(
                    content, report_type
                )
            
            # Format the final report
            formatted_report = self._format_final_report(
                report_sections, report_structure, report_type, format_style
            )
            
            # Generate formatting guidelines
            formatting_guide = self._create_formatting_guidelines(format_style, report_type)
            
            # Create metadata
            report_metadata = self._create_report_metadata(
                file, report_type, format_style, length, include_citations
            )
            
            logger.info(f"Successfully generated {report_type} report for {file.filename}")
            
            return {
                'report_content': formatted_report,
                'report_structure': report_structure,
                'formatting_guidelines': formatting_guide,
                'metadata': report_metadata,
                'sections_summary': {
                    'total_sections': len(report_sections),
                    'word_count_estimate': self._estimate_word_count(formatted_report),
                    'includes_citations': include_citations,
                    'report_type': report_type,
                    'format_style': format_style
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating report for {file.filename}: {str(e)}")
            raise
    
    def _create_report_structure(self, report_type: str, format_style: str, length: str) -> Dict[str, Any]:
        """Create the structural framework for the report."""
        
        base_structure = {
            'title_page': True,
            'table_of_contents': length in ['medium', 'comprehensive'],
            'page_numbers': True,
            'headers_footers': format_style in ['academic', 'professional']
        }
        
        if report_type == "research":
            structure = {
                **base_structure,
                'sections': [
                    'abstract',
                    'introduction',
                    'literature_review',
                    'methodology',
                    'findings',
                    'analysis',
                    'conclusions',
                    'references'
                ]
            }
        elif report_type == "business":
            structure = {
                **base_structure,
                'sections': [
                    'executive_summary',
                    'situation_analysis',
                    'key_findings',
                    'recommendations',
                    'implementation',
                    'appendices'
                ]
            }
        elif report_type == "technical":
            structure = {
                **base_structure,
                'sections': [
                    'abstract',
                    'introduction',
                    'technical_background',
                    'analysis',
                    'results',
                    'discussion',
                    'conclusions',
                    'technical_appendices'
                ]
            }
        elif report_type == "executive":
            structure = {
                **base_structure,
                'sections': [
                    'executive_summary',
                    'key_insights',
                    'strategic_recommendations',
                    'next_steps'
                ]
            }
        else:  # survey or general
            structure = {
                **base_structure,
                'sections': [
                    'executive_summary',
                    'overview',
                    'key_findings',
                    'analysis',
                    'recommendations',
                    'conclusion'
                ]
            }
        
        # Add comprehensive sections for longer reports
        if length == "comprehensive":
            structure['sections'].extend(['detailed_appendices', 'supplementary_data'])
        
        return structure
    
    def _generate_executive_summary(self, content: str, report_type: str, length: str) -> Dict[str, Any]:
        """Generate executive summary or abstract."""
        
        length_guidance = {
            'short': '150-200 words',
            'medium': '200-300 words', 
            'comprehensive': '300-500 words'
        }
        
        prompt = f"""
        Create a professional executive summary for a {report_type} report based on the following content.
        
        Guidelines:
        - Length: {length_guidance[length]}
        - Highlight the most important findings and insights
        - Include key statistics or data points if available
        - Provide a clear overview of the main conclusions
        - Write in a professional, concise style
        
        Content to analyze:
        {content[:3000]}
        
        Generate an executive summary that captures the essence of this content.
        """
        
        summary_response = self._query_ai_service(prompt, max_tokens=600)
        
        return {
            'title': 'Executive Summary',
            'content': summary_response,
            'word_count': len(summary_response.split()),
            'section_type': 'summary'
        }
    
    def _generate_introduction(self, content: str, report_type: str, format_style: str) -> Dict[str, Any]:
        """Generate introduction section."""
        
        prompt = f"""
        Write a comprehensive introduction for a {report_type} report in {format_style} style.
        
        The introduction should:
        - Provide context and background
        - Clearly state the purpose and scope
        - Outline the methodology or approach (if applicable)
        - Preview the main sections and findings
        
        Base the introduction on this content:
        {content[:2500]}
        
        Write a professional introduction that sets the stage for the full report.
        """
        
        introduction_response = self._query_ai_service(prompt, max_tokens=500)
        
        return {
            'title': 'Introduction',
            'content': introduction_response,
            'word_count': len(introduction_response.split()),
            'section_type': 'introduction'
        }
    
    def _generate_main_sections(self, content: str, report_type: str, format_style: str, length: str) -> List[Dict[str, Any]]:
        """Generate the main body sections of the report."""
        
        sections = []
        
        # Determine sections based on report type
        if report_type == "research":
            section_titles = ['Literature Review', 'Methodology', 'Findings', 'Discussion']
        elif report_type == "business":
            section_titles = ['Situation Analysis', 'Market Assessment', 'Key Findings', 'Strategic Analysis']
        elif report_type == "technical":
            section_titles = ['Technical Background', 'System Analysis', 'Results', 'Technical Discussion']
        elif report_type == "executive":
            section_titles = ['Key Insights', 'Market Position', 'Strategic Opportunities']
        else:  # survey or general
            section_titles = ['Overview', 'Key Findings', 'Detailed Analysis', 'Implications']
        
        # Adjust number of sections based on length
        if length == "short":
            section_titles = section_titles[:2]
        elif length == "comprehensive":
            section_titles.extend(['Additional Analysis', 'Comparative Assessment'])
        
        content_chunks = self._split_content_for_sections(content, len(section_titles))
        
        for i, title in enumerate(section_titles):
            chunk_content = content_chunks[i] if i < len(content_chunks) else content[-1500:]
            
            prompt = f"""
            Write a detailed section titled "{title}" for a {report_type} report in {format_style} style.
            
            This section should:
            - Be substantive and well-structured
            - Include specific details and examples from the content
            - Use professional language appropriate for {format_style} format
            - Include data points, statistics, or evidence where available
            - Be approximately 200-400 words depending on importance
            
            Base this section on:
            {chunk_content}
            
            Write the section content with appropriate subheadings if needed.
            """
            
            section_response = self._query_ai_service(prompt, max_tokens=600)
            
            sections.append({
                'title': title,
                'content': section_response,
                'word_count': len(section_response.split()),
                'section_type': 'main_content',
                'order': i + 1
            })
        
        return sections
    
    def _generate_analysis_section(self, content: str, report_type: str, format_style: str) -> Dict[str, Any]:
        """Generate detailed analysis section."""
        
        prompt = f"""
        Create a comprehensive analysis section for a {report_type} report.
        
        The analysis should:
        - Provide deep insights into the key themes and patterns
        - Compare and contrast different aspects or viewpoints
        - Identify trends, correlations, or significant findings
        - Use analytical thinking and critical evaluation
        - Support points with evidence from the content
        
        Content to analyze:
        {content[:3000]}
        
        Write a thorough analysis that demonstrates critical thinking and professional insight.
        """
        
        analysis_response = self._query_ai_service(prompt, max_tokens=700)
        
        return {
            'title': 'Analysis and Discussion',
            'content': analysis_response,
            'word_count': len(analysis_response.split()),
            'section_type': 'analysis'
        }
    
    def _generate_conclusions(self, content: str, report_type: str, format_style: str) -> Dict[str, Any]:
        """Generate conclusions and recommendations."""
        
        prompt = f"""
        Write comprehensive conclusions and recommendations for a {report_type} report.
        
        Include:
        - Clear, actionable conclusions based on the analysis
        - Specific recommendations with rationale
        - Next steps or implementation suggestions
        - Implications for stakeholders
        - Future considerations or areas for further research
        
        Base conclusions on:
        {content[:2500]}
        
        Provide practical, well-reasoned conclusions and recommendations.
        """
        
        conclusions_response = self._query_ai_service(prompt, max_tokens=600)
        
        return {
            'title': 'Conclusions and Recommendations',
            'content': conclusions_response,
            'word_count': len(conclusions_response.split()),
            'section_type': 'conclusions'
        }
    
    def _generate_references_section(self, content: str, format_style: str) -> Dict[str, Any]:
        """Generate references and citations section."""
        
        prompt = f"""
        Create a references section in {format_style} citation style.
        
        Guidelines:
        - Extract any cited sources, references, or attributions from the content
        - Format citations according to {format_style} standards
        - Include both in-text citations and a bibliography if sources are available
        - If no explicit sources, note that content is based on provided materials
        
        Content to review for sources:
        {content[:2000]}
        
        Create an appropriate references section.
        """
        
        references_response = self._query_ai_service(prompt, max_tokens=400)
        
        return {
            'title': 'References',
            'content': references_response,
            'word_count': len(references_response.split()),
            'section_type': 'references'
        }
    
    def _generate_appendices(self, content: str, report_type: str) -> Dict[str, Any]:
        """Generate appendices for comprehensive reports."""
        
        prompt = f"""
        Create appendices for a comprehensive {report_type} report.
        
        Include:
        - Supplementary data or detailed information
        - Additional charts, graphs, or tables (descriptions)
        - Extended methodology details
        - Raw data summaries
        - Technical specifications (if applicable)
        
        Base appendices on:
        {content[:2000]}
        
        Create useful appendix content that supplements the main report.
        """
        
        appendices_response = self._query_ai_service(prompt, max_tokens=500)
        
        return {
            'title': 'Appendices',
            'content': appendices_response,
            'word_count': len(appendices_response.split()),
            'section_type': 'appendices'
        }
    
    def _format_final_report(self, sections: Dict[str, Any], structure: Dict[str, Any], 
                           report_type: str, format_style: str) -> Dict[str, Any]:
        """Format the complete report with proper structure."""
        
        formatted_report = {
            'title': f"{report_type.title()} Report",
            'subtitle': f"Generated Analysis - {format_style.title()} Format",
            'generation_date': datetime.now().strftime("%B %d, %Y"),
            'document_structure': structure,
            'sections': {}
        }
        
        # Add sections in proper order
        section_order = structure.get('sections', [])
        
        for section_key in section_order:
            if section_key in ['abstract', 'executive_summary'] and 'executive_summary' in sections:
                formatted_report['sections'][section_key] = sections['executive_summary']
            elif section_key == 'introduction' and 'introduction' in sections:
                formatted_report['sections'][section_key] = sections['introduction']
            elif section_key in ['findings', 'key_findings', 'analysis'] and 'analysis' in sections:
                formatted_report['sections'][section_key] = sections['analysis']
            elif section_key in ['conclusions', 'recommendations'] and 'conclusions' in sections:
                formatted_report['sections'][section_key] = sections['conclusions']
            elif section_key == 'references' and 'references' in sections:
                formatted_report['sections'][section_key] = sections['references']
            elif section_key in ['appendices', 'detailed_appendices'] and 'appendices' in sections:
                formatted_report['sections'][section_key] = sections['appendices']
        
        # Add main sections
        if 'main_sections' in sections:
            for i, main_section in enumerate(sections['main_sections']):
                section_key = f"main_section_{i+1}"
                formatted_report['sections'][section_key] = main_section
        
        return formatted_report
    
    def _create_formatting_guidelines(self, format_style: str, report_type: str) -> Dict[str, Any]:
        """Create formatting guidelines for the report."""
        
        guidelines = {
            'document_settings': {
                'font': 'Times New Roman' if format_style == 'academic' else 'Arial',
                'font_size': '12pt',
                'line_spacing': '1.5' if format_style == 'academic' else '1.15',
                'margins': '1 inch all sides' if format_style == 'academic' else '0.75 inch',
                'page_orientation': 'Portrait'
            },
            'heading_styles': {
                'title': 'Bold, 16pt, centered',
                'section_headings': 'Bold, 14pt, left-aligned',
                'subsection_headings': 'Bold, 12pt, left-aligned',
                'paragraph_text': 'Regular, 12pt, justified'
            },
            'citation_style': {
                'academic': 'APA 7th Edition',
                'professional': 'Business citation format',
                'technical': 'IEEE format',
                'executive': 'Minimal citations, focus on content'
            }.get(format_style, 'Standard format'),
            'page_layout': {
                'title_page': True,
                'page_numbers': 'Bottom right',
                'headers': f"{report_type.title()} Report" if format_style != 'executive' else None,
                'footers': 'Page numbers and date'
            }
        }
        
        return guidelines
    
    def _create_report_metadata(self, file, report_type: str, format_style: str, 
                              length: str, include_citations: bool) -> Dict[str, Any]:
        """Create metadata for the generated report."""
        
        return {
            'source_file': {
                'filename': file.filename,
                'file_type': file.file_type,
                'file_size': getattr(file, 'file_size', 'unknown')
            },
            'generation_info': {
                'report_type': report_type,
                'format_style': format_style,
                'length': length,
                'includes_citations': include_citations,
                'generated_at': datetime.now().isoformat(),
                'service_version': '1.0'
            },
            'quality_indicators': {
                'content_analysis_depth': 'comprehensive' if length == 'comprehensive' else 'standard',
                'professional_formatting': True,
                'structured_sections': True,
                'citation_compliance': include_citations
            }
        }
    
    def _split_content_for_sections(self, content: str, num_sections: int) -> List[str]:
        """Split content into chunks for different sections."""
        words = content.split()
        chunk_size = len(words) // num_sections
        
        chunks = []
        for i in range(num_sections):
            start = i * chunk_size
            end = start + chunk_size if i < num_sections - 1 else len(words)
            chunks.append(' '.join(words[start:end]))
        
        return chunks
    
    def _estimate_word_count(self, formatted_report: Dict[str, Any]) -> int:
        """Estimate total word count for the report."""
        total_words = 0
        
        sections = formatted_report.get('sections', {})
        for section in sections.values():
            if isinstance(section, dict) and 'content' in section:
                total_words += len(section['content'].split())
            elif isinstance(section, list):
                for subsection in section:
                    if isinstance(subsection, dict) and 'content' in subsection:
                        total_words += len(subsection['content'].split())
        
        return total_words
