CREATE TABLE accounts (
    user_id uuid PRIMARY KEY,
    username varchar(64) NOT NULL UNIQUE
        CHECK (username ~ '^[a-z0-9][a-z0-9_.-]{2,63}$'),
    role text NOT NULL CHECK (role IN ('owner', 'collaborator')),
    password_hash text NOT NULL,
    auth_version bigint NOT NULL DEFAULT 1 CHECK (auth_version > 0),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX accounts_single_owner ON accounts (role) WHERE role = 'owner';

CREATE TABLE sessions (
    token_hash char(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    user_id uuid NOT NULL REFERENCES accounts(user_id),
    auth_version bigint NOT NULL CHECK (auth_version > 0),
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX sessions_user_id ON sessions(user_id);
CREATE INDEX sessions_expires_at ON sessions(expires_at);
