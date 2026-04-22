# Project Context

## Purpose

FamilyTripHelper is a small self-hosted web service for one shared family trip.

The service is used in a manual Codex workflow:
- Codex prepares new trip plan versions outside the service.
- The owner imports a new version into the service.
- Family members open personal guest links and leave comments.
- The owner exports collected comments back to Codex.

## Product boundaries

- one trip only
- guest links without registration
- comments only
- all participants see all comments
- participants do not edit imported plan content directly

## Main entities

- `Trip`
- `PlanVersion`
- `PlanItem`
- `Participant`
- `Comment`

Important identity rule:
- `stable_key` connects the same logical item across different versions

## Current stack

- backend: Go
- frontend: Vue 3 + Vite
- database: PostgreSQL
- runtime: Docker Compose

## Runtime shape

- the backend serves both API and frontend static files
- PostgreSQL is used as the persistent store
- the local dev stack is started from the repo root with `docker compose`
- the production deployment uses `deploy/docker-compose.prod.yml`

## Routing

Owner routes:
- `/`
- `/versions/:versionId`
- `/items/:itemId`
- `/tools`

Guest routes:
- `/guest/:guestToken`
- `/guest/:guestToken/versions/:versionId`
- `/guest/:guestToken/items/:itemId`

## Guest links

Guest links are created from the running container with `create-guest`.

The command requires:
- `--name`
- `--base-url`

The service returns a ready-to-share personal URL.

## Import flow

Import is available from the owner tools page.

Backend endpoint:
- `POST /api/v1/imports/markdown`

Source format:
- structured markdown with front matter
- required fields include trip and version metadata
- each item must have a `stable_key`

Import behavior:
- creates a new immutable `PlanVersion`
- stores all `PlanItem` records for that version
- rejects duplicate `version_id`

## Export flow

Export is available from the owner tools page.

Backend endpoint:
- `GET /api/v1/exports/codex?versionId=<id>`

Export result:
- markdown text
- version-level comments first
- item-level comments grouped by `stable_key`
- each comment includes author and timestamp

This export format is intended to be copied directly into Codex.

## UI notes

- the overview page shows the trip hero image and the current version
- internal pages use a header with the `FamilyTrip-v4.png` background
- guest mode shows `Комментарии от имени <name>`
- version pages contain item cards and a separate block for general version comments
- the tools page provides import and export operations for the owner

## Deployment notes

Production assumptions:
- nginx runs on the host
- the app container is published on `127.0.0.1:18080`
- nginx proxies public traffic to that local port
- PostgreSQL is not published publicly

See also:
- `docs/deploy.md`

## Important current state

- the project currently contains a test import of `v2`
- the database may also contain smoke-test comments from local verification

If needed, these test records can be cleaned separately.
