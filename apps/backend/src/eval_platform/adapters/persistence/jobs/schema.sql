CREATE TABLE evaluation_jobs (
    job_id uuid PRIMARY KEY,
    created_by uuid NOT NULL REFERENCES accounts(user_id),
    created_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN (
        'AWAITING_OWNER_APPROVAL', 'QUEUED', 'PREPARING', 'EXECUTING',
        'FINALIZING', 'COMPLETED', 'FAILED', 'REJECTED'
    )),
    evaluation_track text NOT NULL CHECK (evaluation_track = 'closed_book'),
    result_scope text NOT NULL CHECK (result_scope IN ('official', 'internal_test')),
    batch_preset text NOT NULL CHECK (batch_preset IN ('demo', 'quick', 'standard')),
    limit_profile_id text NOT NULL CHECK (limit_profile_id = 'default-single-host-v1'),
    limit_snapshot jsonb NOT NULL CHECK (jsonb_typeof(limit_snapshot) = 'object'),
    network_policy_id text NOT NULL CHECK (length(network_policy_id) > 0),
    network_policy_snapshot jsonb NOT NULL CHECK (jsonb_typeof(network_policy_snapshot) = 'object'),
    tool_profile_id text NOT NULL CHECK (length(tool_profile_id) > 0),
    tool_profile_snapshot jsonb NOT NULL CHECK (jsonb_typeof(tool_profile_snapshot) = 'object'),
    harbor_revision char(40) NOT NULL CHECK (harbor_revision ~ '^[0-9a-f]{40}$'),
    swe_gym_revision char(40) NOT NULL CHECK (swe_gym_revision ~ '^[0-9a-f]{40}$'),
    swe_bench_fork_revision char(40) NOT NULL CHECK (swe_bench_fork_revision ~ '^[0-9a-f]{40}$'),
    trial_count integer NOT NULL CHECK (trial_count BETWEEN 1 AND 60),
    row_version bigint NOT NULL DEFAULT 0 CHECK (row_version >= 0),
    idempotency_key_hash char(64) NOT NULL CHECK (idempotency_key_hash ~ '^[0-9a-f]{64}$'),
    request_sha256 char(64) NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    owner_decided_by uuid REFERENCES accounts(user_id),
    owner_decided_at timestamptz,
    owner_decision_reason text CHECK (owner_decision_reason IS NULL OR char_length(owner_decision_reason) BETWEEN 1 AND 500),
    owner_decision_key_hash char(64) CHECK (owner_decision_key_hash IS NULL OR owner_decision_key_hash ~ '^[0-9a-f]{64}$'),
    owner_decision_request_sha256 char(64) CHECK (owner_decision_request_sha256 IS NULL OR owner_decision_request_sha256 ~ '^[0-9a-f]{64}$'),
    claimed_by varchar(64) CHECK (claimed_by IS NULL OR claimed_by ~ '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$'),
    claimed_at timestamptz,
    heartbeat_at timestamptz,
    lease_expires_at timestamptz,
    failure_code varchar(128),
    failure_summary varchar(500),
    started_at timestamptz,
    finished_at timestamptz,
    CHECK (num_nonnulls(owner_decided_by, owner_decided_at, owner_decision_key_hash, owner_decision_request_sha256) IN (0, 4)),
    CHECK ((status = 'AWAITING_OWNER_APPROVAL' AND owner_decided_by IS NULL) OR (status <> 'AWAITING_OWNER_APPROVAL' AND owner_decided_by IS NOT NULL)),
    CHECK (num_nonnulls(claimed_by, claimed_at, heartbeat_at, lease_expires_at, started_at) IN (0, 5)),
    CHECK ((status IN ('AWAITING_OWNER_APPROVAL', 'QUEUED', 'REJECTED') AND claimed_by IS NULL) OR (status NOT IN ('AWAITING_OWNER_APPROVAL', 'QUEUED', 'REJECTED') AND claimed_by IS NOT NULL)),
    CHECK ((status = 'FAILED') = (failure_code IS NOT NULL AND failure_summary IS NOT NULL)),
    UNIQUE (created_by, idempotency_key_hash)
);

