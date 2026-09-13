CREATE TABLE evaluation_tasks (
    task_id uuid PRIMARY KEY,
    dataset_id varchar(128) NOT NULL CHECK (length(dataset_id) > 0),
    dataset_revision varchar(64) NOT NULL CHECK (length(dataset_revision) > 0),
    split varchar(64) NOT NULL CHECK (length(split) > 0),
    instance_id varchar(128) NOT NULL CHECK (length(instance_id) > 0),
    repo varchar(128) NOT NULL CHECK (length(repo) > 0),
    base_commit char(40) NOT NULL CHECK (base_commit ~ '^[0-9a-f]{40}$'),
    problem_statement text NOT NULL CHECK (length(problem_statement) > 0),
    environment_image text NOT NULL CHECK (length(environment_image) > 0),
    problem_sha256 char(64) NOT NULL CHECK (problem_sha256 ~ '^[0-9a-f]{64}$'),
    raw_record_sha256 char(64) NOT NULL CHECK (raw_record_sha256 ~ '^[0-9a-f]{64}$'),
    source_snapshot_ref uuid NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE (dataset_id, dataset_revision, split, instance_id)
);

CREATE TABLE artifact_records (
    artifact_id uuid PRIMARY KEY,
    task_id uuid REFERENCES evaluation_tasks(task_id),
    run_id uuid,
    artifact_type text NOT NULL CHECK (artifact_type IN (
        'task_source_snapshot', 'agent_patch', 'harness_report',
        'harness_summary', 'harness_test_output', 'public_test_summary',
        'public_trajectory', 'harbor_trial_config', 'harbor_trial_result',
        'agent_trajectory', 'harness_report_raw', 'harness_summary_raw',
        'harness_test_output_raw', 'harness_log_raw'
    )),
    object_key text NOT NULL UNIQUE CHECK (length(object_key) > 0),
    original_filename varchar(128) NOT NULL CHECK (
        original_filename ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'
    ),
    sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0 AND size_bytes <= 52428800),
    original_size_bytes bigint NOT NULL CHECK (original_size_bytes >= size_bytes),
    content_type text NOT NULL CHECK (
        content_type IN (
            'application/json', 'application/x-ndjson', 'text/plain', 'text/x-diff'
        )
    ),
    retention_class text NOT NULL CHECK (retention_class IN ('long_term', 'raw_30d')),
    expires_at timestamptz,
    redaction_status text NOT NULL DEFAULT 'not_required'
        CHECK (redaction_status IN ('not_required', 'redacted', 'blocked')),
    truncated boolean NOT NULL DEFAULT false,
    deleted_at timestamptz,
    deleted_by uuid REFERENCES accounts(user_id),
    deletion_reason varchar(128),
    created_at timestamptz NOT NULL,
    CHECK (num_nonnulls(task_id, run_id) = 1),
    CHECK (
        (task_id IS NOT NULL AND artifact_type = 'task_source_snapshot' AND
            content_type = 'application/json' AND object_key LIKE 'tasks/%')
        OR
        (run_id IS NOT NULL AND artifact_type <> 'task_source_snapshot' AND
            object_key LIKE 'runs/%')
    ),
    CHECK (artifact_type <> 'agent_patch' OR
        (content_type = 'text/x-diff' AND size_bytes <= 1048576)),
    CHECK (
        (retention_class = 'long_term' AND expires_at IS NULL AND NOT truncated
            AND original_size_bytes = size_bytes)
        OR
        (retention_class = 'raw_30d' AND expires_at IS NOT NULL
            AND expires_at > created_at
            AND truncated = (original_size_bytes > size_bytes))
    ),
    CHECK (num_nonnulls(deleted_at, deleted_by, deletion_reason) IN (0, 3)),
    CHECK (deleted_at IS NULL OR
        (retention_class = 'raw_30d' AND deleted_at >= expires_at)),
    CHECK (
        (retention_class = 'raw_30d' AND redaction_status = 'blocked'
            AND artifact_type IN (
                'harbor_trial_config', 'harbor_trial_result', 'agent_trajectory',
                'harness_report_raw', 'harness_summary_raw',
                'harness_test_output_raw', 'harness_log_raw'
            ))
        OR
        (retention_class = 'long_term' AND artifact_type NOT IN (
            'harbor_trial_config', 'harbor_trial_result', 'agent_trajectory',
            'harness_report_raw', 'harness_summary_raw',
            'harness_test_output_raw', 'harness_log_raw'
        ))
    ),
    UNIQUE (task_id, artifact_id, sha256)
);

ALTER TABLE evaluation_tasks ADD CONSTRAINT task_source_owns_artifact
    FOREIGN KEY (task_id, source_snapshot_ref, raw_record_sha256)
    REFERENCES artifact_records(task_id, artifact_id, sha256)
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE agent_configurations (
    agent_configuration_id uuid PRIMARY KEY,
    display_name varchar(128) NOT NULL CHECK (length(display_name) > 0),
    agent_type text NOT NULL CHECK (agent_type = 'codex'),
    agent_version varchar(128) NOT NULL CHECK (length(agent_version) > 0),
    model_provider text NOT NULL CHECK (model_provider = 'openai_chatgpt'),
    model varchar(128) NOT NULL CHECK (length(model) > 0),
    authentication_type text NOT NULL CHECK (authentication_type = 'chatgpt_auth_json'),
    credential_profile_id varchar(128) NOT NULL
        CHECK (credential_profile_id ~ '^[a-zA-Z0-9_-]+$'),
    public_options jsonb NOT NULL CHECK (
        jsonb_typeof(public_options) = 'object'
        AND public_options ? 'reasoning_effort'
        AND jsonb_typeof(public_options -> 'reasoning_effort') = 'string'
        AND public_options - 'reasoning_effort' = '{}'::jsonb
        AND public_options ->> 'reasoning_effort' IN ('low', 'medium', 'high', 'xhigh')
    ),
    configuration_fingerprint char(64) NOT NULL UNIQUE
        CHECK (configuration_fingerprint ~ '^[0-9a-f]{64}$'),
    limit_profile_id uuid CHECK (limit_profile_id IS NULL),
    enabled boolean NOT NULL,
    created_at timestamptz NOT NULL,
    disabled_at timestamptz,
    CHECK ((enabled AND disabled_at IS NULL) OR (NOT enabled AND disabled_at IS NOT NULL))
);

CREATE INDEX evaluation_tasks_filters ON evaluation_tasks(dataset_id, split, repo, task_id);
CREATE INDEX agent_configurations_enabled ON agent_configurations(enabled, agent_configuration_id);
