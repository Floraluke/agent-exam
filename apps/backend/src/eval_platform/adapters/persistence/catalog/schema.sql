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
    task_id uuid NOT NULL REFERENCES evaluation_tasks(task_id),
    artifact_type text NOT NULL CHECK (artifact_type = 'task_source_snapshot'),
    object_key text NOT NULL UNIQUE CHECK (length(object_key) > 0),
    sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0 AND size_bytes <= 52428800),
    content_type text NOT NULL CHECK (content_type = 'application/json'),
    retention_class text NOT NULL CHECK (retention_class = 'long_term'),
    created_at timestamptz NOT NULL,
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
