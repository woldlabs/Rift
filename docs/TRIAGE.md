# Triage rubric — Rift

Use this checklist when reviewing PRs or issues against [VISION.md](../VISION.md). Prefer purpose fit, non-goals, architecture boundaries, and tests over nits.

## Against VISION.md

- [ ] **Purpose fit** — Does the change serve geographic triangulation of abnormal-event reports (internet-shaped feeds, local data, Judge reports) onto an inspectable map?
- [ ] **Non-goals** — Does it avoid: multimodal media analysis (Judge’s job), social-network features, scraping behind login walls we don’t own, faking live X/news feeds, claiming portals are proven?
- [ ] **Architecture boundaries** — Any change to portal-as-site clustering (radius + time window), fracture/corroboration rules, `rift/integrations/judge.py` / `judge` source, session persistence / JSON·GeoJSON·KML exports, or Flask+Leaflet / `RIFT_NO_BROWSER` contracts? If yes → needs explicit review.
- [ ] **Success metrics** — Still green: CI pytest (3.10–3.12) with `RIFT_NO_BROWSER=1`, portal overlay replace, EXPORT FOR JUDGE manifest + Judge import pins, deterministic scoring knobs, XSS-safe map UI.
- [ ] **Cross-repo (Rift ↔ Judge)** — Does this touch Judge report import, pin format, or export manifest shape? If yes, flag Judge follow-up risk before merge.

## PR quality (after vision fit)

- [ ] Clear **testable goal** in title/body.
- [ ] Risk called out (data loss, secrets, XSS, blast radius) or N/A.
- [ ] Tests added/updated when behavior changes.
- [ ] Docs-only changes stay docs-only.

## Labels (suggested)

`needs-vision-review` · `docs` · `schema-risk` (if Judge bridge) · `architecture`
