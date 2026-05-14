# ADR-001: Optimize the repository for AI-operated audio asset production

- Status: Accepted
- Date: 2026-05-14

## Context

The repository's main value is generating assets for other repositories, not shipping itself as a polished product. Future work will often be done by AI agents operating through GitHub/Copilot workflows.

## Decision

Treat the repository as an AI-first audio asset factory. Prefer explicit docs, continuity files, stable naming, and small resumable PRs over compactness or architectural elegance.

## Consequences

- The repo may contain many documentation files.
- Agents are expected to update memory docs when they change behavior or process.
- Downstream usefulness is prioritized over internal minimalism.
- Persistent handoff quality becomes part of normal development, not optional overhead.
