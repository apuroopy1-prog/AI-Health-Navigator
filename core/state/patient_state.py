"""
Enhanced Patient State for multi-agent healthcare workflow
"""
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field


class ConversationPhase(Enum):
    """Phases of the conversational intake"""
    GREETING = "greeting"
    SYMPTOM_COLLECTION = "symptom_collection"
    HISTORY_COLLECTION = "history_collection"
    CLARIFICATION = "clarification"
    SUMMARY_CONFIRMATION = "summary_confirmation"
    ASSESSMENT_READY = "assessment_ready"


class CareLevel(Enum):
    """Care urgency levels"""
    SELF_CARE = "self_care"
    PRIMARY_CARE = "primary_care"
    URGENT_CARE = "urgent_care"
    EMERGENCY = "emergency"


@dataclass
class SpecialistResponse:
    """Response from a specialist agent"""
    specialist: str
    diagnosis: str
    confidence: float
    reasoning: str
    recommendations: List[str]
    follow_up_questions: List[str]
    red_flags: List[str]


@dataclass
class ConsensusResult:
    """Result of consensus synthesis"""
    primary_diagnosis: str
    differential_diagnoses: List[str]
    confidence: float
    agreement_level: str  # "unanimous", "majority", "split"
    dissenting_opinions: List[str]
    recommended_actions: List[str]


class PatientState(TypedDict, total=False):
    """
    Comprehensive state object for the multi-agent healthcare workflow.
    Flows through all agents and accumulates information.
    """

    # ===== Patient Demographics =====
    patient_id: str
    name: str
    age: Optional[int]
    gender: Optional[str]
    contact_info: str
    emergency_contact: Optional[str]

    # ===== Conversation State =====
    conversation_phase: str  # ConversationPhase value
    conversation_history: List[Dict[str, str]]  # {"role": "user/assistant", "content": "..."}
    latest_user_message: str
    assistant_response: str
    awaiting_user_input: bool
    intake_complete: bool

    # ===== Symptom Data =====
    primary_complaints: List[str]
    symptom_details: Dict[str, Dict[str, Any]]  # Per-symptom details
    symptom_duration: Optional[str]
    symptom_severity: Optional[int]  # 1-10 scale
    symptom_triggers: List[str]
    symptom_relievers: List[str]
    symptom_onset: Optional[str]

    # ===== Medical Background =====
    medical_history: List[str]
    surgical_history: List[str]
    family_history: List[str]
    current_medications: List[str]
    allergies: List[str]
    lifestyle_factors: Dict[str, Any]

    # ===== Intake Results =====
    initial_risk_level: str
    intake_summary: str
    intake_timestamp: str

    # ===== Routing Data =====
    selected_specialists: List[str]
    routing_rationale: str
    routing_timestamp: str

    # ===== Specialist Consultation =====
    specialist_responses: Dict[str, Dict[str, Any]]  # SpecialistResponse as dict per specialist
    specialist_questions: Dict[str, List[str]]

    # ===== Consensus Data =====
    consensus_result: Optional[Dict[str, Any]]  # ConsensusResult as dict
    primary_diagnosis: str
    differential_diagnoses: List[str]
    diagnostic_confidence: float
    agreement_level: str

    # ===== Clinical Assessment =====
    assessment_findings: str
    clinical_risk_level: str
    assessment_timestamp: str
    rag_context: List[str]
    red_flags_identified: List[str]

    # ===== Care Planning =====
    treatment_recommendations: List[str]
    care_level: str  # CareLevel value
    referrals: List[Dict[str, str]]
    follow_up_schedule: List[Dict[str, str]]
    patient_education: List[str]
    compliance_notes: str
    final_report: str
    pdf_path: Optional[str]

    # ===== Workflow Metadata =====
    current_phase: str
    workflow_history: List[str]
    error_message: Optional[str]
    session_id: str
    created_at: str
    updated_at: str


def create_initial_state(patient_data: Optional[Dict[str, Any]] = None) -> PatientState:
    """
    Create an initial PatientState with default values.

    Args:
        patient_data: Optional initial patient data

    Returns:
        Initialized PatientState
    """
    data = patient_data or {}

    return PatientState(
        # Demographics
        patient_id=data.get("patient_id", ""),
        name=data.get("name", ""),
        age=data.get("age"),
        gender=data.get("gender"),
        contact_info=data.get("contact_info", ""),
        emergency_contact=data.get("emergency_contact"),

        # Conversation
        conversation_phase=ConversationPhase.GREETING.value,
        conversation_history=[],
        latest_user_message="",
        assistant_response="",
        awaiting_user_input=False,
        intake_complete=False,

        # Symptoms
        primary_complaints=data.get("primary_complaints", []),
        symptom_details={},
        symptom_duration=data.get("symptom_duration"),
        symptom_severity=None,
        symptom_triggers=[],
        symptom_relievers=[],
        symptom_onset=None,

        # Medical background
        medical_history=data.get("medical_history", []),
        surgical_history=[],
        family_history=[],
        current_medications=data.get("current_medications", []),
        allergies=data.get("allergies", []),
        lifestyle_factors={},

        # Intake
        initial_risk_level="",
        intake_summary="",
        intake_timestamp="",

        # Routing
        selected_specialists=[],
        routing_rationale="",
        routing_timestamp="",

        # Specialist consultation
        specialist_responses={},
        specialist_questions={},

        # Consensus
        consensus_result=None,
        primary_diagnosis="",
        differential_diagnoses=[],
        diagnostic_confidence=0.0,
        agreement_level="",

        # Assessment
        assessment_findings="",
        clinical_risk_level="",
        assessment_timestamp="",
        rag_context=[],
        red_flags_identified=[],

        # Care planning
        treatment_recommendations=[],
        care_level="",
        referrals=[],
        follow_up_schedule=[],
        patient_education=[],
        compliance_notes="",
        final_report="",
        pdf_path=None,

        # Metadata
        current_phase="initialization",
        workflow_history=[],
        error_message=None,
        session_id="",
        created_at="",
        updated_at=""
    )
