"""Closed artifact vocabulary shared by publication, storage and delivery."""

from enum import StrEnum


class ArtifactType(StrEnum):
    TASK_SOURCE_SNAPSHOT = "task_source_snapshot"
    AGENT_PATCH = "agent_patch"
    HARNESS_REPORT = "harness_report"
    HARNESS_SUMMARY = "harness_summary"
    HARNESS_TEST_OUTPUT = "harness_test_output"
    PUBLIC_TEST_SUMMARY = "public_test_summary"
    PUBLIC_TRAJECTORY = "public_trajectory"
    HARBOR_TRIAL_CONFIG = "harbor_trial_config"
    HARBOR_TRIAL_RESULT = "harbor_trial_result"
    AGENT_TRAJECTORY = "agent_trajectory"
    HARNESS_REPORT_RAW = "harness_report_raw"
    HARNESS_SUMMARY_RAW = "harness_summary_raw"
    HARNESS_TEST_OUTPUT_RAW = "harness_test_output_raw"
    HARNESS_LOG_RAW = "harness_log_raw"


ARTIFACT_CONTENT_TYPES = {
    ArtifactType.TASK_SOURCE_SNAPSHOT.value: "application/json",
    ArtifactType.AGENT_PATCH.value: "text/x-diff",
    ArtifactType.HARNESS_REPORT.value: "application/json",
    ArtifactType.HARNESS_SUMMARY.value: "application/json",
    ArtifactType.HARNESS_TEST_OUTPUT.value: "text/plain",
    ArtifactType.PUBLIC_TEST_SUMMARY.value: "application/json",
    ArtifactType.PUBLIC_TRAJECTORY.value: "application/x-ndjson",
    ArtifactType.HARBOR_TRIAL_CONFIG.value: "application/json",
    ArtifactType.HARBOR_TRIAL_RESULT.value: "application/json",
    ArtifactType.AGENT_TRAJECTORY.value: "application/json",
    ArtifactType.HARNESS_REPORT_RAW.value: "application/json",
    ArtifactType.HARNESS_SUMMARY_RAW.value: "application/json",
    ArtifactType.HARNESS_TEST_OUTPUT_RAW.value: "text/plain",
    ArtifactType.HARNESS_LOG_RAW.value: "text/plain",
}
ARTIFACT_FILENAMES = {
    ArtifactType.TASK_SOURCE_SNAPSHOT.value: "task.json",
    ArtifactType.AGENT_PATCH.value: "agent.patch",
    ArtifactType.HARNESS_REPORT.value: "harness-report.json",
    ArtifactType.HARNESS_SUMMARY.value: "harness-summary.json",
    ArtifactType.HARNESS_TEST_OUTPUT.value: "test-output.txt",
    ArtifactType.PUBLIC_TEST_SUMMARY.value: "test-summary.json",
    ArtifactType.PUBLIC_TRAJECTORY.value: "trajectory.jsonl",
    ArtifactType.HARBOR_TRIAL_CONFIG.value: "trial-config.json",
    ArtifactType.HARBOR_TRIAL_RESULT.value: "trial-result.json",
    ArtifactType.AGENT_TRAJECTORY.value: "trajectory.json",
    ArtifactType.HARNESS_REPORT_RAW.value: "harness-report.json",
    ArtifactType.HARNESS_SUMMARY_RAW.value: "harness-summary.json",
    ArtifactType.HARNESS_TEST_OUTPUT_RAW.value: "test-output.txt",
    ArtifactType.HARNESS_LOG_RAW.value: "harness.log",
}
PUBLIC_ARTIFACT_TYPES = frozenset(
    {
        ArtifactType.AGENT_PATCH.value,
        ArtifactType.PUBLIC_TEST_SUMMARY.value,
        ArtifactType.PUBLIC_TRAJECTORY.value,
    }
)
RAW_ARTIFACT_TYPES = frozenset(
    {
        ArtifactType.HARBOR_TRIAL_CONFIG.value,
        ArtifactType.HARBOR_TRIAL_RESULT.value,
        ArtifactType.AGENT_TRAJECTORY.value,
        ArtifactType.HARNESS_REPORT_RAW.value,
        ArtifactType.HARNESS_SUMMARY_RAW.value,
        ArtifactType.HARNESS_TEST_OUTPUT_RAW.value,
        ArtifactType.HARNESS_LOG_RAW.value,
    }
)
RUN_ARTIFACT_TYPES = frozenset(ARTIFACT_CONTENT_TYPES) - {
    ArtifactType.TASK_SOURCE_SNAPSHOT.value
}
