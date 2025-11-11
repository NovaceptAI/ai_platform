# app/services/stages/create/data_story_builder_service.py
"""
Data Story Builder Service

Core service for generating data analysis stories with AI insights and visualizations.
"""

import io
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from app.services.ai_service_base import AIServiceBase
from app.db import db

logger = logging.getLogger(__name__)

# Set style for better-looking charts
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'


def convert_to_json_serializable(obj):
    """
    Recursively convert numpy/pandas types to JSON-serializable Python types.
    
    Args:
        obj: Object to convert (can be dict, list, numpy type, etc.)
        
    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray, pd.Series)):
        return convert_to_json_serializable(obj.tolist())
    elif pd.isna(obj):
        return None
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    else:
        return obj


class DataStoryBuilderService(AIServiceBase):
    """Service for generating data analysis stories with AI insights and visualizations."""

    def __init__(self):
        """Initialize service."""
        super().__init__()
        self.service_name = "DataStoryBuilder"

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about this service.

        Returns:
            Dictionary with service information
        """
        return {
            'service_name': 'DataStoryBuilder',
            'description': 'Transforms CSV/Excel datasets into compelling visual stories with AI insights',
            'capabilities': [
                'data_profiling',
                'ai_insights_generation',
                'narrative_creation',
                'chart_suggestions',
                'visualization_generation'
            ],
            'supported_formats': ['csv', 'xlsx', 'xls'],
            'supported_charts': ['line', 'bar', 'scatter', 'histogram', 'pie', 'heatmap'],
            'max_file_size_mb': 50,
            'max_rows': 100000,
            'version': '1.0'
        }

    # ========== STAGE 1: DATA PROFILING ==========

    def profile_dataset(self, df, filename):
        """
        Generate comprehensive data profile from pandas DataFrame.

        Args:
            df: pandas DataFrame
            filename: Original filename

        Returns:
            dict: Data profile with dataset info and column statistics
        """
        logger.info(f"Profiling dataset: {filename}")

        # Basic dataset info
        dataset_info = {
            "file_name": filename,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB",
            "has_missing_values": bool(df.isnull().any().any()),
            "total_missing_values": int(df.isnull().sum().sum())
        }

        # Profile each column
        columns = []
        for col in df.columns:
            col_profile = self._profile_column(df, col)
            columns.append(col_profile)

        # Suggest chart types based on data
        suggested_charts = self._suggest_charts(df, columns)

        profile = {
            "dataset_info": dataset_info,
            "columns": columns,
            "suggested_charts": suggested_charts
        }

        # Convert all numpy/pandas types to JSON-serializable Python types
        profile = convert_to_json_serializable(profile)

        logger.info(f"Profile complete: {len(columns)} columns analyzed")
        return profile

    def _profile_column(self, df, col_name):
        """Profile a single column."""
        col = df[col_name]
        total_rows = len(df)
        missing_count = int(col.isnull().sum())
        missing_percent = round((missing_count / total_rows) * 100, 2) if total_rows > 0 else 0

        profile = {
            "name": col_name,
            "type": str(col.dtype),
            "missing": missing_count,
            "missing_percent": missing_percent,
            "unique": int(col.nunique())
        }

        # Numeric columns
        if pd.api.types.is_numeric_dtype(col):
            profile["stats"] = {
                "mean": float(col.mean()) if not col.isnull().all() else None,
                "median": float(col.median()) if not col.isnull().all() else None,
                "std": float(col.std()) if not col.isnull().all() else None,
                "min": float(col.min()) if not col.isnull().all() else None,
                "max": float(col.max()) if not col.isnull().all() else None,
                "q25": float(col.quantile(0.25)) if not col.isnull().all() else None,
                "q75": float(col.quantile(0.75)) if not col.isnull().all() else None
            }

        # Datetime columns
        elif pd.api.types.is_datetime64_any_dtype(col):
            profile["type"] = "datetime"
            if not col.isnull().all():
                profile["stats"] = {
                    "min": col.min().isoformat() if pd.notna(col.min()) else None,
                    "max": col.max().isoformat() if pd.notna(col.max()) else None,
                    "range_days": (col.max() - col.min()).days if pd.notna(col.min()) and pd.notna(col.max()) else None
                }

        # Categorical/text columns
        else:
            # Get top 10 most frequent values
            value_counts = col.value_counts().head(10)
            profile["top_values"] = [
                {"value": str(val), "count": int(count)}
                for val, count in value_counts.items()
            ]

        return profile

    def _suggest_charts(self, df, columns):
        """Suggest appropriate chart types based on data characteristics."""
        suggestions = []

        # Find datetime columns
        datetime_cols = [c for c in columns if c['type'] == 'datetime']
        numeric_cols = [c for c in columns if 'stats' in c and c['type'] != 'datetime']
        categorical_cols = [c for c in columns if c['type'] in ['object', 'string', 'category']]

        # Time series: datetime + numeric
        if datetime_cols and numeric_cols:
            for dt_col in datetime_cols[:1]:  # Take first datetime
                for num_col in numeric_cols[:3]:  # Take up to 3 numeric
                    suggestions.append({
                        "chart_type": "line",
                        "x_column": dt_col['name'],
                        "y_column": num_col['name'],
                        "title": f"{num_col['name']} over time",
                        "priority": "high"
                    })

        # Distribution: numeric columns
        for num_col in numeric_cols[:3]:
            suggestions.append({
                "chart_type": "histogram",
                "column": num_col['name'],
                "title": f"Distribution of {num_col['name']}",
                "priority": "medium"
            })

        # Categorical breakdown
        for cat_col in categorical_cols[:2]:
            if cat_col['unique'] <= 20:  # Not too many categories
                suggestions.append({
                    "chart_type": "bar",
                    "column": cat_col['name'],
                    "title": f"Count by {cat_col['name']}",
                    "priority": "medium"
                })

        # Correlation: two numeric columns
        if len(numeric_cols) >= 2:
            suggestions.append({
                "chart_type": "scatter",
                "x_column": numeric_cols[0]['name'],
                "y_column": numeric_cols[1]['name'],
                "title": f"{numeric_cols[1]['name']} vs {numeric_cols[0]['name']}",
                "priority": "low"
            })

        return suggestions

    # ========== STAGE 1: AI INSIGHTS GENERATION ==========

    def generate_insights(self, df: pd.DataFrame, data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered insights from the data.

        Args:
            df: pandas DataFrame
            data_profile: Data profile from profile_dataset()

        Returns:
            dict: Insights with narratives and recommendations
        """
        try:
            self._log_analysis_start("AI insights generation", f"{len(df)} rows, {len(df.columns)} columns")

            # Prepare data summary for GPT-4
            data_summary = self._prepare_data_summary(df, data_profile)

            # Call GPT-4
            prompt = self._build_insights_prompt(data_summary)

            messages = [
                {
                    "role": "system",
                    "content": "You are a data analyst expert. Analyze datasets and provide clear, actionable insights in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = self._make_openai_call(
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )

            # Parse insights into structured format
            insights = self._parse_json_response(response)

            # Validate insights structure
            if not self._validate_response(insights, ['key_insights', 'narrative', 'recommendations']):
                logger.warning("Insights response missing required keys, using fallback")
                insights = self._create_fallback_insights(response)

            self._log_analysis_complete("AI insights generation", 
                f"{len(insights.get('key_insights', []))} insights generated")

            return insights

        except Exception as e:
            self._log_analysis_error("AI insights generation", e)
            raise

    def _prepare_data_summary(self, df, data_profile):
        """Prepare concise data summary for GPT-4."""
        # Sample data (first 5 rows)
        sample_data = df.head(5).to_dict(orient='records')

        # Column summaries
        col_summaries = []
        for col in data_profile['columns']:
            summary = f"{col['name']} ({col['type']}): {col['unique']} unique values"
            if 'stats' in col:
                if 'mean' in col['stats'] and col['stats']['mean'] is not None:
                    summary += f", mean={col['stats']['mean']:.2f}"
            col_summaries.append(summary)

        return {
            "dataset_info": data_profile['dataset_info'],
            "columns": col_summaries,
            "sample_data": sample_data
        }

    def _build_insights_prompt(self, data_summary):
        """Build prompt for GPT-4 insights generation."""
        prompt = f"""Analyze this dataset and provide insights:

Dataset Overview:
- Rows: {data_summary['dataset_info']['total_rows']}
- Columns: {data_summary['dataset_info']['total_columns']}
- Filename: {data_summary['dataset_info']['file_name']}

Columns:
{chr(10).join(f"- {col}" for col in data_summary['columns'])}

Sample Data (first 5 rows):
{json.dumps(data_summary['sample_data'], indent=2)}

Provide a data analysis report in the following JSON format:
{{
  "key_insights": [
    {{
      "id": "insight_1",
      "type": "trend|correlation|anomaly|pattern",
      "title": "Brief title (max 8 words)",
      "description": "Detailed description (2-3 sentences)",
      "confidence": "high|medium|low"
    }}
  ],
  "narrative": {{
    "introduction": "Brief overview of the dataset (2-3 sentences)",
    "key_findings": "Main patterns and trends discovered (3-4 sentences)",
    "conclusion": "Overall assessment and implications (2 sentences)"
  }},
  "recommendations": [
    "Actionable recommendation 1",
    "Actionable recommendation 2",
    "Actionable recommendation 3"
  ]
}}

Focus on:
1. Identify 3-5 key insights (trends, patterns, anomalies, correlations)
2. Write a compelling narrative that tells the data's story
3. Provide 3-4 actionable recommendations based on the insights

Return ONLY valid JSON, no additional text."""

        return prompt

    def _parse_insights(self, insights_text: str) -> Dict[str, Any]:
        """
        Parse GPT-4 response into structured insights.
        Deprecated: Use _parse_json_response from base class instead.
        """
        return self._parse_json_response(insights_text)

    def _create_fallback_insights(self, raw_response: str) -> Dict[str, Any]:
        """Create fallback insights structure when parsing fails."""
        logger.warning("Creating fallback insights structure")
        return {
            "key_insights": [
                {
                    "id": "insight_1",
                    "type": "pattern",
                    "title": "Dataset Analysis Complete",
                    "description": "The AI has analyzed your dataset. Review the data profile for detailed statistics.",
                    "confidence": "medium"
                }
            ],
            "narrative": {
                "introduction": "Analysis completed for your dataset.",
                "key_findings": raw_response[:500] if raw_response else "See data profile for details.",
                "conclusion": "Review the visualizations to explore patterns in your data."
            },
            "recommendations": [
                "Review data quality and missing values",
                "Explore suggested visualizations",
                "Investigate key columns for insights"
            ]
        }

    # ========== STAGE 2: VISUALIZATION GENERATION ==========

    def generate_chart(self, df, chart_config):
        """
        Generate a chart image from DataFrame.

        Args:
            df: pandas DataFrame
            chart_config: Chart configuration dict with:
                - chart_type: line|bar|scatter|histogram|pie|heatmap
                - title: Chart title
                - x_column: X-axis column (if applicable)
                - y_column: Y-axis column (if applicable)
                - column: Single column (for histogram/pie)

        Returns:
            BytesIO: Chart image as PNG bytes
        """
        chart_type = chart_config['chart_type']
        title = chart_config.get('title', 'Chart')

        logger.info(f"Generating {chart_type} chart: {title}")

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        try:
            if chart_type == 'line':
                self._create_line_chart(df, chart_config, ax)
            elif chart_type == 'bar':
                self._create_bar_chart(df, chart_config, ax)
            elif chart_type == 'scatter':
                self._create_scatter_chart(df, chart_config, ax)
            elif chart_type == 'histogram':
                self._create_histogram(df, chart_config, ax)
            elif chart_type == 'pie':
                self._create_pie_chart(df, chart_config, ax)
            elif chart_type == 'heatmap':
                self._create_heatmap(df, chart_config, ax)
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")

            # Set title
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

            # Adjust layout
            plt.tight_layout()

            # Save to bytes
            img_bytes = io.BytesIO()
            plt.savefig(img_bytes, format='png', bbox_inches='tight', facecolor='white')
            img_bytes.seek(0)

            plt.close(fig)

            logger.info(f"Chart generated successfully: {title}")
            return img_bytes

        except Exception as e:
            plt.close(fig)
            logger.error(f"Error generating chart: {str(e)}")
            raise

    def _create_line_chart(self, df, config, ax):
        """Create line chart."""
        x_col = config['x_column']
        y_col = config['y_column']

        # Sort by x column if datetime
        if pd.api.types.is_datetime64_any_dtype(df[x_col]):
            df = df.sort_values(x_col)

        ax.plot(df[x_col], df[y_col], marker='o', linewidth=2, markersize=4)
        ax.set_xlabel(x_col, fontsize=11)
        ax.set_ylabel(y_col, fontsize=11)
        ax.grid(True, alpha=0.3)

    def _create_bar_chart(self, df, config, ax):
        """Create bar chart."""
        col = config['column']

        # Get value counts
        value_counts = df[col].value_counts().head(15)  # Top 15

        ax.bar(range(len(value_counts)), value_counts.values, color='steelblue')
        ax.set_xticks(range(len(value_counts)))
        ax.set_xticklabels(value_counts.index, rotation=45, ha='right')
        ax.set_xlabel(col, fontsize=11)
        ax.set_ylabel('Count', fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')

    def _create_scatter_chart(self, df, config, ax):
        """Create scatter plot."""
        x_col = config['x_column']
        y_col = config['y_column']

        ax.scatter(df[x_col], df[y_col], alpha=0.6, s=30, color='steelblue')
        ax.set_xlabel(x_col, fontsize=11)
        ax.set_ylabel(y_col, fontsize=11)
        ax.grid(True, alpha=0.3)

    def _create_histogram(self, df, config, ax):
        """Create histogram."""
        col = config['column']

        ax.hist(df[col].dropna(), bins=30, color='steelblue', edgecolor='black', alpha=0.7)
        ax.set_xlabel(col, fontsize=11)
        ax.set_ylabel('Frequency', fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')

    def _create_pie_chart(self, df, config, ax):
        """Create pie chart."""
        col = config['column']

        # Get top 10 categories
        value_counts = df[col].value_counts().head(10)

        ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')

    def _create_heatmap(self, df, config, ax):
        """Create correlation heatmap."""
        # Select only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])

        # Calculate correlation
        corr = numeric_df.corr()

        # Create heatmap
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0,
                    square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)

    # ========== HELPER METHODS ==========

    def _extract_file_content(self, file) -> bytes:
        """
        Extract file content from uploaded file.
        
        Args:
            file: UploadedFile object
            
        Returns:
            File bytes
        """
        try:
            from app.models.files import UploadedFile

            # For CSV/Excel files, we need the raw file bytes
            # This should integrate with your existing file storage system
            # TODO: Implement based on your storage setup
            
            logger.info(f"Extracting file content for {file.original_file_name}")
            
            # Placeholder - adjust based on your file storage
            # If files are in Azure, download from file.file_path
            # If files are in local storage, read from file path
            
            return b""  # Return actual file bytes

        except Exception as e:
            logger.error(f"Error extracting file content: {str(e)}")
            raise