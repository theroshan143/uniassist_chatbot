"""Per-session conversation memory with TTL."""

import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger("uniassist.memory")

MAX_TURNS = 6  # Keep last 6 turns (12 messages: user + assistant)
TTL_SECONDS = 1800  # 30 minutes


@dataclass
class SessionMemory:
    """Stores conversation history for one session."""
    messages: list[dict] = field(default_factory=list)
    last_access: float = field(default_factory=time.time)

    def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        """Add a user-assistant turn to memory."""
        self.messages.append({"role": "user", "content": user_msg})
        self.messages.append({"role": "assistant", "content": assistant_msg})
        # Trim to MAX_TURNS (each turn = 2 messages)
        if len(self.messages) > MAX_TURNS * 2:
            self.messages = self.messages[-(MAX_TURNS * 2):]
        self.last_access = time.time()

    def get_history(self) -> list[dict]:
        """Return conversation history."""
        self.last_access = time.time()
        return list(self.messages)

    def is_expired(self) -> bool:
        """Check if this session has expired."""
        return (time.time() - self.last_access) > TTL_SECONDS


class MemoryStore:
    """Thread-safe in-memory store for session memories."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = threading.Lock()

    def get_session(self, session_id: str) -> SessionMemory:
        """Get or create a session memory."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory()
            session = self._sessions[session_id]
            session.last_access = time.time()
            return session

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Add a conversation turn to a session."""
        session = self.get_session(session_id)
        session.add_turn(user_msg, assistant_msg)

    def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        return self.get_session(session_id).get_history()

    def clear_session(self, session_id: str) -> None:
        """Clear a specific session."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        with self._lock:
            expired = [
                sid for sid, mem in self._sessions.items() if mem.is_expired()
            ]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            return len(expired)

    def session_count(self) -> int:
        """Return number of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global memory store
memory_store = MemoryStore()
