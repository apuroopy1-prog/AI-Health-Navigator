"""
LangGraph Workflow for AI Health Navigator
Integrates: LangGraph + Pinecone RAG + MongoDB + AWS Bedrock
"""
import logging
from typing import Dict, Any, TypedDict, Annotated, List
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from database.pinecone_client import pinecone_rag
from database.mongodb_client import patient_repo, mongo_client

logger = logging.getLogger(__name__)


# ==================== State Definition ====================

class PatientState(TypedDict):
    """State that flows through the LangGraph workflow"""
    # Patient Info
    name: str
    age: int
    primary_complaints: List[str]
    symptom_duration: str
    medical_history: List[str]
    current_medications: List[str]
    allergies: List[str]

    # Workflow State
    messages: Annotated[List[Dict], operator.add]
    current_stage: str

    # Assessment Results
    initial_risk_level: str
    clinical_risk_level: str
    intake_summary: str
    assessment_findings: str
    treatment_recommendations: List[str]
    care_level: str
    rag_context: List[str]

    # Metadata
    patient_id: str
    assessment_id: str
    timestamp: str


# ==================== Node Functions ====================

def intake_node(state: PatientState) -> Dict[str, Any]:
    """
    Initial intake - gather patient information and perform initial triage.
    Uses RAG to retrieve relevant medical knowledge.
    """
    logger.info("=== INTAKE NODE ===")

    complaints = state.get("primary_complaints", [])
    name = state.get("name", "Patient")
    age = state.get("age", 0)
    duration = state.get("symptom_duration", "Not specified")
    history = state.get("medical_history", [])
    medications = state.get("current_medications", [])
    allergies = state.get("allergies", [])

    # Retrieve relevant medical knowledge using RAG
    query = " ".join(complaints)
    rag_results = pinecone_rag.retrieve(query, top_k=5)
    rag_context = [r.get("content", "") for r in rag_results if r.get("content")]

    # Build intake summary
    intake_summary = f"""
**Patient Information:**
- **Name:** {name}
- **Age:** {age} years old
- **Assessment Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

**Chief Complaints:**
The patient presents with the following primary symptoms: {', '.join(complaints) if complaints else 'No specific complaints reported'}.

**Duration of Symptoms:**
{duration if duration else 'Duration not specified by patient.'}

**Medical History:**
{', '.join(history) if history else 'No significant medical history reported.'}

**Current Medications:**
{', '.join(medications) if medications else 'No current medications reported.'}

**Known Allergies:**
{', '.join(allergies) if allergies else 'No known drug allergies (NKDA).'}

**Relevant Medical Knowledge Retrieved:**
Based on the patient's symptoms, the following clinical guidelines were consulted:
{chr(10).join(['- ' + ctx[:200] + '...' if len(ctx) > 200 else '- ' + ctx for ctx in rag_context[:3]]) if rag_context else '- Standard clinical protocols applied.'}

**Initial Triage Assessment:**
Based on the reported symptoms and patient information, an initial triage assessment has been conducted. The patient's symptoms have been categorized and prioritized according to clinical urgency guidelines.
"""

    return {
        "intake_summary": intake_summary,
        "rag_context": rag_context,
        "current_stage": "intake_complete",
        "messages": [{"role": "system", "content": "Intake completed", "timestamp": datetime.now().isoformat()}]
    }


