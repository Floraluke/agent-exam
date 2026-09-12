CREATE TABLE evaluation_jobs (
    job_id uuid PRIMARY KEY,
    created_by uuid NOT NULL REFERENCES accounts(user_id),
    created_at timestamptz NOT NULL,
    status text NOT NULL CHECK (
        status IN ('AWAITING_OWNER_APPROVAL', 'QUEUED', 'REJECTED')
    ),
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
    row_version bigint NOT NULL DEFAULT 0 CHECK (row_version IN (0, 1)),
    idempotency_key_hash char(64) NOT NULL
        CHECK (idempotency_key_hash ~ '^[0-9a-f]{64}$'),
    request_sha256 char(64) NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    owner_decided_by uuid REFERENCES accounts(user_id),
    owner_decided_at timestamptz,
    owner_decision_reason text CHECK (
        owner_decision_reason IS NULL OR
        char_length(owner_decision_reason) BETWEEN 1 AND 500
    ),
    owner_decision_key_hash char(64) CHECK (
        owner_decision_key_hash IS NULL OR
        owner_decision_key_hash ~ '^[0-9a-f]{64}$'
    ),
    owner_decision_request_sha256 char(64) CHECK (
        owner_decision_request_sha256 IS NULL OR
        owner_decision_request_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CHECK (
        (status = 'AWAITING_OWNER_APPROVAL' AND row_version = 0 AND
            owner_decided_by IS NULL AND owner_decided_at IS NULL AND
            owner_decision_reason IS NULL AND owner_decision_key_hash IS NULL AND
            owner_decision_request_sha256 IS NULL)
        OR
        (status IN ('QUEUED', 'REJECTED') AND row_version = 1 AND
            owner_decided_by IS NOT NULL AND owner_decided_at IS NOT NULL AND
            owner_decision_key_hash IS NOT NULL AND
            owner_decision_request_sha256 IS NOT NULL)
    ),
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
    status text NOT NULL CHECK (status IN ('PENDING', 'CANCELED')),
    row_version bigint NOT NULL DEFAULT 0 CHECK (row_version IN (0, 1)),
    created_at timestamptz NOT NULL,
    CHECK (
        (status = 'PENDING' AND row_version = 0) OR
        (status = 'CANCELED' AND row_version = 1)
    ),
    UNIQUE (job_id, task_id, agent_configuration_id, attempt_index)
);

CREATE TABLE job_state_events (
    event_id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES evaluation_jobs(job_id),
    sequence integer NOT NULL CHECK (sequence IN (1, 2)),
    from_status text,
    to_status text NOT NULL,
    reason_code text NOT NULL,
    actor_user_id uuid NOT NULL REFERENCES accounts(user_id),
    occurred_at timestamptz NOT NULL,
    note text CHECK (note IS NULL OR char_length(note) BETWEEN 1 AND 500),
    CHECK (
        (sequence = 1 AND from_status IS NULL AND
            to_status = 'AWAITING_OWNER_APPROVAL' AND
            reason_code = 'JOB_SUBMITTED' AND note IS NULL)
        OR
        (sequence = 2 AND from_status = 'AWAITING_OWNER_APPROVAL' AND
            ((to_status = 'QUEUED' AND reason_code = 'OWNER_APPROVED') OR
             (to_status = 'REJECTED' AND reason_code = 'OWNER_REJECTED')))
    ),
    UNIQUE (job_id, sequence)
);

CREATE TABLE run_state_events (
    event_id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES evaluation_runs(run_id),
    sequence integer NOT NULL CHECK (sequence IN (1, 2)),
    from_status text,
    to_status text NOT NULL,
    reason_code text NOT NULL,
    occurred_at timestamptz NOT NULL,
    CHECK (
        (sequence = 1 AND from_status IS NULL AND to_status = 'PENDING' AND
            reason_code = 'JOB_SUBMITTED')
        OR
        (sequence = 2 AND from_status = 'PENDING' AND to_status = 'CANCELED' AND
            reason_code = 'JOB_REJECTED')
    ),
    UNIQUE (run_id, sequence)
);

CREATE INDEX evaluation_jobs_scope ON evaluation_jobs(created_by, job_id);
CREATE INDEX evaluation_jobs_queue ON evaluation_jobs(status, created_at, job_id);
CREATE INDEX evaluation_runs_job ON evaluation_runs(job_id, run_id);
