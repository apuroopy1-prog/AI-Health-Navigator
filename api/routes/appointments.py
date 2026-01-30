"""
Appointment API Routes
"""
from typing import List, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo

router = APIRouter()


# ==================== Enums ====================

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ProviderType(str, Enum):
    PRIMARY_CARE = "primary_care"
    SPECIALIST = "specialist"
    FOLLOW_UP = "follow_up"
    URGENT_CARE = "urgent_care"
    TELEHEALTH = "telehealth"


# ==================== Pydantic Models ====================

class AppointmentCreate(BaseModel):
    """Request model for creating an appointment"""
    patient_id: str = Field(..., description="Patient identifier")
    assessment_id: Optional[str] = Field(None, description="Related assessment ID")
    provider_name: Optional[str] = Field(None, description="Healthcare provider name")
    provider_type: str = Field(default="follow_up", description="Type of provider/visit")
    specialty: Optional[str] = Field(None, description="Medical specialty (e.g., cardiology)")
    scheduled_datetime: datetime = Field(..., description="Appointment date and time")
    duration_minutes: int = Field(default=30, ge=15, le=180, description="Appointment duration")
    location: Optional[str] = Field(None, description="Appointment location")
    telehealth: bool = Field(default=False, description="Is this a telehealth appointment")
    telehealth_link: Optional[str] = Field(None, description="Video call link for telehealth")
    notes: Optional[str] = Field(None, description="Additional notes")


class AppointmentUpdate(BaseModel):
    """Request model for updating an appointment"""
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    specialty: Optional[str] = None
    scheduled_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=180)
    location: Optional[str] = None
    telehealth: Optional[bool] = None
    telehealth_link: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    """Response model for appointment data"""
    appointment_id: str
    patient_id: str
    assessment_id: Optional[str] = None
    provider_name: Optional[str] = None
    provider_type: str
    specialty: Optional[str] = None
    scheduled_datetime: datetime
    duration_minutes: int
    location: Optional[str] = None
    telehealth: bool = False
    telehealth_link: Optional[str] = None
    status: str
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AppointmentListResponse(BaseModel):
    """Response model for list of appointments"""
    count: int
    appointments: List[AppointmentResponse]


# ==================== Endpoints ====================

@router.post("/", response_model=dict)
async def create_appointment(appointment: AppointmentCreate):
    """
    Create a new appointment.

    Returns the created appointment ID.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(appointment.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        appointment_id = patient_repo.create_appointment(appointment.model_dump())
        return {
            "appointment_id": appointment_id,
            "message": "Appointment created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=AppointmentListResponse)
async def list_appointments(
    limit: int = Query(50, ge=1, le=100),
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    patient_id: Optional[str] = Query(None, description="Filter by patient")
):
    """
    List appointments with optional filtering.
    """
    if patient_id:
        appointments = patient_repo.get_patient_appointments(
            patient_id,
            status=status.value if status else None,
            limit=limit
        )
    else:
        appointments = patient_repo.get_all_appointments(
            status=status.value if status else None,
            limit=limit
        )

    return {
        "count": len(appointments),
        "appointments": appointments
    }


@router.get("/upcoming", response_model=AppointmentListResponse)
async def get_upcoming_appointments(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    patient_id: Optional[str] = Query(None, description="Filter by patient")
):
    """
    Get upcoming appointments within the specified number of days.
    """
    appointments = patient_repo.get_upcoming_appointments(
        days=days,
        patient_id=patient_id
    )

    return {
        "count": len(appointments),
        "appointments": appointments
    }


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: str):
    """
    Get an appointment by ID.
    """
    appointment = patient_repo.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.put("/{appointment_id}")
async def update_appointment(appointment_id: str, updates: AppointmentUpdate):
    """
    Update an appointment record.
    """
    # Verify appointment exists
    existing = patient_repo.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Filter out None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    # Convert enum to value if present
    if "status" in update_data and isinstance(update_data["status"], AppointmentStatus):
        update_data["status"] = update_data["status"].value

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = patient_repo.update_appointment(appointment_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update appointment")

    return {"message": "Appointment updated successfully"}


@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = Query(None, description="Cancellation reason")
):
    """
    Cancel an appointment (soft delete by updating status).
    """
    existing = patient_repo.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Soft delete - update status to cancelled
    update_data = {
        "status": "cancelled",
        "cancellation_reason": reason
    }
    patient_repo.update_appointment(appointment_id, update_data)

    return {"message": "Appointment cancelled successfully"}


@router.post("/{appointment_id}/confirm")
async def confirm_appointment(appointment_id: str):
    """
    Confirm a scheduled appointment.
    """
    existing = patient_repo.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if existing.get("status") != "scheduled":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm appointment with status: {existing.get('status')}"
        )

    patient_repo.update_appointment(appointment_id, {"status": "confirmed"})
    return {"message": "Appointment confirmed successfully"}


@router.post("/{appointment_id}/complete")
async def complete_appointment(
    appointment_id: str,
    notes: Optional[str] = Query(None, description="Completion notes")
):
    """
    Mark an appointment as completed.
    """
    existing = patient_repo.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if existing.get("status") not in ["scheduled", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete appointment with status: {existing.get('status')}"
        )

    update_data = {
        "status": "completed",
        "completed_at": datetime.utcnow()
    }
    if notes:
        update_data["completion_notes"] = notes

    patient_repo.update_appointment(appointment_id, update_data)
    return {"message": "Appointment marked as completed"}


@router.post("/{appointment_id}/no-show")
async def mark_no_show(appointment_id: str):
    """
    Mark an appointment as no-show.
    """
    existing = patient_repo.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if existing.get("status") not in ["scheduled", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark no-show for appointment with status: {existing.get('status')}"
        )

    patient_repo.update_appointment(appointment_id, {"status": "no_show"})
    return {"message": "Appointment marked as no-show"}


# ==================== Patient-specific Endpoints ====================

@router.get("/patient/{patient_id}", response_model=AppointmentListResponse)
async def get_patient_appointments(
    patient_id: str,
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get all appointments for a specific patient.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appointments = patient_repo.get_patient_appointments(
        patient_id,
        status=status.value if status else None,
        limit=limit
    )

    return {
        "count": len(appointments),
        "appointments": appointments
    }