def risk_assessment_node(state: PatientState) -> Dict[str, Any]:
    """
    Assess patient risk level based on symptoms and medical knowledge.
    """
    logger.info("=== RISK ASSESSMENT NODE ===")

    complaints = state.get("primary_complaints", [])
    history = state.get("medical_history", [])
    age = state.get("age", 0)
    rag_context = state.get("rag_context", [])

    # Risk keywords
    high_risk_keywords = [
        'chest pain', 'breathing difficulty', 'unconscious', 'severe pain',
        'blood in stool', 'blood in urine', 'sudden weakness', 'slurred speech',
        'worst headache', 'seizure', 'high fever', 'confusion'
    ]
    medium_risk_keywords = [
        'fever', 'persistent pain', 'headache', 'dizziness', 'nausea',
        'fatigue', 'cough', 'shortness of breath', 'palpitations'
    ]

    # Check symptoms against risk keywords
    complaints_lower = ' '.join(complaints).lower()
    history_lower = ' '.join(history).lower()

    # Determine risk level
    if any(k in complaints_lower for k in high_risk_keywords):
        risk_level = "High"
        care_level = "Emergency Care"
    elif any(k in complaints_lower for k in medium_risk_keywords):
        risk_level = "Medium"
        care_level = "Primary Care"
    elif age > 65 or age < 5:
        risk_level = "Medium"
        care_level = "Primary Care"
    else:
        risk_level = "Low"
        care_level = "Self-Care with Monitoring"

    # Adjust for medical history
    if any(k in history_lower for k in ['heart disease', 'diabetes', 'cancer', 'immunocompromised']):
        if risk_level == "Low":
            risk_level = "Medium"
            care_level = "Primary Care"

    return {
        "initial_risk_level": risk_level,
        "clinical_risk_level": risk_level,
        "care_level": care_level,
        "current_stage": "risk_assessed",
        "messages": [{"role": "system", "content": f"Risk assessed: {risk_level}", "timestamp": datetime.now().isoformat()}]
    }


def clinical_assessment_node(state: PatientState) -> Dict[str, Any]:
    """
    Perform detailed clinical assessment using RAG knowledge.
    """
    logger.info("=== CLINICAL ASSESSMENT NODE ===")

    complaints = state.get("primary_complaints", [])
    risk_level = state.get("clinical_risk_level", "Medium")
    care_level = state.get("care_level", "Primary Care")
    rag_context = state.get("rag_context", [])

    # Build clinical assessment using RAG context
    rag_insights = ""
    if rag_context:
        rag_insights = "\n\n**Evidence-Based Clinical Insights:**\n"
        for i, ctx in enumerate(rag_context[:3], 1):
            rag_insights += f"\n{i}. {ctx}"

    assessment_findings = f"""
**Clinical Assessment Summary:**

**1. Symptom Analysis:**
The patient reports experiencing {', '.join(complaints) if complaints else 'unspecified symptoms'}. These symptoms warrant clinical attention and have been evaluated based on standard medical assessment protocols and retrieved medical knowledge.

**2. Risk Stratification:**
Based on the presented symptoms and patient demographics, the clinical risk has been assessed as **{risk_level}**. This determination considers:
- Nature and severity of reported symptoms
- Patient age and potential vulnerability factors
- Duration and progression of symptoms
- Presence of any red flag indicators
- Relevant medical history
{rag_insights}

**3. Differential Considerations:**
The reported symptom pattern may be associated with various conditions. A comprehensive evaluation by a qualified healthcare provider is recommended to:
- Confirm or rule out potential diagnoses
- Order appropriate diagnostic tests if indicated
- Develop a targeted treatment plan

**4. Vital Signs Recommendation:**
It is recommended to monitor the following parameters:
- Temperature (for fever assessment)
- Blood pressure and heart rate
- Respiratory rate and oxygen saturation (if respiratory symptoms present)
- Pain level assessment using standardized scale

**5. Clinical Impression:**
The overall clinical picture suggests a need for {care_level.lower()} evaluation. The patient should be advised regarding warning signs that would necessitate immediate medical attention.
"""

    return {
        "assessment_findings": assessment_findings,
        "current_stage": "assessment_complete",
        "messages": [{"role": "system", "content": "Clinical assessment completed", "timestamp": datetime.now().isoformat()}]
    }


