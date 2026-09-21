import psycopg
import pytest
from jobs.support.postgres_api import postgres_api

from eval_platform.adapters.persistence.jobs import upgrade_continuous_preset
from eval_platform.delivery import jobs as jobs_delivery
from eval_platform.domain.jobs.models import JobUnavailable

OLD_VALUES = "'demo', 'quick', 'standard'"
NEW_VALUES = "'demo', 'quick', 'standard', 'continuous'"


def _replace_constraint(dsn: str, values: str) -> None:
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "ALTER TABLE evaluation_jobs "
            "DROP CONSTRAINT evaluation_jobs_batch_preset_check, "
            "ADD CONSTRAINT evaluation_jobs_batch_preset_check "
            f"CHECK (batch_preset IN ({values}))"
        )


def _constraint(dsn: str) -> str:
    with psycopg.connect(dsn) as connection:
        row = connection.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid='evaluation_jobs'::regclass "
            "AND conname='evaluation_jobs_batch_preset_check'"
        ).fetchone()
    assert row is not None
    return str(row[0])


def test_continuous_upgrade_changes_old_constraint_once(postgres_sandbox):
    with postgres_api(postgres_sandbox):
        _replace_constraint(postgres_sandbox.dsn, OLD_VALUES)

        assert upgrade_continuous_preset(postgres_sandbox.dsn) is True
        assert "continuous" in _constraint(postgres_sandbox.dsn)
        assert upgrade_continuous_preset(postgres_sandbox.dsn) is False


def test_continuous_upgrade_refuses_unknown_constraint(postgres_sandbox):
    with postgres_api(postgres_sandbox):
        _replace_constraint(postgres_sandbox.dsn, "'demo'")

        with pytest.raises(JobUnavailable):
            upgrade_continuous_preset(postgres_sandbox.dsn)
        assert "continuous" not in _constraint(postgres_sandbox.dsn)


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        (True, "已升级"),
        (False, "无需重复升级"),
    ],
)
def test_continuous_upgrade_command_reports_result(
    monkeypatch, capsys, changed, expected
):
    monkeypatch.setattr(jobs_delivery, "database_url", lambda: "test-dsn")
    monkeypatch.setattr(jobs_delivery, "upgrade_continuous_preset", lambda dsn: changed)

    assert jobs_delivery.main(["upgrade-continuous-preset"]) == 0
    assert expected in capsys.readouterr().out
