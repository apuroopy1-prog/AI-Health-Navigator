"""
Follow-up Tracking API Routes
"""
from typing import List, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo

router = APIRouter()


# ==================== Enums ====================

class FollowUpStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class FollowUpType(str, Enum):
    SYMPTOM_CHECK = "symptom_check"
    TEST_RESULTS = "test_results"
    TREATMENT_REVIEW = "treatment_review"
    MEDICATION_REVIEW = "medication_review"
    GENERAL = "general"


# ==================== Pydantic Models ====================

class FollowUpScheduleCreate(BaseModel):
    """Request model for creating a follow-up schedule"""
    original_assessment_id: str = Field(..., description="Original assessment identifier")
    scheduled_date: datetime = Field(..., description="Scheduled follow-up date")
    follow_up_type: FollowUpType = Field(default=FollowUpType.TREATMENT_REVIEW)
    reason: str = Field(..., min_length=1, description="Reason for follow-up")


class FollowUpScheduleUpdate(BaseModel):
    """Request model for updating a follow-up schedule"""
    scheduled_date: Optional[datetime] = None
    follow_up_type: Optional[FollowUpType] = None
    reason: Optional[str] = None
    status: Optional[FollowUpStatus] = None


class FollowUpScheduleResponse(BaseModel):
    """Response model for follow-up schedule data"""
    schedule_id: str
    original_assessment_id: str
    patient_id: str
    scheduled_date: datetime
    follow_up_type: str
    reason: str
    status: str
    care_level: Optional[str] = None
    completed_assessment_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FollowUpListResponse(BaseModel):
    """Response model for list of follow-up schedules"""
    count: int
    follow_ups: List[FollowUpScheduleResponse]


class AssessmentTimelineResponse(BaseModel):
    """Response model for patient assessment timeline"""
    patient_id: str
    total_assessments: int
    assessments: List[dict]


# ==================== Follow-up Schedule Endpoints ====================

