"""
Session Manager for patient assessment sessions
Manages state persistence and session lifecycle
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .patient_state import PatientState, create_initial_state, ConversationPhase


class SessionManager:
    """
    Manages patient assessment sessions.
    Currently uses in-memory storage; can be extended to use Redis/DynamoDB.
    """

    def __init__(self):
        self._sessions: Dict[str, PatientState] = {}

    def create_session(self, patient_data: Optional[Dict[str, Any]] = None) -> PatientState:
        """
        Create a new patient assessment session.

        Args:
            patient_data: Optional initial patient data

        Returns:
            Initialized PatientState with session ID
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        state = create_initial_state(patient_data)
        state["session_id"] = session_id
        state["patient_id"] = patient_data.get("patient_id") if patient_data else f"PAT{uuid.uuid4().hex[:8].upper()}"
        state["created_at"] = now
        state["updated_at"] = now

        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[PatientState]:
        """
        Retrieve an existing session by ID.

        Args:
            session_id: The session identifier

        Returns:
            PatientState if found, None otherwise
        """
        return self._sessions.get(session_id)

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> PatientState:
        """
        Update an existing session with new data.

        Args:
            session_id: The session identifier
            updates: Dictionary of fields to update

        Returns:
            Updated PatientState

        Raises:
            ValueError: If session not found
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        state = self._sessions[session_id]

        for key, value in updates.items():
            if key in state:
                state[key] = value

        state["updated_at"] = datetime.now().isoformat()

        # Track workflow history
        if "current_phase" in updates:
            if "workflow_history" not in state:
                state["workflow_history"] = []
            state["workflow_history"].append(updates["current_phase"])

        return state

    def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> PatientState:
        """
        Add a message to the conversation history.

        Args:
            session_id: The session identifier
            role: "user" or "assistant"
            content: Message content

        Returns:
            Updated PatientState
        """
        state = self.get_session(session_id)
        if state is None:
            raise ValueError(f"Session {session_id} not found")

        if "conversation_history" not in state:
            state["conversation_history"] = []

        state["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        if role == "user":
            state["latest_user_message"] = content
        else:
            state["assistant_response"] = content

        state["updated_at"] = datetime.now().isoformat()

        return state

    def transition_phase(
        self,
        session_id: str,
        new_phase: ConversationPhase
    ) -> PatientState:
        """
        Transition the conversation to a new phase.

        Args:
            session_id: The session identifier
            new_phase: The new ConversationPhase

        Returns:
            Updated PatientState
        """
        return self.update_session(session_id, {
            "conversation_phase": new_phase.value,
            "current_phase": new_phase.value
        })

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_all_sessions(self) -> Dict[str, PatientState]:
        """Get all active sessions (for debugging/admin)"""
        return self._sessions.copy()


# Global session manager instance
session_manager = SessionManager()
