"""
Application settings and configuration for AI Health Navigator
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ModelConfig:
    """Configuration for Claude models via AWS Bedrock"""
    haiku_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    sonnet_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    max_tokens_haiku: int = 1024
    max_tokens_sonnet: int = 4096


@dataclass
class Settings:
    """Main application settings"""

    # AWS Configuration
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))

    # Model Configuration
    models: ModelConfig = field(default_factory=ModelConfig)

    # Task to Model Mapping
    task_model_mapping: Dict[str, str] = field(default_factory=lambda: {
        # Haiku Tasks (Fast, Simple)
        "intake_greeting": "haiku",
        "basic_triage": "haiku",
        "simple_query": "haiku",
        "entity_extraction": "haiku",
        "follow_up_questions": "haiku",

        # Sonnet Tasks (Complex Analysis)
        "specialist_consultation": "sonnet",
        "differential_diagnosis": "sonnet",
        "care_planning": "sonnet",
        "consensus_synthesis": "sonnet",
        "complex_medical_reasoning": "sonnet",
        "supervisor_routing": "sonnet",
    })

    # Specialist Configuration
    enabled_specialists: List[str] = field(default_factory=lambda: [
        "general_practitioner",
        "cardiologist",
        "neurologist",
        "pulmonologist",
        "gastroenterologist",
    ])

    # Workflow Settings
    max_conversation_turns: int = 20
    max_specialists_per_case: int = 3
    consensus_confidence_threshold: float = 0.7

    # Report Settings
    reports_directory: str = "./reports"


# Global settings instance
settings = Settings()
