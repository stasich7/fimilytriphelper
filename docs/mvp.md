# MVP

## Goal

Build a small service that lets one trip owner share structured trip plan versions with family members and collect contextual comments.

## In Scope

- Single trip workspace
- Manual import of plan versions
- Personal guest links without registration
- Shared read access to the whole plan and all comments
- Comments attached to:
  - the whole plan version
  - a route option
  - a stay option
  - a transport option
  - an activity option
  - a general note
- Export of structured feedback for Codex
- Version-to-version item matching by stable IDs

## Out of Scope

- Notifications
- Realtime collaboration
- Attachments
- Voting and reactions
- Participant-created plan items
- Multiple trips
- AI integration inside the service

## Main User Flow

1. Owner imports a structured plan version.
2. Service parses stable item IDs and stores items.
3. Owner shares personal guest links.
4. Participants browse plan items and leave comments.
5. Owner exports open feedback for Codex.
6. Codex returns a new structured plan version.
7. Owner imports the new version.
8. Service matches existing items by stable IDs and preserves comment context.

## Screens

### 1. Trip Overview

- Current version
- Previous versions
- Open comment count
- Recent comments
- Import new version action
- Export feedback action

### 2. Plan Version View

- Version header
- Sections grouped by item type
- Item cards
- General comments for the version

### 3. Plan Item View

- Item title
- Item type
- Body content
- Metadata
- Comment thread

### 4. Guest Access Page

- Guest identity from personal link
- Read-only plan access
- Ability to add comments

## Functional Notes

- Each plan item must have a stable ID.
- Deleted items should be archived, not hard deleted.
- Comments remain attached to archived items.
- New version import must show unmatched or duplicate IDs as errors.
