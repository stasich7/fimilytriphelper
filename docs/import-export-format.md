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

## Import Rules

- Front matter is required.
- `trip_id` must match the current trip.
- `version_id` must be unique.
- Every item heading must contain a stable key in square brackets.
- Duplicate stable keys inside one import are invalid.
- Unknown item type falls back to `note` or fails validation, depending on strict mode.

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
