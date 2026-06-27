import os
import re
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field

from research_agent.config import Settings
from research_agent.dto import Round

_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class SessionState(BaseModel):
    """Persisted per-session memory: full chat history plus long-term summary.

    ``rounds`` is the complete chat history (never trimmed by compression).
    ``summary`` is the long-term summary folded in by async compression; it
    stays empty until that milestone (``## 10``) fills it.
    """

    rounds: list[Round] = Field(default_factory=list)
    summary: str = ""


class SessionNotFoundError(Exception):
    """Raised when retrieving a session id that was never persisted."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id!r}")
        self.session_id = session_id


class SessionStore(BaseModel, ABC):
    """Thin seam over per-session persistence, keyed by ``session_id``.

    Synchronous: backed by local file I/O, which is small and fast, so it
    stays sync rather than dragging async through the storage layer. The seam
    lets the file backend be swapped for Redis/DB later without touching the
    coordinator. ``load`` returns a fresh empty state for an unknown session
    so the coordinator can start one; ``get_history`` instead raises for an
    unknown session, since "no such session" and "session with no rounds yet"
    are different facts the API must distinguish.
    """

    @abstractmethod
    def load(self, session_id: str) -> SessionState: ...

    @abstractmethod
    def save(self, session_id: str, state: SessionState) -> None: ...

    @abstractmethod
    def list_sessions(self) -> list[str]: ...

    @abstractmethod
    def get_history(self, session_id: str) -> list[Round]: ...


class FileSessionStore(SessionStore):
    """``SessionStore`` backed by one JSON file per session under a data dir.

    Writes are atomic (temp file then ``os.replace``) so a crash mid-write
    cannot leave a half-written session. Sized for a single MVP instance.
    """

    data_dir: Path

    def load(self, session_id: str) -> SessionState:
        state = self._read(session_id)
        return state if state is not None else SessionState()

    def save(self, session_id: str, state: SessionState) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(session_id)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(state.model_dump_json(), encoding="utf-8")
        os.replace(temp, path)

    def list_sessions(self) -> list[str]:
        if not self.data_dir.exists():
            return []
        return sorted(path.stem for path in self.data_dir.glob("*.json"))

    def get_history(self, session_id: str) -> list[Round]:
        state = self._read(session_id)
        if state is None:
            raise SessionNotFoundError(session_id)
        return state.rounds

    def _read(self, session_id: str) -> SessionState | None:
        path = self._path_for(session_id)
        if not path.exists():
            return None
        return SessionState.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def _path_for(self, session_id: str) -> Path:
        # session_id is untrusted client input that becomes a filename; reject
        # anything outside a safe charset to block path traversal.
        if not _SAFE_SESSION_ID.match(session_id):
            raise ValueError(f"Invalid session id: {session_id!r}")
        return self.data_dir / f"{session_id}.json"


def build_session_store(settings: Settings) -> SessionStore:
    return FileSessionStore(data_dir=settings.memory_data_dir)
