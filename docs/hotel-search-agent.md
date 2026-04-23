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
- normalization, deduplication, ranking;
- markdown export compatible with current importer;
- browser-driven `booking` adapter path through Selenium + Safari;
- explicit unavailable error for `ozon_travel` until dedicated browser path is added.

Planned next step:
- enable Safari WebDriver locally and verify live `booking` extraction on real dates.
- add `ozon_travel` browser flow with same normalized output.
