CREATE TABLE trips (
    id BIGSERIAL PRIMARY KEY,
    singleton_key TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plan_versions (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id),
    version_code TEXT NOT NULL,
    title TEXT NOT NULL,
    source_format TEXT NOT NULL DEFAULT 'markdown',
    raw_source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, version_code)
);

CREATE TABLE plan_items (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id),
    plan_version_id BIGINT NOT NULL REFERENCES plan_versions(id),
    stable_key TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active',
    replaces_item_id BIGINT NULL REFERENCES plan_items(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plan_version_id, stable_key)
);

CREATE INDEX idx_plan_items_trip_stable_key
    ON plan_items (trip_id, stable_key);

CREATE INDEX idx_plan_items_version_type
    ON plan_items (plan_version_id, type);

CREATE TABLE participants (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id),
    display_name TEXT NOT NULL,
    guest_token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NULL
);

CREATE TABLE comments (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id),
    plan_version_id BIGINT NOT NULL REFERENCES plan_versions(id),
    plan_item_id BIGINT NULL REFERENCES plan_items(id),
    participant_id BIGINT NOT NULL REFERENCES participants(id),
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_comments_version_created_at
    ON comments (plan_version_id, created_at DESC);

CREATE INDEX idx_comments_item_created_at
    ON comments (plan_item_id, created_at ASC);
