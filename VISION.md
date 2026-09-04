# Vision — Rift

## Product purpose
Rift (Reality Integrity & Fracture Tracker) triangulates portals, rifts, and abnormal-event reports onto geography. It ingests internet-shaped feeds (simulated today), user local data, and Judge forensic reports, then visualizes events, heat, and portal zones on an interactive map.

Aligned with Wold Labs’ first-principles north star: make sparse, noisy, high-strangeness signals inspectable and corroborable — not vibes, scores and sites you can audit.

## Non-goals
- Not a multimodal media analyzer (that is Judge).
- Not a social network, and not scraping behind login walls we do not own.
- Web scan is provider-shaped; “real-time X/news” connectors are roadmap, not current scope to fake as live.
- Not multi-user collaborative sessions yet (roadmap).
- Does not claim portals are proven; likelihoods are transparent scores from documented heuristics.

## Architecture boundaries (change only with review)
- Portal = *site*: seed-and-gather requires spatial radius + time window (no hop-chain continents).
- Fracture score: internet skepticism discount + cross-source corroboration rules in `rift/core/events.py` / detector.
- Judge bridge in `rift/integrations/judge.py` and first-class `judge` source on the map.
- Session persistence model (`rift_session.json`) and export shapes (JSON/GeoJSON/KML).
- Local Flask + Leaflet UI; keep `RIFT_NO_BROWSER` / port env contracts for CI and headless use.

## Success metrics
- pytest green on CI (3.10–3.12) with `RIFT_NO_BROWSER=1`.
- Portal re-runs replace overlays cleanly; bad coordinates skipped on ingest.
- EXPORT FOR JUDGE produces a real media-collection manifest; Judge report upload lands as `judge` pins.
- Scoring/clustering remain deterministic and tunable via documented module knobs.
- XSS-escaped popups/list items stay intact for map UI safety.

## Relation to Judge
Rift aggregates and clusters geography; Judge processes the recordings collected at high-fracture sites. Workflow: Rift → collect media → Judge analyze → upload report back to Rift. Schema or pin-format drift in either direction needs coordinated review across both repos.
