import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from streamlit_langgraph import run_patient_assessment

SAMPLE_PATIENT = {
    "patient_id": "TEST001",
    "name": "Test Patient",
    "age": 30,
    "contact_info": "test@example.com",
    "emergency_contact": "EC: 555-0000",
    "primary_complaints": ["cough", "fever"],
}



def test_local_run_creates_pdf(tmp_path):
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = run_patient_assessment(SAMPLE_PATIENT)
        # Check workflow completed successfully
        assert result.get("workflow_completed") is True, f"Workflow not completed: {result}"
        # Verify expected fields are present
        assert result.get("care_level") is not None, "care_level should be set"
        assert result.get("assessment_id") is not None, "assessment_id should be set"
    finally:
        os.chdir(cwd)
