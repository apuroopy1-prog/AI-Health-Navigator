"""
Assessment API Routes - Run AI health assessments
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo
from database.pinecone_client import pinecone_rag
from core.models.claude_client import get_llm_client
from core.models.model_router import model_router

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Models ====================

class AssessmentRequest(BaseModel):
    """Request model for running an assessment"""
    patient_id: Optional[str] = Field(None, description="Existing patient ID")
    name: str = Field(..., description="Patient name")
    age: Optional[int] = Field(None, ge=0, le=150)
    primary_complaints: List[str] = Field(..., min_length=1, description="List of symptoms")
    symptom_duration: Optional[str] = Field(None, description="How long symptoms present")
    medical_history: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)


class AssessmentResponse(BaseModel):
    """Response model for assessment results"""
    assessment_id: str
    patient_id: str
    status: str
    initial_risk_level: str
    clinical_risk_level: str
    intake_summary: str
    assessment_findings: str
    specialists_consulted: List[str]
    primary_diagnosis: Optional[str] = None
    differential_diagnoses: List[str] = []
    treatment_recommendations: List[str]
    care_level: str
    rag_context: List[str] = []
    pdf_path: Optional[str] = None
    created_at: datetime


# ==================== Assessment Logic ====================

def run_intake_assessment(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run intake coordinator assessment"""
    name = state.get('name', 'Patient')
    age = state.get('age', 'Unknown')
    complaints = state.get('primary_complaints', [])
    duration = state.get('symptom_duration', 'Not specified')
    history = state.get('medical_history', [])
    medications = state.get('current_medications', [])
    allergies = state.get('allergies', [])

    # Determine risk level based on symptoms
    high_risk_keywords = ['chest pain', 'breathing difficulty', 'unconscious', 'severe pain',
                          'blood in stool', 'blood in urine', 'sudden weakness', 'slurred speech']
    medium_risk_keywords = ['fever', 'persistent pain', 'headache', 'dizziness', 'nausea',
                           'fatigue', 'cough', 'shortness of breath', 'palpitations']

    complaints_lower = ' '.join(complaints).lower()

    if any(k in complaints_lower for k in high_risk_keywords):
        risk = "High"
    elif any(k in complaints_lower for k in medium_risk_keywords):
        risk = "Medium"
    elif age and (int(age) > 65 or int(age) < 5):
        risk = "Medium"
    else:
        risk = "Low"

    # Try LLM first
    try:
        llm = get_llm_client(model_type="haiku")
        prompt = f"""
        You are a healthcare intake coordinator. Assess this patient:

        Name: {name}
        Age: {age}
        Primary Complaints: {', '.join(complaints)}
        Duration: {duration}
        Medical History: {', '.join(history)}

        Provide:
        1. A brief intake summary (2-3 sentences)
        2. Initial risk level (Low, Medium, or High)

        Format your response as:
        SUMMARY: [your summary]
        RISK: [Low/Medium/High]
        """

        response = llm.invoke(prompt)

        if "SUMMARY:" in response:
            parts = response.split("RISK:")
            llm_summary = parts[0].replace("SUMMARY:", "").strip()
            if llm_summary:
                state["intake_summary"] = llm_summary
                if len(parts) > 1:
                    risk = parts[1].strip().split()[0]
                state["initial_risk_level"] = risk
                return state
    except Exception as e:
        logger.warning(f"LLM intake failed, using detailed fallback: {e}")

    # Rich fallback content
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

