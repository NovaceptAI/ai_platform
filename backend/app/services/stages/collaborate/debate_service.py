"""
Digital Debate Platform AI Service

Handles AI-powered debate analysis, argument evaluation, fact-checking,
and real-time moderation for structured debates.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

logger = logging.getLogger(__name__)


class DebateService(AIServiceBase):
    """Service for AI-assisted debate analysis and moderation."""

    def __init__(self):
        super().__init__()
        self.service_name = "DebateService"
        self.model_name = "gpt-4"

    def get_service_info(self) -> Dict[str, Any]:
        """Return service metadata."""
        return {
            'service_name': 'DebateService',
            'description': 'AI-assisted debate platform with argument analysis and moderation',
            'capabilities': [
                'argument_analysis',
                'fact_checking',
                'fallacy_detection',
                'real_time_moderation',
                'performance_scoring',
                'debate_summarization'
            ],
            'supported_formats': ['parliamentary', 'lincoln_douglas', 'public_forum', 'free_form'],
            'categories': ['politics', 'science', 'philosophy', 'ethics', 'education', 'technology']
        }

    def analyze_argument(
        self,
        argument_text: str,
        debate_context: Optional[Dict[str, Any]] = None,
        previous_arguments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a debate argument using GPT-4.

        Args:
            argument_text: The argument to analyze
            debate_context: Context about the debate (motion, format, etc.)
            previous_arguments: Previous arguments in the debate for context

        Returns:
            Dictionary with comprehensive argument analysis
        """
        try:
            logger.info("[DebateService] Analyzing argument")

            # Build context
            context_str = ""
            if debate_context:
                context_str = f"\n\nDebate Motion: {debate_context.get('motion', 'N/A')}"
                if debate_context.get('format'):
                    context_str += f"\nDebate Format: {debate_context.get('format')}"

            previous_args_str = ""
            if previous_arguments:
                prev_list = []
                for i, arg in enumerate(previous_arguments[-3:]):  # Last 3 arguments for context
                    prev_list.append(f"{i+1}. [{arg.get('role', 'Unknown')}]: {arg.get('content', '')[:200]}...")
                previous_args_str = "\n\nPrevious Arguments:\n" + "\n".join(prev_list)

            system_prompt = """You are an expert debate analyst and critical thinking instructor. Analyze the provided argument with academic rigor.

CRITICAL INSTRUCTIONS:
1. Evaluate argument strength, logical structure, and evidence quality
2. Identify any logical fallacies or weak reasoning
3. Assess persuasiveness and rhetorical effectiveness
4. Be objective and balanced in your analysis
5. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after

JSON STRUCTURE (copy this exactly):
{
    "argument_strength": 7.5,
    "logical_structure": {
        "claim": "Main claim statement",
        "evidence": ["Evidence 1", "Evidence 2"],
        "reasoning": "How evidence supports claim",
        "conclusion": "Conclusion statement"
    },
    "fallacies_detected": [
        {
            "type": "ad_hominem",
            "severity": "minor",
            "explanation": "Brief explanation",
            "location": "Quote from argument"
        }
    ],
    "strengths": ["Strength 1", "Strength 2"],
    "weaknesses": ["Weakness 1", "Weakness 2"],
    "sentiment": "positive|negative|neutral",
    "persuasiveness": 8.0,
    "evidence_quality": 7.0,
    "logical_consistency": 8.5,
    "improvement_suggestions": ["Suggestion 1", "Suggestion 2"]
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"""Analyze this debate argument:{context_str}{previous_args_str}

ARGUMENT TO ANALYZE:
{argument_text}

