import os, json, logging, re
import openai
from typing import List, Dict, Any
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Safe clamp helpers
def _clampi(v, lo, hi):
    try:
        v = int(v)
    except Exception:
        v = lo
    return max(lo, min(hi, v))

class EthicalAITutorService:
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[EthicalAITutorService] Using Azure slot #{idx} ({api_base})")

    def _ask(self, prompt: str, max_tokens: int = 1200) -> str:
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are an expert AI ethics educator who creates thought-provoking ethical scenarios. Reply ONLY with valid compact JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,      # slightly more creative for diverse scenarios
                max_tokens=max_tokens,
                timeout=60,
            )

            # Validate response structure
            if not resp or "choices" not in resp or len(resp["choices"]) == 0:
                log.error(f"[EthicalAITutor] Invalid API response structure: {resp}")
                return "[]"

            message = resp["choices"][0].get("message", {})
            content = message.get("content")

            # Check for content filtering
            if content is None:
                finish_reason = resp["choices"][0].get("finish_reason")
                log.warning(f"[EthicalAITutor] No content in response. Finish reason: {finish_reason}")

                # Check if content was filtered
                if finish_reason == "content_filter":
                    log.error("[EthicalAITutor] Content was filtered by Azure content policy")
                    return "[]"

                log.error(f"[EthicalAITutor] Missing content field. Full response: {resp}")
                return "[]"

            return content.strip()

        except openai.error.RateLimitError as e:
            log.warning(f"[EthicalAITutor] Rate limited: {e}; rotating key.")
            self._use_new_credentials()
            raise
        except Exception as e:
            log.error(f"[EthicalAITutor] Error in _ask: {e}", exc_info=True)
            return "[]"

    def generate_scenarios_from_text(
        self,
        text: str,
        k: int = 3,
        difficulty: str = "medium",
        scenario_type: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        From page text, generate up to k ethical AI scenarios.

        scenario_type options:
        - 'mixed': Mix of all types
        - 'bias_fairness': Bias, discrimination, and fairness issues
        - 'privacy_security': Data privacy and security concerns
        - 'transparency_accountability': Explainability and accountability
        - 'safety_reliability': AI safety and reliability issues
        - 'social_impact': Broader societal and environmental impacts

        Returns list of {
            type: str,
            scenario: str,
            stakeholders: [str],
            ethical_considerations: [str],
            discussion_questions: [str],
            recommended_approach: str,
            difficulty: str
        }
        """
        if not (text or "").strip():
            return []

        k = _clampi(k, 1, 3)
        difficulty = (difficulty or "medium").lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        scenario_type = (scenario_type or "mixed").lower()
        valid_types = {"mixed", "bias_fairness", "privacy_security", "transparency_accountability", "safety_reliability", "social_impact"}
        if scenario_type not in valid_types:
            scenario_type = "mixed"

        type_instructions = self._get_type_instructions(scenario_type)

        prompt = (
            "Create up to {k} thought-provoking ETHICAL AI SCENARIOS from the TEXT.\n"
            "Difficulty = '{difficulty}'. Type = '{scenario_type}'.\n"
            "{type_instructions}\n\n"
            "Return ONLY a JSON array of objects with keys:\n"
            "- type: scenario type (bias_fairness/privacy_security/transparency_accountability/safety_reliability/social_impact)\n"
            "- scenario: detailed scenario description (40-100 words)\n"
            "- stakeholders: array of 2-4 affected parties or stakeholder groups\n"
            "- ethical_considerations: array of 3-5 key ethical issues to consider\n"
            "- discussion_questions: array of 3-4 open-ended questions for reflection\n"
            "- recommended_approach: brief ethical framework or approach (40-80 words)\n"
            "- difficulty: '{difficulty}'\n\n"
            "Make scenarios realistic, nuanced, and relevant to real-world AI applications.\n\n"
            "TEXT:\n{t}"
        ).format(
            k=k,
            difficulty=difficulty,
            scenario_type=scenario_type,
            type_instructions=type_instructions,
            t=(text[:12000])
        )

        raw = self._ask(prompt, max_tokens=1200)

        # Try JSON parse
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [self._normalize_scenario(x, difficulty) for x in data if isinstance(x, dict)]
        except Exception as e:
            log.warning(f"[EthicalAITutor] JSON parse failed: {e}")
            pass

        # Fallback: create simple scenario from text
        return [self._create_fallback_scenario(text, difficulty)]

    def _get_type_instructions(self, scenario_type: str) -> str:
        instructions = {
            "mixed": "Include diverse ethical scenarios covering bias, privacy, transparency, safety, and social impact.",
            "bias_fairness": "Focus on algorithmic bias, discrimination, fairness in AI systems, and equitable outcomes.",
            "privacy_security": "Focus on data privacy, surveillance, consent, security vulnerabilities, and data protection.",
            "transparency_accountability": "Focus on explainability, interpretability, accountability, and responsible AI governance.",
            "safety_reliability": "Focus on AI safety, robustness, reliability, unintended consequences, and fail-safes.",
            "social_impact": "Focus on societal implications, environmental impact, job displacement, and long-term effects on humanity."
        }
        return instructions.get(scenario_type, instructions["mixed"])

    def _normalize_scenario(self, obj: Dict[str, Any], difficulty: str) -> Dict[str, Any]:
        stype = (obj.get("type") or "bias_fairness").strip().lower()
        valid_types = {"bias_fairness", "privacy_security", "transparency_accountability", "safety_reliability", "social_impact"}
        if stype not in valid_types:
            stype = "bias_fairness"

        scenario = (obj.get("scenario") or "").strip()
        if len(scenario) > 600:
            scenario = scenario[:600]
        if not scenario:
            scenario = "Scenario not available"

        stakeholders = obj.get("stakeholders") or []
        if not isinstance(stakeholders, list):
            stakeholders = [str(stakeholders)]
        stakeholders = [str(x or "").strip() for x in stakeholders if str(x or "").strip()][:4]
        if not stakeholders:
            stakeholders = ["AI developers", "End users", "Society"]

        ethical_considerations = obj.get("ethical_considerations") or []
        if not isinstance(ethical_considerations, list):
            ethical_considerations = [str(ethical_considerations)]
        ethical_considerations = [str(x or "").strip() for x in ethical_considerations if str(x or "").strip()][:5]
        if not ethical_considerations:
            ethical_considerations = ["Fairness", "Privacy", "Transparency", "Accountability"]

        discussion_questions = obj.get("discussion_questions") or []
        if not isinstance(discussion_questions, list):
            discussion_questions = [str(discussion_questions)]
        discussion_questions = [str(x or "").strip() for x in discussion_questions if str(x or "").strip()][:4]
        if not discussion_questions:
            discussion_questions = [
                "What are the ethical implications?",
                "Who is affected and how?",
                "What would be a responsible solution?"
            ]

        recommended_approach = (obj.get("recommended_approach") or "").strip()
        if len(recommended_approach) > 500:
            recommended_approach = recommended_approach[:500]
        if not recommended_approach:
            recommended_approach = "Apply ethical AI principles with stakeholder consultation and transparent decision-making."

        return {
            "type": stype,
            "scenario": scenario,
            "stakeholders": stakeholders,
            "ethical_considerations": ethical_considerations,
            "discussion_questions": discussion_questions,
            "recommended_approach": recommended_approach,
            "difficulty": difficulty
        }

    def _create_fallback_scenario(self, text: str, difficulty: str) -> Dict[str, Any]:
        """Create a simple scenario when API fails"""
        return {
            "type": "bias_fairness",
            "scenario": "An AI system trained on historical data is being deployed in a critical decision-making context. Consider the ethical implications of using past data that may contain historical biases.",
            "stakeholders": [
                "AI system users",
                "Affected individuals",
                "AI developers",
                "Regulatory bodies"
            ],
            "ethical_considerations": [
                "Historical bias in training data",
                "Fairness and equity in outcomes",
                "Accountability for AI decisions",
                "Transparency in AI operations",
                "Impact on vulnerable populations"
            ],
            "discussion_questions": [
                "How can we identify and mitigate historical biases in the training data?",
                "What measures should be in place to ensure fairness?",
                "Who should be held accountable if the AI makes biased decisions?",
                "How can we make the AI's decision-making process more transparent?"
            ],
            "recommended_approach": "Conduct thorough bias audits, implement fairness metrics, ensure diverse representation in training data, establish clear accountability frameworks, and maintain ongoing monitoring and evaluation of AI system outcomes.",
            "difficulty": difficulty
        }