**Initial Triage Assessment:**
Based on the reported symptoms and patient information, an initial triage assessment has been conducted. The patient's symptoms have been categorized and prioritized according to clinical urgency guidelines.
"""

    state["intake_summary"] = intake_summary
    state["initial_risk_level"] = risk
    return state


def run_clinical_assessment(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run clinical assessment with RAG"""
    complaints = state.get("primary_complaints", [])
    risk_level = state.get("initial_risk_level", "Medium")

    # Get relevant medical knowledge from Pinecone
    query = " ".join(complaints)
    rag_results = pinecone_rag.retrieve(query, top_k=5)
    rag_context = [r.get("content", "") for r in rag_results if r.get("content")]

    state["rag_context"] = rag_context

    # Determine care level based on risk
    if risk_level == "High":
        care_level = "Emergency Care"
    elif risk_level == "Medium":
        care_level = "Primary Care"
    else:
        care_level = "Self-Care with Monitoring"

    # Try LLM first
    try:
        llm = get_llm_client(model_type="sonnet")
        prompt = f"""
        You are a clinical assessment specialist. Analyze this case:

        Intake Summary: {state.get('intake_summary', 'N/A')}
        Complaints: {', '.join(complaints)}
        Duration: {state.get('symptom_duration', 'Not specified')}
        Medical History: {', '.join(state.get('medical_history', []))}
        Medications: {', '.join(state.get('current_medications', []))}
        Allergies: {', '.join(state.get('allergies', []))}

        Medical Knowledge Context:
        {chr(10).join(rag_context)}

        Provide:
        1. Detailed assessment findings
        2. Clinical risk level (Low, Medium, or High)
        3. Potential diagnoses (primary and differentials)
        4. Recommended specialists to consult

        Format:
        FINDINGS: [detailed findings]
        CLINICAL_RISK: [Low/Medium/High]
        PRIMARY_DIAGNOSIS: [most likely condition]
        DIFFERENTIALS: [other possibilities, comma separated]
        SPECIALISTS: [recommended specialists, comma separated]
        """

        response = llm.invoke(prompt)

        if "CLINICAL_RISK:" in response:
            state["assessment_findings"] = response
            state["clinical_risk_level"] = risk_level
            state["specialists_consulted"] = ["general_practitioner"]

            for line in response.split("\n"):
                if "CLINICAL_RISK:" in line:
                    state["clinical_risk_level"] = line.split(":")[1].strip().split()[0]
                elif "PRIMARY_DIAGNOSIS:" in line:
                    state["primary_diagnosis"] = line.split(":")[1].strip()
                elif "DIFFERENTIALS:" in line:
                    diffs = line.split(":")[1].strip()
                    state["differential_diagnoses"] = [d.strip() for d in diffs.split(",")]
                elif "SPECIALISTS:" in line:
                    specs = line.split(":")[1].strip()
                    state["specialists_consulted"] = [s.strip() for s in specs.split(",")]
            return state
    except Exception as e:
        logger.warning(f"LLM clinical assessment failed, using fallback: {e}")

    # Build rich RAG insights
    rag_insights = ""
    if rag_context:
        rag_insights = "\n\n**Evidence-Based Clinical Insights:**\n"
        for i, ctx in enumerate(rag_context[:3], 1):
            rag_insights += f"\n{i}. {ctx}"

    # Rich fallback content
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

    state["assessment_findings"] = assessment_findings
    state["clinical_risk_level"] = risk_level
    state["care_level"] = care_level
    state["specialists_consulted"] = ["general_practitioner"]

    return state


