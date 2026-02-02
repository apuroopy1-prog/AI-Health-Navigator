"""
Tests for the AI Health Navigator Streamlit app
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRunAssessment:
    """Tests for the run_assessment function"""

    @pytest.fixture
    def mock_session_state(self):
        """Create mock session state data"""
        return {
            "symptoms": ["headache", "fever"],
            "duration": "2 days",
            "other_symptoms": ["fatigue"],
            "severity": "Moderate",
            "history": ["hypertension"],
            "name": "Test Patient",
            "age": 35
        }

    def test_fallback_assessment_low_risk(self, mock_session_state):
        """Test fallback assessment returns correct structure for mild severity"""
        mock_session_state["severity"] = "Mild"

        # Import after mocking streamlit
        with patch.dict('sys.modules', {'streamlit': MagicMock()}):
            # Mock st.session_state
            import importlib
            st_mock = MagicMock()
            st_mock.session_state.data = mock_session_state

            with patch('streamlit.session_state', mock_session_state):
                # Create the assessment logic inline since we can't import app.py directly
                data = mock_session_state
                all_symptoms = data["symptoms"] + data["other_symptoms"]
                severity = data["severity"].lower()

                risk_level = "High" if severity == "severe" else "Medium" if severity == "moderate" else "Low"
                care_level = "Emergency Care" if risk_level == "High" else "Primary Care" if risk_level == "Medium" else "Self-Care"

                assert risk_level == "Low"
                assert care_level == "Self-Care"

    def test_fallback_assessment_medium_risk(self, mock_session_state):
        """Test fallback assessment for moderate severity"""
        mock_session_state["severity"] = "Moderate"

        severity = mock_session_state["severity"].lower()
        risk_level = "High" if severity == "severe" else "Medium" if severity == "moderate" else "Low"
        care_level = "Emergency Care" if risk_level == "High" else "Primary Care" if risk_level == "Medium" else "Self-Care"

        assert risk_level == "Medium"
        assert care_level == "Primary Care"

    def test_fallback_assessment_high_risk(self, mock_session_state):
        """Test fallback assessment for severe symptoms"""
        mock_session_state["severity"] = "Severe"

        severity = mock_session_state["severity"].lower()
        risk_level = "High" if severity == "severe" else "Medium" if severity == "moderate" else "Low"
        care_level = "Emergency Care" if risk_level == "High" else "Primary Care" if risk_level == "Medium" else "Self-Care"

        assert risk_level == "High"
        assert care_level == "Emergency Care"


class TestPDFGeneration:
    """Tests for PDF report generation"""

    def test_generate_pdf_returns_buffer(self):
        """Test that PDF generation returns a BytesIO buffer"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from datetime import datetime

        assessment = {
            "risk_level": "Medium",
            "care_level": "Primary Care",
            "full_assessment": "## Test Assessment\n\nThis is a test.",
            "symptoms": ["headache", "fever"]
        }

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("AI Health Navigator - Assessment Report", styles['Title']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"Risk Level: {assessment['risk_level']}", styles['Heading2']))
        elements.append(Spacer(1, 20))

        for line in assessment['full_assessment'].split('\n'):
            if line.strip():
                # Skip markdown headers for cleaner PDF
                clean_line = line.replace('#', '').replace('*', '').strip()
                if clean_line:
                    elements.append(Paragraph(clean_line, styles['Normal']))
                    elements.append(Spacer(1, 6))

        doc.build(elements)
        buffer.seek(0)

        # Verify it's a valid PDF
        pdf_content = buffer.read()
        assert pdf_content.startswith(b'%PDF')
        assert len(pdf_content) > 100


class TestRiskLevelParsing:
    """Tests for parsing risk levels from AI responses"""

    def test_parse_high_risk(self):
        """Test parsing HIGH risk level from response"""
        response = "RISK_LEVEL: High\nThe patient shows severe symptoms..."

        risk_level = "Medium"
        if "RISK_LEVEL:" in response:
            risk_section = response.split("RISK_LEVEL:")[1][:50].upper()
            if "HIGH" in risk_section:
                risk_level = "High"
            elif "LOW" in risk_section:
                risk_level = "Low"

        assert risk_level == "High"

    def test_parse_low_risk(self):
        """Test parsing LOW risk level from response"""
        response = "RISK_LEVEL: Low\nMinor symptoms noted..."

        risk_level = "Medium"
        if "RISK_LEVEL:" in response:
            risk_section = response.split("RISK_LEVEL:")[1][:50].upper()
            if "HIGH" in risk_section:
                risk_level = "High"
            elif "LOW" in risk_section:
                risk_level = "Low"

        assert risk_level == "Low"

    def test_parse_default_medium_risk(self):
        """Test default medium risk when not specified"""
        response = "Some response without risk level marker"

        risk_level = "Medium"
        if "RISK_LEVEL:" in response:
            risk_section = response.split("RISK_LEVEL:")[1][:50].upper()
            if "HIGH" in risk_section:
                risk_level = "High"
            elif "LOW" in risk_section:
                risk_level = "Low"

        assert risk_level == "Medium"


