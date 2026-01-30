"""
Base Agent class for all healthcare AI agents
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

from core.models import get_llm_client
from config.agent_prompts import AGENT_PROMPTS


class AgentCapability(Enum):
    """Capabilities that agents can have"""
    SYMPTOM_ANALYSIS = "symptom_analysis"
    DIAGNOSIS = "diagnosis"
    TREATMENT_PLANNING = "treatment_planning"
    TRIAGE = "triage"
    CONSULTATION = "consultation"
    ROUTING = "routing"
    CONSENSUS = "consensus"


@dataclass
class AgentResponse:
    """Standardized response from any agent"""
    content: str
    confidence: float = 0.0  # 0.0 - 1.0
    reasoning: str = ""
    follow_up_needed: bool = False
    follow_up_questions: List[str] = field(default_factory=list)
    suggested_specialists: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for state storage"""
        return {
            "content": self.content,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "follow_up_needed": self.follow_up_needed,
            "follow_up_questions": self.follow_up_questions,
            "suggested_specialists": self.suggested_specialists,
            "red_flags": self.red_flags,
            "recommendations": self.recommendations,
            "metadata": self.metadata
        }


class BaseAgent(ABC):
    """
    Abstract base class for all healthcare AI agents.
    Provides common functionality and enforces interface.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        model_type: str = "haiku",
        capabilities: Optional[List[AgentCapability]] = None,
        system_prompt_key: Optional[str] = None
    ):
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name
            model_type: "haiku" or "sonnet"
            capabilities: List of agent capabilities
            system_prompt_key: Key to look up system prompt in AGENT_PROMPTS
        """
        self.agent_id = agent_id
        self.name = name
        self.model_type = model_type
        self.capabilities = capabilities or []
        self.system_prompt = AGENT_PROMPTS.get(system_prompt_key, "")
        self._llm = None

    @property
    def llm(self):
        """Lazy initialization of LLM client (Claude API or Bedrock)"""
        if self._llm is None:
            self._llm = get_llm_client(model_type=self.model_type)
        return self._llm

    @abstractmethod
    def process(self, state: Dict[str, Any]) -> AgentResponse:
        """
        Process patient state and return agent response.
        Must be implemented by all agents.

        Args:
            state: Current PatientState

        Returns:
            AgentResponse with analysis results
        """
        pass

    def invoke_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Invoke the LLM with the agent's system prompt.

        Args:
            prompt: User prompt
            temperature: Sampling temperature

        Returns:
            LLM response text
        """
        return self.llm.invoke(
            prompt,
            system_prompt=self.system_prompt,
            temperature=temperature
        )

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities

    def format_patient_summary(self, state: Dict[str, Any]) -> str:
        """
        Format patient data into a readable summary for prompts.

        Args:
            state: PatientState dictionary

        Returns:
            Formatted patient summary string
        """
        summary_parts = []

        if state.get("name"):
            summary_parts.append(f"Patient: {state['name']}")
        if state.get("age"):
            summary_parts.append(f"Age: {state['age']}")
        if state.get("gender"):
            summary_parts.append(f"Gender: {state['gender']}")

        if state.get("primary_complaints"):
            complaints = ", ".join(state["primary_complaints"])
            summary_parts.append(f"Chief Complaints: {complaints}")

        if state.get("symptom_duration"):
            summary_parts.append(f"Duration: {state['symptom_duration']}")

        if state.get("symptom_severity"):
            summary_parts.append(f"Severity: {state['symptom_severity']}/10")

        if state.get("medical_history"):
            history = ", ".join(state["medical_history"])
            summary_parts.append(f"Medical History: {history}")

        if state.get("current_medications"):
            meds = ", ".join(state["current_medications"])
            summary_parts.append(f"Current Medications: {meds}")

        if state.get("allergies"):
            allergies = ", ".join(state["allergies"])
            summary_parts.append(f"Allergies: {allergies}")

        return "\n".join(summary_parts)

    def extract_confidence(self, response: str) -> float:
        """
        Extract confidence score from LLM response.

        Args:
            response: LLM response text

        Returns:
            Confidence score (0.0 - 1.0)
        """
        import re

        # Look for patterns like "Confidence: 0.75" or "confidence: 75%"
        patterns = [
            r"[Cc]onfidence[:\s]+(\d+\.?\d*)%?",
            r"(\d+\.?\d*)\s*(?:out of|\/)\s*(?:10|100|1\.0)",
        ]

        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                value = float(match.group(1))
                # Normalize to 0-1 range
                if value > 1:
                    value = value / 100 if value <= 100 else value / 10
                return min(max(value, 0.0), 1.0)

        # Default confidence if not found
        return 0.7

    def extract_red_flags(self, response: str, symptoms: List[str]) -> List[str]:
        """
        Extract any red flag symptoms mentioned.

        Args:
            response: LLM response text
            symptoms: List of reported symptoms

        Returns:
            List of identified red flags
        """
        red_flag_keywords = [
            "red flag", "urgent", "emergency", "immediate",
            "severe", "critical", "alarming", "concerning",
            "worst headache", "sudden onset", "chest pain radiating",
            "difficulty breathing", "loss of consciousness"
        ]

        flags = []
        response_lower = response.lower()

        for keyword in red_flag_keywords:
            if keyword in response_lower:
                # Try to extract context around the keyword
                idx = response_lower.find(keyword)
                start = max(0, idx - 50)
                end = min(len(response), idx + len(keyword) + 50)
                context = response[start:end].strip()
                if context and context not in flags:
                    flags.append(context)

        return flags[:5]  # Limit to top 5
