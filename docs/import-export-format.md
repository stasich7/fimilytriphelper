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
- If an item benefits from a visual cue, add one small image inside the same block.
- Images should use markdown form `![alt](https://example.com/image.jpg)`.
- All prices should be shown in USD in the imported plan content.
- When the source price is in GEL, convert it using the working planning rate `1 GEL = 0.37 USD`.
- Every price should clearly say what it covers: per person, per vehicle, per room, or for a specific guest composition.
- Stay items should include an approximate nightly price or total stay price when a reliable public source is available.
- Activity and transport items should include booking links and approximate prices when a reliable public source is available.

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
- Unknown item type falls back to `note` or fails validation, depending on strict mode.

## Change Discipline Across Versions

- An accepted plan should not be silently rewritten.
- Locations, stays, hotels, ordering, and other accepted plan decisions must only change in response to explicit comments or direct user instructions.
- Meaningful plan updates should be imported as a new version instead of overwriting the previous one.
- When the logical item stays the same across versions, keep the same `stable_key` so the change history remains visible.

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
