"""
Patient API Routes
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo

router = APIRouter()


# ==================== Pydantic Models ====================

class PatientCreate(BaseModel):
    """Request model for creating a patient"""
    name: str = Field(..., min_length=1, description="Patient full name")
    age: Optional[int] = Field(None, ge=0, le=150, description="Patient age")
    gender: Optional[str] = Field(None, description="Patient gender")
    contact_info: Optional[str] = Field(None, description="Phone or email")
    emergency_contact: Optional[str] = Field(None, description="Emergency contact")
    medical_history: List[str] = Field(default_factory=list, description="Past medical conditions")
    current_medications: List[str] = Field(default_factory=list, description="Current medications")
    allergies: List[str] = Field(default_factory=list, description="Known allergies")


class PatientUpdate(BaseModel):
    """Request model for updating a patient"""
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    contact_info: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[List[str]] = None
    current_medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None


class PatientResponse(BaseModel):
    """Response model for patient data"""
    patient_id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    contact_info: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: List[str] = []
    current_medications: List[str] = []
    allergies: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== Endpoints ====================

@router.post("/", response_model=dict)
async def create_patient(patient: PatientCreate):
    """
    Create a new patient record.

    Returns the created patient ID.
    """
    try:
        patient_id = patient_repo.create_patient(patient.model_dump())
        return {
            "patient_id": patient_id,
            "message": "Patient created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str):
    """
    Get a patient by ID.
    """
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}")
async def update_patient(patient_id: str, updates: PatientUpdate):
    """
    Update a patient record.
    """
    # Filter out None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = patient_repo.update_patient(patient_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {"message": "Patient updated successfully"}


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    limit: int = Query(50, ge=1, le=100),
    name: Optional[str] = Query(None, description="Filter by name (partial match)")
):
    """
    List patients with optional filtering.
    """
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    patients = patient_repo.search_patients(query, limit=limit)
    return patients


@router.get("/{patient_id}/assessments")
async def get_patient_assessments(
    patient_id: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get all assessments for a patient.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    assessments = patient_repo.get_patient_assessments(patient_id, limit=limit)
    return {
        "patient_id": patient_id,
        "count": len(assessments),
        "assessments": assessments
    }
