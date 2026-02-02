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
try:
    if 'ANTHROPIC_API_KEY' in st.secrets:
        os.environ['ANTHROPIC_API_KEY'] = st.secrets['ANTHROPIC_API_KEY']
    if 'MONGODB_URI' in st.secrets:
        os.environ['MONGODB_URI'] = st.secrets['MONGODB_URI']
except Exception:
    pass  # No secrets file locally, use .env instead

# Import LangGraph workflow
try:
    from streamlit_langgraph import run_patient_assessment
    LANGGRAPH_AVAILABLE = True
except Exception as e:
    LANGGRAPH_AVAILABLE = False

# Import Claude client as fallback
try:
    from core.models.claude_client import get_llm_client
    LLM_AVAILABLE = True
except Exception as e:
    LLM_AVAILABLE = False

# PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Page configuration
st.set_page_config(
    page_title="AI Health Navigator",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Minimal styling - keep Streamlit defaults
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
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
    """Run AI assessment using LangGraph workflow"""
    data = st.session_state.data
    all_symptoms = data["symptoms"] + data["other_symptoms"]
    symptoms_str = ', '.join(all_symptoms) if all_symptoms else 'Not specified'
    history_str = ', '.join(data['history']) if data['history'] else 'None reported'

    # Try LangGraph workflow first (preferred method)
    if LANGGRAPH_AVAILABLE:
        try:
            # Prepare patient data for LangGraph
            patient_data = {
                "name": data.get('name', 'Patient'),
                "age": data.get('age', 30),
                "primary_complaints": all_symptoms,
                "symptom_duration": data.get('duration', ''),
                "medical_history": data.get('history', []),
                "current_medications": [],
                "allergies": []
            }

            # Run the LangGraph workflow
            result = run_patient_assessment(patient_data)

            # Build comprehensive report from LangGraph results
            full_report = f"""## HEALTH ASSESSMENT REPORT

---

{result.get('intake_summary', '')}

---

{result.get('assessment_findings', '')}

---

### TREATMENT RECOMMENDATIONS

"""
            # Add treatment recommendations
            recommendations = result.get('treatment_recommendations', [])
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    full_report += f"{i}. {rec}\n\n"
            else:
                full_report += "Please consult with your healthcare provider for personalized treatment recommendations.\n\n"

            full_report += f"""
---

### CARE LEVEL RECOMMENDATION

**Recommended Care Level:** {result.get('care_level', 'Primary Care')}

Based on the comprehensive assessment above, the following care pathway is recommended:

"""
            care_level = result.get('care_level', 'Primary Care')
            if care_level == "Emergency Care":
                full_report += """**URGENT:** Please seek immediate emergency medical care. Call 911 or go to the nearest emergency room.

This recommendation is based on the severity and nature of your reported symptoms which may require immediate medical intervention."""
            elif care_level == "Urgent Care":
                full_report += """**IMPORTANT:** Please visit an urgent care center or contact your healthcare provider within 24 hours.

While not an emergency, your symptoms warrant prompt medical evaluation to prevent potential complications."""
            elif care_level == "Primary Care":
                full_report += """**RECOMMENDED:** Schedule an appointment with your primary care physician within 1-3 days.

Your symptoms should be evaluated by a healthcare professional to ensure proper diagnosis and treatment."""
            else:
                full_report += """**GUIDANCE:** Your symptoms may be managed with self-care and home monitoring.

However, if symptoms persist beyond 7 days or worsen significantly, please consult a healthcare provider."""

            full_report += f"""

---

### WARNING SIGNS - SEEK IMMEDIATE CARE IF:

- Difficulty breathing or shortness of breath
- Chest pain, pressure, or tightness
- Sudden severe headache (worst headache of your life)
- Confusion, difficulty speaking, or sudden weakness
- High fever (over 103F/39.4C) unresponsive to medication
- Severe abdominal pain
- Signs of dehydration (no urination, extreme thirst, dizziness)
- Loss of consciousness or fainting
- Uncontrolled bleeding
- Severe allergic reaction (swelling of face/throat, difficulty breathing)

---

### IMPORTANT DISCLAIMER

This assessment is generated for **informational purposes only** and does **NOT** constitute medical advice, diagnosis, or treatment. This tool cannot replace professional medical evaluation.

**Always consult with a qualified healthcare provider** for:
- Accurate diagnosis
- Appropriate treatment plans
- Prescription medications
- Any health concerns

**In case of emergency, call 911 or your local emergency number immediately.**

---
*Report Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*
*AI Health Navigator - Powered by LangGraph*
*Assessment ID: {result.get('assessment_id', 'N/A')}*
"""

            return {
                "risk_level": result.get('clinical_risk_level', result.get('initial_risk_level', 'Medium')),
                "care_level": care_level,
                "full_assessment": full_report,
                "symptoms": all_symptoms,
                "assessment_id": result.get('assessment_id', ''),
                "patient_id": result.get('patient_id', '')
            }
        except Exception as e:
            st.warning(f"LangGraph workflow error: {e}. Falling back to direct assessment.")

    # Fallback to direct Claude API if LangGraph is not available
    if LLM_AVAILABLE:
        try:
            llm = get_llm_client("sonnet")
            prompt = f"""You are an expert medical triage AI assistant. Provide a comprehensive health assessment based on the following patient information.

## PATIENT INFORMATION
- **Name:** {data.get('name', 'Patient')}
- **Age:** {data.get('age', 'Not specified')}
- **Primary Symptoms:** {symptoms_str}
- **Duration:** {data['duration']}
- **Severity:** {data['severity']}
- **Medical History:** {history_str}

## REQUIRED ASSESSMENT FORMAT

Please provide a detailed assessment with the following sections:

### 1. RISK ASSESSMENT
- **RISK_LEVEL:** [Low / Medium / High]
- **CARE_LEVEL:** [Self-Care / Primary Care / Urgent Care / Emergency]
- Explain your reasoning for this risk classification.

### 2. CLINICAL ANALYSIS
Provide a detailed analysis of the symptoms, considering:
- Symptom patterns and their significance
- Duration and progression implications
- How severity affects the assessment
- Relevant factors from medical history

### 3. POSSIBLE CONDITIONS
List 3-4 possible conditions that could explain these symptoms:
- For each condition, explain why it's being considered
- Note which symptoms support each possibility
- Indicate likelihood (most likely, possible, less likely but consider)

### 4. DETAILED RECOMMENDATIONS
Provide 5-6 specific, actionable recommendations:
- Immediate actions to take
- Symptom management strategies
- Lifestyle modifications
- When and how to seek medical care
- Any tests or examinations that might be helpful

### 5. WARNING SIGNS
List specific symptoms or changes that would require immediate medical attention:
- Be specific about what to watch for
- Explain why each warning sign is concerning

### 6. FOLLOW-UP PLAN
- Recommended timeline for follow-up
- What to monitor in the meantime
- When to return for reassessment

### 7. SELF-CARE GUIDANCE
Provide practical self-care advice:
- Home remedies that may help
- Over-the-counter options (if appropriate)
- Rest and activity recommendations
- Dietary considerations

Remember: This is for informational purposes. Always recommend consulting a healthcare provider for proper diagnosis."""

            response = llm.invoke(prompt, temperature=0.3, max_tokens=2000)

            # Parse risk level
            risk_level = "Medium"
            if "RISK_LEVEL:" in response:
                risk_section = response.split("RISK_LEVEL:")[1][:50].upper()
                if "HIGH" in risk_section:
                    risk_level = "High"
                elif "LOW" in risk_section:
                    risk_level = "Low"

            # Parse care level
            care_level = "Primary Care"
            if "CARE_LEVEL:" in response:
                care_section = response.split("CARE_LEVEL:")[1][:50].upper()
                if "EMERGENCY" in care_section:
                    care_level = "Emergency Care"
                elif "URGENT" in care_section:
                    care_level = "Urgent Care"
                elif "SELF" in care_section:
                    care_level = "Self-Care"

            return {
                "risk_level": risk_level,
                "care_level": care_level,
                "full_assessment": response,
                "symptoms": all_symptoms
            }
        except Exception as e:
            st.error(f"AI Error: {e}")

    # Fallback assessment (when AI is not available)
    severity = data["severity"].lower()
    risk_level = "High" if severity == "severe" else "Medium" if severity == "moderate" else "Low"
    care_level = "Emergency Care" if risk_level == "High" else "Primary Care" if risk_level == "Medium" else "Self-Care"

    # Build detailed fallback response
    fallback_report = f"""## HEALTH ASSESSMENT REPORT

---

### 1. RISK ASSESSMENT

**RISK_LEVEL:** {risk_level}
**CARE_LEVEL:** {care_level}

**Assessment Basis:**
Based on your reported symptoms ({symptoms_str}) with {data['severity'].lower()} severity lasting {data['duration']}, this assessment has been generated to help guide your next steps.

---

### 2. CLINICAL ANALYSIS

**Symptoms Reported:** {symptoms_str}
**Duration:** {data['duration']}
**Severity Level:** {data['severity']}
**Medical History:** {history_str}

Your symptoms have been categorized as **{data['severity'].lower()}** in severity. {'Given the severe nature of your symptoms, immediate medical evaluation is strongly recommended.' if risk_level == 'High' else 'While not immediately life-threatening, these symptoms warrant professional medical evaluation.' if risk_level == 'Medium' else 'These symptoms can typically be managed with home care and monitoring.'}

---

### 3. POSSIBLE CONDITIONS

Based on general symptom patterns, consider discussing these possibilities with a healthcare provider:

1. **Common conditions** - Many symptoms can be attributed to viral infections, stress, or lifestyle factors
2. **Underlying conditions** - Symptoms persisting beyond expected duration may indicate conditions requiring treatment
3. **Environmental factors** - Allergies, dietary issues, or environmental exposures can cause similar symptoms

*Note: Only a qualified healthcare provider can provide an accurate diagnosis after proper examination.*

---

### 4. DETAILED RECOMMENDATIONS

{'**URGENT:** Given your severe symptoms, please:' if risk_level == 'High' else '**IMPORTANT:** Based on your moderate symptoms:' if risk_level == 'Medium' else '**GUIDANCE:** For your mild symptoms:'}

1. **{'Seek immediate medical care' if risk_level == 'High' else 'Schedule an appointment with your doctor within 24-48 hours' if risk_level == 'Medium' else 'Monitor your symptoms at home'}**
   - {'Call 911 or go to the emergency room if symptoms are severe' if risk_level == 'High' else 'Contact your primary care physician or visit an urgent care center' if risk_level == 'Medium' else 'Keep track of any changes in your condition'}

2. **Rest and Recovery**
   - Get adequate sleep (7-9 hours per night)
   - Avoid strenuous physical activity until symptoms improve
   - Take time off work/school if needed

3. **Stay Hydrated**
   - Drink 8-10 glasses of water daily
   - Consider electrolyte drinks if experiencing fluid loss
   - Avoid excessive caffeine and alcohol

4. **Symptom Management**
   - Over-the-counter pain relievers (acetaminophen, ibuprofen) as directed
   - Use appropriate OTC medications for specific symptoms
   - Apply heat or cold therapy as appropriate

5. **Document Your Symptoms**
   - Keep a symptom diary noting timing, severity, and triggers
   - Record any new symptoms that develop
   - Note what helps or worsens your symptoms

6. **Environmental Considerations**
   - Ensure adequate ventilation in living spaces
   - Maintain comfortable room temperature
   - Reduce exposure to known irritants

---

### 5. WARNING SIGNS - SEEK IMMEDIATE CARE IF:

**Go to the Emergency Room or Call 911 immediately if you experience:**

- Difficulty breathing or shortness of breath
- Chest pain, pressure, or tightness
- Sudden severe headache (worst headache of your life)
- Confusion, difficulty speaking, or sudden weakness
- High fever (over 103F/39.4C) unresponsive to medication
- Severe abdominal pain
- Signs of dehydration (no urination, extreme thirst, dizziness)
- Loss of consciousness or fainting
- Uncontrolled bleeding
- Severe allergic reaction (swelling of face/throat, difficulty breathing)

---

### 6. FOLLOW-UP PLAN

**Recommended Timeline:** {'Immediately - Do not delay seeking care' if risk_level == 'High' else 'Within 24-48 hours' if risk_level == 'Medium' else 'If symptoms persist beyond 7 days or worsen'}

**Monitoring Guidelines:**
- Check your symptoms every few hours
- Take your temperature twice daily if fever is present
- Note any new symptoms or changes
- Keep this assessment for reference when speaking with healthcare providers

**When to Reassess:**
- If symptoms significantly worsen
- If new concerning symptoms develop
- If symptoms don't improve within the expected timeframe
- If you have any doubts about your condition

---

### 7. SELF-CARE GUIDANCE

**Home Remedies That May Help:**
- Warm salt water gargle for throat discomfort
- Honey and warm water for cough (adults only)
- Steam inhalation for congestion
- Warm compress for muscle aches
- Cool compress for fever or headache

**Nutrition Recommendations:**
- Eat light, easily digestible foods
- Include fruits and vegetables for vitamins
- Chicken soup or warm broths can be soothing
- Avoid heavy, greasy, or spicy foods if experiencing digestive issues

**Rest Guidelines:**
- Prioritize sleep and rest
- Limit screen time before bed
- Create a comfortable recovery environment
- Listen to your body's signals

---

### IMPORTANT DISCLAIMER

This assessment is generated for **informational purposes only** and does **NOT** constitute medical advice, diagnosis, or treatment. This tool cannot replace professional medical evaluation.

**Always consult with a qualified healthcare provider** for:
- Accurate diagnosis
- Appropriate treatment plans
- Prescription medications
- Any health concerns

**In case of emergency, call 911 or your local emergency number immediately.**

---
*Report Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*
*AI Health Navigator v2.0*
"""

    return {
        "risk_level": risk_level,
        "care_level": care_level,
        "full_assessment": fallback_report,
        "symptoms": all_symptoms
    }

def generate_pdf(assessment):
    """Generate professional PDF report"""
    import re
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.units import inch
    from reportlab.platypus import Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib import colors

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.75*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )
    styles = getSampleStyleSheet()

    # Define colors
    PRIMARY_COLOR = HexColor('#1e40af')  # Deep blue
    SECONDARY_COLOR = HexColor('#3b82f6')  # Lighter blue
    SUCCESS_COLOR = HexColor('#16a34a')  # Green
    WARNING_COLOR = HexColor('#d97706')  # Amber
    DANGER_COLOR = HexColor('#dc2626')  # Red
    GRAY_COLOR = HexColor('#6b7280')
    LIGHT_GRAY = HexColor('#f3f4f6')
    DARK_TEXT = HexColor('#1f2937')

    # Custom styles
    styles.add(styles['Heading1'].__class__(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=5,
        alignment=TA_CENTER,
        textColor=PRIMARY_COLOR,
        fontName='Helvetica-Bold'
    ))

    styles.add(styles['Normal'].__class__(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=GRAY_COLOR
    ))

    styles.add(styles['Heading2'].__class__(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=PRIMARY_COLOR,
        fontName='Helvetica-Bold',
        borderPadding=(5, 5, 5, 5)
    ))

    styles.add(styles['Normal'].__class__(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=DARK_TEXT,
        alignment=TA_JUSTIFY
    ))

    styles.add(styles['Normal'].__class__(
        'BulletText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        textColor=DARK_TEXT
    ))

    styles.add(styles['Normal'].__class__(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GRAY_COLOR
    ))

    styles.add(styles['Normal'].__class__(
        'DisclaimerText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=GRAY_COLOR,
        alignment=TA_JUSTIFY
    ))

    elements = []

    # ===== HEADER SECTION =====
    # Title with icon
    elements.append(Paragraph("🏥 AI Health Navigator", styles['MainTitle']))
    elements.append(Paragraph("Comprehensive Health Assessment Report", styles['Subtitle']))

    # Decorative line
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceAfter=20))

    # ===== PATIENT INFO TABLE =====
    patient_name = st.session_state.data.get('name', 'Not provided') or 'Not provided'
    patient_age = st.session_state.data.get('age', 'N/A')
    report_date = datetime.now().strftime('%B %d, %Y at %H:%M')

    # Get risk level color
    risk = assessment['risk_level']
    if risk == 'High':
        risk_color = DANGER_COLOR
        risk_bg = HexColor('#fee2e2')
    elif risk == 'Medium':
        risk_color = WARNING_COLOR
        risk_bg = HexColor('#fef3c7')
    else:
        risk_color = SUCCESS_COLOR
        risk_bg = HexColor('#dcfce7')

    # Patient info and summary table
    info_data = [
        ['PATIENT INFORMATION', '', 'ASSESSMENT SUMMARY', ''],
        ['Patient Name:', patient_name, 'Risk Level:', risk],
        ['Age:', str(patient_age), 'Care Level:', assessment['care_level']],
        ['Report Date:', report_date, 'Symptoms:', ', '.join(assessment.get('symptoms', [])[:3]) + ('...' if len(assessment.get('symptoms', [])) > 3 else '')]
    ]

    info_table = Table(info_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
    info_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (1, 0), PRIMARY_COLOR),
        ('BACKGROUND', (2, 0), (3, 0), SECONDARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (2, 0), (3, 0)),
        # Data rows
        ('BACKGROUND', (0, 1), (1, -1), LIGHT_GRAY),
        ('BACKGROUND', (2, 1), (3, -1), HexColor('#eff6ff')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), DARK_TEXT),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, white),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY_COLOR),
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        # Alignment
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # ===== RISK LEVEL BANNER =====
    risk_text = f"RISK LEVEL: {risk.upper()}"
    care_text = f"Recommended: {assessment['care_level']}"

    risk_data = [[risk_text, care_text]]
    risk_table = Table(risk_data, colWidths=[3.25*inch, 3.25*inch])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), risk_bg),
        ('BACKGROUND', (1, 0), (1, 0), HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (0, 0), risk_color),
        ('TEXTCOLOR', (1, 0), (1, 0), PRIMARY_COLOR),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 1, GRAY_COLOR),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 25))

    # ===== ASSESSMENT CONTENT =====
    def process_markdown_line(line):
        """Convert markdown to reportlab markup"""
        if line.strip() == '---':
            return ('hr', None)

        if line.startswith('### '):
            return ('h3', line[4:].strip())
        elif line.startswith('## '):
            return ('h2', line[3:].strip())
        elif line.startswith('# '):
            return ('h1', line[2:].strip())

        # Convert bold and italic
        line = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', line)
        line = line.replace('*', '')

        # Check for bullet points
        stripped = line.strip()
        if stripped.startswith('- '):
            return ('bullet', '• ' + stripped[2:])
        elif stripped and stripped[0].isdigit() and '. ' in stripped[:4]:
            return ('bullet', stripped)

        return ('text', line)

    current_section = []

    for line in assessment['full_assessment'].split('\n'):
        if not line.strip():
            continue

        result = process_markdown_line(line)
        line_type, content = result

        if line_type == 'hr':
            elements.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceBefore=10, spaceAfter=10))
        elif line_type in ('h1', 'h2', 'h3'):
            # Section header with background
            header_data = [[content.upper()]]
            header_table = Table(header_data, colWidths=[6.5*inch])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, -1), white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(Spacer(1, 15))
            elements.append(header_table)
            elements.append(Spacer(1, 10))
        elif line_type == 'bullet':
            try:
                elements.append(Paragraph(content, styles['BulletText']))
            except:
                clean = re.sub(r'<[^>]+>', '', content)
                elements.append(Paragraph(clean, styles['BulletText']))
        else:
            if content.strip():
                try:
                    elements.append(Paragraph(content, styles['CustomBody']))
                except:
                    clean = re.sub(r'<[^>]+>', '', content)
                    elements.append(Paragraph(clean, styles['CustomBody']))

    # ===== DISCLAIMER SECTION =====
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=1, color=DANGER_COLOR, spaceAfter=15))

    disclaimer_data = [['⚠️ IMPORTANT DISCLAIMER']]
    disclaimer_header = Table(disclaimer_data, colWidths=[6.5*inch])
    disclaimer_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#fef2f2')),
        ('TEXTCOLOR', (0, 0), (-1, -1), DANGER_COLOR),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(disclaimer_header)
    elements.append(Spacer(1, 10))

    disclaimer_text = """This health assessment report is generated by an AI system for <b>informational purposes only</b>.
    It does NOT constitute medical advice, diagnosis, or treatment. The information provided should not be used as a
    substitute for professional medical advice. Always seek the advice of your physician or other qualified health
    provider with any questions you may have regarding a medical condition. <b>In case of emergency, call 911 or
    your local emergency number immediately.</b>"""

    elements.append(Paragraph(disclaimer_text, styles['DisclaimerText']))

    # ===== FOOTER =====
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_COLOR, spaceAfter=10))

    footer_text = f"Generated by AI Health Navigator • {datetime.now().strftime('%B %d, %Y at %H:%M')} • Powered by Claude AI"
    elements.append(Paragraph(footer_text, styles['SmallText']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== MAIN UI ====================

# Simple Header
st.title("🏥 AI Health Navigator")
st.caption("Intelligent symptom assessment powered by AI")
st.divider()

# Progress
phase_index = PHASES.index(st.session_state.phase)
progress = phase_index / (len(PHASES) - 1)
col1, col2 = st.columns([4, 1])
with col1:
    st.progress(progress)
with col2:
    st.write(f"Step {phase_index + 1}/{len(PHASES)}")

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.info(msg["content"])
    else:
        st.success(msg["content"])

# ==================== PHASE HANDLERS ====================

phase = st.session_state.phase

if phase == "greeting":
    st.markdown("### Welcome!")
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
    st.markdown("### What symptoms are you experiencing?")
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
    st.markdown("### How long have you had these symptoms?")

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
    st.markdown("### Any other symptoms?")
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
    st.markdown("### How severe are your symptoms?")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Mild", help="Noticeable but not affecting daily life"):
            st.session_state.data["severity"] = "Mild"
            add_message("user", "Mild")
            add_message("assistant", "Do you have any relevant medical history?")
            st.session_state.phase = "history"
            st.rerun()
    with col2:
        if st.button("Moderate", help="Affecting some daily activities"):
            st.session_state.data["severity"] = "Moderate"
            add_message("user", "Moderate")
            add_message("assistant", "Do you have any relevant medical history?")
            st.session_state.phase = "history"
            st.rerun()
    with col3:
        if st.button("Severe", help="Significantly impacting daily life"):
            st.session_state.data["severity"] = "Severe"
            add_message("user", "Severe")
            add_message("assistant", "Do you have any relevant medical history?")
            st.session_state.phase = "history"
            st.rerun()

elif phase == "history":
    st.markdown("### Any relevant medical history?")
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
    st.markdown("### Please confirm your information")

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
        if st.button("Run Assessment", type="primary"):
            add_message("assistant", "Analyzing your symptoms... Please wait.")
            st.session_state.phase = "assessment"
            st.rerun()
    with col2:
        if st.button("Start Over"):
            reset()
            st.rerun()

elif phase == "assessment":
    with st.spinner("Analyzing your symptoms with AI..."):
        result = run_assessment()
        st.session_state.assessment_result = result
        st.session_state.phase = "complete"
        st.rerun()

elif phase == "complete":
    result = st.session_state.assessment_result

    # Risk level display
    risk = result["risk_level"]
    if risk == "High":
        st.error(f"**Risk Level: {risk}**")
    elif risk == "Medium":
        st.warning(f"**Risk Level: {risk}**")
    else:
        st.success(f"**Risk Level: {risk}**")

    st.info(f"**Recommended Care:** {result['care_level']}")

    # Full assessment
    with st.expander("View Full Assessment", expanded=True):
        st.markdown(result["full_assessment"])

    # Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Assessment", type="primary"):
            reset()
            st.rerun()
    with col2:
        pdf = generate_pdf(result)
        st.download_button(
            "Download PDF",
            data=pdf.getvalue(),
            file_name=f"health_assessment_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

    # Disclaimer
    st.divider()
    st.warning("**Disclaimer:** This assessment is for informational purposes only and does not constitute medical advice. Always consult with a qualified healthcare provider. In emergencies, call 911.")

# Footer
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns([2, 1, 2])
with col_footer2:
    if st.button("🔄 Start Over", key="reset_btn"):
        reset()
        st.rerun()
st.caption("Powered by Claude AI • For informational purposes only")
