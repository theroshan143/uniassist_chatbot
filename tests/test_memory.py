"""Unit tests for conversation memory module."""

import time
from app.memory import MemoryStore, SessionMemory, MAX_TURNS


def test_session_memory_add_turn():
    mem = SessionMemory()
    mem.add_turn("Hello", "Hi there!")
    history = mem.get_history()
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there!"}


def test_session_memory_max_turns_truncation():
    mem = SessionMemory()
    # Add more than MAX_TURNS
    for i in range(MAX_TURNS + 5):
        mem.add_turn(f"User {i}", f"Bot {i}")

    history = mem.get_history()
    # Each turn is 2 messages (user + assistant)
    assert len(history) == MAX_TURNS * 2
    # Verify the most recent turn is present
    assert history[-2]["content"] == f"User {MAX_TURNS + 4}"
    assert history[-1]["content"] == f"Bot {MAX_TURNS + 4}"


def test_session_memory_expiry():
    mem = SessionMemory()
    assert not mem.is_expired()
    # Simulate time passing beyond TTL
    mem.last_access = time.time() - 3600
    assert mem.is_expired()


def test_memory_store_lifecycle():
    store = MemoryStore()
    sid = "test_sess_001"
    
    store.add_turn(sid, "What is my fee?", "Tuition fee is 1,20,000 INR.")
    hist = store.get_history(sid)
    assert len(hist) == 2
    assert store.session_count() == 1

    # Clear session
    store.clear_session(sid)
    assert store.session_count() == 0
    assert len(store.get_history(sid)) == 0


def test_memory_store_cleanup_expired():
    store = MemoryStore()
    s1 = "active_sess"
    s2 = "expired_sess"

    store.add_turn(s1, "Hi", "Hello")
    store.add_turn(s2, "Bye", "Goodbye")

    # Expire s2
    store._sessions[s2].last_access = time.time() - 3600

    removed = store.cleanup_expired()
    assert removed == 1
    assert s1 in store._sessions
    assert s2 not in store._sessions
