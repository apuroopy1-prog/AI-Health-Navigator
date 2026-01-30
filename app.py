"""
AI Health Navigator - Interactive Health Assessment Chatbot
"""
import streamlit as st
import os
from datetime import datetime
from typing import List, Optional
from io import BytesIO

# Load environment variables (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required on Streamlit Cloud

# For Streamlit Cloud secrets
if hasattr(st, 'secrets'):
    if 'ANTHROPIC_API_KEY' in st.secrets:
        os.environ['ANTHROPIC_API_KEY'] = st.secrets['ANTHROPIC_API_KEY']
    if 'MONGODB_URI' in st.secrets:
        os.environ['MONGODB_URI'] = st.secrets['MONGODB_URI']

# Import Claude client
try:
    from core.models.claude_client import get_llm_client
    LLM_AVAILABLE = True
except Exception as e:
    LLM_AVAILABLE = False
    st.warning(f"LLM not available: {e}")

# PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Page configuration
st.set_page_config(
    page_title="AI Health Navigator",
    page_icon="🏥",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main .block-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin-top: 1rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
    }
    .bot-message {
        background: #f0f2f6;
    }
    .user-message {
        background: #667eea;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Conversation phases
PHASES = ["greeting", "symptoms", "duration", "other_symptoms", "severity", "history", "confirm", "assessment", "complete"]

# Initialize session state
if "phase" not in st.session_state:
    st.session_state.phase = "greeting"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "data" not in st.session_state:
    st.session_state.data = {
        "symptoms": [],
        "duration": "",
        "other_symptoms": [],
        "severity": "",
        "history": [],
        "name": "",
        "age": 30
    }
if "assessment_result" not in st.session_state:
    st.session_state.assessment_result = None

def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def reset():
    st.session_state.phase = "greeting"
    st.session_state.messages = []
    st.session_state.data = {"symptoms": [], "duration": "", "other_symptoms": [], "severity": "", "history": [], "name": "", "age": 30}
    st.session_state.assessment_result = None

def run_assessment():
    """Run AI assessment using Claude"""
    data = st.session_state.data
    all_symptoms = data["symptoms"] + data["other_symptoms"]

    if LLM_AVAILABLE:
        try:
            llm = get_llm_client("sonnet")
            prompt = f"""You are an expert medical assessment AI. Analyze the following patient information:

Patient: {data.get('name', 'Patient')}, Age: {data.get('age', 'Unknown')}
Symptoms: {', '.join(all_symptoms)}
Duration: {data['duration']}
Severity: {data['severity']}
Medical History: {', '.join(data['history']) if data['history'] else 'None'}

Provide:
1. RISK_LEVEL: Low, Medium, or High
2. CARE_LEVEL: Self-Care, Primary Care, Urgent Care, or Emergency
3. POSSIBLE_CONDITIONS: 2-3 possible conditions
4. RECOMMENDATIONS: 4-5 specific recommendations
5. WARNING_SIGNS: When to seek immediate care
6. FOLLOW_UP: When to follow up"""

            response = llm.invoke(prompt, temperature=0.3)

            # Parse risk level
            risk_level = "Medium"
            if "High" in response and "RISK" in response:
                risk_level = "High"
            elif "Low" in response and "RISK" in response:
                risk_level = "Low"

            # Parse care level
            care_level = "Primary Care"
            if "Emergency" in response:
                care_level = "Emergency Care"
            elif "Urgent" in response:
                care_level = "Urgent Care"
            elif "Self-Care" in response or "Self Care" in response:
                care_level = "Self-Care"

            return {
                "risk_level": risk_level,
                "care_level": care_level,
                "full_assessment": response,
                "symptoms": all_symptoms
            }
        except Exception as e:
            st.error(f"AI Error: {e}")

    # Fallback assessment
    severity = data["severity"].lower()
    risk_level = "High" if severity == "severe" else "Medium" if severity == "moderate" else "Low"
    care_level = "Emergency Care" if risk_level == "High" else "Primary Care" if risk_level == "Medium" else "Self-Care"

    return {
        "risk_level": risk_level,
        "care_level": care_level,
        "full_assessment": f"""Assessment Summary:

RISK LEVEL: {risk_level}
CARE LEVEL: {care_level}

Based on your symptoms ({', '.join(all_symptoms)}) lasting {data['duration']} with {data['severity']} severity:

RECOMMENDATIONS:
1. {'Seek immediate medical attention' if risk_level == 'High' else 'Schedule a doctor appointment' if risk_level == 'Medium' else 'Monitor symptoms at home'}
2. Stay hydrated and get adequate rest
3. Keep a symptom diary
4. Take OTC medications as appropriate

WARNING SIGNS - Seek immediate care if:
- Difficulty breathing
- Chest pain
- High fever unresponsive to treatment
- Sudden severe symptoms

FOLLOW-UP: {'Immediately' if risk_level == 'High' else 'Within 24-48 hours' if risk_level == 'Medium' else 'If symptoms persist beyond 7 days'}""",
        "symptoms": all_symptoms
    }

def generate_pdf(assessment):
    """Generate PDF report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Health Navigator - Assessment Report", styles['Title']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Patient: {st.session_state.data.get('name', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Risk Level: {assessment['risk_level']}", styles['Heading2']))
    elements.append(Paragraph(f"Recommended Care: {assessment['care_level']}", styles['Heading2']))
    elements.append(Spacer(1, 20))

    # Add assessment text
    for line in assessment['full_assessment'].split('\n'):
        if line.strip():
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("⚠️ Disclaimer: This is for informational purposes only. Always consult a healthcare provider.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== MAIN UI ====================

# Header
st.markdown("# 🏥 AI Health Navigator")
st.markdown("*Your intelligent healthcare companion*")
st.divider()

# Progress bar
phase_index = PHASES.index(st.session_state.phase)
progress = phase_index / (len(PHASES) - 1)
st.progress(progress)
st.caption(f"Step {phase_index + 1} of {len(PHASES)}")

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.info(msg["content"])
    else:
        st.success(msg["content"])

# ==================== PHASE HANDLERS ====================

phase = st.session_state.phase

if phase == "greeting":
    st.markdown("### 👋 Welcome!")
    st.markdown("I'm here to help assess your symptoms and guide you to appropriate care.")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your name (optional):", key="name_input")
    with col2:
        age = st.number_input("Your age:", min_value=1, max_value=120, value=30, key="age_input")

    if st.button("Start Assessment", type="primary"):
        st.session_state.data["name"] = name
        st.session_state.data["age"] = age
        add_message("assistant", f"Hello{' ' + name if name else ''}! Let's begin. What symptoms are you experiencing today?")
        st.session_state.phase = "symptoms"
        st.rerun()

elif phase == "symptoms":
    st.markdown("### 🩺 What symptoms are you experiencing?")
    symptoms = st.text_area("Describe your symptoms:", placeholder="e.g., headache, fever, cough, fatigue...", key="symptoms_input")

    if st.button("Continue", type="primary"):
        if symptoms.strip():
            symptom_list = [s.strip() for s in symptoms.replace(",", "\n").split("\n") if s.strip()]
            st.session_state.data["symptoms"] = symptom_list
            add_message("user", symptoms)
            add_message("assistant", f"I understand you're experiencing: {', '.join(symptom_list)}. How long have you had these symptoms?")
            st.session_state.phase = "duration"
            st.rerun()
        else:
            st.warning("Please describe your symptoms.")

elif phase == "duration":
    st.markdown("### ⏱️ How long have you had these symptoms?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Few hours"):
            st.session_state.data["duration"] = "a few hours"
            add_message("user", "A few hours")
            add_message("assistant", "Got it. Are you experiencing any other symptoms?")
            st.session_state.phase = "other_symptoms"
            st.rerun()
        if st.button("1-3 days"):
            st.session_state.data["duration"] = "1-3 days"
            add_message("user", "1-3 days")
            add_message("assistant", "Got it. Are you experiencing any other symptoms?")
            st.session_state.phase = "other_symptoms"
            st.rerun()
    with col2:
        if st.button("About a week"):
            st.session_state.data["duration"] = "about a week"
            add_message("user", "About a week")
            add_message("assistant", "Got it. Are you experiencing any other symptoms?")
            st.session_state.phase = "other_symptoms"
            st.rerun()
        if st.button("More than a week"):
            st.session_state.data["duration"] = "more than a week"
            add_message("user", "More than a week")
            add_message("assistant", "Got it. Are you experiencing any other symptoms?")
            st.session_state.phase = "other_symptoms"
            st.rerun()

    custom = st.text_input("Or type custom duration:", key="custom_duration")
    if st.button("Submit", key="duration_submit"):
        if custom.strip():
            st.session_state.data["duration"] = custom
            add_message("user", custom)
            add_message("assistant", "Got it. Are you experiencing any other symptoms?")
            st.session_state.phase = "other_symptoms"
            st.rerun()

elif phase == "other_symptoms":
    st.markdown("### ➕ Any other symptoms?")
    other = st.text_input("Other symptoms (or type 'none'):", key="other_input")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("No other symptoms"):
            add_message("user", "No other symptoms")
            add_message("assistant", "How would you rate the severity of your symptoms?")
            st.session_state.phase = "severity"
            st.rerun()
    with col2:
        if st.button("Submit other symptoms"):
            if other.strip() and other.lower() not in ["none", "no", "n/a"]:
                other_list = [s.strip() for s in other.replace(",", "\n").split("\n") if s.strip()]
                st.session_state.data["other_symptoms"] = other_list
                add_message("user", other)
            add_message("assistant", "How would you rate the severity of your symptoms?")
            st.session_state.phase = "severity"
            st.rerun()

elif phase == "severity":
    st.markdown("### 📊 How severe are your symptoms?")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("😊 Mild", help="Noticeable but not affecting daily life"):
            st.session_state.data["severity"] = "Mild"
            add_message("user", "Mild")
            add_message("assistant", "Do you have any relevant medical history?")
            st.session_state.phase = "history"
            st.rerun()
    with col2:
        if st.button("😐 Moderate", help="Affecting some daily activities"):
            st.session_state.data["severity"] = "Moderate"
            add_message("user", "Moderate")
            add_message("assistant", "Do you have any relevant medical history?")
            st.session_state.phase = "history"
            st.rerun()
    with col3:
        if st.button("😣 Severe", help="Significantly impacting daily life"):
            st.session_state.data["severity"] = "Severe"
            add_message("user", "Severe")
            add_message("assistant", "Do you have any relevant medical history?")
            st.session_state.phase = "history"
            st.rerun()

elif phase == "history":
    st.markdown("### 📋 Any relevant medical history?")
    history = st.text_input("e.g., diabetes, hypertension, allergies (or 'none'):", key="history_input")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("No relevant history"):
            add_message("user", "None")
            st.session_state.phase = "confirm"
            st.rerun()
    with col2:
        if st.button("Submit history"):
            if history.strip() and history.lower() not in ["none", "no", "n/a"]:
                history_list = [h.strip() for h in history.replace(",", "\n").split("\n") if h.strip()]
                st.session_state.data["history"] = history_list
                add_message("user", history)
            st.session_state.phase = "confirm"
            st.rerun()

elif phase == "confirm":
    st.markdown("### ✅ Please confirm your information")

    data = st.session_state.data
    st.markdown(f"""
    | Field | Value |
    |-------|-------|
    | **Symptoms** | {', '.join(data['symptoms'])} |
    | **Duration** | {data['duration']} |
    | **Other Symptoms** | {', '.join(data['other_symptoms']) if data['other_symptoms'] else 'None'} |
    | **Severity** | {data['severity']} |
    | **Medical History** | {', '.join(data['history']) if data['history'] else 'None'} |
    """)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Run Assessment", type="primary"):
            add_message("assistant", "Analyzing your symptoms... Please wait.")
            st.session_state.phase = "assessment"
            st.rerun()
    with col2:
        if st.button("🔄 Start Over"):
            reset()
            st.rerun()

elif phase == "assessment":
    with st.spinner("🔍 Analyzing your symptoms with AI..."):
        result = run_assessment()
        st.session_state.assessment_result = result
        st.session_state.phase = "complete"
        st.rerun()

elif phase == "complete":
    result = st.session_state.assessment_result

    # Risk level display
    risk = result["risk_level"]
    if risk == "High":
        st.error(f"🚨 **Risk Level: {risk}**")
    elif risk == "Medium":
        st.warning(f"⚠️ **Risk Level: {risk}**")
    else:
        st.success(f"✅ **Risk Level: {risk}**")

    st.info(f"**Recommended Care:** {result['care_level']}")

    # Full assessment
    with st.expander("📋 View Full Assessment", expanded=True):
        st.markdown(result["full_assessment"])

    # Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Assessment", type="primary"):
            reset()
            st.rerun()
    with col2:
        pdf = generate_pdf(result)
        st.download_button(
            "📄 Download PDF",
            data=pdf.getvalue(),
            file_name=f"health_assessment_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

    # Disclaimer
    st.divider()
    st.warning("⚠️ **Disclaimer:** This assessment is for informational purposes only and does not constitute medical advice. Always consult with a qualified healthcare provider. In emergencies, call 911.")

# Sidebar
with st.sidebar:
    st.markdown("### ℹ️ About")
    st.markdown("AI Health Navigator helps you understand your symptoms and guides you to appropriate care.")
    st.divider()
    if st.button("🔄 Reset"):
        reset()
        st.rerun()
    st.divider()
    st.caption("Powered by Claude AI")
