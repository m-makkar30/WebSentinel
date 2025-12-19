# 1. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-05-31

## Context

WebSentinel makes several non-obvious engineering choices (noise-suppression
strategy, provider abstraction over NVIDIA NIM, the deliberate naive-vs-semantic
diff split for measurable metrics). We want a lightweight, durable record of
_why_ decisions were made, so reviewers and future-us can follow the reasoning
without archaeology through commit history.

## Decision

We will keep short Architecture Decision Records (ADRs) in `docs/adr/`, one file
per decision, numbered sequentially (`NNNN-title.md`), in the
[Michael Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
Each ADR captures context, the decision, and its consequences. Smaller,
tactical choices may instead be recorded inline in the relevant commit body.

## Consequences

- Meaningful decisions are discoverable in one place.
- ADRs are immutable once accepted; we supersede rather than rewrite them.
- This adds light overhead per significant decision — accepted as worthwhile.
