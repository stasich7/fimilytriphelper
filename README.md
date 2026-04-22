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