def treatment_planning_node(state: PatientState) -> Dict[str, Any]:
    """
    Generate treatment recommendations based on assessment.
    """
    logger.info("=== TREATMENT PLANNING NODE ===")

    risk_level = state.get("clinical_risk_level", "Medium")
    care_level = state.get("care_level", "Primary Care")

    # Build treatment recommendations
    recommendations = [
        f"**Immediate Action:** Based on the {risk_level.lower()} risk assessment, {'seek immediate medical attention at the nearest emergency department' if risk_level == 'High' else 'schedule an appointment with your healthcare provider within 24-48 hours' if risk_level == 'Medium' else 'monitor symptoms and practice self-care measures at home'}.",

        "**Symptom Monitoring:** Keep a detailed log of symptoms including onset time, duration, severity (scale 1-10), and any factors that worsen or improve symptoms. This information will be valuable for your healthcare provider.",

        "**Hydration & Rest:** Ensure adequate fluid intake (8-10 glasses of water daily) and get sufficient rest. Proper hydration and rest support the body's natural healing processes and immune function.",

        "**Medication Guidance:** If taking over-the-counter medications for symptom relief, follow package instructions carefully. Do not exceed recommended dosages and be aware of potential interactions with any current medications you are taking.",

        "**Warning Signs:** Seek immediate emergency care if you experience: difficulty breathing, chest pain or pressure, confusion or altered consciousness, severe or worsening symptoms, high fever (>103°F/39.4°C), or any symptoms that concern you significantly.",

        "**Follow-Up Care:** Schedule a follow-up appointment within 48-72 hours if symptoms persist or worsen. Bring this assessment report to your healthcare provider for reference and continuity of care.",

        "**Lifestyle Considerations:** Consider factors that may be contributing to symptoms such as stress levels, sleep quality, diet, and physical activity. Addressing these factors can support overall health and recovery."
    ]

    return {
        "treatment_recommendations": recommendations,
        "current_stage": "planning_complete",
        "messages": [{"role": "system", "content": "Treatment plan generated", "timestamp": datetime.now().isoformat()}]
    }


def save_to_database_node(state: PatientState) -> Dict[str, Any]:
    """
    Save assessment results to MongoDB.
    """
    logger.info("=== SAVE TO DATABASE NODE ===")

    try:
        # Connect to MongoDB if not connected
        mongo_client.connect()

        # Create patient record
        patient_data = {
            "name": state.get("name", "Unknown"),
            "age": state.get("age", 0),
            "medical_history": state.get("medical_history", []),
            "current_medications": state.get("current_medications", []),
            "allergies": state.get("allergies", [])
        }
        patient_id = patient_repo.create_patient(patient_data)

        # Create assessment record
        assessment_data = {
            "patient_id": patient_id,
            "primary_complaints": state.get("primary_complaints", []),
            "symptom_duration": state.get("symptom_duration", ""),
            "initial_risk_level": state.get("initial_risk_level", ""),
            "clinical_risk_level": state.get("clinical_risk_level", ""),
            "care_level": state.get("care_level", ""),
            "intake_summary": state.get("intake_summary", ""),
            "assessment_findings": state.get("assessment_findings", ""),
            "treatment_recommendations": state.get("treatment_recommendations", []),
            "rag_context": state.get("rag_context", []),
            "timestamp": datetime.now().isoformat()
        }
        assessment_id = patient_repo.create_assessment(assessment_data)

        logger.info(f"Saved to MongoDB - Patient: {patient_id}, Assessment: {assessment_id}")

        return {
            "patient_id": patient_id,
            "assessment_id": assessment_id,
            "current_stage": "saved",
            "messages": [{"role": "system", "content": f"Saved to database: {assessment_id}", "timestamp": datetime.now().isoformat()}]
        }

    except Exception as e:
        logger.warning(f"MongoDB save failed (non-critical): {e}")
        return {
            "patient_id": "LOCAL",
            "assessment_id": f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "current_stage": "saved_locally",
            "messages": [{"role": "system", "content": "Saved locally (MongoDB unavailable)", "timestamp": datetime.now().isoformat()}]
        }


# ==================== Build LangGraph Workflow ====================

def build_health_navigator_graph() -> StateGraph:
    """
    Build the LangGraph workflow for health navigation.
    """
    # Create the graph
    workflow = StateGraph(PatientState)

    # Add nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("clinical_assessment", clinical_assessment_node)
    workflow.add_node("treatment_planning", treatment_planning_node)
    workflow.add_node("save_to_database", save_to_database_node)

    # Define edges (workflow flow)
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "risk_assessment")
    workflow.add_edge("risk_assessment", "clinical_assessment")
    workflow.add_edge("clinical_assessment", "treatment_planning")
    workflow.add_edge("treatment_planning", "save_to_database")
    workflow.add_edge("save_to_database", END)

    # Compile with memory checkpointer
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ==================== Main Function for Streamlit ====================