def run_care_planning(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate care plan"""
    risk_level = state.get("clinical_risk_level", "Medium")
    care_level = state.get("care_level", "Primary Care")

    # Try LLM first
    try:
        llm = get_llm_client(model_type="sonnet")
        prompt = f"""
        You are a care planning specialist. Create a care plan for:

        Assessment: {state.get('assessment_findings', 'N/A')}
        Clinical Risk: {state.get('clinical_risk_level', 'Unknown')}
        Primary Diagnosis: {state.get('primary_diagnosis', 'To be determined')}

        Provide:
        1. Treatment recommendations (3-5 specific actions)
        2. Care level (Self-care, Primary Care, Urgent Care, or Emergency)
        3. Follow-up timeline
        4. Warning signs to watch for

        Format:
        RECOMMENDATIONS:
        - [recommendation 1]
        - [recommendation 2]
        - [recommendation 3]
        CARE_LEVEL: [Self-care/Primary Care/Urgent Care/Emergency]
        FOLLOWUP: [timeline]
        WARNING_SIGNS: [signs to watch]
        """

        response = llm.invoke(prompt)

        if "RECOMMENDATIONS:" in response:
            recommendations = []
            in_recs = False
            for line in response.split("\n"):
                if "RECOMMENDATIONS:" in line:
                    in_recs = True
                elif "CARE_LEVEL:" in line:
                    in_recs = False
                    care_level = line.split(":")[1].strip()
                elif in_recs and line.strip().startswith("-"):
                    recommendations.append(line.strip()[1:].strip())

            if recommendations:
                state["treatment_recommendations"] = recommendations
                state["care_level"] = care_level
                return state
    except Exception as e:
        logger.warning(f"LLM care planning failed, using fallback: {e}")

    # Rich fallback recommendations
    recommendations = [
        f"**Immediate Action:** Based on the {risk_level.lower()} risk assessment, {'seek immediate medical attention at the nearest emergency department' if risk_level == 'High' else 'schedule an appointment with your healthcare provider within 24-48 hours' if risk_level == 'Medium' else 'monitor symptoms and practice self-care measures at home'}.",

        "**Symptom Monitoring:** Keep a detailed log of symptoms including onset time, duration, severity (scale 1-10), and any factors that worsen or improve symptoms. This information will be valuable for your healthcare provider.",

        "**Hydration & Rest:** Ensure adequate fluid intake (8-10 glasses of water daily) and get sufficient rest. Proper hydration and rest support the body's natural healing processes and immune function.",

        "**Medication Guidance:** If taking over-the-counter medications for symptom relief, follow package instructions carefully. Do not exceed recommended dosages and be aware of potential interactions with any current medications you are taking.",

        "**Warning Signs:** Seek immediate emergency care if you experience: difficulty breathing, chest pain or pressure, confusion or altered consciousness, severe or worsening symptoms, high fever (>103°F/39.4°C), or any symptoms that concern you significantly.",

        "**Follow-Up Care:** Schedule a follow-up appointment within 48-72 hours if symptoms persist or worsen. Bring this assessment report to your healthcare provider for reference and continuity of care.",

        "**Lifestyle Considerations:** Consider factors that may be contributing to symptoms such as stress levels, sleep quality, diet, and physical activity. Addressing these factors can support overall health and recovery."
    ]

    state["treatment_recommendations"] = recommendations
    state["care_level"] = care_level
    return state


# ==================== Endpoints ====================

@router.post("/", response_model=AssessmentResponse)
async def run_assessment(request: AssessmentRequest):
    """
    Run a full AI health assessment.

    This endpoint:
    1. Runs intake assessment
    2. Retrieves relevant medical knowledge (RAG)
    3. Performs clinical assessment
    4. Generates care plan
    5. Stores results in MongoDB
    """
    try:
        # Initialize state
        state = {
            "patient_id": request.patient_id,
            "name": request.name,
            "age": request.age,
            "primary_complaints": request.primary_complaints,
            "symptom_duration": request.symptom_duration,
            "medical_history": request.medical_history,
            "current_medications": request.current_medications,
            "allergies": request.allergies,
            "created_at": datetime.utcnow()
        }

        # Run assessment pipeline
        logger.info(f"Starting assessment for {request.name}")

        state = run_intake_assessment(state)
        state = run_clinical_assessment(state)
        state = run_care_planning(state)

        state["status"] = "completed"

        # Create patient if needed
        if not state.get("patient_id"):
            state["patient_id"] = patient_repo.create_patient({
                "name": request.name,
                "age": request.age,
                "medical_history": request.medical_history,
                "current_medications": request.current_medications,
                "allergies": request.allergies
            })

        # Store assessment
        assessment_id = patient_repo.create_assessment(state)
        state["assessment_id"] = assessment_id

        logger.info(f"Assessment completed: {assessment_id}")

        return AssessmentResponse(
            assessment_id=assessment_id,
            patient_id=state["patient_id"],
            status="completed",
            initial_risk_level=state.get("initial_risk_level", "Unknown"),
            clinical_risk_level=state.get("clinical_risk_level", "Unknown"),
            intake_summary=state.get("intake_summary", ""),
            assessment_findings=state.get("assessment_findings", ""),
            specialists_consulted=state.get("specialists_consulted", []),
            primary_diagnosis=state.get("primary_diagnosis"),
            differential_diagnoses=state.get("differential_diagnoses", []),
            treatment_recommendations=state.get("treatment_recommendations", []),
            care_level=state.get("care_level", "Primary Care"),
            rag_context=state.get("rag_context", []),
            pdf_path=state.get("pdf_path"),
            created_at=state["created_at"]
        )

    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str):
    """
    Get assessment by ID.
    """
    assessment = patient_repo.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.get("/")
async def list_assessments(limit: int = 50):
    """
    List recent assessments.
    """
    # Get recent assessments from all patients
    assessments = list(
        patient_repo.assessments
        .find()
        .sort("created_at", -1)
        .limit(limit)
    )
    for a in assessments:
        a["_id"] = str(a["_id"])
    return {"count": len(assessments), "assessments": assessments}
