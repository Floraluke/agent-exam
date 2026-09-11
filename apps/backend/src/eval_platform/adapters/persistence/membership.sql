CREATE TABLE invitations (
    invitation_id uuid PRIMARY KEY,
    token_hash char(64) NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_by uuid NOT NULL REFERENCES accounts(user_id),
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at),
    revoked_at timestamptz,
    redeemed_at timestamptz,
    redeemed_by uuid UNIQUE REFERENCES accounts(user_id),
    CHECK ((redeemed_at IS NULL) = (redeemed_by IS NULL)),
    CHECK (revoked_at IS NULL OR redeemed_at IS NULL)
);