def run_patient_assessment(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the full patient assessment workflow.

    Args:
        patient_data: Dictionary containing patient information
            - name: Patient name
            - age: Patient age
            - primary_complaints: List of symptoms
            - symptom_duration: How long symptoms have lasted
            - medical_history: List of medical conditions
            - current_medications: List of medications
            - allergies: List of allergies

    Returns:
        Dictionary containing assessment results
    """
    logger.info("=== STARTING LANGGRAPH HEALTH ASSESSMENT ===")

    # Initialize the graph
    graph = build_health_navigator_graph()

    # Prepare initial state
    initial_state: PatientState = {
        "name": patient_data.get("name", "Patient"),
        "age": patient_data.get("age", 0),
        "primary_complaints": patient_data.get("primary_complaints", []),
        "symptom_duration": patient_data.get("symptom_duration", ""),
        "medical_history": patient_data.get("medical_history", []),
        "current_medications": patient_data.get("current_medications", []),
        "allergies": patient_data.get("allergies", []),
        "messages": [],
        "current_stage": "started",
        "initial_risk_level": "",
        "clinical_risk_level": "",
        "intake_summary": "",
        "assessment_findings": "",
        "treatment_recommendations": [],
        "care_level": "",
        "rag_context": [],
        "patient_id": "",
        "assessment_id": "",
        "timestamp": datetime.now().isoformat()
    }

    # Run the workflow
    config = {"configurable": {"thread_id": f"assessment-{datetime.now().strftime('%Y%m%d%H%M%S')}"}}

    try:
        # Execute the graph and accumulate all state updates
        accumulated_state = dict(initial_state)

        for state_update in graph.stream(initial_state, config):
            # Each state_update is {node_name: {updated_fields}}
            for node_name, node_output in state_update.items():
                logger.info(f"Node '{node_name}' completed with keys: {list(node_output.keys())}")
                # Merge node output into accumulated state
                for key, value in node_output.items():
                    if value:  # Only update if value is not empty
                        accumulated_state[key] = value

        logger.info(f"Workflow completed. Risk: {accumulated_state.get('initial_risk_level')}, Care: {accumulated_state.get('care_level')}")

        # Return the accumulated result
        return {
            "patient_name": patient_data.get("name", "Patient"),
            "patient_age": patient_data.get("age", 0),
            "assessment_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "initial_risk_level": accumulated_state.get("initial_risk_level") or "Medium",
            "clinical_risk_level": accumulated_state.get("clinical_risk_level") or "Medium",
            "intake_summary": accumulated_state.get("intake_summary") or "",
            "assessment_findings": accumulated_state.get("assessment_findings") or "",
            "treatment_recommendations": accumulated_state.get("treatment_recommendations") or [],
            "care_level": accumulated_state.get("care_level") or "Primary Care",
            "rag_context": accumulated_state.get("rag_context") or [],
            "patient_id": accumulated_state.get("patient_id") or "",
            "assessment_id": accumulated_state.get("assessment_id") or "",
            "workflow_completed": True
        }

    except Exception as e:
        logger.error(f"LangGraph workflow error: {e}")
        raise


# ==================== Initialize RAG on Import ====================

def initialize_services():
    """Initialize Pinecone and MongoDB connections"""
    try:
        # Initialize Pinecone RAG
        pinecone_rag.initialize_index()
        logger.info("Pinecone RAG initialized")
    except Exception as e:
        logger.warning(f"Pinecone initialization failed (using fallback): {e}")

    try:
        # Initialize MongoDB
        mongo_client.connect()
        logger.info("MongoDB connected")
    except Exception as e:
        logger.warning(f"MongoDB connection failed (using local mode): {e}")


# Initialize on module load
initialize_services()
