CREATE TABLE evaluation_jobs (
    job_id uuid PRIMARY KEY,
    created_by uuid NOT NULL REFERENCES accounts(user_id),
    created_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status = 'AWAITING_OWNER_APPROVAL'),
    evaluation_track text NOT NULL CHECK (evaluation_track = 'closed_book'),
    result_scope text NOT NULL CHECK (result_scope IN ('official', 'internal_test')),
    batch_preset text NOT NULL CHECK (batch_preset IN ('demo', 'quick', 'standard')),
    limit_profile_id text NOT NULL CHECK (limit_profile_id = 'default-single-host-v1'),
    limit_snapshot jsonb NOT NULL CHECK (jsonb_typeof(limit_snapshot) = 'object'),
    network_policy_id text NOT NULL CHECK (length(network_policy_id) > 0),
    network_policy_snapshot jsonb NOT NULL
        CHECK (jsonb_typeof(network_policy_snapshot) = 'object'),
    tool_profile_id text NOT NULL CHECK (length(tool_profile_id) > 0),
    tool_profile_snapshot jsonb NOT NULL
        CHECK (jsonb_typeof(tool_profile_snapshot) = 'object'),
    harbor_revision char(40) NOT NULL CHECK (harbor_revision ~ '^[0-9a-f]{40}$'),
    swe_gym_revision char(40) NOT NULL CHECK (swe_gym_revision ~ '^[0-9a-f]{40}$'),
    swe_bench_fork_revision char(40) NOT NULL
        CHECK (swe_bench_fork_revision ~ '^[0-9a-f]{40}$'),
    trial_count integer NOT NULL CHECK (trial_count BETWEEN 1 AND 60),
    row_version bigint NOT NULL DEFAULT 0 CHECK (row_version = 0),
    idempotency_key_hash char(64) NOT NULL
        CHECK (idempotency_key_hash ~ '^[0-9a-f]{64}$'),
    request_sha256 char(64) NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    UNIQUE (created_by, idempotency_key_hash)
);

CREATE TABLE evaluation_runs (
    run_id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES evaluation_jobs(job_id),
    task_id uuid NOT NULL REFERENCES evaluation_tasks(task_id),
    agent_configuration_id uuid NOT NULL
        REFERENCES agent_configurations(agent_configuration_id),
    attempt_index integer NOT NULL CHECK (attempt_index = 1),
    task_snapshot jsonb NOT NULL CHECK (jsonb_typeof(task_snapshot) = 'object'),
    agent_snapshot jsonb NOT NULL CHECK (jsonb_typeof(agent_snapshot) = 'object'),
    execution_contract_version text NOT NULL CHECK (length(execution_contract_version) > 0),
    backend_kind text NOT NULL CHECK (backend_kind IN ('harbor', 'mock')),
    backend_revision char(40) NOT NULL CHECK (backend_revision ~ '^[0-9a-f]{40}$'),
    status text NOT NULL CHECK (status = 'PENDING'),
    row_version bigint NOT NULL DEFAULT 0 CHECK (row_version = 0),
    created_at timestamptz NOT NULL,
    UNIQUE (job_id, task_id, agent_configuration_id, attempt_index)
);

CREATE TABLE job_state_events (
    event_id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES evaluation_jobs(job_id),
    sequence integer NOT NULL CHECK (sequence = 1),
    from_status text CHECK (from_status IS NULL),
    to_status text NOT NULL CHECK (to_status = 'AWAITING_OWNER_APPROVAL'),
    reason_code text NOT NULL CHECK (reason_code = 'JOB_SUBMITTED'),
    actor_user_id uuid NOT NULL REFERENCES accounts(user_id),
    occurred_at timestamptz NOT NULL,
    UNIQUE (job_id, sequence)
);

CREATE TABLE run_state_events (
    event_id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES evaluation_runs(run_id),
    sequence integer NOT NULL CHECK (sequence = 1),
    from_status text CHECK (from_status IS NULL),
    to_status text NOT NULL CHECK (to_status = 'PENDING'),
    reason_code text NOT NULL CHECK (reason_code = 'JOB_SUBMITTED'),
    occurred_at timestamptz NOT NULL,
    UNIQUE (run_id, sequence)
);

CREATE INDEX evaluation_jobs_scope ON evaluation_jobs(created_by, job_id);
CREATE INDEX evaluation_runs_job ON evaluation_runs(job_id, run_id);