@router.post("/schedule", response_model=dict)
async def schedule_follow_up(follow_up: FollowUpScheduleCreate):
    """
    Schedule a new follow-up.

    Returns the created schedule ID.
    """
    # Verify original assessment exists
    assessment = patient_repo.get_assessment(follow_up.original_assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Original assessment not found")

    try:
        schedule_data = follow_up.model_dump()
        schedule_data["patient_id"] = assessment.get("patient_id")

        # Convert enum to value
        if isinstance(schedule_data.get("follow_up_type"), FollowUpType):
            schedule_data["follow_up_type"] = schedule_data["follow_up_type"].value

        schedule_id = patient_repo.create_follow_up_schedule(schedule_data)

        return {
            "schedule_id": schedule_id,
            "message": "Follow-up scheduled successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=FollowUpListResponse)
async def list_follow_ups(
    patient_id: Optional[str] = Query(None, description="Filter by patient"),
    status: Optional[FollowUpStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List follow-up schedules with optional filtering.
    """
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    follow_ups = patient_repo.get_patient_follow_ups(
        patient_id,
        status=status.value if status else None,
        limit=limit
    )

    return {
        "count": len(follow_ups),
        "follow_ups": follow_ups
    }


@router.get("/pending", response_model=FollowUpListResponse)
async def get_pending_follow_ups(
    days: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    patient_id: Optional[str] = Query(None, description="Filter by patient")
):
    """
    Get pending follow-ups within the specified number of days.
    """
    follow_ups = patient_repo.get_pending_follow_ups(
        days=days,
        patient_id=patient_id
    )

    return {
        "count": len(follow_ups),
        "follow_ups": follow_ups
    }


@router.get("/overdue", response_model=FollowUpListResponse)
async def get_overdue_follow_ups(
    patient_id: Optional[str] = Query(None, description="Filter by patient")
):
    """
    Get overdue follow-ups.
    """
    follow_ups = patient_repo.get_overdue_follow_ups(patient_id=patient_id)

    return {
        "count": len(follow_ups),
        "follow_ups": follow_ups
    }


@router.get("/{schedule_id}", response_model=FollowUpScheduleResponse)
async def get_follow_up(schedule_id: str):
    """
    Get a follow-up schedule by ID.
    """
    schedule = patient_repo.get_follow_up_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Follow-up schedule not found")
    return schedule


@router.put("/{schedule_id}")
async def update_follow_up(schedule_id: str, updates: FollowUpScheduleUpdate):
    """
    Update a follow-up schedule.
    """
    existing = patient_repo.get_follow_up_schedule(schedule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Follow-up schedule not found")

    # Filter out None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    # Convert enums to values
    if "follow_up_type" in update_data and isinstance(update_data["follow_up_type"], FollowUpType):
        update_data["follow_up_type"] = update_data["follow_up_type"].value
    if "status" in update_data and isinstance(update_data["status"], FollowUpStatus):
        update_data["status"] = update_data["status"].value

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = patient_repo.update_follow_up_schedule(schedule_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update follow-up")

    return {"message": "Follow-up updated successfully"}


@router.delete("/{schedule_id}")
async def cancel_follow_up(schedule_id: str):
    """
    Cancel a follow-up schedule.
    """
    existing = patient_repo.get_follow_up_schedule(schedule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Follow-up schedule not found")

    success = patient_repo.update_follow_up_schedule(schedule_id, {"status": "cancelled"})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel follow-up")

    return {"message": "Follow-up cancelled successfully"}


@router.post("/{schedule_id}/complete")
async def complete_follow_up(
    schedule_id: str,
    assessment_id: str = Query(..., description="Assessment ID of the completed follow-up")
):
    """
    Mark a follow-up as completed with the assessment ID.
    """
    existing = patient_repo.get_follow_up_schedule(schedule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Follow-up schedule not found")

    # Verify the assessment exists
    assessment = patient_repo.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Complete the follow-up
    success = patient_repo.complete_follow_up(schedule_id, assessment_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to complete follow-up")

    # Link the assessments
    patient_repo.link_assessments(
        existing.get("original_assessment_id"),
        assessment_id
    )

    return {"message": "Follow-up completed successfully"}


# ==================== Assessment Timeline Endpoints ====================

@router.get("/patient/{patient_id}/timeline", response_model=AssessmentTimelineResponse)
async def get_patient_timeline(
    patient_id: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get the assessment timeline for a patient.
    Shows all assessments with their relationships.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get all assessments for the patient
    assessments = patient_repo.get_patient_assessments(patient_id, limit=limit)

    # Enrich with follow-up information
    for assessment in assessments:
        # Get any follow-up schedules linked to this assessment
        follow_ups = patient_repo.get_patient_follow_ups(
            patient_id,
            limit=5
        )
        related_follow_ups = [
            fu for fu in follow_ups
            if fu.get("original_assessment_id") == assessment.get("assessment_id")
        ]
        assessment["follow_ups"] = related_follow_ups

        # Check if this is a follow-up assessment
        assessment["is_follow_up"] = assessment.get("is_follow_up", False)
        assessment["parent_assessment_id"] = assessment.get("parent_assessment_id")

    return {
        "patient_id": patient_id,
        "total_assessments": len(assessments),
        "assessments": assessments
    }


@router.get("/assessment/{assessment_id}/chain")
async def get_assessment_chain(assessment_id: str):
    """
    Get the full chain of linked assessments (original + all follow-ups).
    """
    chain = patient_repo.get_assessment_chain(assessment_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return {
        "root_assessment_id": chain[0].get("assessment_id") if chain else None,
        "total_in_chain": len(chain),
        "assessments": chain
    }


@router.post("/assessment/{assessment_id}/auto-schedule")
async def auto_schedule_follow_up(assessment_id: str):
    """
    Automatically schedule a follow-up based on the assessment's care level.
    """
    assessment = patient_repo.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    care_level = assessment.get("care_level", "Self-Care")

    schedule_id = patient_repo.auto_create_follow_up(assessment_id, care_level)
    if not schedule_id:
        raise HTTPException(status_code=500, detail="Failed to create follow-up schedule")

    # Get the created schedule for response
    schedule = patient_repo.get_follow_up_schedule(schedule_id)

    return {
        "schedule_id": schedule_id,
        "scheduled_date": schedule.get("scheduled_date"),
        "care_level": care_level,
        "message": f"Follow-up scheduled based on {care_level} care level"
    }


# ==================== Patient-specific Endpoints ====================

@router.get("/patient/{patient_id}", response_model=FollowUpListResponse)
async def get_patient_follow_ups(
    patient_id: str,
    status: Optional[FollowUpStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get all follow-up schedules for a specific patient.
    """
    # Verify patient exists
    patient = patient_repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    follow_ups = patient_repo.get_patient_follow_ups(
        patient_id,
        status=status.value if status else None,
        limit=limit
    )

    return {
        "count": len(follow_ups),
        "follow_ups": follow_ups
    }
