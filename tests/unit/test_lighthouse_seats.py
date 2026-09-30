import pytest

from src.lighthouse.seats import SEAT_CAP, claim_seat, release_seat, reset_seats, seat_count

SESSION = "2026-09-29"
LATER = "2026-10-01"


def test_one_browser_holds_one_seat_per_session_and_the_room_stops_at_thirty():
    reset_seats()
    first = claim_seat("alpha", SESSION)
    again = claim_seat("alpha", SESSION)
    assert first == {
        "session": SESSION,
        "seats_taken": 1,
        "seat_cap": SEAT_CAP,
        "accepted": True,
    }
    assert again == first
    assert seat_count(SESSION) == 1

    other = claim_seat("alpha", LATER)
    assert other["seats_taken"] == 1
    assert seat_count(SESSION) == 1

    for index in range(SEAT_CAP - 1):
        claim_seat(f"seat-{index}", SESSION)
    overflow = claim_seat("overflow", SESSION)
    assert overflow["seats_taken"] == SEAT_CAP
    assert overflow["accepted"] is False
    assert seat_count(LATER) == 1
    reset_seats()
    assert seat_count(SESSION) == 0


def test_release_returns_one_seat_and_leaves_everyone_else():
    reset_seats()
    claim_seat("alpha", SESSION)
    claim_seat("beta", SESSION)
    released = release_seat("alpha", SESSION)
    assert released["released"] is True
    assert released["seats_taken"] == 1
    assert seat_count(SESSION) == 1
    missing = release_seat("alpha", SESSION)
    assert missing["released"] is False
    assert missing["seats_taken"] == 1
    reset_seats()


def test_claim_rejects_a_blank_token_or_a_session_that_is_not_a_date():
    with pytest.raises(ValueError):
        claim_seat("   ", SESSION)
    with pytest.raises(ValueError):
        claim_seat("browser-1", "tuesday")