CREATE TABLE evaluation_runs (
    run_id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES evaluation_jobs(job_id),
    task_id uuid NOT NULL REFERENCES evaluation_tasks(task_id),
    agent_configuration_id uuid NOT NULL REFERENCES agent_configurations(agent_configuration_id),
    attempt_index integer NOT NULL CHECK (attempt_index = 1),
    task_snapshot jsonb NOT NULL CHECK (jsonb_typeof(task_snapshot) = 'object'),
    agent_snapshot jsonb NOT NULL CHECK (jsonb_typeof(agent_snapshot) = 'object'),
    execution_contract_version text NOT NULL CHECK (length(execution_contract_version) > 0),
    backend_kind text NOT NULL CHECK (backend_kind IN ('harbor', 'mock')),
    backend_revision char(40) NOT NULL CHECK (backend_revision ~ '^[0-9a-f]{40}$'),
    backend_job_ref varchar(256),
    backend_trial_ref varchar(256),
    status text NOT NULL CHECK (status IN (
        'PENDING', 'PREPARING', 'RUNNING_AGENT', 'VERIFYING',
        'COMPLETED', 'FAILED', 'CANCELED'
    )),
    stage varchar(64),
    row_version bigint NOT NULL DEFAULT 0 CHECK (row_version >= 0),
    failure_code varchar(128),
    failure_summary varchar(500),
    resolved_summary boolean,
    process_metrics jsonb,
    warnings jsonb,
    created_at timestamptz NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    CHECK ((status IN ('PENDING', 'CANCELED') AND started_at IS NULL) OR (status NOT IN ('PENDING', 'CANCELED') AND started_at IS NOT NULL)),
    CHECK ((status = 'FAILED') = (failure_code IS NOT NULL AND failure_summary IS NOT NULL)),
    CHECK ((status = 'COMPLETED') = (resolved_summary IS NOT NULL)),
    UNIQUE (job_id, task_id, agent_configuration_id, attempt_index)
);

ALTER TABLE artifact_records ADD CONSTRAINT artifact_run_owner
    FOREIGN KEY (run_id) REFERENCES evaluation_runs(run_id);
CREATE UNIQUE INDEX artifact_run_identity ON artifact_records(run_id, artifact_id);

CREATE TABLE job_state_events (
    event_id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES evaluation_jobs(job_id),
    sequence integer NOT NULL CHECK (sequence > 0),
    from_status text,
    to_status text NOT NULL,
    reason_code varchar(128) NOT NULL,
    actor_user_id uuid REFERENCES accounts(user_id),
    worker_id varchar(64),
    occurred_at timestamptz NOT NULL,
    note text CHECK (note IS NULL OR char_length(note) BETWEEN 1 AND 500),
    CHECK (num_nonnulls(actor_user_id, worker_id) = 1),
    UNIQUE (job_id, sequence)
);

CREATE TABLE run_state_events (
    event_id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES evaluation_runs(run_id),
    sequence integer NOT NULL CHECK (sequence > 0),
    from_status text,
    to_status text NOT NULL,
    reason_code varchar(128) NOT NULL,
    worker_id varchar(64),
    occurred_at timestamptz NOT NULL,
    CHECK (
        (worker_id IS NULL AND (sequence = 1 OR reason_code = 'JOB_REJECTED')) OR
        (worker_id IS NOT NULL AND sequence > 1 AND reason_code <> 'JOB_REJECTED')
    ),
    UNIQUE (run_id, sequence)
);

CREATE TABLE deterministic_results (
    run_id uuid PRIMARY KEY REFERENCES evaluation_runs(run_id),
    patch_exists boolean NOT NULL,
    patch_successfully_applied boolean NOT NULL,
    resolved boolean NOT NULL,
    tests_status_summary jsonb NOT NULL CHECK (jsonb_typeof(tests_status_summary) = 'object'),
    harness_revision char(40) NOT NULL CHECK (harness_revision ~ '^[0-9a-f]{40}$'),
    report_artifact_id uuid NOT NULL,
    test_output_artifact_id uuid,
    duration_ms bigint CHECK (duration_ms IS NULL OR duration_ms >= 0),
    created_at timestamptz NOT NULL,
    FOREIGN KEY (run_id, report_artifact_id) REFERENCES artifact_records(run_id, artifact_id),
    FOREIGN KEY (run_id, test_output_artifact_id) REFERENCES artifact_records(run_id, artifact_id)
);

CREATE INDEX evaluation_jobs_scope ON evaluation_jobs(created_by, job_id);
CREATE INDEX evaluation_jobs_queue ON evaluation_jobs(status, created_at, job_id);
CREATE INDEX evaluation_runs_job ON evaluation_runs(job_id, run_id);
CREATE INDEX artifact_records_run ON artifact_records(run_id, artifact_type, created_at);
