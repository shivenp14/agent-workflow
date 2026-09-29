# Task State: Simplify job flow

## Goal

Implement public Simplify job browsing, reviewed import, existing tailoring, employer handoff, and explicit submission tracking.

## Acceptance Criteria

- Browse/search/filter current public internship listings with source links and import progress.
- Extract or paste job description, edit listing details, choose a base resume, and confirm before creating an application.
- Duplicate source listings map to an existing application.
- Generated PDF is available before employer handoff; handoff alone never marks submitted.
- User explicitly confirms submission and the exact generated revision used.
- Targeted backend/frontend tests and build pass; important changes receive independent review.

## Decisions

- No save-for-later state in this version; application creation occurs after review.
- Existing application lifecycle statuses remain; browsing progress labels are derived.
- Source is public SimplifyJobs listings JSON, configurable for later lists.
- Existing scraper supplies best-effort text and always requires user review.

## Workstreams

### listing_feed

Status: completed

Owner: /root/listing_feed

Scope:
- backend/app/services/simplify_listings.py and its tests

Depends on: none

Outcome: Public JSON adapter returns 4,598 active entries from live feed; bounded fetch and cache single-flight behavior reviewed, including failure sharing.

Verification: 18 targeted tests passed; live default feed succeeded; independent review found no remaining issue.

### application_api

Status: completed

Owner: /root/application_api

Scope:
- backend/app/main.py and application API tests

Depends on: listing adapter contract (agreed)

Outcome: Browse, description, deduplicated import fields, URL fallback matching, newest-first ordering, and derived progress endpoints implemented.

Verification: 16 API/lifecycle tests passed; full backend suite 164 passed; independent review finding corrected.

### frontend_flow

Status: completed

Owner: /root/frontend_flow

Scope:
- src/main.jsx, src/application-workflows.jsx, src/api.js, src/styles.css, UI tests

Depends on: API contract (agreed)

Outcome: Jobs browse/review/import/handoff UI implemented with exact PDF attachment link, explicit submission confirmation, and closed-state label.

Verification: Full UI suite 27 passed, 1 platform-specific skip; build passed; independent review findings corrected.

### integration_review

Status: completed

Owner: /root

Scope:
- cross-component verification, browser inspection, independent review

Depends on: implementation workstreams

Outcome: Live feed returned 4,598 active listings during verification. Independent final review found no remaining substantive issues after terminal-status correction.

Verification: Full backend suite 165 passed; full UI suite 27 passed, 1 skipped; production frontend build passed.

## Known Risks

- Public feed availability and season changes.
- Employer description retrieval remains best-effort.

## Next Actions

1. No remaining implementation work for the agreed version.
