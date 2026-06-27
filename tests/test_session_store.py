from pathlib import Path

import pytest

from research_agent.dto import Round
from research_agent.memory.context import assemble_context
from research_agent.memory.session_store import (
    FileSessionStore,
    SessionNotFoundError,
    SessionState,
)


def _make_store(data_dir: Path) -> FileSessionStore:
    return FileSessionStore(data_dir=data_dir)


def _state(*queries: str) -> SessionState:
    return SessionState(
        rounds=[Round(query=q, response=f"r-{q}") for q in queries]
    )


class TestSessionStorePersistence:
    def test_round_trips_state(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save("s1", _state("q1", "q2"))
        loaded = store.load("s1")
        assert [r.query for r in loaded.rounds] == ["q1", "q2"]

    def test_reloads_after_restart(self, tmp_path: Path) -> None:
        _make_store(tmp_path).save("s1", _state("q1"))
        # Fresh store instance simulates a service restart against the same dir.
        reloaded = _make_store(tmp_path).load("s1")
        assert [r.query for r in reloaded.rounds] == ["q1"]

    def test_load_unknown_session_returns_empty_state(
        self, tmp_path: Path
    ) -> None:
        loaded = _make_store(tmp_path).load("missing")
        assert loaded.rounds == []
        assert loaded.summary == ""


class TestSessionStoreIsolation:
    def test_sessions_do_not_leak(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save("a", _state("only-a"))
        store.save("b", _state("only-b"))
        assert [r.query for r in store.load("a").rounds] == ["only-a"]
        assert [r.query for r in store.load("b").rounds] == ["only-b"]


class TestSessionStoreListAndHistory:
    def test_list_sessions_empty_when_none_persisted(
        self, tmp_path: Path
    ) -> None:
        assert _make_store(tmp_path).list_sessions() == []

    def test_list_sessions_returns_persisted_ids(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save("s2", _state("q"))
        store.save("s1", _state("q"))
        assert store.list_sessions() == ["s1", "s2"]

    def test_get_history_returns_rounds(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save("s1", _state("q1", "q2"))
        assert [r.query for r in store.get_history("s1")] == ["q1", "q2"]

    def test_get_history_unknown_session_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SessionNotFoundError, match="missing"):
            _make_store(tmp_path).get_history("missing")


class TestSessionStoreValidation:
    @pytest.mark.parametrize(
        "session_id", ["../escape", "a/b", "", "with space", "dot.dot"]
    )
    def test_unsafe_session_id_rejected(
        self, tmp_path: Path, session_id: str
    ) -> None:
        with pytest.raises(ValueError, match="Invalid session id"):
            _make_store(tmp_path).save(session_id, _state("q"))


class TestContextWindow:
    @pytest.mark.parametrize(
        ("total", "recent", "expected"),
        [(5, 3, 3), (2, 3, 2), (3, 3, 3), (1, 1, 1)],
    )
    def test_window_is_capped_to_recent_rounds(
        self, total: int, recent: int, expected: int
    ) -> None:
        state = _state(*(f"q{i}" for i in range(total)))
        window = assemble_context(state, recent)
        assert len(window) == expected
        # Window keeps the most recent rounds, in order.
        assert [r.query for r in window] == [
            f"q{i}" for i in range(total - expected, total)
        ]

    @pytest.mark.parametrize("recent", [0, -1])
    def test_non_positive_window_is_empty(self, recent: int) -> None:
        # rounds[-0:] would return the whole history; guard yields [].
        state = _state("q0", "q1", "q2")
        assert assemble_context(state, recent) == []
