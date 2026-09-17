import json
from collections.abc import Callable

import pytest

from eval_platform.delivery.worker.command import run_command
from eval_platform.delivery.worker.main import WorkerShell


class SyntheticWorker(WorkerShell):
    """The existing Worker seam, with no storage, model or credential dependencies."""

    def __init__(self, cycle: Callable[[str], bool]) -> None:
        self.cycle = cycle

    def run_once(self, worker_id: str) -> bool:
        return self.cycle(worker_id)


@pytest.mark.parametrize("worked", [True, False])
def test_default_command_keeps_single_cycle_output(capsys, worked):
    seen = []

    def cycle(worker_id):
        seen.append(worker_id)
        return worked

    assert run_command(["synthetic"], lambda: SyntheticWorker(cycle)) == 0
    assert seen == ["synthetic"]
    assert json.loads(capsys.readouterr().out) == {
        "status": "worker_cycle_finished",
        "claimed": worked,
    }


def test_existing_stop_marker_prevents_dependency_creation(tmp_path, capsys):
    marker = tmp_path / "stop"
    marker.touch()

    def forbidden_factory():
        raise AssertionError("Stopped command must not compose production dependencies")

    assert (
        run_command(
            ["synthetic", "--loop", "--stop-file", str(marker)], forbidden_factory
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "status": "worker_stopped",
        "completed_cycles": 0,
    }


def test_loop_drains_current_cycle_then_stops_before_next_claim(tmp_path, capsys):
    marker = tmp_path / "stop"
    events = []

    def cycle(worker_id):
        assert worker_id == "synthetic"
        assert len(events) < 4, "No claim may follow the observed stop marker"
        events.append("start")
        if len(events) == 3:
            marker.touch()
        events.append("finished")
        return True

    assert (
        run_command(
            ["synthetic", "--loop", "--stop-file", str(marker)],
            lambda: SyntheticWorker(cycle),
        )
        == 0
    )
    assert events == ["start", "finished", "start", "finished"]
    assert json.loads(capsys.readouterr().out) == {
        "status": "worker_stopped",
        "completed_cycles": 2,
    }


def test_empty_queue_waits_and_honors_stop_during_idle(tmp_path, capsys):
    marker = tmp_path / "stop"
    events = []

    def cycle(worker_id):
        assert not events, "Empty queue must not be polled in a busy loop"
        events.append("empty")
        return False

    def wait(seconds):
        events.append(seconds)
        marker.touch()

    assert (
        run_command(
            ["synthetic", "--loop", "--stop-file", str(marker)],
            lambda: SyntheticWorker(cycle),
            wait=wait,
        )
        == 0
    )
    assert events == ["empty", 1.0]
    assert json.loads(capsys.readouterr().out) == {
        "status": "worker_stopped",
        "completed_cycles": 0,
    }


@pytest.mark.parametrize(
    "options",
    [
        ["--loop"],
        ["--loop", "--stop-file", "relative.stop"],
        ["--stop-file", "unused.stop"],
    ],
)
def test_invalid_stop_options_fail_before_composition(options):
    def forbidden_factory():
        raise AssertionError("Invalid command must not read production configuration")

    with pytest.raises(SystemExit) as error:
        run_command(["synthetic", *options], forbidden_factory)
    assert error.value.code == 2


def test_cycle_failure_exits_without_retry_or_private_diagnostics(tmp_path, capsys):
    attempts = []

    def cycle(worker_id):
        attempts.append(worker_id)
        raise RuntimeError("synthetic-private-password")

    assert (
        run_command(
            ["synthetic", "--loop", "--stop-file", str(tmp_path / "stop")],
            lambda: SyntheticWorker(cycle),
        )
        == 2
    )
    assert attempts == ["synthetic"]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == '{"status": "worker_cycle_unavailable"}\n'


def test_stop_arriving_during_composition_prevents_first_claim(tmp_path, capsys):
    marker = tmp_path / "stop"

    def forbidden_cycle(worker_id):
        raise AssertionError("Claim must not start after stop is observed")

    def factory():
        marker.touch()
        return SyntheticWorker(forbidden_cycle)

    assert (
        run_command(["synthetic", "--loop", "--stop-file", str(marker)], factory) == 0
    )
    assert json.loads(capsys.readouterr().out)["completed_cycles"] == 0


def test_runtime_entrypoint_honors_stop_without_runtime_configuration(
    tmp_path, monkeypatch, capsys
):
    from eval_platform.delivery.worker.runtime import main

    marker = tmp_path / "stop"
    marker.touch()
    monkeypatch.delenv("AGENTEXAM_PROJECT_ROOT", raising=False)
    assert main(["synthetic", "--loop", "--stop-file", str(marker)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "worker_stopped"


def test_missing_stop_directory_refuses_composition(tmp_path, capsys):
    composed = []

    def factory():
        composed.append(True)
        raise RuntimeError("synthetic-no-production-dependencies")

    assert (
        run_command(
            ["synthetic", "--loop", "--stop-file", str(tmp_path / "missing" / "stop")],
            factory,
        )
        == 2
    )
    assert composed == []
    assert capsys.readouterr().err == '{"status": "worker_cycle_unavailable"}\n'
