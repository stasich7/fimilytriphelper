# Hotel Search Agent

Hotel search agent is external helper for FamilyTripHelper workflow.

Why external:
- current product scope keeps AI automation outside web service;
- existing import/export flow already fits generated hotel stay candidates;
- external agent keeps backend, frontend, and DB unchanged.

Agent location:
- `agents/hotel_search/`

Current scaffold includes:
- request schema;
- parallel orchestrator by `area x aggregator`;
- normalization, stay-type classification, deduplication, ranking;
- soft area profiles instead of strict polygons;
- scoring for public transport, sleeping places, price, amenities, and risk flags;
- grouped shortlist by area and accommodation type;
- markdown export compatible with current importer;
- browser-driven `booking` adapter path through Selenium;
- explicit unavailable error for `ozon_travel` until dedicated browser path is added.
- hard filtering by `price.max` as a nightly family budget cap before final shortlist generation.

Planned next step:
- improve Booking extraction depth and primary image capture.
- add `ozon_travel` browser flow with same normalized output after Booking-only flow is stable.
