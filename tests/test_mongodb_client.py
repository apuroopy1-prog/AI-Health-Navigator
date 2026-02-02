"""
Tests for MongoDB client
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatetimeUsage:
    """Tests to verify timezone-aware datetime usage"""

    def test_datetime_now_utc_returns_aware_datetime(self):
        """Test that datetime.now(timezone.utc) returns timezone-aware datetime"""
        now = datetime.now(timezone.utc)

        # Should be timezone-aware
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_datetime_comparison(self):
        """Test that timezone-aware datetimes can be compared"""
        time1 = datetime.now(timezone.utc)
        time2 = datetime.now(timezone.utc)

        # time2 should be >= time1
        assert time2 >= time1


class TestMongoDBClientInit:
    """Tests for MongoDB client initialization"""

    def test_default_connection_string(self):
        """Test default connection string when env not set"""
        with patch.dict(os.environ, {}, clear=True):
            # Remove MONGODB_URI if present
            os.environ.pop('MONGODB_URI', None)

            from database.mongodb_client import MongoDBClient
            client = MongoDBClient()

            assert "mongodb://" in client.connection_string

    def test_custom_database_name(self):
        """Test custom database name"""
        from database.mongodb_client import MongoDBClient

        client = MongoDBClient(database_name="test_db")
        assert client.database_name == "test_db"


class TestPatientRepository:
    """Tests for PatientRepository operations"""

    @pytest.fixture
    def mock_mongo_client(self):
        """Create a mock MongoDB client"""
        mock = MagicMock()
        mock.get_collection.return_value = MagicMock()
        return mock

    def test_patient_data_includes_timestamps(self, mock_mongo_client):
        """Test that patient creation includes created_at and updated_at"""
        from database.mongodb_client import PatientRepository

        repo = PatientRepository(mock_mongo_client)

        # Mock the insert
        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_mongo_client.get_collection.return_value = mock_collection

        patient_data = {
            "name": "Test Patient",
            "age": 30
        }

        repo.create_patient(patient_data)

        # Verify insert was called
        call_args = mock_collection.insert_one.call_args[0][0]

        assert "created_at" in call_args
        assert "updated_at" in call_args
        # Verify the timestamps are timezone-aware
        assert call_args["created_at"].tzinfo is not None

    def test_assessment_data_includes_timestamp(self, mock_mongo_client):
        """Test that assessment creation includes created_at"""
        from database.mongodb_client import PatientRepository

        repo = PatientRepository(mock_mongo_client)

        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_mongo_client.get_collection.return_value = mock_collection

        assessment_data = {
            "patient_id": "PAT123",
            "symptoms": ["headache"]
        }

        repo.create_assessment(assessment_data)

        call_args = mock_collection.insert_one.call_args[0][0]

        assert "created_at" in call_args
        assert "assessment_id" in call_args
        assert call_args["assessment_id"].startswith("ASM")


class TestSessionOperations:
    """Tests for session-related operations"""

    @pytest.fixture
    def mock_mongo_client(self):
        mock = MagicMock()
        mock.get_collection.return_value = MagicMock()
        return mock

    def test_session_creation_includes_messages_list(self, mock_mongo_client):
        """Test that session creation includes empty messages list"""
        from database.mongodb_client import PatientRepository

        repo = PatientRepository(mock_mongo_client)

        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_mongo_client.get_collection.return_value = mock_collection

        session_data = {"patient_id": "PAT123"}

        repo.create_session(session_data)

        call_args = mock_collection.insert_one.call_args[0][0]

        assert "messages" in call_args
        assert call_args["messages"] == []
        assert call_args["session_id"].startswith("SES")


class TestAppointmentOperations:
    """Tests for appointment operations"""

    @pytest.fixture
    def mock_mongo_client(self):
        mock = MagicMock()
        mock.get_collection.return_value = MagicMock()
        return mock

    def test_appointment_default_status(self, mock_mongo_client):
        """Test appointment creation with default status"""
        from database.mongodb_client import PatientRepository

        repo = PatientRepository(mock_mongo_client)

        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_mongo_client.get_collection.return_value = mock_collection

        appointment_data = {
            "patient_id": "PAT123",
            "provider": "Dr. Smith"
        }

        repo.create_appointment(appointment_data)

        call_args = mock_collection.insert_one.call_args[0][0]

        assert call_args["status"] == "scheduled"
        assert call_args["appointment_id"].startswith("APT")


class TestMedicationOperations:
    """Tests for medication operations"""

    @pytest.fixture
    def mock_mongo_client(self):
        mock = MagicMock()
        mock.get_collection.return_value = MagicMock()
        return mock

    def test_medication_default_active(self, mock_mongo_client):
        """Test medication creation defaults to active"""
        from database.mongodb_client import PatientRepository

        repo = PatientRepository(mock_mongo_client)

        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock_mongo_client.get_collection.return_value = mock_collection

        medication_data = {
            "patient_id": "PAT123",
            "name": "Aspirin",
            "dosage": "100mg"
        }

        repo.create_medication(medication_data)

        call_args = mock_collection.insert_one.call_args[0][0]

        assert call_args["is_active"] is True
        assert call_args["medication_id"].startswith("MED")
