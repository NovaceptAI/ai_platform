# app/services/stages/master/science_lab_service.py
import os
import json
import logging
import math
from typing import Dict, List, Any
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class ScienceLabService:
    """
    Provides virtual science lab simulations and AI tutoring.
    Supports physics, chemistry, and biology experiments.
    """

    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[ScienceLab] Using Azure OpenAI slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.7, max_tokens=1000, timeout=40) -> str:
        try:
            r = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            log.error(f"[ScienceLab] OpenAI API error: {e}")
            self._use_new_credentials()
            raise

    # =============================================================================
    # PHYSICS SIMULATIONS
    # =============================================================================

    def simulate_pendulum(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a simple pendulum.
        params: {length: float (meters), initial_angle: float (degrees), gravity: float (m/s²)}
        """
        length = params.get('length', 1.0)  # meters
        initial_angle = params.get('initial_angle', 15)  # degrees
        gravity = params.get('gravity', 9.81)  # m/s²

        # Convert angle to radians
        theta = math.radians(initial_angle)

        # Period formula: T = 2π√(L/g) for small angles
        period = 2 * math.pi * math.sqrt(length / gravity)

        # Frequency
        frequency = 1 / period

        # Maximum velocity (at bottom): v = √(2gL(1 - cos(θ)))
        max_velocity = math.sqrt(2 * gravity * length * (1 - math.cos(theta)))

        # Potential energy at initial position: PE = mgL(1 - cos(θ))
        # Using normalized mass = 1
        potential_energy = gravity * length * (1 - math.cos(theta))

        # Kinetic energy at bottom (all PE converts to KE)
        kinetic_energy = potential_energy

        return {
            "period": round(period, 3),
            "frequency": round(frequency, 3),
            "max_velocity": round(max_velocity, 3),
            "potential_energy": round(potential_energy, 3),
            "kinetic_energy": round(kinetic_energy, 3),
            "units": {
                "period": "seconds",
                "frequency": "Hz",
                "max_velocity": "m/s",
                "energy": "Joules (per kg mass)"
            }
        }

    def simulate_projectile_motion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate projectile motion.
        params: {initial_velocity: float (m/s), angle: float (degrees), height: float (m)}
        """
        v0 = params.get('initial_velocity', 20)  # m/s
        angle = params.get('angle', 45)  # degrees
        h0 = params.get('height', 0)  # initial height in meters
        g = 9.81  # gravity

        # Convert angle to radians
        theta = math.radians(angle)

        # Components of velocity
        v0x = v0 * math.cos(theta)
        v0y = v0 * math.sin(theta)

        # Time to reach maximum height
        time_to_peak = v0y / g

        # Maximum height
        max_height = h0 + (v0y ** 2) / (2 * g)

        # Total time of flight (using quadratic formula)
        # h = h0 + v0y*t - 0.5*g*t²
        # At landing, h = 0
        a = -0.5 * g
        b = v0y
        c = h0
        discriminant = b**2 - 4*a*c
        if discriminant >= 0:
            time_of_flight = (-b - math.sqrt(discriminant)) / (2 * a)
        else:
            time_of_flight = 0

        # Range
        range_distance = v0x * time_of_flight

        return {
            "time_to_peak": round(time_to_peak, 3),
            "max_height": round(max_height, 3),
            "time_of_flight": round(time_of_flight, 3),
            "range": round(range_distance, 3),
            "initial_velocity_x": round(v0x, 3),
            "initial_velocity_y": round(v0y, 3),
            "units": {
                "time": "seconds",
                "distance": "meters",
                "velocity": "m/s"
            }
        }

    def simulate_springs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate Hooke's Law and spring systems.
        params: {spring_constant: float (N/m), mass: float (kg), displacement: float (m)}
        """
        k = params.get('spring_constant', 100)  # N/m
        m = params.get('mass', 1)  # kg
        x = params.get('displacement', 0.1)  # meters

        # Force: F = -kx
        force = k * x

        # Period of oscillation: T = 2π√(m/k)
        period = 2 * math.pi * math.sqrt(m / k)

        # Frequency
        frequency = 1 / period

        # Potential energy: PE = 0.5 * k * x²
        potential_energy = 0.5 * k * (x ** 2)

        # Maximum velocity (when PE converts to KE): v = x√(k/m)
        max_velocity = x * math.sqrt(k / m)

        return {
            "force": round(force, 3),
            "period": round(period, 3),
            "frequency": round(frequency, 3),
            "potential_energy": round(potential_energy, 3),
            "max_velocity": round(max_velocity, 3),
            "units": {
                "force": "Newtons",
                "time": "seconds",
                "frequency": "Hz",
                "energy": "Joules",
                "velocity": "m/s"
            }
        }

    # =============================================================================
    # CHEMISTRY SIMULATIONS
    # =============================================================================

    def simulate_ph_calculation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate pH for acids and bases.
        params: {concentration: float (M), acid_or_base: str, strong_or_weak: str}
        """
        concentration = params.get('concentration', 0.1)  # Molarity
        acid_or_base = params.get('acid_or_base', 'acid')
        strong_or_weak = params.get('strong_or_weak', 'strong')

        if acid_or_base == 'acid':
            if strong_or_weak == 'strong':
                # Strong acid: pH = -log[H+]
                if concentration > 0:
                    pH = -math.log10(concentration)
                else:
                    pH = 7
            else:
                # Weak acid approximation: pH ≈ 0.5(pKa - log[HA])
                # Using generic weak acid with pKa = 4.76 (acetic acid)
                pKa = params.get('pKa', 4.76)
                if concentration > 0:
                    pH = 0.5 * (pKa - math.log10(concentration))
                else:
                    pH = 7
        else:  # base
            if strong_or_weak == 'strong':
                # Strong base: pOH = -log[OH-], pH = 14 - pOH
                if concentration > 0:
                    pOH = -math.log10(concentration)
                    pH = 14 - pOH
                else:
                    pH = 7
            else:
                # Weak base approximation
                pKb = params.get('pKb', 4.74)
                if concentration > 0:
                    pOH = 0.5 * (pKb - math.log10(concentration))
                    pH = 14 - pOH
                else:
                    pH = 7

        # Determine acidity/basicity
        if pH < 7:
            classification = "Acidic"
        elif pH > 7:
            classification = "Basic"
        else:
            classification = "Neutral"

        return {
            "pH": round(pH, 2),
            "classification": classification,
            "concentration": concentration,
            "type": f"{strong_or_weak} {acid_or_base}",
            "note": "pH scale ranges from 0 (most acidic) to 14 (most basic)"
        }

    def simulate_chemical_reaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate basic stoichiometry.
        params: {reactant_amount: float, reactant_molar_mass: float, product_molar_mass: float, ratio: str}
        """
        reactant_grams = params.get('reactant_amount', 10)  # grams
        reactant_mm = params.get('reactant_molar_mass', 18)  # g/mol (e.g., H2O)
        product_mm = params.get('product_molar_mass', 32)  # g/mol (e.g., O2)
        ratio_str = params.get('ratio', '2:1')  # reactant:product ratio

        # Parse ratio
        ratio_parts = ratio_str.split(':')
        reactant_ratio = float(ratio_parts[0])
        product_ratio = float(ratio_parts[1])

        # Calculate moles of reactant
        reactant_moles = reactant_grams / reactant_mm

        # Calculate moles of product using stoichiometry
        product_moles = reactant_moles * (product_ratio / reactant_ratio)

        # Calculate mass of product
        product_grams = product_moles * product_mm

        return {
            "reactant_moles": round(reactant_moles, 4),
            "product_moles": round(product_moles, 4),
            "product_mass": round(product_grams, 2),
            "stoichiometric_ratio": ratio_str,
            "units": {
                "moles": "mol",
                "mass": "grams"
            }
        }

    # =============================================================================
    # AI TUTOR FUNCTIONS
    # =============================================================================

    def generate_hint(self, experiment_type: str, current_data: Dict[str, Any], question: str = None) -> str:
        """Generate an AI hint based on experiment progress."""
        prompt = f"""You are a friendly science tutor helping a student with a virtual lab experiment.

Experiment Type: {experiment_type}
Current Data: {json.dumps(current_data, indent=2)}
Student Question: {question or "What should I observe or try next?"}

Provide a helpful hint that:
1. Guides the student without giving away the answer
2. Encourages scientific thinking
3. Suggests what to observe or what variable to change
4. Is encouraging and supportive

Keep the hint concise (2-3 sentences)."""

        try:
            messages = [{"role": "user", "content": prompt}]
            return self._chat(messages, temperature=0.7, max_tokens=200)
        except Exception as e:
            log.error(f"[ScienceLab] Failed to generate hint: {e}")
            return "Try changing one variable at a time and observe what happens!"

    def provide_feedback(self, experiment_type: str, trials: List[Dict], observations: str, conclusions: str) -> Dict[str, Any]:
        """Provide AI feedback on student's experiment, observations, and conclusions."""
        prompt = f"""You are a science teacher reviewing a student's virtual lab experiment.

Experiment Type: {experiment_type}

Trial Data:
{json.dumps(trials, indent=2)}

Student Observations:
{observations}

Student Conclusions:
{conclusions}

Provide constructive feedback in JSON format:
{{
  "strengths": ["strength1", "strength2"],
  "areas_for_improvement": ["area1", "area2"],
  "scientific_accuracy": "high|medium|low",
  "suggestions": ["suggestion1", "suggestion2"],
  "overall_comment": "encouraging overall comment"
}}

Focus on scientific thinking, proper use of evidence, and clarity of conclusions."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat(messages, temperature=0.5, max_tokens=500)
            return self._parse_json_response(response)
        except Exception as e:
            log.error(f"[ScienceLab] Failed to provide feedback: {e}")
            return {
                "strengths": ["Good effort on completing the experiment"],
                "areas_for_improvement": ["Consider running more trials"],
                "scientific_accuracy": "medium",
                "suggestions": ["Try to connect your observations more clearly to your conclusions"],
                "overall_comment": "Keep up the great work exploring science!"
            }

    def suggest_next_experiment(self, completed_experiments: List[str], subject: str) -> Dict[str, Any]:
        """Suggest the next experiment based on what the student has completed."""
        prompt = f"""You are a science curriculum advisor. A student has completed these experiments:
{', '.join(completed_experiments) if completed_experiments else 'None yet'}

Subject focus: {subject}

Suggest the next experiment they should try. Return JSON:
{{
  "experiment_name": "name",
  "experiment_type": "simulation_type_id",
  "difficulty": "beginner|intermediate|advanced",
  "learning_objectives": ["objective1", "objective2"],
  "why_this_next": "brief explanation of why this is a good next step"
}}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat(messages, temperature=0.7, max_tokens=400)
            return self._parse_json_response(response)
        except Exception as e:
            log.error(f"[ScienceLab] Failed to suggest experiment: {e}")
            return {
                "experiment_name": "Pendulum Motion",
                "experiment_type": "physics_pendulum",
                "difficulty": "beginner",
                "learning_objectives": ["Understand periodic motion", "Explore the effect of length on period"],
                "why_this_next": "Great starting point for understanding oscillations!"
            }

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx == -1 or end_idx == -1:
                return {}

            json_str = response[start_idx:end_idx + 1]
            return json.loads(json_str)
        except Exception as e:
            log.error(f"[ScienceLab] JSON parse error: {e}")
            return {}
