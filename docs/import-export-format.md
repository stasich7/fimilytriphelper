# Import / Export Format

## Goal

Keep manual exchange between Codex and FamilyTripHelper structured enough to preserve context between versions.

## Preferred Import Format

Markdown with front matter and explicit item IDs.

Example:

```md
---
trip_id: georgia-2026-08
version_id: v1
title: Georgia Trip Plan
---

## [route.option.a] Option A
Type: route_option

8 nights in Tbilisi and 8 nights in Batumi.

## [stay.tbilisi.aparthotel-1] Tbilisi Aparthotel
Type: stay
Area: Mtatsminda

Pros:
- quiet
- kitchen
- family friendly

Cons:
- mid-range price

## [transport.train.tbilisi-batumi] Tbilisi to Batumi Train
Type: transport

Pros:
- easier than a long road transfer
- comfortable for children

Cons:
- tickets should be booked in advance
```

## Content Style Guidance

- Imported plan content should read naturally for family members.
- Avoid the Russian term `база` in plan titles and bodies.
- Prefer `проживание`, `размещение`, and `локация`.
- Put links directly inside the item block they describe.
- Prefer markdown links in the form `[label](https://example.com)` instead of bare URLs.
- Bare URLs are allowed, but markdown links with a readable label are the preferred import format.
- Use `[label](item:stable_key)` for internal links to another plan item in the same version.
- If an item benefits from a visual cue, add one small image inside the same block.
- Images should use markdown form `![alt](https://example.com/image.jpg)` for external images or `![alt](/maps/day.png)` for local generated route maps.
- Route map images should be published as PNG assets, not SVG assets. The current route-map target size is `1600x1000`; route maps should use a real map tile basemap with route overlays.
- All prices should be shown in USD in the imported plan content.
- When the source price is in GEL, convert it using the working planning rate `1 GEL = 0.37 USD`.
- Every price should clearly say what it covers: per person, per vehicle, per room, or for a specific guest composition.
- Stay items should include an approximate nightly price or total stay price when a reliable public source is available.
- Activity and transport items should include booking links and approximate prices when a reliable public source is available.

## Accommodation Fill Rules

- Accommodation search results for publication must be merged into the canonical full plan snapshot, not saved as a separate publication summary file.
- The only current publication source is `context/georgia-trip-plan-current.md`; each accepted publication version must also be archived as a full snapshot in `context/versions/vX.md`.
- Replace outdated `stay.*.option.*` candidates inside the plan when the user asks to update accommodation options.
- Keep existing area blocks when they still describe the intended geography; add a new area block only when a selected accommodation is outside existing areas.
- Use stable keys in the form `stay.<city>.option.<hotel-slug>` for new accommodation candidates.
- If a logical accommodation candidate continues across versions, keep its stable key.
- Each live-checked accommodation option should state aggregator, search date, stay dates, guest composition, room count, required sleeping places, room configuration, availability status, total USD price, nightly USD price, and important risk notes.
- Use USD for all accommodation prices. If the source currency differs, show USD in the plan and keep original currency only in internal search artifacts.
- For Booking results, use a stable hotel page link in the published plan instead of a long volatile search-result URL.
- Add the first object image only when the agent result or another reliable public source provides a direct image URL. Do not invent or scrape an image URL manually just to fill the field.
- If beds, cancellation, taxes, or availability are not fully confirmed by the agent, say that explicitly inside the accommodation block.

Example with a link and image:

```md
## [stay.tbilisi.option.example] Тбилиси: семейный апарт-отель
Type: stay
Area: Sololaki

Удобный вариант для проживания в спокойной центральной локации.

Ссылка:
https://www.booking.com/

Изображение:
![Вид апарт-отеля](https://example.com/hotel.jpg)
```

## Link and Image Formatting Rules

- Preferred external link format: `[label](https://example.com)`.
- Allowed fallback format: plain `https://example.com` URL when a short label is not available yet.
- Place each link inside the item block it supports, not in a detached common section.
- Use human-readable labels such as `Сайт отеля`, `Booking`, `Описание`, `Карта`, `Официальная страница`.
- Images should use markdown format `![alt](https://example.com/image.jpg)`.
- In the UI, external links open in a new tab.

## Price Formatting Rules

- Preferred format: `Ориентир по цене: около $98 за ночь`.
- If a source gives a vehicle price, keep that meaning explicit: `около $65 за автомобиль`.
- If a source gives a group tour price, keep that meaning explicit: `около $30 за взрослого` or `около $160 за группу`.
- If the public source does not expose exact stay dates in crawlable form, mark the amount as an approximate planning reference instead of presenting it as a final confirmed booking total.

## Import Rules

- Front matter is required.
- `trip_id` must match the current trip.
- `version_id` must be unique.
- `version_id` must use the compact format `vX`, for example `v1`, `v2`, `v3`.
- Numbering starts from `v1`.
- Every item heading must contain a stable key in square brackets.
- Duplicate stable keys inside one import are invalid.
- Supported publication item types are `route_option`, `day_plan`, `stay`, `transport`, `activity`, and `note`.
- Use `day_plan` for separate day-by-day itinerary cards shown in the `Ритм по дням` UI section.
- Unknown item type falls back to `note` or fails validation, depending on strict mode.

## Change Discipline Across Versions

- An accepted plan should not be silently rewritten.
- Locations, stays, hotels, ordering, and other accepted plan decisions must only change in response to explicit comments or direct user instructions.
- Meaningful plan updates should be imported as a new version instead of overwriting the previous one.
- When the logical item stays the same across versions, keep the same `stable_key` so the change history remains visible.

## Canonical File Workflow

- Keep one canonical markdown file in the repository for the current working plan.
- Keep one full snapshot markdown file per accepted version in a version archive.
- The canonical file should mirror the latest accepted version.
- When a comment targets a specific `stable_key`, edit only that block in the next version unless the owner explicitly requests broader plan changes.
- All other blocks should be carried forward unchanged.
- Service imports should always be generated from a full version snapshot, not from a partial patch.

## Comment History Workflow

- Keep comment history in repository files alongside the plan snapshots.
- Do not delete comments after a new version is released.
- Comments should have a status such as `open`, `addressed`, or `rejected`.
- Addressed comments should include `resolved_in_version`.
- When a comment targets a specific `stable_key`, keep that association in the comment archive.
- Comment history should remain readable as a timeline of discussion and decisions.

Example:

```md
### stable_key=activity.mtskheta.daytrip
title=Мцхета и Джвари

1. author=Стас
   created_at=2026-04-23T10:16:20Z
   status=addressed
   resolved_in_version=v3
   text=Интересно было бы узнать как сюда добраться без экскурсии. Стоимость, расстояние, как вернуться обратно, где походить.
```

## Export Format for Codex

Markdown summary with explicit references to stable keys.

Example:

```md
Trip: georgia-2026-08
Current version: v1

Open comments:
1. target_id=stay.tbilisi.aparthotel-1
   author=Anna
   text=Looks expensive. Do we have a quieter and cheaper alternative?

2. target_id=route.option.a
   author=Ivan
   text=Can we stay near Batumi but in a calmer place?

3. target_id=transport.train.tbilisi-batumi
   author=Olga
   text=The train option looks better than a long car ride.
```

## Suggested Validation

- Front matter presence
- Valid trip ID
- Unique version ID
- Unique stable keys
- Supported item types
- Non-empty titles
- Non-empty content for major item types
