# Architecture - metafloor-scm-plugin

> System structure, flow, and safety. Update only when these change.

## Overview
A Claude Code plugin that adds supply-chain capability on top of Claude Code, which owns the runtime,
agent loop, tools/MCP connections, permissions, and execution. The plugin contributes **expertise** (how
enterprise systems work + how supply-chain decisions are made) and **safety** (a deterministic gate over
consequential actions). It owns **no** tools, connectors, or integration layer — that keeps it portable
across whatever the customer connects.

## Components
- **Platform expertise skills** — `skills/platforms/<category>/<vendor>/SKILL.md`. Prose operator knowledge
  for one specific vendor system (object/state model, the vocabulary that bites, the read/write/destructive
  matrix, the gotchas as causal chains, edge states, recovery patterns, guardrails; deep material in
  `references/`). 15 categories: erp, planning, warehouse, transportation, oms, procurement, contracts,
  quality, mes, maintenance, customs, visibility, risk, plm, crm. No tool names.
- **Business-workflow skills** — `skills/business-workflows/<name>/SKILL.md`. One end-to-end supply-chain
  decision each (grounded in a real use case): the operating method (the computation with thresholds), a
  worked example with numbers, and a failure→recovery playbook. Defers each vendor HOW by name to the
  matching expertise skill.
- **Gating skill** — `skills/gating/supply-chain-gating/` — the cross-cutting read/write/destructive
  reference the workflows and gate share.
- **Specialist agents** — `agents/*.md` — independent subagents the main agent delegates to for a fresh,
  uncontaminated context (independence is the one thing a skill cannot give): `decision-reviewer` (red-teams a
  decision pre-action), `scope-auditor` (blast radius vs evidence), `genealogy-tracer` (lot genealogy +
  where-distributed map for recall / multi-tier), `cross-system-reconciler` (resolves system-vs-system
  disagreements). Each is self-contained and **fully tool-enabled** (no crippling restrictions); it stays
  analysis-only by its prompt (it advises, it does not execute on its own), and the gate enforces regardless of
  any agent's verdict. Safety comes from judgment + the gate, never from disabling the agent's tools.
- **Safety harness** — `core/` (stdlib, unit-tested): `registry.py` classifies a connector tool call;
  `autonomy.py` resolves the customer's dial; `gate.py` decides allow/ask/deny; `session.py` tracks the
  session blast-radius; `audit.py` records governed decisions. Wired via `hooks/pretooluse.py` on `mcp__*`.
- **Operator commands** — `commands/scm-*.md` backed by `scripts/scm_*.py` (run, audit, autonomy,
  connectors); `scm-replenish` reuses `scm_run.py`.
- **Eval** — `eval/`: `run.py` (P0 gate-safety scenarios), `lint_skills.py` (skill + registry consistency),
  `tests/` (harness unit tests). CI runs all three.

## Data flow (a consequential action)
```
Claude proposes an mcp__<app>__<op> tool call
  -> PreToolUse hook (hooks/pretooluse.py)
  -> registry.classify: read | write | destructive | outbound | unknown | non-connector
  -> autonomy.resolve: the customer's dial level for this workflow + app
  -> gate.decide -> allow | ask | deny   (reads pass; committing/destructive/outbound gate;
                                          unknown fails closed; bounded-auto enforces value/qty/count/currency limits)
  -> audit the governed decision; on auto-allow, add to the session blast-radius total
```
SessionStart injects a compact safety context so the model reasons in read/write/destructive terms even
before any tool call.

## Safety model
One model: **autonomy dial (L0 observe → L5 yolo, customer-set) × action class (read / write-reversible /
write-committing / destructive / outbound, taught by every expertise skill's matrix)**, enforced
deterministically in `core/gate.py`. The gate never consults the model's opinion, so a prompt-injected
"auto-approve" cannot move it. Precedence and defaults ship gated-only (a fresh install never
auto-approves); unknown consequential operations fail closed.

## Integrations
None owned by the plugin. It ships no MCP server, connector, adapter, or orchestrator. The customer maps
their real connector tool names in `.scm/connectors.json` (merged over `core/registries/<app>.json`, which
carry overridable defaults that fail closed). Live enforcement runs in the customer's environment on their
own connectors; the plugin provides the judgment and the deterministic mechanism.
