# VISION.md process — Rift

How [VISION.md](../VISION.md) is owned and changed. Agents and humans follow this so triage stays coherent.

## Who updates VISION.md

- **DoE** — eng-fit (process, shipping reality, repo hygiene).
- **CTO** — architecture alignment (boundaries, schemas, cross-repo risk).
- **100x Engineer / coding agents** — may draft updates; may not merge.
- **AJ (or designee)** — final merge authority.

## Dual gate (required before merge)

1. **DoE eng-fit** — COMMENT LGTM (or equivalent) that the change matches how we actually build.
2. **CTO architecture** — APPROVE / architecture LGTM that purpose, non-goals, and boundaries stay sound.

Shared-bot accounts that cannot APPROVE their own PRs still post COMMENT; a human or separate role provides the architecture gate.

## Draft PR required

- Changes to `VISION.md` land via **draft PR** first (docs-only preferred).
- **No silent edits to `main`** for vision text.
- Pair related README / triage / process doc updates in the same PR when they are one intent.

## Amend vs bump

- **Amend** — clarify wording, fix typos, tighten checklists without changing product scope or boundaries.
- **Bump / material revision** — new purpose, non-goals, architecture boundary, success metric, or Rift↔Judge contract. Call it out in the PR body; dual gate still required; consider notifying Judge owners if relation/schema text changes.

## Comments & labels only until human merge

Bots: comments and labels only. No merges from eng bots.

## Automated risk-delta comment

PRs may receive an informational VISION risk-delta comment (path → VISION heading links). See [TRIAGE.md](TRIAGE.md#vision-risk-delta-action). Still comments/labels only until human merge.

