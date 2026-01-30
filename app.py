"""
AI Health Navigator - Interactive Chatbot with LangGraph
Step-by-step symptom collection with modern UI
"""
import streamlit as st
import requests
import os
import io
from datetime import datetime
from typing import TypedDict, Annotated, List, Optional
from enum import Enum

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# LangGraph imports
from langgraph.graph import StateGraph, END

# Import Claude client
from core.models.claude_client import get_llm_client

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Configuration
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="AI Health Navigator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern CSS styling
st.markdown("""
<style>
    /* Modern gradient background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%) !important;
    }

    .block-container {
        max-width: 900px !important;
        padding: 2rem !important;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main chat container */
    .chat-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 25px;
        padding: 2rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        margin: 1rem 0;
    }

    /* Header styling */
    .header-container {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 25px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
    }

    .header-title {
        color: white !important;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }

    .header-subtitle {
        color: rgba(255,255,255,0.9) !important;
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }

    /* Message bubbles */
    .message-container {
        display: flex;
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .message-bot {
        justify-content: flex-start;
    }

    .message-user {
        justify-content: flex-end;
    }

    .message-bubble {
        max-width: 80%;
        padding: 1rem 1.5rem;
        border-radius: 20px;
        font-size: 1rem;
        line-height: 1.5;
    }

    .bubble-bot {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        color: #2d3748;
        border-bottom-left-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }

    .bubble-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-bottom-right-radius: 5px;
        box-shadow: 0 2px 15px rgba(102, 126, 234, 0.3);
    }

    /* Avatar styling */
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        margin: 0 0.75rem;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }

    .avatar-bot {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .avatar-user {
        background: linear-gradient(135deg, #38b2ac 0%, #319795 100%);
    }

    /* Option buttons */
    .option-btn {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px solid #e2e8f0;
        color: #4a5568;
        padding: 0.75rem 1.5rem;
        border-radius: 25px;
        margin: 0.25rem;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500;
    }

    .option-btn:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: transparent;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }

    /* Progress indicator */
    .progress-container {
        display: flex;
        justify-content: center;
        margin: 1.5rem 0;
        gap: 0.5rem;
    }

    .progress-step {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #e2e8f0;
        transition: all 0.3s ease;
    }

    .progress-step.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        transform: scale(1.2);
    }

    .progress-step.completed {
        background: #38b2ac;
    }

    /* Input area */
    .stTextInput > div > div > input {
        border-radius: 25px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    }

    /* Severity buttons */
    .severity-mild {
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%) !important;
    }

    .severity-moderate {
        background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%) !important;
    }

    .severity-severe {
        background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%) !important;
    }

    /* Result cards */
    .result-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }

    .risk-high {
        border-left-color: #f56565 !important;
        background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%) !important;
    }

    .risk-medium {
        border-left-color: #ed8936 !important;
        background: linear-gradient(135deg, #fffaf0 0%, #feebc8 100%) !important;
    }

    .risk-low {
        border-left-color: #48bb78 !important;
        background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 100%) !important;
    }

    /* Typing indicator */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 0.5rem 1rem;
    }

    .typing-dot {
        width: 8px;
        height: 8px;
        background: #667eea;
        border-radius: 50%;
        animation: typingBounce 1.4s infinite ease-in-out;
    }

    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }

    @keyframes typingBounce {
        0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }

    /* Scrollable chat area */
    .chat-messages {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 1.5rem;
        color: rgba(255,255,255,0.7);
        font-size: 0.9rem;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ==================== Conversation States ====================

class ConversationPhase(str, Enum):
    GREETING = "greeting"
    ASK_SYMPTOMS = "ask_symptoms"
    ASK_DURATION = "ask_duration"
    ASK_OTHER_SYMPTOMS = "ask_other_symptoms"
    ASK_SEVERITY = "ask_severity"
    ASK_HISTORY = "ask_history"
    CONFIRM = "confirm"
    ASSESSMENT = "assessment"
    COMPLETE = "complete"


class ConversationState(TypedDict):
    phase: str
    messages: List[dict]
    primary_symptoms: List[str]
    duration: str
    other_symptoms: List[str]
    severity: str
    medical_history: List[str]
    patient_name: str
    patient_age: int
    assessment_result: Optional[dict]


# ==================== LangGraph Workflow ====================

def greeting_node(state: ConversationState) -> ConversationState:
    """Initial greeting"""
    state["messages"].append({
        "role": "assistant",
        "content": "Hello! I'm your AI Health Navigator. I'm here to help assess your symptoms and guide you to appropriate care.\n\n**Let's start with some questions.**\n\nWhat symptoms are you experiencing today?"
    })
    state["phase"] = ConversationPhase.ASK_SYMPTOMS
    return state


def process_symptoms_node(state: ConversationState) -> ConversationState:
    """Process primary symptoms and ask for duration"""
    symptoms = state.get("primary_symptoms", [])
    if symptoms:
        symptom_text = ", ".join(symptoms)
        state["messages"].append({
            "role": "assistant",
            "content": f"I understand you're experiencing **{symptom_text}**.\n\nHow long have you been experiencing these symptoms?\n\n*For example: 2 days, 1 week, a few hours*"
        })
        state["phase"] = ConversationPhase.ASK_DURATION
    return state


def process_duration_node(state: ConversationState) -> ConversationState:
    """Process duration and ask for other symptoms"""
    duration = state.get("duration", "")
    if duration:
        state["messages"].append({
            "role": "assistant",
            "content": f"Thank you. So you've had these symptoms for **{duration}**.\n\nAre you experiencing any other symptoms along with these?\n\n*Type them in or say 'No' if that's all*"
        })
        state["phase"] = ConversationPhase.ASK_OTHER_SYMPTOMS
    return state


def process_other_symptoms_node(state: ConversationState) -> ConversationState:
    """Process other symptoms and ask for severity"""
    state["messages"].append({
        "role": "assistant",
        "content": "Now, please rate the severity of your symptoms:\n\nHow would you describe your symptoms overall?"
    })
    state["phase"] = ConversationPhase.ASK_SEVERITY
    return state


def process_severity_node(state: ConversationState) -> ConversationState:
    """Process severity and ask for medical history"""
    severity = state.get("severity", "")
    state["messages"].append({
        "role": "assistant",
        "content": f"Got it - your symptoms are **{severity}**.\n\nDo you have any existing medical conditions or past medical history I should know about?\n\n*For example: diabetes, hypertension, asthma, or say 'None'*"
    })
    state["phase"] = ConversationPhase.ASK_HISTORY
    return state


def process_history_node(state: ConversationState) -> ConversationState:
    """Process history and show confirmation"""
    all_symptoms = state.get("primary_symptoms", []) + state.get("other_symptoms", [])
    symptom_list = ", ".join(all_symptoms) if all_symptoms else "Not specified"
    history = state.get("medical_history", [])
    history_text = ", ".join(history) if history else "None reported"

    summary = f"""**Summary of Information:**

- **Symptoms:** {symptom_list}
- **Duration:** {state.get('duration', 'Not specified')}
- **Severity:** {state.get('severity', 'Not specified')}
- **Medical History:** {history_text}

Is this information correct? I'll now analyze your symptoms and provide recommendations."""

    state["messages"].append({
        "role": "assistant",
        "content": summary
    })
    state["phase"] = ConversationPhase.CONFIRM
    return state


def run_assessment_node(state: ConversationState) -> ConversationState:
    """Run the actual AI assessment"""
    all_symptoms = state.get("primary_symptoms", []) + state.get("other_symptoms", [])

    # Get LLM client
    llm = get_llm_client("sonnet")

    # Build prompt for Claude
    prompt = f"""You are an expert medical assessment AI. Analyze the following patient information and provide a comprehensive assessment.

Patient Information:
- Name: {state.get('patient_name', 'Patient')}
- Age: {state.get('patient_age', 'Unknown')}
- Symptoms: {', '.join(all_symptoms)}
- Duration: {state.get('duration', 'Not specified')}
- Severity: {state.get('severity', 'Moderate')}
- Medical History: {', '.join(state.get('medical_history', ['None']))}

Please provide:
1. RISK_LEVEL: (Low, Medium, or High)
2. CARE_LEVEL: (Self-Care, Primary Care, Urgent Care, or Emergency)
3. POSSIBLE_CONDITIONS: List 2-3 possible conditions
4. KEY_RECOMMENDATIONS: List 4-5 specific recommendations
5. WARNING_SIGNS: What symptoms would require immediate care
6. FOLLOW_UP: When to follow up with a doctor

Format your response clearly with these sections."""

    system_prompt = """You are a compassionate and thorough healthcare AI assistant. Provide evidence-based medical guidance while always recommending professional consultation for serious concerns. Be specific and actionable in your recommendations."""

    try:
        response = llm.invoke(prompt, system_prompt=system_prompt, temperature=0.3)

        # Parse the response
        risk_level = "Medium"
        care_level = "Primary Care"

        if "RISK_LEVEL:" in response:
            risk_line = response.split("RISK_LEVEL:")[1].split("\n")[0]
            if "High" in risk_line:
                risk_level = "High"
            elif "Low" in risk_line:
                risk_level = "Low"

        if "CARE_LEVEL:" in response:
            care_line = response.split("CARE_LEVEL:")[1].split("\n")[0]
            if "Emergency" in care_line:
                care_level = "Emergency Care"
            elif "Urgent" in care_line:
                care_level = "Urgent Care"
            elif "Self" in care_line:
                care_level = "Self-Care with Monitoring"

        state["assessment_result"] = {
            "risk_level": risk_level,
            "care_level": care_level,
            "full_assessment": response,
            "symptoms": all_symptoms,
            "duration": state.get("duration"),
            "severity": state.get("severity"),
            "medical_history": state.get("medical_history", [])
        }

    except Exception as e:
        # Fallback assessment
        state["assessment_result"] = generate_fallback_assessment(state)

    state["phase"] = ConversationPhase.COMPLETE
    return state


def generate_fallback_assessment(state: ConversationState) -> dict:
    """Generate fallback assessment when LLM is unavailable"""
    all_symptoms = state.get("primary_symptoms", []) + state.get("other_symptoms", [])
    symptoms_text = " ".join(all_symptoms).lower()
    severity = state.get("severity", "moderate").lower()

    # Determine risk based on symptoms and severity
    emergency_keywords = ["chest pain", "difficulty breathing", "unconscious", "severe bleeding", "stroke"]
    urgent_keywords = ["high fever", "severe pain", "blood", "confusion", "rapid heartbeat"]

    risk_level = "Low"
    care_level = "Self-Care with Monitoring"

    if severity == "severe" or any(k in symptoms_text for k in emergency_keywords):
        risk_level = "High"
        care_level = "Emergency Care"
    elif severity == "moderate" or any(k in symptoms_text for k in urgent_keywords):
        risk_level = "Medium"
        care_level = "Primary Care"

    assessment = f"""**Assessment Results:**

**RISK LEVEL:** {risk_level}

**RECOMMENDED CARE:** {care_level}

**POSSIBLE CONDITIONS:**
Based on your symptoms ({', '.join(all_symptoms)}), several conditions may need to be considered. A healthcare provider can perform a thorough evaluation.

**KEY RECOMMENDATIONS:**
1. {'Seek immediate medical attention' if risk_level == 'High' else 'Schedule an appointment with your healthcare provider' if risk_level == 'Medium' else 'Monitor your symptoms at home'}
2. Keep a symptom diary noting severity and triggers
3. Stay hydrated and get adequate rest
4. Avoid activities that worsen your symptoms
5. Take over-the-counter medications as appropriate for symptom relief

**WARNING SIGNS - Seek Immediate Care If:**
- Difficulty breathing or shortness of breath
- Chest pain or pressure
- Sudden severe headache
- Confusion or altered consciousness
- High fever unresponsive to treatment

**FOLLOW-UP:**
{'Immediately if symptoms worsen' if risk_level == 'High' else 'Within 24-48 hours' if risk_level == 'Medium' else 'If symptoms persist beyond 7 days or worsen'}"""

    return {
        "risk_level": risk_level,
        "care_level": care_level,
        "full_assessment": assessment,
        "symptoms": all_symptoms,
        "duration": state.get("duration"),
        "severity": state.get("severity"),
        "medical_history": state.get("medical_history", [])
    }


# Build the LangGraph workflow
def build_conversation_graph():
    """Build the LangGraph conversation workflow"""
    graph = StateGraph(ConversationState)

    # Add nodes
    graph.add_node("greeting", greeting_node)
    graph.add_node("process_symptoms", process_symptoms_node)
    graph.add_node("process_duration", process_duration_node)
    graph.add_node("process_other_symptoms", process_other_symptoms_node)
    graph.add_node("process_severity", process_severity_node)
    graph.add_node("process_history", process_history_node)
    graph.add_node("run_assessment", run_assessment_node)

    # Add edges
    graph.set_entry_point("greeting")
    graph.add_edge("greeting", END)
    graph.add_edge("process_symptoms", END)
    graph.add_edge("process_duration", END)
    graph.add_edge("process_other_symptoms", END)
    graph.add_edge("process_severity", END)
    graph.add_edge("process_history", END)
    graph.add_edge("run_assessment", END)

    return graph.compile()


# ==================== Session State ====================

if "conversation_state" not in st.session_state:
    st.session_state.conversation_state = {
        "phase": ConversationPhase.GREETING,
        "messages": [],
        "primary_symptoms": [],
        "duration": "",
        "other_symptoms": [],
        "severity": "",
        "medical_history": [],
        "patient_name": "",
        "patient_age": 30,
        "assessment_result": None
    }

if "workflow" not in st.session_state:
    st.session_state.workflow = build_conversation_graph()


def add_message(role: str, content: str):
    """Add a message to the conversation"""
    st.session_state.conversation_state["messages"].append({
        "role": role,
        "content": content
    })


def reset_conversation():
    """Reset the conversation"""
    st.session_state.conversation_state = {
        "phase": ConversationPhase.GREETING,
        "messages": [],
        "primary_symptoms": [],
        "duration": "",
        "other_symptoms": [],
        "severity": "",
        "medical_history": [],
        "patient_name": "",
        "patient_age": 30,
        "assessment_result": None
    }


# ==================== UI Rendering ====================

def render_message(role: str, content: str):
    """Render a chat message with custom styling"""
    if role == "assistant":
        st.markdown(f"""
        <div class="message-container message-bot">
            <div class="avatar avatar-bot">🏥</div>
            <div class="message-bubble bubble-bot">{content.replace(chr(10), '<br>')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="message-container message-user">
            <div class="message-bubble bubble-user">{content.replace(chr(10), '<br>')}</div>
            <div class="avatar avatar-user">👤</div>
        </div>
        """, unsafe_allow_html=True)


def render_progress():
    """Render progress indicator"""
    phases = [
        ConversationPhase.GREETING,
        ConversationPhase.ASK_SYMPTOMS,
        ConversationPhase.ASK_DURATION,
        ConversationPhase.ASK_OTHER_SYMPTOMS,
        ConversationPhase.ASK_SEVERITY,
        ConversationPhase.ASK_HISTORY,
        ConversationPhase.COMPLETE
    ]
    current = st.session_state.conversation_state["phase"]

    progress_html = '<div class="progress-container">'
    for i, phase in enumerate(phases):
        if phases.index(current) > i:
            progress_html += '<div class="progress-step completed"></div>'
        elif phase == current:
            progress_html += '<div class="progress-step active"></div>'
        else:
            progress_html += '<div class="progress-step"></div>'
    progress_html += '</div>'

    st.markdown(progress_html, unsafe_allow_html=True)


# ==================== Main App ====================

# Header
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🏥 AI Health Navigator</h1>
    <p class="header-subtitle">Your intelligent healthcare companion powered by Claude AI</p>
</div>
""", unsafe_allow_html=True)

# Progress indicator
render_progress()

# Chat container
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Initialize conversation if needed
state = st.session_state.conversation_state
if state["phase"] == ConversationPhase.GREETING and not state["messages"]:
    result = st.session_state.workflow.invoke(state)
    st.session_state.conversation_state = result

# Display messages
for msg in st.session_state.conversation_state["messages"]:
    render_message(msg["role"], msg["content"])

# Handle current phase
phase = st.session_state.conversation_state["phase"]

if phase == ConversationPhase.ASK_SYMPTOMS:
    user_input = st.text_input("", placeholder="Describe your symptoms (e.g., headache, fever, cough)...", key="symptoms_input")
    if st.button("Continue", key="btn_symptoms"):
        if user_input:
            add_message("user", user_input)
            symptoms = [s.strip() for s in user_input.replace(",", "\n").split("\n") if s.strip()]
            st.session_state.conversation_state["primary_symptoms"] = symptoms
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()

elif phase == ConversationPhase.ASK_DURATION:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Few hours", key="dur_hours"):
            add_message("user", "A few hours")
            st.session_state.conversation_state["duration"] = "a few hours"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()
    with col2:
        if st.button("1-3 days", key="dur_days"):
            add_message("user", "1-3 days")
            st.session_state.conversation_state["duration"] = "1-3 days"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()
    with col3:
        if st.button("About a week", key="dur_week"):
            add_message("user", "About a week")
            st.session_state.conversation_state["duration"] = "about a week"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()
    with col4:
        if st.button("More than a week", key="dur_more"):
            add_message("user", "More than a week")
            st.session_state.conversation_state["duration"] = "more than a week"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()

    # Custom input
    custom_duration = st.text_input("", placeholder="Or type custom duration...", key="custom_dur")
    if st.button("Submit Duration", key="btn_dur"):
        if custom_duration:
            add_message("user", custom_duration)
            st.session_state.conversation_state["duration"] = custom_duration
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()

elif phase == ConversationPhase.ASK_OTHER_SYMPTOMS:
    user_input = st.text_input("", placeholder="Any other symptoms? (or type 'No')...", key="other_input")
    if st.button("Continue", key="btn_other"):
        add_message("user", user_input if user_input else "No other symptoms")
        if user_input and user_input.lower() not in ["no", "none", "no other symptoms", "that's all"]:
            other_symptoms = [s.strip() for s in user_input.replace(",", "\n").split("\n") if s.strip()]
            st.session_state.conversation_state["other_symptoms"] = other_symptoms
        result = st.session_state.workflow.invoke(st.session_state.conversation_state)
        st.session_state.conversation_state = result
        st.rerun()

elif phase == ConversationPhase.ASK_SEVERITY:
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("😊 Mild", key="sev_mild", help="Noticeable but not interfering with daily activities"):
            add_message("user", "Mild")
            st.session_state.conversation_state["severity"] = "Mild"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()
    with col2:
        if st.button("😐 Moderate", key="sev_mod", help="Affecting daily activities somewhat"):
            add_message("user", "Moderate")
            st.session_state.conversation_state["severity"] = "Moderate"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()
    with col3:
        if st.button("😣 Severe", key="sev_sev", help="Significantly impacting daily life"):
            add_message("user", "Severe")
            st.session_state.conversation_state["severity"] = "Severe"
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()

elif phase == ConversationPhase.ASK_HISTORY:
    user_input = st.text_input("", placeholder="Enter medical history (or 'None')...", key="history_input")
    if st.button("Continue", key="btn_history"):
        add_message("user", user_input if user_input else "None")
        if user_input and user_input.lower() not in ["no", "none", "nothing"]:
            history = [h.strip() for h in user_input.replace(",", "\n").split("\n") if h.strip()]
            st.session_state.conversation_state["medical_history"] = history
        result = st.session_state.workflow.invoke(st.session_state.conversation_state)
        st.session_state.conversation_state = result
        st.rerun()

elif phase == ConversationPhase.CONFIRM:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, Run Assessment", key="confirm_yes"):
            add_message("user", "Yes, proceed with the assessment")
            # Add loading message
            add_message("assistant", "Analyzing your symptoms... This may take a moment.")
            result = st.session_state.workflow.invoke(st.session_state.conversation_state)
            st.session_state.conversation_state = result
            st.rerun()
    with col2:
        if st.button("🔄 Start Over", key="confirm_no"):
            reset_conversation()
            st.rerun()

elif phase == ConversationPhase.COMPLETE:
    # Display assessment results
    assessment = st.session_state.conversation_state.get("assessment_result", {})
    if assessment:
        risk_level = assessment.get("risk_level", "Medium")
        risk_class = "risk-low" if risk_level == "Low" else "risk-medium" if risk_level == "Medium" else "risk-high"
        risk_icon = "✅" if risk_level == "Low" else "⚠️" if risk_level == "Medium" else "🚨"

        st.markdown(f"""
        <div class="result-card {risk_class}">
            <h2 style="margin-top: 0; color: inherit;">{risk_icon} Assessment Complete</h2>
            <p><strong>Risk Level:</strong> {risk_level}</p>
            <p><strong>Recommended Care:</strong> {assessment.get('care_level', 'Primary Care')}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 View Full Assessment", expanded=True):
            st.markdown(assessment.get("full_assessment", "No detailed assessment available."))

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Assessment", key="new_assessment"):
                reset_conversation()
                st.rerun()
        with col2:
            # Generate PDF
            from io import BytesIO
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph("AI Health Navigator - Assessment Report", styles['Title']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
            elements.append(Paragraph(f"Risk Level: {risk_level}", styles['Normal']))
            elements.append(Paragraph(f"Care Level: {assessment.get('care_level', 'N/A')}", styles['Normal']))
            elements.append(Spacer(1, 20))
            assessment_text = assessment.get("full_assessment", "").replace("**", "").replace("*", "")
            for line in assessment_text.split("\n"):
                if line.strip():
                    elements.append(Paragraph(line, styles['Normal']))
                    elements.append(Spacer(1, 6))
            doc.build(elements)
            pdf_buffer.seek(0)

            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_buffer.getvalue(),
                file_name=f"health_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

        # Disclaimer
        st.markdown("""
        <div style="background: #fef3c7; padding: 1rem; border-radius: 15px; margin-top: 1.5rem; border-left: 4px solid #f59e0b;">
            <p style="color: #92400e; margin: 0; font-size: 0.9rem;">
                <strong>⚠️ Disclaimer:</strong> This assessment is for informational purposes only and does not constitute medical advice.
                Always consult with a qualified healthcare provider for medical concerns. In emergencies, call 911 immediately.
            </p>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Sidebar with patient info
with st.sidebar:
    st.markdown("### 👤 Patient Info")
    name = st.text_input("Name", value=st.session_state.conversation_state.get("patient_name", ""))
    age = st.number_input("Age", min_value=0, max_value=120, value=st.session_state.conversation_state.get("patient_age", 30))
    st.session_state.conversation_state["patient_name"] = name
    st.session_state.conversation_state["patient_age"] = age

    st.markdown("---")
    st.markdown("### 🔌 System Status")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.warning("⚠️ API Offline")
    except:
        st.warning("⚠️ API Offline - Using Local Mode")

    st.markdown("---")
    if st.button("🔄 Reset Conversation"):
        reset_conversation()
        st.rerun()

# Footer
st.markdown("""
<div class="footer">
    <p>AI Health Navigator v2.0 | Powered by Claude AI & LangGraph</p>
</div>
""", unsafe_allow_html=True)
