# Product Rules

## Product Scope

- The service supports one trip only.
- If another trip is needed later, the project can be re-initialized.

## Access Model

- The owner manages plan imports and exports.
- Other participants use personal guest links.
- Guests do not register and do not need passwords.
- All participants can see the full plan and all comments.

## Collaboration Model

- Participants can only leave comments.
- Participants cannot create or edit plan items directly.
- New participant wishes or ideas may appear through comments and can be reflected in the next imported version.

## Versioning Rules

- The owner imports complete plan versions.
- Each plan item must have a stable key.
- Cross-version matching is based on the stable key.
- Removed items must be archived instead of deleted.

## Non-Goals

- No notifications
- No reactions or voting
- No attachments
- No multi-trip support
- No AI automation inside the service