Provide comprehensive analysis in the JSON format specified."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            result = self._parse_json_response(response_text)

            # Check if parsing failed
            if 'error' in result and 'raw_response' in result:
                logger.error(f"[DebateService] Failed to parse argument analysis")
                return {
                    'success': False,
                    'error': 'Failed to parse AI analysis response'
                }

            # Validate required fields
            required_fields = ['argument_strength', 'logical_structure']
            if not self._validate_response(result, required_fields):
                logger.error(f"[DebateService] Response missing required fields")
                return {
                    'success': False,
                    'error': 'Invalid analysis structure received'
                }

            logger.info("[DebateService] Argument analysis completed successfully")

            return {
                'success': True,
                'analysis': result,
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[DebateService] Error analyzing argument: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def fact_check_claims(
        self,
        claims: List[str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fact-check claims made in debate arguments.

        Args:
            claims: List of factual claims to verify
            context: Additional context for fact-checking

        Returns:
            Dictionary with fact-check results for each claim
        """
        try:
            logger.info(f"[DebateService] Fact-checking {len(claims)} claims")

            if not claims:
                return {
                    'success': True,
                    'fact_checks': []
                }

            claims_str = "\n".join([f"{i+1}. {claim}" for i, claim in enumerate(claims)])
            context_str = f"\n\nContext: {context}" if context else ""

            system_prompt = """You are a fact-checking expert. Evaluate the factual accuracy of claims based on verifiable information.

CRITICAL INSTRUCTIONS:
1. Assess each claim as: "true", "false", "partially_true", "unverifiable", or "misleading"
2. Provide brief evidence for your verdict
3. Include confidence level (0-100%)
4. Cite sources when possible
5. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after

JSON STRUCTURE:
{
    "fact_checks": [
        {
            "claim": "Original claim text",
            "verdict": "true|false|partially_true|unverifiable|misleading",
            "confidence": 85,
            "explanation": "Brief explanation of verdict",
            "evidence": "Supporting evidence or reasoning",
            "sources": ["Source 1", "Source 2"]
        }
    ],
    "overall_accuracy": 75
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"""Fact-check these claims:{context_str}

CLAIMS:
{claims_str}

Provide fact-check results in the JSON format specified."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,  # Lower temperature for fact-checking
                max_tokens=2000
            )

            result = self._parse_json_response(response_text)

            if 'error' in result and 'raw_response' in result:
                logger.error(f"[DebateService] Failed to parse fact-check response")
                return {
                    'success': False,
                    'error': 'Failed to parse fact-check response'
                }

            if not self._validate_response(result, ['fact_checks']):
                logger.error(f"[DebateService] Invalid fact-check structure")
                return {
                    'success': False,
                    'error': 'Invalid fact-check structure received'
                }

            logger.info(f"[DebateService] Fact-checking completed successfully")

            return {
                'success': True,
                'fact_checks': result.get('fact_checks', []),
                'overall_accuracy': result.get('overall_accuracy', 0),
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[DebateService] Error in fact-checking: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def moderate_content(
        self,
        content: str,
        debate_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Moderate debate content for rule violations.

        Args:
            content: Content to moderate
            debate_rules: Debate-specific rules and guidelines

        Returns:
            Moderation result with flags and suggestions
        """
        try:
            logger.info("[DebateService] Moderating content")

            rules_str = ""
            if debate_rules:
                rules_str = f"\n\nDebate Rules:\n{json.dumps(debate_rules, indent=2)}"

            system_prompt = """You are a debate moderator ensuring respectful and productive discourse.

CRITICAL INSTRUCTIONS:
1. Check for personal attacks, offensive language, or rule violations
2. Assess whether content is appropriate for constructive debate
3. Provide specific reasons for any flags
4. Suggest improvements if needed
5. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after

JSON STRUCTURE:
{
    "is_appropriate": true,
    "violations": [
        {
            "type": "personal_attack|offensive_language|off_topic|time_violation",
            "severity": "minor|moderate|severe",
            "description": "Specific violation description",
            "quote": "Relevant quote from content"
        }
    ],
    "moderation_action": "none|warning|remove|escalate",
    "suggestion": "How to improve the contribution",
    "respectfulness_score": 8
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"""Moderate this debate content:{rules_str}

CONTENT:
{content}

Provide moderation assessment in the JSON format specified."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Low temperature for consistent moderation
                max_tokens=1000
            )

            result = self._parse_json_response(response_text)

            if 'error' in result and 'raw_response' in result:
                logger.warning("[DebateService] Failed to parse moderation response, defaulting to safe")
                return {
                    'success': True,
                    'is_appropriate': True,
                    'violations': [],
                    'moderation_action': 'none'
                }

            logger.info("[DebateService] Content moderation completed")

            return {
                'success': True,
                'moderation': result,
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[DebateService] Error in moderation: {str(e)}")
            # Default to safe in case of errors
            return {
                'success': True,
                'is_appropriate': True,
                'violations': [],
                'moderation_action': 'none',
                'error': str(e)
            }

    def calculate_performance_metrics(
        self,
        participant_messages: List[Dict[str, Any]],
        debate_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics for a debate participant.

        Args:
            participant_messages: All messages from the participant
            debate_context: Debate context and settings

        Returns:
            Comprehensive performance metrics
        """
        try:
            logger.info(f"[DebateService] Calculating performance metrics for {len(participant_messages)} messages")

            if not participant_messages:
                return {
                    'success': True,
                    'metrics': self._get_default_metrics()
                }

            # Prepare message summary
            messages_summary = []
            for msg in participant_messages[:10]:  # Limit to 10 messages for token efficiency
                messages_summary.append({
                    'type': msg.get('message_type', 'unknown'),
                    'content': msg.get('content', '')[:300],  # Truncate long messages
                    'analysis': msg.get('ai_analysis', {})
                })

            system_prompt = """You are a debate coach providing comprehensive performance assessment.

CRITICAL INSTRUCTIONS:
1. Analyze overall debate performance across multiple dimensions
2. Assess argumentation, evidence usage, and rhetorical skills
3. Provide actionable improvement suggestions
4. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after

JSON STRUCTURE:
{
    "argument_metrics": {
        "total_arguments": 5,
        "average_strength": 7.5,
        "evidence_usage": 8,
        "logical_consistency": 8.0
    },
    "rebuttal_metrics": {
        "total_rebuttals": 3,
        "effectiveness_score": 7.0,
        "responsiveness": 8.5
    },
    "communication_metrics": {
        "clarity_score": 8.5,
        "conciseness_score": 7.0,
        "persuasiveness_score": 8.0
    },
    "skills_assessment": {
        "critical_thinking": 8,
        "logical_reasoning": 7.5,
        "evidence_evaluation": 7,
        "argumentation": 8.5,
        "persuasion": 8
    },
    "improvement_areas": [
        {
            "area": "Evidence Quality",
            "current_score": 6.5,
            "suggestions": ["Suggestion 1", "Suggestion 2"]
        }
    ],
    "overall_score": 7.8
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"""Assess this participant's debate performance:

Debate Motion: {debate_context.get('motion', 'N/A')}
Role: {debate_context.get('role', 'N/A')}
Format: {debate_context.get('format', 'N/A')}

Messages and Arguments:
{json.dumps(messages_summary, indent=2)}

Provide comprehensive performance assessment in the JSON format specified."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            result = self._parse_json_response(response_text)

            if 'error' in result and 'raw_response' in result:
                logger.error("[DebateService] Failed to parse performance metrics")
                return {
                    'success': True,
                    'metrics': self._get_default_metrics()
                }

            logger.info("[DebateService] Performance metrics calculated successfully")

            return {
                'success': True,
                'metrics': result,
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[DebateService] Error calculating performance: {str(e)}")
            return {
                'success': True,
                'metrics': self._get_default_metrics(),
                'error': str(e)
            }

    def generate_debate_summary(
        self,
        debate_data: Dict[str, Any],
        all_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive debate summary with AI insights.

        Args:
            debate_data: Debate metadata
            all_messages: All messages from the debate

        Returns:
            Comprehensive debate summary
        """
        try:
            logger.info("[DebateService] Generating debate summary")

            # Prepare messages by round
            messages_by_round = {}
            for msg in all_messages:
                round_num = msg.get('round_number', 0)
                if round_num not in messages_by_round:
                    messages_by_round[round_num] = []
                messages_by_round[round_num].append({
                    'type': msg.get('message_type'),
                    'role': msg.get('participant_role', 'unknown'),
                    'content': msg.get('content', '')[:200],  # Truncate
                    'strength': msg.get('ai_analysis', {}).get('argument_strength', 0)
                })

            system_prompt = """You are a debate judge providing final analysis and verdict.

CRITICAL INSTRUCTIONS:
1. Summarize the debate objectively
2. Identify strongest arguments from each side
3. Evaluate logical fallacies and debate quality
4. Provide a reasoned verdict (can be tie)
5. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after

JSON STRUCTURE:
{
    "overall_quality": 8,
    "winner": "proposition|opposition|tie",
    "verdict_reasoning": "Explanation of verdict",
    "strongest_arguments": [
        {
            "side": "proposition",
            "argument": "Brief summary",
            "strength": 8.5
        }
    ],
    "key_moments": [
        {
            "round": 2,
            "description": "Turning point description"
        }
    ],
    "logical_fallacies_detected": [
        {
            "side": "opposition",
            "fallacy": "straw man",
            "impact": "moderate"
        }
    ],
    "statistics": {
        "total_arguments": 12,
        "total_rebuttals": 8,
        "proposition_avg_strength": 7.5,
        "opposition_avg_strength": 7.2
    },
    "improvement_suggestions": ["Suggestion 1", "Suggestion 2"]
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"""Provide final analysis for this debate:

Motion: {debate_data.get('motion', 'N/A')}
Format: {debate_data.get('format', 'N/A')}
Duration: {debate_data.get('duration', 'N/A')}

Arguments by Round:
{json.dumps(messages_by_round, indent=2)}

Provide comprehensive debate summary in the JSON format specified."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )

            result = self._parse_json_response(response_text)

            if 'error' in result and 'raw_response' in result:
                logger.error("[DebateService] Failed to parse debate summary")
                return {
                    'success': False,
                    'error': 'Failed to generate debate summary'
                }

            logger.info("[DebateService] Debate summary generated successfully")

            return {
                'success': True,
                'summary': result,
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[DebateService] Error generating summary: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics structure when analysis fails."""
        return {
            "argument_metrics": {
                "total_arguments": 0,
                "average_strength": 0,
                "evidence_usage": 0,
                "logical_consistency": 0
            },
            "rebuttal_metrics": {
                "total_rebuttals": 0,
                "effectiveness_score": 0,
                "responsiveness": 0
            },
            "communication_metrics": {
                "clarity_score": 0,
                "conciseness_score": 0,
                "persuasiveness_score": 0
            },
            "skills_assessment": {
                "critical_thinking": 0,
                "logical_reasoning": 0,
                "evidence_evaluation": 0,
                "argumentation": 0,
                "persuasion": 0
            },
            "improvement_areas": [],
            "overall_score": 0
        }

    def suggest_counter_arguments(
        self,
        original_argument: str,
        debate_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Suggest potential counter-arguments (educational feature).

        Args:
            original_argument: The argument to counter
            debate_context: Debate context

        Returns:
            List of suggested counter-arguments with reasoning
        """
        try:
            logger.info("[DebateService] Generating counter-argument suggestions")

            system_prompt = """You are a debate coach helping students learn argumentation.

CRITICAL INSTRUCTIONS:
1. Suggest 3-5 strong counter-arguments
2. Explain the reasoning behind each counter
3. Identify weaknesses in the original argument
4. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after

JSON STRUCTURE:
{
    "counter_arguments": [
        {
            "argument": "Counter-argument text",
            "reasoning": "Why this counter is effective",
            "targets": "Which part of original argument it addresses",
            "strength": 8
        }
    ],
    "weaknesses_identified": ["Weakness 1", "Weakness 2"]
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"""Suggest counter-arguments for this debate argument:

Motion: {debate_context.get('motion', 'N/A')}

ORIGINAL ARGUMENT:
{original_argument}

Provide counter-argument suggestions in the JSON format specified."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # Higher temperature for creative suggestions
                max_tokens=1500
            )

            result = self._parse_json_response(response_text)

            if 'error' in result and 'raw_response' in result:
                logger.error("[DebateService] Failed to parse counter-arguments")
                return {
                    'success': False,
                    'error': 'Failed to generate counter-arguments'
                }

            logger.info("[DebateService] Counter-arguments generated successfully")

            return {
                'success': True,
                'suggestions': result,
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[DebateService] Error generating counter-arguments: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
