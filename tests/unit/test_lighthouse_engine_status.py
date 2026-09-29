from src.lighthouse.engine_status import engine_snapshot, reset_engine_status, step_for


def test_step_names_follow_the_hugging_face_startup_sequence():
    assert step_for("PAUSED") == "waking"
    assert step_for("BUILDING") == "building"
    assert step_for("RUNNING_BUILDING") == "building"
    assert step_for("APP_STARTING") == "starting"
    assert step_for("RUNNING_APP_STARTING") == "starting"
    assert step_for("RUNNING") == "ready"
    assert step_for("RUNTIME_ERROR") == "error"


def test_a_closed_calendar_does_not_read_the_engine():
    calls = []
    body = engine_snapshot("closed", False, lambda: calls.append(1))
    assert body["step"] == "asleep"
    assert calls == []


def test_a_practice_session_does_not_read_the_engine():
    calls = []
    body = engine_snapshot("open", True, lambda: calls.append(1))
    assert body["step"] == "practice"
    assert calls == []


def test_a_failed_engine_read_does_not_pretend_the_wake_started():
    reset_engine_status()

    def reader():
        raise RuntimeError("status unavailable")

    body = engine_snapshot("pre_warm", False, reader, now=5)
    assert body["step"] == "unknown"
    reset_engine_status()


def test_a_live_session_caches_one_engine_read():
    reset_engine_status()
    calls = {"n": 0}

    def reader():
        calls["n"] += 1
        return {"stage": "BUILDING", "hardware": "t4-medium"}

    first = engine_snapshot("pre_warm", False, reader, now=10)
    second = engine_snapshot("open", False, reader, now=20)
    assert first["step"] == "building"
    assert first["hardware"] == "t4-medium"
    assert second == first
    assert calls["n"] == 1
    third = engine_snapshot("drain", False, reader, now=30)
    assert third["step"] == "building"
    assert calls["n"] == 2
    reset_engine_status()
