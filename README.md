# FamilyTripHelper

FamilyTripHelper is a small self-hosted web service for discussing one family trip plan.

The service is designed for a manual Codex workflow:
- Codex prepares structured trip plan variants.
- The owner imports a new plan version into the service.
- Family members open personal guest links and leave comments.
- The service exports structured feedback back to Codex without losing context.

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
