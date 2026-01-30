"""
Medication API Routes
"""
from typing import List, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo

router = APIRouter()


# ==================== Enums ====================

class MedicationFrequency(str, Enum):
    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    FOUR_TIMES_DAILY = "four_times_daily"
    AS_NEEDED = "as_needed"
    WEEKLY = "weekly"
    EVERY_OTHER_DAY = "every_other_day"


class ReminderStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    MISSED = "missed"


# ==================== Pydantic Models ====================

class MedicationCreate(BaseModel):
    """Request model for creating a medication"""
    patient_id: str = Field(..., description="Patient identifier")
    name: str = Field(..., min_length=1, description="Medication name")
    dosage: str = Field(..., description="Dosage (e.g., '10mg', '500mg')")
    dosage_form: str = Field(default="tablet", description="Form (tablet, capsule, liquid, etc.)")
    frequency: MedicationFrequency = Field(default=MedicationFrequency.ONCE_DAILY)
    specific_times: List[str] = Field(
        default=["09:00"],
        description="Times to take medication (24h format, e.g., ['09:00', '21:00'])"
    )
    instructions: Optional[str] = Field(None, description="Special instructions (e.g., 'Take with food')")
    prescribing_provider: Optional[str] = Field(None, description="Name of prescribing provider")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date (if temporary)")
    refill_reminder: bool = Field(default=False, description="Enable refill reminders")
    pills_remaining: Optional[int] = Field(None, ge=0, description="Number of pills remaining")
    refill_threshold: Optional[int] = Field(None, ge=0, description="Remind when this many pills left")


class MedicationUpdate(BaseModel):
    """Request model for updating a medication"""
    name: Optional[str] = None
    dosage: Optional[str] = None
    dosage_form: Optional[str] = None
    frequency: Optional[MedicationFrequency] = None
    specific_times: Optional[List[str]] = None
    instructions: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    discontinued_reason: Optional[str] = None
    pills_remaining: Optional[int] = Field(None, ge=0)
    refill_reminder: Optional[bool] = None
    refill_threshold: Optional[int] = Field(None, ge=0)


class MedicationResponse(BaseModel):
    """Response model for medication data"""
    medication_id: str
    patient_id: str
    name: str
    dosage: str
    dosage_form: str
    frequency: str
    specific_times: List[str]
    instructions: Optional[str] = None
    prescribing_provider: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    discontinued_reason: Optional[str] = None
    refill_reminder: bool = False
    pills_remaining: Optional[int] = None
    refill_threshold: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MedicationListResponse(BaseModel):
    """Response model for list of medications"""
    count: int
    medications: List[MedicationResponse]


class ReminderResponse(BaseModel):
    """Response model for medication reminder"""
    reminder_id: str
    medication_id: str
    patient_id: str
    medication_name: Optional[str] = None
    dosage: Optional[str] = None
    scheduled_time: datetime
    status: str
    instructions: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ReminderListResponse(BaseModel):
    """Response model for list of reminders"""
    count: int
    reminders: List[ReminderResponse]


# ==================== Medication Endpoints ====================

