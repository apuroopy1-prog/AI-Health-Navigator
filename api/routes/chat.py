"""
Chat API Routes - Conversational AI for symptom checking
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo
from database.pinecone_client import pinecone_rag
from core.models.claude_client import get_llm_client
from config.agent_prompts import AGENT_PROMPTS, SYMPTOM_FOLLOWUPS

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Models ====================

class ChatMessage(BaseModel):
    """A single chat message"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    session_id: Optional[str] = Field(None, description="Existing session ID")
    message: str = Field(..., min_length=1, description="User message")
    patient_id: Optional[str] = Field(None, description="Link to existing patient")


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    session_id: str
    message: str
    phase: str
    collected_symptoms: List[str] = []
    follow_up_questions: List[str] = []
    ready_for_assessment: bool = False
    metadata: Dict[str, Any] = {}


class SessionCreate(BaseModel):
    """Request to create a new chat session"""
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None


# ==================== Chat Logic ====================

class ConversationalAgent:
    """
    Conversational AI agent for symptom collection.
    Uses Claude to have natural conversations and collect medical info.
    """

    def __init__(self):
        self.llm = get_llm_client(model_type="haiku")  # Fast for chat

    def get_greeting(self) -> str:
        """Generate initial greeting"""
        return (
            "Hello! I'm your AI Health Navigator. I'm here to help understand "
            "your symptoms and guide you to appropriate care.\n\n"
            "What brings you in today? Please describe what you're experiencing."
        )

    def process_message(
        self,
        message: str,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a user message and generate response.

        Args:
            message: User's message
            session_data: Current session state

        Returns:
            Updated session data with response
        """
        messages = session_data.get("messages", [])
        collected_symptoms = session_data.get("collected_symptoms", [])
        phase = session_data.get("phase", "symptom_collection")

        # Extract symptoms from message
        new_symptoms = self._extract_symptoms(message)
        collected_symptoms.extend(new_symptoms)
        collected_symptoms = list(set(collected_symptoms))  # Dedupe

        # Determine if we have enough info
        if len(collected_symptoms) >= 3 and len(messages) >= 4:
            # We have enough, offer to proceed
            response = self._generate_summary_response(collected_symptoms, session_data)
            phase = "summary_confirmation"
            ready = True
        else:
            # Generate follow-up questions
            response = self._generate_follow_up(message, collected_symptoms, messages)
            ready = False

        # Get follow-up questions for display
        follow_ups = self._get_follow_up_questions(collected_symptoms)

        return {
            "response": response,
            "phase": phase,
            "collected_symptoms": collected_symptoms,
            "follow_up_questions": follow_ups,
            "ready_for_assessment": ready
        }

    def _extract_symptoms(self, message: str) -> List[str]:
        """Extract symptoms from user message using LLM"""
        prompt = f"""
        Extract any symptoms or health complaints from this message.
        Return only the symptoms as a comma-separated list.
        If no symptoms found, return "none".

        Message: "{message}"

        Symptoms:
        """

        response = self.llm.invoke(prompt, temperature=0.3)

        if "none" in response.lower():
            return []

        symptoms = [s.strip() for s in response.split(",") if s.strip()]
        return symptoms[:5]  # Limit to 5 per message

    def _generate_follow_up(
        self,
        message: str,
        symptoms: List[str],
        history: List[Dict[str, str]]
    ) -> str:
        """Generate a follow-up response"""
        # Build conversation context
        context = "\n".join([
            f"{m['role'].title()}: {m['content']}"
            for m in history[-6:]  # Last 6 messages
        ])

        prompt = f"""
        You are a friendly healthcare intake assistant. Continue this conversation
        to gather more information about the patient's symptoms.

        Previous conversation:
        {context}

        User's latest message: {message}

        Symptoms collected so far: {', '.join(symptoms) if symptoms else 'None yet'}

        Generate a helpful response that:
        1. Acknowledges what the patient said
        2. Asks a relevant follow-up question about their symptoms
        3. Is warm and empathetic
        4. Keeps the response concise (2-3 sentences)

        Response:
        """

        return self.llm.invoke(prompt, temperature=0.7)

    def _generate_summary_response(
        self,
        symptoms: List[str],
        session_data: Dict[str, Any]
    ) -> str:
        """Generate summary and offer to proceed to assessment"""
        return (
            f"Thank you for sharing that information. Let me summarize what I've gathered:\n\n"
            f"**Symptoms reported:** {', '.join(symptoms)}\n\n"
            f"I have enough information to run a comprehensive AI assessment. "
            f"Would you like me to proceed with the assessment? "
            f"This will analyze your symptoms and provide personalized recommendations."
        )

    def _get_follow_up_questions(self, symptoms: List[str]) -> List[str]:
        """Get relevant follow-up questions for symptoms"""
        questions = []

        for symptom in symptoms:
            symptom_lower = symptom.lower()
            for key, qs in SYMPTOM_FOLLOWUPS.items():
                if key in symptom_lower:
                    questions.extend(qs[:2])  # First 2 questions per symptom

        return list(set(questions))[:5]  # Max 5 unique questions


# Global agent instance
chat_agent = ConversationalAgent()


# ==================== Endpoints ====================

@router.post("/sessions", response_model=dict)
async def create_session(request: SessionCreate):
    """
    Create a new chat session.
    """
    session_data = {
        "patient_id": request.patient_id,
        "patient_name": request.patient_name,
        "phase": "greeting",
        "collected_symptoms": [],
        "messages": [],
        "state": {}
    }

    session_id = patient_repo.create_session(session_data)

    # Get greeting
    greeting = chat_agent.get_greeting()

    # Add greeting to session
    patient_repo.add_message_to_session(session_id, "assistant", greeting)

    return {
        "session_id": session_id,
        "message": greeting,
        "phase": "symptom_collection"
    }


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message in a chat session.

    If no session_id provided, creates a new session.
    """
    # Get or create session
    if request.session_id:
        session = patient_repo.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = request.session_id
    else:
        # Create new session
        session_data = {
            "patient_id": request.patient_id,
            "phase": "symptom_collection",
            "collected_symptoms": [],
            "messages": []
        }
        session_id = patient_repo.create_session(session_data)
        session = patient_repo.get_session(session_id)

    # Add user message
    patient_repo.add_message_to_session(session_id, "user", request.message)

    # Process message
    result = chat_agent.process_message(request.message, session)

    # Add assistant response
    patient_repo.add_message_to_session(session_id, "assistant", result["response"])

    # Update session state
    patient_repo.update_session_state(session_id, {
        "phase": result["phase"],
        "collected_symptoms": result["collected_symptoms"]
    })

    return ChatResponse(
        session_id=session_id,
        message=result["response"],
        phase=result["phase"],
        collected_symptoms=result["collected_symptoms"],
        follow_up_questions=result["follow_up_questions"],
        ready_for_assessment=result["ready_for_assessment"],
        metadata={"timestamp": datetime.utcnow().isoformat()}
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get session details and message history.
    """
    session = patient_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/assess")
async def trigger_assessment(session_id: str):
    """
    Trigger full assessment from chat session data.
    """
    session = patient_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session.get("state", {})
    symptoms = state.get("collected_symptoms", [])

    if not symptoms:
        raise HTTPException(
            status_code=400,
            detail="No symptoms collected. Continue the conversation first."
        )

    # Import assessment logic
    from api.routes.assessments import (
        run_intake_assessment,
        run_clinical_assessment,
        run_care_planning
    )

    # Build assessment state from session
    assessment_state = {
        "patient_id": session.get("patient_id"),
        "name": session.get("patient_name", "Chat Patient"),
        "primary_complaints": symptoms,
        "created_at": datetime.utcnow()
    }

    # Run assessment pipeline
    assessment_state = run_intake_assessment(assessment_state)
    assessment_state = run_clinical_assessment(assessment_state)
    assessment_state = run_care_planning(assessment_state)
    assessment_state["status"] = "completed"

    # Store assessment
    assessment_id = patient_repo.create_assessment(assessment_state)

    return {
        "assessment_id": assessment_id,
        "session_id": session_id,
        "status": "completed",
        "message": "Assessment completed successfully"
    }
