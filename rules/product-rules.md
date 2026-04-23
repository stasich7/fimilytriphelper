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
- Imported version codes must use the compact format `vX` where `X` is a positive integer.
- Numbering starts from `v1` and continues as `v2`, `v3`, `v4`, and so on.
- Each plan item must have a stable key.
- Cross-version matching is based on the stable key.
- Removed items must be archived instead of deleted.

## Plan Content Style

- Trip plan content should use reader-friendly language instead of internal planning jargon.
- Avoid the Russian term `база` in imported plan content.
- Prefer the Russian terms `проживание`, `размещение`, and `локация` when describing where people stay.
- Links should be placed inside the same item block they refer to.
- Prefer markdown links in the form `[label](https://example.com)` instead of bare URLs.
- Bare URLs are allowed, but markdown links with a readable label are the project standard.
- External links are expected to open in a new browser tab in the UI.
- Images should be added in markdown form `![alt](https://example.com/image.jpg)`.
- Stay and activity items may include one small illustrative image when it helps participants recognize the place faster.
- All prices in imported plan content should be shown in USD.
- When the source price is in GEL, convert it using the working planning rate `1 GEL = 0.37 USD`.
- Every price should explicitly state the pricing scope: for example per person, per vehicle, per room, or for a specific guest composition.
- Stay items should include an approximate nightly price or total stay price when a reliable public source is available.
- Activity and transport items should include booking links and approximate prices when a reliable public source is available.

## Plan Change Discipline

- Codex prepares an initial plan version.
- The owner and participants review the plan and leave comments.
- Codex updates the plan only in response to explicit comments or direct user instructions.
- Codex must not change locations, stays, hotels, ordering, or other accepted plan choices on its own initiative.
- Every meaningful update must be delivered as a new plan version so the change history remains traceable.
- Existing items should keep their stable keys whenever the logical item remains the same across versions.

## Non-Goals

- No notifications
- No reactions or voting
- No attachments
- No multi-trip support
- No AI automation inside the service