@router.post("/", response_model=dict)
async def create_medication(medication: MedicationCreate):
    """
    Create a new medication for a patient.

    Returns the created medication ID.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(medication.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        medication_data = medication.model_dump()
        # Convert enum to value
        if isinstance(medication_data.get("frequency"), MedicationFrequency):
            medication_data["frequency"] = medication_data["frequency"].value

        medication_id = patient_repo.create_medication(medication_data)

        # Auto-generate reminders for the next 7 days
        reminder_ids = patient_repo.generate_reminders_for_medication(medication_id, days=7)

        return {
            "medication_id": medication_id,
            "reminders_created": len(reminder_ids),
            "message": "Medication created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=MedicationListResponse)
async def list_medications(
    patient_id: Optional[str] = Query(None, description="Filter by patient"),
    active_only: bool = Query(True, description="Only show active medications"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List medications with optional filtering.
    """
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    medications = patient_repo.get_patient_medications(
        patient_id,
        active_only=active_only,
        limit=limit
    )

    return {
        "count": len(medications),
        "medications": medications
    }


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(medication_id: str):
    """
    Get a medication by ID.
    """
    medication = patient_repo.get_medication(medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    return medication


@router.put("/{medication_id}")
async def update_medication(medication_id: str, updates: MedicationUpdate):
    """
    Update a medication record.
    """
    existing = patient_repo.get_medication(medication_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Medication not found")

    # Filter out None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    # Convert enum to value if present
    if "frequency" in update_data and isinstance(update_data["frequency"], MedicationFrequency):
        update_data["frequency"] = update_data["frequency"].value

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = patient_repo.update_medication(medication_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update medication")

    return {"message": "Medication updated successfully"}


@router.delete("/{medication_id}")
async def discontinue_medication(
    medication_id: str,
    reason: str = Query(..., description="Reason for discontinuation")
):
    """
    Discontinue a medication.
    """
    existing = patient_repo.get_medication(medication_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Medication not found")

    success = patient_repo.discontinue_medication(medication_id, reason)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to discontinue medication")

    return {"message": "Medication discontinued successfully"}


@router.post("/{medication_id}/log-dose")
async def log_dose(
    medication_id: str,
    taken_at: Optional[datetime] = Query(None, description="When the dose was taken (defaults to now)")
):
    """
    Log that a dose was taken.
    """
    existing = patient_repo.get_medication(medication_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Medication not found")

    # Update pills remaining if tracked
    if existing.get("pills_remaining") is not None:
        new_count = max(0, existing["pills_remaining"] - 1)
        patient_repo.update_medication(medication_id, {
            "pills_remaining": new_count,
            "last_dose_at": taken_at or datetime.utcnow()
        })

        # Check refill threshold
        if existing.get("refill_reminder") and existing.get("refill_threshold"):
            if new_count <= existing["refill_threshold"]:
                return {
                    "message": "Dose logged successfully",
                    "pills_remaining": new_count,
                    "refill_warning": True,
                    "refill_message": f"Only {new_count} pills remaining. Consider refilling soon."
                }

        return {
            "message": "Dose logged successfully",
            "pills_remaining": new_count
        }

    return {"message": "Dose logged successfully"}


@router.post("/{medication_id}/generate-reminders")
async def generate_medication_reminders(
    medication_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days to generate reminders for")
):
    """
    Generate reminders for a medication for the specified number of days.
    """
    existing = patient_repo.get_medication(medication_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Medication not found")

    if not existing.get("is_active"):
        raise HTTPException(status_code=400, detail="Cannot generate reminders for inactive medication")

    reminder_ids = patient_repo.generate_reminders_for_medication(medication_id, days=days)

    return {
        "message": f"Generated {len(reminder_ids)} reminders",
        "reminder_count": len(reminder_ids)
    }


# ==================== Reminder Endpoints ====================

@router.get("/reminders/upcoming", response_model=ReminderListResponse)
async def get_upcoming_reminders(
    patient_id: str = Query(..., description="Patient ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look ahead")
):
    """
    Get upcoming medication reminders for a patient.
    """
    reminders = patient_repo.get_upcoming_reminders(patient_id, hours=hours)

    return {
        "count": len(reminders),
        "reminders": reminders
    }


@router.get("/reminders/overdue", response_model=ReminderListResponse)
async def get_overdue_reminders(
    patient_id: Optional[str] = Query(None, description="Optional patient filter")
):
    """
    Get overdue medication reminders.
    """
    reminders = patient_repo.get_overdue_reminders(patient_id)

    return {
        "count": len(reminders),
        "reminders": reminders
    }


@router.post("/reminders/{reminder_id}/acknowledge")
async def acknowledge_reminder(reminder_id: str):
    """
    Acknowledge a medication reminder.
    """
    success = patient_repo.acknowledge_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found or already acknowledged")

    return {"message": "Reminder acknowledged successfully"}


# ==================== Patient-specific Endpoints ====================

@router.get("/patient/{patient_id}", response_model=MedicationListResponse)
async def get_patient_medications(
    patient_id: str,
    active_only: bool = Query(True, description="Only show active medications"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get all medications for a specific patient.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    medications = patient_repo.get_patient_medications(
        patient_id,
        active_only=active_only,
        limit=limit
    )

    return {
        "count": len(medications),
        "medications": medications
    }


@router.get("/patient/{patient_id}/reminders", response_model=ReminderListResponse)
async def get_patient_reminders(
    patient_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to look ahead")
):
    """
    Get upcoming reminders for a specific patient.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    reminders = patient_repo.get_upcoming_reminders(patient_id, hours=hours)

    return {
        "count": len(reminders),
        "reminders": reminders
    }
