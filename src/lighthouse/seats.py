import re
import threading

SEAT_CAP = 30
_SESSION_ID = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_lock = threading.Lock()
_holders: dict[str, set[str]] = {}


def reset_seats() -> None:
    with _lock:
        _holders.clear()


def seat_count(session_id: str) -> int:
    with _lock:
        return len(_holders.get(session_id, ()))


def holds_seat(token: str, session_id: str) -> bool:
    cleaned = (token or "").strip()
    if not cleaned or not _SESSION_ID.match(session_id or ""):
        return False
    with _lock:
        return cleaned in _holders.get(session_id, ())


def claim_seat(token: str, session_id: str) -> dict:
    cleaned = (token or "").strip()
    if not cleaned or len(cleaned) > 64 or not cleaned.replace("-", "").isalnum():
        raise ValueError("invalid seat token")
    if not _SESSION_ID.match(session_id or ""):
        raise ValueError("invalid session")
    with _lock:
        holders = _holders.setdefault(session_id, set())
        accepted = cleaned in holders
        if not accepted and len(holders) < SEAT_CAP:
            holders.add(cleaned)
            accepted = True
        return {
            "session": session_id,
            "seats_taken": len(holders),
            "seat_cap": SEAT_CAP,
            "accepted": accepted,
        }
