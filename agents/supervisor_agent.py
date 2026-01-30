"""
Supervisor Agent - Routes cases to appropriate specialists
"""
import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

from .base_agent import BaseAgent, AgentResponse, AgentCapability
from config.settings import settings
from config.agent_prompts import AGENT_PROMPTS

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Master coordinator that:
    1. Analyzes incoming patient data
    2. Routes to appropriate specialist(s)
    3. Determines urgency level
    4. Orchestrates multi-agent collaboration
    """

    # Symptom to specialist mapping
    SYMPTOM_ROUTING = {
        "cardiologist": [
            "chest pain", "palpitations", "heart", "cardiac",
            "shortness of breath", "irregular heartbeat", "fainting",
            "high blood pressure", "hypertension", "swelling legs"
        ],
        "neurologist": [
            "headache", "migraine", "dizziness", "vertigo",
            "numbness", "tingling", "seizure", "tremor",
            "vision changes", "memory", "confusion", "weakness"
        ],
        "pulmonologist": [
            "cough", "breathing", "wheezing", "asthma",
            "shortness of breath", "chest tightness", "lung",
            "respiratory", "sleep apnea", "snoring"
        ],
        "gastroenterologist": [
            "abdominal pain", "stomach", "nausea", "vomiting",
            "diarrhea", "constipation", "heartburn", "acid reflux",
            "bloating", "blood in stool", "difficulty swallowing"
        ],
    }

    # Emergency symptoms requiring immediate attention
    EMERGENCY_SYMPTOMS = [
        "crushing chest pain", "can't breathe", "unconscious",
        "stroke symptoms", "severe bleeding", "worst headache ever",
        "sudden paralysis", "seizure", "heart attack"
    ]

    def __init__(self):
        super().__init__(
            agent_id="supervisor_001",
            name="Medical Supervisor",
            model_type="sonnet",  # Use powerful model for routing decisions
            capabilities=[AgentCapability.ROUTING, AgentCapability.TRIAGE],
            system_prompt_key="supervisor"
        )

    def process(self, state: Dict[str, Any]) -> AgentResponse:
        """
        Analyze patient case and determine routing.

        Args:
            state: Current PatientState

        Returns:
            AgentResponse with routing decisions
        """
        logger.info("=== SUPERVISOR AGENT PROCESSING ===")

        symptoms = state.get("primary_complaints", [])
        medical_history = state.get("medical_history", [])

        # Check for emergency
        is_emergency, emergency_reason = self._check_emergency(symptoms)
        if is_emergency:
            return self._create_emergency_response(emergency_reason, state)

        # Determine specialists using rule-based + LLM
        selected_specialists = self._route_to_specialists(symptoms, medical_history)

        # Get LLM analysis for complex cases
        if len(selected_specialists) > 1 or not selected_specialists:
            llm_routing = self._get_llm_routing(state)
            selected_specialists = self._merge_routing(
                selected_specialists,
                llm_routing
            )

        # Always include GP
        if "general_practitioner" not in selected_specialists:
            selected_specialists.insert(0, "general_practitioner")

        # Limit specialists
        selected_specialists = selected_specialists[:settings.max_specialists_per_case]

        rationale = self._generate_rationale(symptoms, selected_specialists)

        return AgentResponse(
            content=f"Routing to specialists: {', '.join(selected_specialists)}",
            confidence=0.85,
            reasoning=rationale,
            suggested_specialists=selected_specialists,
            metadata={
                "routing_timestamp": datetime.now().isoformat(),
                "symptom_count": len(symptoms),
                "urgency": "routine"
            }
        )

    def _check_emergency(self, symptoms: List[str]) -> Tuple[bool, str]:
        """Check if symptoms indicate an emergency"""
        symptoms_lower = " ".join(symptoms).lower()

        for emergency in self.EMERGENCY_SYMPTOMS:
            if emergency in symptoms_lower:
                return True, f"Emergency detected: {emergency}"

        return False, ""

    def _create_emergency_response(
        self,
        reason: str,
        state: Dict[str, Any]
    ) -> AgentResponse:
        """Create response for emergency cases"""
        return AgentResponse(
            content="EMERGENCY: Immediate medical attention required",
            confidence=0.95,
            reasoning=reason,
            red_flags=[reason],
            recommendations=[
                "Call 911 immediately",
                "Go to nearest emergency room",
                "Do not drive yourself"
            ],
            metadata={
                "routing_timestamp": datetime.now().isoformat(),
                "urgency": "emergency",
                "emergency_reason": reason
            }
        )

    def _route_to_specialists(
        self,
        symptoms: List[str],
        medical_history: List[str]
    ) -> List[str]:
        """
        Rule-based routing to specialists based on symptoms.

        Args:
            symptoms: List of symptoms
            medical_history: Patient's medical history

        Returns:
            List of specialist IDs to consult
        """
        specialists_scores: Dict[str, float] = {}
        symptoms_text = " ".join(symptoms).lower()
        history_text = " ".join(medical_history).lower()

        for specialist, keywords in self.SYMPTOM_ROUTING.items():
            score = 0.0
            for keyword in keywords:
                if keyword in symptoms_text:
                    score += 1.0
                if keyword in history_text:
                    score += 0.5
            if score > 0:
                specialists_scores[specialist] = score

        # Sort by score descending
        sorted_specialists = sorted(
            specialists_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [s[0] for s in sorted_specialists]

    def _get_llm_routing(self, state: Dict[str, Any]) -> List[str]:
        """
        Use LLM for complex routing decisions.

        Args:
            state: Patient state

        Returns:
            List of specialists suggested by LLM
        """
        prompt = f"""
        Analyze this patient case and determine which specialists should be consulted.

        {self.format_patient_summary(state)}

        Available specialists:
        - general_practitioner: General medicine, initial evaluation
        - cardiologist: Heart and cardiovascular issues
        - neurologist: Brain, nerves, headaches, dizziness
        - pulmonologist: Lungs and breathing
        - gastroenterologist: Digestive system, stomach, intestines

        Based on the symptoms and history, list the most relevant specialists
        (maximum 3) in order of relevance.

        Return your answer as a JSON array of specialist names, for example:
        ["cardiologist", "general_practitioner"]
        """

        try:
            response = self.invoke_llm(prompt, temperature=0.3)

            # Extract JSON array from response
            import re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                specialists = json.loads(match.group())
                # Validate specialists
                valid = [s for s in specialists if s in settings.enabled_specialists]
                return valid
        except Exception as e:
            logger.error(f"LLM routing error: {e}")

        return []

    def _merge_routing(
        self,
        rule_based: List[str],
        llm_based: List[str]
    ) -> List[str]:
        """Merge rule-based and LLM routing recommendations"""
        # Prioritize overlapping recommendations
        combined = []

        # First add specialists recommended by both
        for s in rule_based:
            if s in llm_based:
                combined.append(s)

        # Then add remaining rule-based
        for s in rule_based:
            if s not in combined:
                combined.append(s)

        # Then add remaining LLM-based
        for s in llm_based:
            if s not in combined:
                combined.append(s)

        return combined

    def _generate_rationale(
        self,
        symptoms: List[str],
        specialists: List[str]
    ) -> str:
        """Generate explanation for routing decision"""
        rationale_parts = [
            f"Patient presents with: {', '.join(symptoms)}.",
            f"Based on symptom analysis, consulting: {', '.join(specialists)}."
        ]

        # Add specific reasoning for each specialist
        for specialist in specialists:
            if specialist == "cardiologist":
                matching = [s for s in symptoms if any(
                    k in s.lower() for k in self.SYMPTOM_ROUTING["cardiologist"]
                )]
                if matching:
                    rationale_parts.append(
                        f"Cardiology for: {', '.join(matching)}"
                    )
            elif specialist == "neurologist":
                matching = [s for s in symptoms if any(
                    k in s.lower() for k in self.SYMPTOM_ROUTING["neurologist"]
                )]
                if matching:
                    rationale_parts.append(
                        f"Neurology for: {', '.join(matching)}"
                    )

        return " ".join(rationale_parts)

    def determine_consensus_need(
        self,
        specialist_responses: Dict[str, AgentResponse]
    ) -> bool:
        """
        Determine if consensus mechanism is needed.

        Args:
            specialist_responses: Responses from all consulted specialists

        Returns:
            True if consensus needed, False otherwise
        """
        if len(specialist_responses) <= 1:
            return False

        confidences = [r.confidence for r in specialist_responses.values()]

        # Need consensus if confidence varies significantly
        if max(confidences) - min(confidences) > 0.3:
            return True

        # Need consensus if any specialist has low confidence
        if any(c < 0.6 for c in confidences):
            return True

        # Need consensus if there are red flags from multiple specialists
        red_flag_count = sum(
            1 for r in specialist_responses.values() if r.red_flags
        )
        if red_flag_count > 1:
            return True

        return False
