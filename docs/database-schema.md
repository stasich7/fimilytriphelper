# Database Schema

## Overview

The database schema is intentionally small and centered around one active trip.

## Tables

### `trips`

- `id BIGSERIAL PRIMARY KEY`
- `singleton_key TEXT NOT NULL UNIQUE`
- `slug TEXT NOT NULL UNIQUE`
- `title TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'active'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

`singleton_key` allows the application to enforce one active trip row.

### `plan_versions`

- `id BIGSERIAL PRIMARY KEY`
- `trip_id BIGINT NOT NULL REFERENCES trips(id)`
- `version_code TEXT NOT NULL`
- `title TEXT NOT NULL`
- `source_format TEXT NOT NULL DEFAULT 'markdown'`
- `raw_source TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Constraints:
- `UNIQUE (trip_id, version_code)`

### `plan_items`

- `id BIGSERIAL PRIMARY KEY`
- `trip_id BIGINT NOT NULL REFERENCES trips(id)`
- `plan_version_id BIGINT NOT NULL REFERENCES plan_versions(id)`
- `stable_key TEXT NOT NULL`
- `type TEXT NOT NULL`
- `title TEXT NOT NULL`
- `body_markdown TEXT NOT NULL`
- `metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb`
- `status TEXT NOT NULL DEFAULT 'active'`
- `replaces_item_id BIGINT NULL REFERENCES plan_items(id)`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Constraints:
- `UNIQUE (plan_version_id, stable_key)`

Indexes:
- `(trip_id, stable_key)`
- `(plan_version_id, type)`

### `participants`

- `id BIGSERIAL PRIMARY KEY`
- `trip_id BIGINT NOT NULL REFERENCES trips(id)`
- `display_name TEXT NOT NULL`
- `guest_token TEXT NOT NULL UNIQUE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `last_seen_at TIMESTAMPTZ NULL`

### `comments`

- `id BIGSERIAL PRIMARY KEY`
- `trip_id BIGINT NOT NULL REFERENCES trips(id)`
- `plan_version_id BIGINT NOT NULL REFERENCES plan_versions(id)`
- `plan_item_id BIGINT NULL REFERENCES plan_items(id)`
- `participant_id BIGINT NOT NULL REFERENCES participants(id)`
- `body TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:
- `(plan_version_id, created_at DESC)`
- `(plan_item_id, created_at ASC)`

## Comment Context Across Versions

Comments are stored against the concrete item row in the version where they were written.

To preserve context across imports:
- every item keeps a stable key;
- the UI can aggregate historic comments by stable key;
- removed items are archived, not deleted.
