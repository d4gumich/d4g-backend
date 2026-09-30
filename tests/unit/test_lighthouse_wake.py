from types import SimpleNamespace
from unittest.mock import patch

import pytest
from huggingface_hub import SpaceHardware

from src.lighthouse.service import LighthouseService


def _service():
    with patch("src.lighthouse.service.HfApi"):
        return LighthouseService()


def _runtime(stage: str, hardware, requested=None):
    return SimpleNamespace(stage=stage, hardware=hardware, requested_hardware=requested)


@pytest.mark.parametrize("stage", ["BUILDING", "APP_STARTING", "RUNNING_APP_STARTING", "RUNNING_BUILDING", "RUNNING"])
def test_wake_up_does_not_restart_an_active_t4(stage: str):
    service = _service()
    service.api.get_space_runtime.return_value = _runtime(stage, SpaceHardware.T4_MEDIUM)
    service.wake_up()
    service.api.request_space_hardware.assert_not_called()
    service.api.restart_space.assert_not_called()


def test_wake_up_restarts_a_paused_space():
    service = _service()
    service.api.get_space_runtime.return_value = _runtime("PAUSED", SpaceHardware.CPU_BASIC)
    service.wake_up()
    service.api.request_space_hardware.assert_called_once()
    kwargs = service.api.request_space_hardware.call_args.kwargs
    assert kwargs["hardware"] == SpaceHardware.T4_MEDIUM
    assert kwargs["sleep_time"] == -1
    service.api.restart_space.assert_called_once()


def test_wake_up_restarts_when_running_on_cpu():
    service = _service()
    service.api.get_space_runtime.return_value = _runtime("RUNNING", SpaceHardware.CPU_BASIC)
    service.wake_up()
    service.api.restart_space.assert_called_once()


def test_wake_up_skips_when_t4_is_already_requested():
    service = _service()
    service.api.get_space_runtime.return_value = _runtime(
        "RUNNING", SpaceHardware.CPU_BASIC, requested=SpaceHardware.T4_MEDIUM
    )
    service.wake_up()
    service.api.restart_space.assert_not_called()