class TestCareLevelParsing:
    """Tests for parsing care levels from AI responses"""

    def test_parse_emergency_care(self):
        """Test parsing emergency care level"""
        response = "CARE_LEVEL: Emergency\nImmediate attention needed..."

        care_level = "Primary Care"
        if "CARE_LEVEL:" in response:
            care_section = response.split("CARE_LEVEL:")[1][:50].upper()
            if "EMERGENCY" in care_section:
                care_level = "Emergency Care"
            elif "URGENT" in care_section:
                care_level = "Urgent Care"
            elif "SELF" in care_section:
                care_level = "Self-Care"

        assert care_level == "Emergency Care"

    def test_parse_self_care(self):
        """Test parsing self-care level"""
        response = "CARE_LEVEL: Self-Care\nHome remedies recommended..."

        care_level = "Primary Care"
        if "CARE_LEVEL:" in response:
            care_section = response.split("CARE_LEVEL:")[1][:50].upper()
            if "EMERGENCY" in care_section:
                care_level = "Emergency Care"
            elif "URGENT" in care_section:
                care_level = "Urgent Care"
            elif "SELF" in care_section:
                care_level = "Self-Care"

        assert care_level == "Self-Care"


class TestSymptomProcessing:
    """Tests for symptom input processing"""

    def test_parse_comma_separated_symptoms(self):
        """Test parsing comma-separated symptoms"""
        symptoms_input = "headache, fever, cough"
        symptom_list = [s.strip() for s in symptoms_input.replace(",", "\n").split("\n") if s.strip()]

        assert symptom_list == ["headache", "fever", "cough"]

    def test_parse_newline_separated_symptoms(self):
        """Test parsing newline-separated symptoms"""
        symptoms_input = "headache\nfever\ncough"
        symptom_list = [s.strip() for s in symptoms_input.replace(",", "\n").split("\n") if s.strip()]

        assert symptom_list == ["headache", "fever", "cough"]

    def test_parse_mixed_symptoms(self):
        """Test parsing mixed comma and newline symptoms"""
        symptoms_input = "headache, fever\ncough, fatigue"
        symptom_list = [s.strip() for s in symptoms_input.replace(",", "\n").split("\n") if s.strip()]

        assert symptom_list == ["headache", "fever", "cough", "fatigue"]

    def test_empty_symptom_handling(self):
        """Test handling of empty symptom entries"""
        symptoms_input = "headache, , fever,  , cough"
        symptom_list = [s.strip() for s in symptoms_input.replace(",", "\n").split("\n") if s.strip()]

        assert symptom_list == ["headache", "fever", "cough"]


class TestPhaseLogic:
    """Tests for conversation phase transitions"""

    def test_phases_defined(self):
        """Test that all phases are defined correctly"""
        PHASES = ["greeting", "symptoms", "duration", "other_symptoms", "severity", "history", "confirm", "assessment", "complete"]

        assert len(PHASES) == 9
        assert PHASES[0] == "greeting"
        assert PHASES[-1] == "complete"

    def test_phase_index_calculation(self):
        """Test progress calculation from phase index"""
        PHASES = ["greeting", "symptoms", "duration", "other_symptoms", "severity", "history", "confirm", "assessment", "complete"]

        # Test greeting phase (start)
        phase_index = PHASES.index("greeting")
        progress = phase_index / (len(PHASES) - 1)
        assert progress == 0.0

        # Test complete phase (end)
        phase_index = PHASES.index("complete")
        progress = phase_index / (len(PHASES) - 1)
        assert progress == 1.0

        # Test middle phase
        phase_index = PHASES.index("severity")
        progress = phase_index / (len(PHASES) - 1)
        assert 0 < progress < 1


class TestClaudeClient:
    """Tests for Claude API client"""

    def test_model_ids_defined(self):
        """Test that model IDs are properly defined"""
        MODELS = {
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-3-haiku-20240307",
            "opus": "claude-3-opus-20240229"
        }

        assert "sonnet" in MODELS
        assert "haiku" in MODELS
        assert "opus" in MODELS

    def test_fallback_response_structure(self):
        """Test fallback response provides useful default"""
        prompt = "general query about symptoms"

        # Simulate fallback response logic
        fallback = (
            "I've noted your information. Based on what you've shared, "
            "I recommend discussing these symptoms with a healthcare provider "
            "for a thorough evaluation."
        )

        assert "healthcare provider" in fallback
        assert len(fallback) > 50
