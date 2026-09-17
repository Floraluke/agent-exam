"""Inspect the public Compose interface without starting a daemon workload."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "compose.yaml"


def render_config(tmp_path: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI with Compose is required for this check"
    cli_config = tmp_path / "docker-client"
    cli_config.mkdir(exist_ok=True)
    env_file = tmp_path / "empty.env"
    env_file.write_text("", encoding="utf-8")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("AGENTEXAM_", "COMPOSE_", "DOCKER_"))
    }
    environment.update(
        AGENTEXAM_DATA_ROOT=(tmp_path / "data space").as_posix(),
        AGENTEXAM_POSTGRES_IMAGE="postgres@sha256:" + "1" * 64,
        AGENTEXAM_MINIO_IMAGE="minio/minio@sha256:" + "2" * 64,
    )
    environment.update(overrides)
    return subprocess.run(
        [
            docker,
            "--config",
            str(cli_config),
            "compose",
            "--project-name",
            "agentexam-config-test",
            "--env-file",
            str(env_file),
            "--file",
            str(COMPOSE_FILE),
            "config",
            "--format",
            "json",
        ],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=False,
    )


def test_postgres_data_uses_explicit_host_directory_not_a_docker_volume(tmp_path):
    result = render_config(tmp_path)

    assert result.returncode == 0, result.stderr
    service = json.loads(result.stdout)["services"]["postgres"]
    mount = next(
        item
        for item in service["volumes"]
        if item["target"] == "/var/lib/postgresql/data"
    )
    assert mount["type"] == "bind"
    assert Path(mount["source"]) == tmp_path / "data space" / "postgres"
    assert not mount.get("bind", {}).get("create_host_path", False)
    assert not (tmp_path / "data space").exists()


def test_minio_objects_use_the_explicit_host_directory(tmp_path):
    result = render_config(tmp_path)

    assert result.returncode == 0, result.stderr
    service = json.loads(result.stdout)["services"]["minio"]
    mount = next(item for item in service["volumes"] if item["target"] == "/data")
    assert mount["type"] == "bind"
    assert Path(mount["source"]) == tmp_path / "data space" / "minio"
    assert not mount.get("bind", {}).get("create_host_path", False)
    assert not (tmp_path / "data space").exists()


def test_stores_publish_only_loopback_ports_and_never_autostart(tmp_path):
    result = render_config(tmp_path)

    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    for name, target in (("postgres", 5432), ("minio", 9000)):
        service = services[name]
        assert service["restart"] == "no"
        assert len(service["ports"]) == 1
        assert service["ports"][0]["host_ip"] == "127.0.0.1"
        assert service["ports"][0]["target"] == target
        assert service.get("network_mode") != "host"
        assert not service.get("privileged", False)


def test_passwords_are_readonly_files_not_embedded_in_compose_environment(tmp_path):
    result = render_config(tmp_path)

    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    for name, variable, filename in (
        ("postgres", "POSTGRES_PASSWORD", "postgres-password"),
        ("minio", "MINIO_ROOT_PASSWORD", "minio-password"),
    ):
        service = services[name]
        assert variable not in service.get("environment", {})
        secret_path = service["environment"][variable + "_FILE"]
        assert secret_path == "/run/secrets/" + filename
        mount = next(
            item for item in service["volumes"] if item["target"] == secret_path
        )
        assert Path(mount["source"]) == tmp_path / "data space" / "private" / filename
        assert mount["read_only"] is True
        assert not mount.get("bind", {}).get("create_host_path", False)


@pytest.mark.parametrize(
    "missing",
    ["AGENTEXAM_DATA_ROOT", "AGENTEXAM_POSTGRES_IMAGE", "AGENTEXAM_MINIO_IMAGE"],
)
def test_configuration_without_an_explicit_root_or_image_is_rejected(tmp_path, missing):
    result = render_config(tmp_path, **{missing: ""})

    assert result.returncode != 0
    assert missing in result.stderr


def test_stores_have_no_broad_host_mounts_or_privileged_runtime(tmp_path):
    result = render_config(tmp_path)

    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    expected_targets = {
        "postgres": {"/var/lib/postgresql/data", "/run/secrets/postgres-password"},
        "minio": {"/data", "/run/secrets/minio-password"},
    }
    for name, targets in expected_targets.items():
        service = services[name]
        assert {mount["target"] for mount in service["volumes"]} == targets
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert not service.get("privileged", False)
        assert not service.get("devices", [])
        assert service.get("pid") != "host"
