"""
MongoDB Client for Patient Data Persistence
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client for patient data storage.
    Supports both local MongoDB and MongoDB Atlas.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: str = "health_navigator"
    ):
        """
        Initialize MongoDB client.

        Args:
            connection_string: MongoDB URI (or from MONGODB_URI env)
            database_name: Name of the database
        """
        self.connection_string = connection_string or os.getenv(
            "MONGODB_URI",
            "mongodb://localhost:27017"
        )
        self.database_name = database_name
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    def connect(self) -> bool:
        """
        Establish connection to MongoDB.

        Returns:
            True if connected successfully
        """
        try:
            self._client = MongoClient(self.connection_string)
            self._db = self._client[self.database_name]

            # Test connection
            self._client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.database_name}")
            return True

        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False

    @property
    def db(self) -> Database:
        """Get database instance, connecting if needed"""
        if self._db is None:
            self.connect()
        return self._db

    def get_collection(self, name: str) -> Collection:
        """Get a collection by name"""
        return self.db[name]

    def close(self):
        """Close the MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None


class PatientRepository:
    """
    Repository for patient-related database operations.
    """

    def __init__(self, mongo_client: Optional[MongoDBClient] = None):
        self.mongo = mongo_client or MongoDBClient()
        self._patients: Optional[Collection] = None
        self._assessments: Optional[Collection] = None
        self._sessions: Optional[Collection] = None
        self._appointments: Optional[Collection] = None
        self._medications: Optional[Collection] = None
        self._medication_reminders: Optional[Collection] = None
        self._follow_up_schedules: Optional[Collection] = None

    @property
    def patients(self) -> Collection:
        """Get patients collection"""
        if self._patients is None:
            self._patients = self.mongo.get_collection("patients")
        return self._patients

    @property
    def assessments(self) -> Collection:
        """Get assessments collection"""
        if self._assessments is None:
            self._assessments = self.mongo.get_collection("assessments")
        return self._assessments

    @property
    def sessions(self) -> Collection:
        """Get sessions collection"""
        if self._sessions is None:
            self._sessions = self.mongo.get_collection("sessions")
        return self._sessions

    @property
    def appointments(self) -> Collection:
        """Get appointments collection"""
        if self._appointments is None:
            self._appointments = self.mongo.get_collection("appointments")
        return self._appointments

    @property
    def medications(self) -> Collection:
        """Get medications collection"""
        if self._medications is None:
            self._medications = self.mongo.get_collection("medications")
        return self._medications

    @property
    def medication_reminders(self) -> Collection:
        """Get medication reminders collection"""
        if self._medication_reminders is None:
            self._medication_reminders = self.mongo.get_collection("medication_reminders")
        return self._medication_reminders

    @property
    def follow_up_schedules(self) -> Collection:
        """Get follow-up schedules collection"""
        if self._follow_up_schedules is None:
            self._follow_up_schedules = self.mongo.get_collection("follow_up_schedules")
        return self._follow_up_schedules

    # ==================== Patient Operations ====================

    def create_patient(self, patient_data: Dict[str, Any]) -> str:
        """
        Create a new patient record.

        Args:
            patient_data: Patient information

        Returns:
            Patient ID (string)
        """
        patient = {
            **patient_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Generate patient_id if not provided
        if "patient_id" not in patient:
            patient["patient_id"] = f"PAT{ObjectId()}"

        result = self.patients.insert_one(patient)
        logger.info(f"Created patient: {patient['patient_id']}")

        return patient["patient_id"]

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by ID.

        Args:
            patient_id: Patient identifier

        Returns:
            Patient document or None
        """
        patient = self.patients.find_one({"patient_id": patient_id})
        if patient:
            patient["_id"] = str(patient["_id"])
        return patient

    def update_patient(
        self,
        patient_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update patient record.

        Args:
            patient_id: Patient identifier
            updates: Fields to update

        Returns:
            True if updated
        """
        updates["updated_at"] = datetime.utcnow()

        result = self.patients.update_one(
            {"patient_id": patient_id},
            {"$set": updates}
        )

        return result.modified_count > 0

    def search_patients(
        self,
        query: Dict[str, Any],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search patients by query.

        Args:
            query: MongoDB query
            limit: Max results

        Returns:
            List of matching patients
        """
        patients = list(self.patients.find(query).limit(limit))
        for p in patients:
            p["_id"] = str(p["_id"])
        return patients

    # ==================== Assessment Operations ====================

    def create_assessment(self, assessment_data: Dict[str, Any]) -> str:
        """
        Create a new assessment record.

        Args:
            assessment_data: Full assessment data

        Returns:
            Assessment ID
        """
        assessment = {
            **assessment_data,
            "assessment_id": f"ASM{ObjectId()}",
            "created_at": datetime.utcnow()
        }

        result = self.assessments.insert_one(assessment)
        logger.info(f"Created assessment: {assessment['assessment_id']}")

        return assessment["assessment_id"]

    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment by ID"""
        assessment = self.assessments.find_one({"assessment_id": assessment_id})
        if assessment:
            assessment["_id"] = str(assessment["_id"])
        return assessment

    def get_patient_assessments(
        self,
        patient_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all assessments for a patient.

        Args:
            patient_id: Patient identifier
            limit: Max results

        Returns:
            List of assessments
        """
        assessments = list(
            self.assessments
            .find({"patient_id": patient_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        for a in assessments:
            a["_id"] = str(a["_id"])
        return assessments

    # ==================== Session Operations ====================

    def create_session(self, session_data: Dict[str, Any]) -> str:
        """
        Create a new chat session.

        Args:
            session_data: Session data

        Returns:
            Session ID
        """
        session = {
            **session_data,
            "session_id": f"SES{ObjectId()}",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "messages": []
        }

        result = self.sessions.insert_one(session)
        return session["session_id"]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        session = self.sessions.find_one({"session_id": session_id})
        if session:
            session["_id"] = str(session["_id"])
        return session

    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        Add a message to session history.

        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Message content

        Returns:
            True if added
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }

        result = self.sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return result.modified_count > 0

    def update_session_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Update session state (for workflow state).

        Args:
            session_id: Session identifier
            state: New state data

        Returns:
            True if updated
        """
        result = self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "state": state,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    # ==================== Analytics Operations ====================

    def get_assessment_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics on assessments"""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "by_risk": {
                        "$push": "$clinical_risk_level"
                    }
                }
            }
        ]

        results = list(self.assessments.aggregate(pipeline))
        if results:
            return results[0]
        return {"total": 0, "by_risk": []}

    # ==================== Appointment Operations ====================

    def create_appointment(self, appointment_data: Dict[str, Any]) -> str:
        """
        Create a new appointment record.

        Args:
            appointment_data: Appointment information

        Returns:
            Appointment ID (string)
        """
        appointment = {
            **appointment_data,
            "appointment_id": f"APT{ObjectId()}",
            "status": appointment_data.get("status", "scheduled"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = self.appointments.insert_one(appointment)
        logger.info(f"Created appointment: {appointment['appointment_id']}")

        return appointment["appointment_id"]

    def get_appointment(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get appointment by ID.

        Args:
            appointment_id: Appointment identifier

        Returns:
            Appointment document or None
        """
        appointment = self.appointments.find_one({"appointment_id": appointment_id})
        if appointment:
            appointment["_id"] = str(appointment["_id"])
        return appointment

    def update_appointment(
        self,
        appointment_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update appointment record.

        Args:
            appointment_id: Appointment identifier
            updates: Fields to update

        Returns:
            True if updated
        """
        updates["updated_at"] = datetime.utcnow()

        result = self.appointments.update_one(
            {"appointment_id": appointment_id},
            {"$set": updates}
        )

        return result.modified_count > 0

    def delete_appointment(self, appointment_id: str) -> bool:
        """
        Delete (cancel) an appointment.

        Args:
            appointment_id: Appointment identifier

        Returns:
            True if deleted
        """
        result = self.appointments.delete_one({"appointment_id": appointment_id})
        return result.deleted_count > 0

    def get_patient_appointments(
        self,
        patient_id: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all appointments for a patient.

        Args:
            patient_id: Patient identifier
            status: Optional status filter
            limit: Max results

        Returns:
            List of appointments
        """
        query = {"patient_id": patient_id}
        if status:
            query["status"] = status

        appointments = list(
            self.appointments
            .find(query)
            .sort("scheduled_datetime", 1)
            .limit(limit)
        )
        for a in appointments:
            a["_id"] = str(a["_id"])
        return appointments

    def get_upcoming_appointments(
        self,
        days: int = 7,
        patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming appointments within specified days.

        Args:
            days: Number of days ahead to look
            patient_id: Optional patient filter

        Returns:
            List of upcoming appointments
        """
        from datetime import timedelta
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)

        query = {
            "scheduled_datetime": {"$gte": now, "$lte": end_date},
            "status": {"$in": ["scheduled", "confirmed"]}
        }
        if patient_id:
            query["patient_id"] = patient_id

        appointments = list(
            self.appointments
            .find(query)
            .sort("scheduled_datetime", 1)
        )
        for a in appointments:
            a["_id"] = str(a["_id"])
        return appointments

    def get_all_appointments(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all appointments with optional status filter.

        Args:
            status: Optional status filter
            limit: Max results

        Returns:
            List of appointments
        """
        query = {}
        if status:
            query["status"] = status

        appointments = list(
            self.appointments
            .find(query)
            .sort("scheduled_datetime", -1)
            .limit(limit)
        )
        for a in appointments:
            a["_id"] = str(a["_id"])
        return appointments

    # ==================== Medication Operations ====================

    def create_medication(self, medication_data: Dict[str, Any]) -> str:
        """
        Create a new medication record.

        Args:
            medication_data: Medication information

        Returns:
            Medication ID (string)
        """
        medication = {
            **medication_data,
            "medication_id": f"MED{ObjectId()}",
            "is_active": medication_data.get("is_active", True),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = self.medications.insert_one(medication)
        logger.info(f"Created medication: {medication['medication_id']}")

        return medication["medication_id"]

    def get_medication(self, medication_id: str) -> Optional[Dict[str, Any]]:
        """Get medication by ID."""
        medication = self.medications.find_one({"medication_id": medication_id})
        if medication:
            medication["_id"] = str(medication["_id"])
        return medication

    def update_medication(
        self,
        medication_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update medication record."""
        updates["updated_at"] = datetime.utcnow()

        result = self.medications.update_one(
            {"medication_id": medication_id},
            {"$set": updates}
        )

        return result.modified_count > 0

    def get_patient_medications(
        self,
        patient_id: str,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all medications for a patient.

        Args:
            patient_id: Patient identifier
            active_only: Only return active medications
            limit: Max results

        Returns:
            List of medications
        """
        query = {"patient_id": patient_id}
        if active_only:
            query["is_active"] = True

        medications = list(
            self.medications
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        for m in medications:
            m["_id"] = str(m["_id"])
        return medications

    def discontinue_medication(
        self,
        medication_id: str,
        reason: str
    ) -> bool:
        """
        Discontinue a medication.

        Args:
            medication_id: Medication identifier
            reason: Reason for discontinuation

        Returns:
            True if updated
        """
        return self.update_medication(medication_id, {
            "is_active": False,
            "discontinued_reason": reason,
            "discontinued_at": datetime.utcnow()
        })

    # ==================== Medication Reminder Operations ====================

    def create_reminder(self, reminder_data: Dict[str, Any]) -> str:
        """
        Create a new medication reminder.

        Args:
            reminder_data: Reminder information

        Returns:
            Reminder ID (string)
        """
        reminder = {
            **reminder_data,
            "reminder_id": f"REM{ObjectId()}",
            "status": reminder_data.get("status", "pending"),
            "email_sent": False,
            "created_at": datetime.utcnow()
        }

        result = self.medication_reminders.insert_one(reminder)
        logger.info(f"Created reminder: {reminder['reminder_id']}")

        return reminder["reminder_id"]

    def get_upcoming_reminders(
        self,
        patient_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming reminders for a patient within specified hours.

        Args:
            patient_id: Patient identifier
            hours: Hours ahead to look

        Returns:
            List of upcoming reminders
        """
        from datetime import timedelta
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)

        reminders = list(
            self.medication_reminders
            .find({
                "patient_id": patient_id,
                "scheduled_time": {"$gte": now, "$lte": end_time},
                "status": "pending"
            })
            .sort("scheduled_time", 1)
        )
        for r in reminders:
            r["_id"] = str(r["_id"])
        return reminders

    def get_overdue_reminders(
        self,
        patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get overdue reminders.

        Args:
            patient_id: Optional patient filter

        Returns:
            List of overdue reminders
        """
        now = datetime.utcnow()
        query = {
            "scheduled_time": {"$lt": now},
            "status": "pending"
        }
        if patient_id:
            query["patient_id"] = patient_id

        reminders = list(
            self.medication_reminders
            .find(query)
            .sort("scheduled_time", 1)
        )
        for r in reminders:
            r["_id"] = str(r["_id"])
        return reminders

    def acknowledge_reminder(self, reminder_id: str) -> bool:
        """
        Acknowledge a reminder.

        Args:
            reminder_id: Reminder identifier

        Returns:
            True if updated
        """
        result = self.medication_reminders.update_one(
            {"reminder_id": reminder_id},
            {"$set": {
                "status": "acknowledged",
                "acknowledged_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0

    def generate_reminders_for_medication(
        self,
        medication_id: str,
        days: int = 7
    ) -> List[str]:
        """
        Generate reminders for a medication for the specified number of days.

        Args:
            medication_id: Medication identifier
            days: Number of days to generate reminders for

        Returns:
            List of created reminder IDs
        """
        from datetime import timedelta

        medication = self.get_medication(medication_id)
        if not medication or not medication.get("is_active"):
            return []

        specific_times = medication.get("specific_times", ["09:00"])
        patient_id = medication.get("patient_id")
        reminder_ids = []

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(days):
            reminder_date = today + timedelta(days=day_offset)

            for time_str in specific_times:
                try:
                    hour, minute = map(int, time_str.split(":"))
                    scheduled_time = reminder_date.replace(hour=hour, minute=minute)

                    # Only create future reminders
                    if scheduled_time > datetime.utcnow():
                        reminder_id = self.create_reminder({
                            "medication_id": medication_id,
                            "patient_id": patient_id,
                            "scheduled_time": scheduled_time,
                            "reminder_type": "dose",
                            "medication_name": medication.get("name"),
                            "dosage": medication.get("dosage"),
                            "instructions": medication.get("instructions")
                        })
                        reminder_ids.append(reminder_id)
                except (ValueError, TypeError):
                    continue

        return reminder_ids

    # ==================== Follow-up Tracking Operations ====================

    def create_follow_up_schedule(self, schedule_data: Dict[str, Any]) -> str:
        """
        Create a new follow-up schedule.

        Args:
            schedule_data: Follow-up schedule information

        Returns:
            Schedule ID (string)
        """
        schedule = {
            **schedule_data,
            "schedule_id": f"FUS{ObjectId()}",
            "status": schedule_data.get("status", "pending"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = self.follow_up_schedules.insert_one(schedule)
        logger.info(f"Created follow-up schedule: {schedule['schedule_id']}")

        return schedule["schedule_id"]

    def get_follow_up_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get follow-up schedule by ID."""
        schedule = self.follow_up_schedules.find_one({"schedule_id": schedule_id})
        if schedule:
            schedule["_id"] = str(schedule["_id"])
        return schedule

    def update_follow_up_schedule(
        self,
        schedule_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update follow-up schedule."""
        updates["updated_at"] = datetime.utcnow()

        result = self.follow_up_schedules.update_one(
            {"schedule_id": schedule_id},
            {"$set": updates}
        )

        return result.modified_count > 0

    def get_patient_follow_ups(
        self,
        patient_id: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all follow-up schedules for a patient.

        Args:
            patient_id: Patient identifier
            status: Optional status filter
            limit: Max results

        Returns:
            List of follow-up schedules
        """
        query = {"patient_id": patient_id}
        if status:
            query["status"] = status

        schedules = list(
            self.follow_up_schedules
            .find(query)
            .sort("scheduled_date", 1)
            .limit(limit)
        )
        for s in schedules:
            s["_id"] = str(s["_id"])
        return schedules

    def get_pending_follow_ups(
        self,
        days: int = 7,
        patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending follow-ups within specified days.

        Args:
            days: Days ahead to look
            patient_id: Optional patient filter

        Returns:
            List of pending follow-ups
        """
        from datetime import timedelta
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)

        query = {
            "scheduled_date": {"$gte": now, "$lte": end_date},
            "status": "pending"
        }
        if patient_id:
            query["patient_id"] = patient_id

        schedules = list(
            self.follow_up_schedules
            .find(query)
            .sort("scheduled_date", 1)
        )
        for s in schedules:
            s["_id"] = str(s["_id"])
        return schedules

    def get_overdue_follow_ups(
        self,
        patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get overdue follow-ups.

        Args:
            patient_id: Optional patient filter

        Returns:
            List of overdue follow-ups
        """
        now = datetime.utcnow()
        query = {
            "scheduled_date": {"$lt": now},
            "status": "pending"
        }
        if patient_id:
            query["patient_id"] = patient_id

        schedules = list(
            self.follow_up_schedules
            .find(query)
            .sort("scheduled_date", 1)
        )
        for s in schedules:
            s["_id"] = str(s["_id"])
        return schedules

    def complete_follow_up(
        self,
        schedule_id: str,
        completed_assessment_id: str
    ) -> bool:
        """
        Mark a follow-up as completed with the assessment ID.

        Args:
            schedule_id: Follow-up schedule identifier
            completed_assessment_id: Assessment ID of the follow-up assessment

        Returns:
            True if updated
        """
        return self.update_follow_up_schedule(schedule_id, {
            "status": "completed",
            "completed_assessment_id": completed_assessment_id,
            "completed_at": datetime.utcnow()
        })

    def link_assessments(
        self,
        original_assessment_id: str,
        follow_up_assessment_id: str
    ) -> bool:
        """
        Link a follow-up assessment to its original assessment.

        Args:
            original_assessment_id: Original assessment identifier
            follow_up_assessment_id: Follow-up assessment identifier

        Returns:
            True if updated
        """
        # Update the follow-up assessment
        result = self.assessments.update_one(
            {"assessment_id": follow_up_assessment_id},
            {"$set": {
                "parent_assessment_id": original_assessment_id,
                "is_follow_up": True,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0

    def get_assessment_chain(
        self,
        assessment_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get the chain of linked assessments (original + all follow-ups).

        Args:
            assessment_id: Any assessment in the chain

        Returns:
            List of linked assessments in chronological order
        """
        # First, find the root assessment
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return []

        # Walk up to find the root
        while assessment.get("parent_assessment_id"):
            parent = self.get_assessment(assessment["parent_assessment_id"])
            if parent:
                assessment = parent
            else:
                break

        root_id = assessment["assessment_id"]

        # Now get all assessments in the chain
        chain = [assessment]

        # Find all follow-ups
        follow_ups = list(
            self.assessments
            .find({"parent_assessment_id": root_id})
            .sort("created_at", 1)
        )

        for fu in follow_ups:
            fu["_id"] = str(fu["_id"])
            chain.append(fu)

            # Find nested follow-ups (recursive)
            nested = self._get_nested_follow_ups(fu["assessment_id"])
            chain.extend(nested)

        return chain

    def _get_nested_follow_ups(self, parent_id: str) -> List[Dict[str, Any]]:
        """Helper to get nested follow-up assessments."""
        follow_ups = list(
            self.assessments
            .find({"parent_assessment_id": parent_id})
            .sort("created_at", 1)
        )

        result = []
        for fu in follow_ups:
            fu["_id"] = str(fu["_id"])
            result.append(fu)
            # Recursive call for deeper nesting
            result.extend(self._get_nested_follow_ups(fu["assessment_id"]))

        return result

    def auto_create_follow_up(
        self,
        assessment_id: str,
        care_level: str
    ) -> Optional[str]:
        """
        Automatically create a follow-up schedule based on care level.

        Args:
            assessment_id: Assessment identifier
            care_level: Care level from assessment

        Returns:
            Created schedule ID or None
        """
        from datetime import timedelta

        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return None

        # Determine follow-up timing based on care level
        follow_up_days = {
            "Emergency": 1,      # 24 hours
            "Urgent Care": 3,    # 3 days
            "Primary Care": 7,   # 1 week
            "Self-Care": 14      # 2 weeks
        }

        days = follow_up_days.get(care_level, 14)
        scheduled_date = datetime.utcnow() + timedelta(days=days)

        schedule_id = self.create_follow_up_schedule({
            "original_assessment_id": assessment_id,
            "patient_id": assessment.get("patient_id"),
            "scheduled_date": scheduled_date,
            "follow_up_type": "treatment_review",
            "reason": f"Follow-up based on {care_level} care level recommendation",
            "care_level": care_level
        })

        return schedule_id


# Global instances
mongo_client = MongoDBClient()
patient_repo = PatientRepository(mongo_client)
