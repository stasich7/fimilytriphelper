# FamilyTripHelper

FamilyTripHelper is a small self-hosted web service for discussing one family trip plan.

The service is designed for a manual Codex workflow:
- Codex prepares structured trip plan variants.
- The owner imports a new plan version into the service.
- Family members open personal guest links and leave comments.
- The service exports structured feedback back to Codex without losing context.

## Creating guest links

Create a personal guest link from the running app container:

```bash
docker exec family-trip-helper-app family-trip-helper create-guest --name "Anna" --base-url https://familytrip.stasich7.ru
```

Production examples:

```bash
docker exec family-trip-helper-app family-trip-helper create-guest --name "Anna" --base-url https://familytrip.stasich7.ru
docker exec family-trip-helper-app family-trip-helper create-guest --name "Ivan" --base-url https://familytrip.stasich7.ru
docker exec family-trip-helper-app family-trip-helper create-guest --name "Olga" --base-url https://familytrip.stasich7.ru
```

Arguments:
- `--name` sets the display name that will be shown in the UI and in comments.
- `--base-url` defines the public base address that will be used in the generated link.

The command prints a ready-to-share personal guest URL.

## Import content style

When preparing a new plan version for import:
- prefer markdown links in the form `[label](https://example.com)`;
- plain URLs are allowed, but markdown links with readable labels are preferred;
- add images in markdown form `![alt](https://example.com/image.jpg)` when a place benefits from a small visual cue;
- links and images should stay inside the same item block they describe.

## Publishing plan images

The image publishing commands create `.venv` and install Python dependencies automatically.

You can publish external images to the local S3-compatible storage:

```bash
AWS_ACCESS_KEY_ID=family_trip_helper \
AWS_SECRET_ACCESS_KEY=family_trip_helper_storage \
make publish-images-local
```

Copy all image objects referenced by the published markdown from local storage to production storage:

```bash
LOCAL_AWS_ACCESS_KEY_ID=family_trip_helper \
LOCAL_AWS_SECRET_ACCESS_KEY=family_trip_helper_storage \
PROD_AWS_ACCESS_KEY_ID=... \
PROD_AWS_SECRET_ACCESS_KEY=... \
make sync-images-prod
```

The sync command reads `context/georgia-trip-plan-current.published.md`, copies only referenced objects from `http://127.0.0.1:19000` to `https://storage.familytrip.stasich7.ru`, and rewrites the markdown image URLs to the production storage host.

Verify that the published markdown no longer contains localhost image URLs before importing it to production:

```bash
make verify-prod-published-images
```

If you want to use a different Python environment, override `IMAGE_PYTHON`:

```bash
IMAGE_PYTHON=/path/to/python make sync-images-prod
```

Local development example:

```bash
docker exec family-trip-helper-backend family-trip-helper create-guest --name "Smoke Test Guest" --base-url http://127.0.0.1
```

Current scope:
- one trip only;
- guest links without registration;
- comments only;
- all participants see all comments;
- no direct participant edits to plan content.

Project structure:
- `docs/` product and technical documents
- `context/` working context for the current trip
- `rules/` product rules and constraints
- `skills/` local helper notes and future skills
- `frontend/` web UI
- `backend/` API and import/export logic
