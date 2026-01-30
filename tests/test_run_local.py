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
        assert result.get("current_phase") == "completed", f"Unexpected phase: {result.get('current_phase')}"
        pdf_path = result.get("pdf_path")
        assert pdf_path is not None
        assert os.path.exists(pdf_path), "PDF report was not created"
        os.remove(pdf_path)
    finally:
        os.chdir(cwd)
