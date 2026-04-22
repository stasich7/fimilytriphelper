# API Contract

## Base Path

`/api/v1`

## Endpoints

### `GET /healthz`

Purpose:
- health check for container and local development

Response:

```json
{
  "status": "ok"
}
```

### `GET /overview`

Purpose:
- return current trip overview for the dashboard

Response shape:

```json
{
  "trip": {
    "id": 1,
    "slug": "georgia-2026-08",
    "title": "Georgia Family Trip 2026"
  },
  "currentVersion": {
    "id": 1,
    "versionCode": "v1",
    "title": "Initial Plan"
  },
  "stats": {
    "items": 0,
    "comments": 0,
    "openComments": 0
  }
}
```

### `GET /versions`

Purpose:
- list all imported plan versions

Response shape:

```json
{
  "versions": [
    {
      "id": 1,
      "versionCode": "v1",
      "title": "Initial Plan",
      "createdAt": "2026-04-22T10:00:00Z"
    }
  ]
}
```

### `GET /versions/{versionID}`

Purpose:
- return one plan version with grouped items

Response shape:

```json
{
  "version": {
    "id": 1,
    "versionCode": "v1",
    "title": "Initial Plan"
  },
  "items": [
    {
      "id": 10,
      "stableKey": "route.option.a",
      "type": "route_option",
      "title": "Option A",
      "bodyMarkdown": "8 nights in Tbilisi and 8 nights in Batumi."
    }
  ]
}
```

### `GET /items/{itemID}`

Purpose:
- return one plan item with its comments

Response shape:

```json
{
  "item": {
    "id": 10,
    "stableKey": "route.option.a",
    "type": "route_option",
    "title": "Option A",
    "bodyMarkdown": "8 nights in Tbilisi and 8 nights in Batumi."
  },
  "comments": [
    {
      "id": 100,
      "author": "Anna",
      "body": "Can we stay in a calmer place near Batumi?",
      "createdAt": "2026-04-22T11:00:00Z"
    }
  ]
}
```

### `POST /comments`

Purpose:
- create a comment from a guest link context

Request shape:

```json
{
  "guestToken": "guest-token",
  "planVersionID": 1,
  "planItemID": 10,
  "body": "I like this option."
}
```

Notes:
- `planItemID` may be omitted for version-level comments.
- Guest token identifies the participant.

### `POST /imports/markdown`

Purpose:
- import a new markdown plan version

Request shape:

```json
{
  "source": "---\ntrip_id: georgia-2026-08\nversion_id: v2\n---\n..."
}
```

Response shape:

```json
{
  "versionID": 2,
  "versionCode": "v2",
  "importedItems": 12
}
```

### `GET /exports/codex?version={versionCode}`

Purpose:
- export structured comment summary for manual use in Codex

Response shape:

```json
{
  "versionCode": "v2",
  "markdown": "Trip: georgia-2026-08\nCurrent version: v2\n..."
}
```
