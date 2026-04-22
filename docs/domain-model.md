# Domain Model

## Entities

### Trip

Represents the single active trip in the system.

Fields:
- `id`
- `slug`
- `title`
- `status`
- `created_at`
- `updated_at`

### PlanVersion

Represents one imported version of the trip plan.

Fields:
- `id`
- `trip_id`
- `version_code`
- `title`
- `source_format`
- `raw_source`
- `created_at`

### PlanItem

Represents one structured item inside a plan version.

Fields:
- `id`
- `trip_id`
- `plan_version_id`
- `stable_key`
- `type`
- `title`
- `body_markdown`
- `metadata_json`
- `status`
- `replaces_item_id`
- `created_at`
- `updated_at`

Suggested item types:
- `route_option`
- `stay`
- `transport`
- `activity`
- `note`

Suggested item statuses:
- `active`
- `archived`

### Participant

Represents one invited commenter.

Fields:
- `id`
- `trip_id`
- `display_name`
- `guest_token`
- `created_at`
- `last_seen_at`

### Comment

Represents a participant comment.

Fields:
- `id`
- `trip_id`
- `plan_version_id`
- `plan_item_id`
- `participant_id`
- `body`
- `created_at`

Rules:
- `plan_item_id` may be null for version-level general comments.
- Comments are immutable in MVP except optional owner-side hide/delete later.

## Matching Rules

- `stable_key` is the main cross-version identity.
- If a new import contains the same `stable_key`, it is treated as the same logical item.
- If a logical item changes substantially but should preserve discussion context, keep the same `stable_key`.
- If a truly new alternative appears, create a new `stable_key`.
- If one item replaces another, store `replaces_item_id` when useful.

## Example Stable Keys

- `route.option.a`
- `stay.tbilisi.aparthotel-1`
- `stay.batumi.chakvi.hotel-1`
- `transport.train.tbilisi-batumi`
- `activity.kazbegi.daytrip`
