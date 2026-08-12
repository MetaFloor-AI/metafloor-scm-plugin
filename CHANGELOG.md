# Changelog

All notable changes to the MetaFloor Supply Chain plugin.

## [0.2.3] - 2026-08-12
### Changed
- Agents are now **fully tool-enabled**: removed the `disallowedTools` restrictions from the 4 review agents.
  Tools must enable, not cripple - the agents stay analysis-only by their prompts + the gate, not by having
  tools taken away.
- Enriched each agent's `skills` grant so it is fully equipped for its role (e.g. `genealogy-tracer` now
  reaches TMS / quality / CRM expertise; `scope-auditor` reaches the recall + shortage workflows).

## [0.2.2] - 2026-08-12
### Fixed
- Manifest workflow count (15 -> 16, matching the 16 shipped workflows).
- `commands/scm-demo` pointed at a non-existent `tests/` path (now removed entirely, see Changed).
- Autonomy-dial **workflow-key mismatch** that silently fell back to `gated`: the example config keyed
  overrides as `workflows-<name>` while the runtime sets the bare `<name>`. Added a lint guard so it can't recur.
- Stray generation artifacts in the Veeva Vault QMS skill + references; added a repo-wide lint guard.
- **PreToolUse gate now fails closed if no Python interpreter is present** (was fail-open at the wiring level):
  a shell launcher emits a `deny` when `python3`/`python` is missing. Python 3 documented as a hard prerequisite.
- Clearer fail-closed gate error message; honest `registry.py` merge-semantics docstring (union is additive-only).
### Changed
- **Honest claims pass**: relabeled the 15 gate scenarios as gate-correctness self-checks (not a safety
  benchmark); scoped "safety" to the policy mechanism, not a proven outcome; knowledge-first README with a
  4-row safety-boundary table (`mcp__*` only; unmapped app ungoverned; Bash ungoverned; write-as-read residual).
- Removed `/scm-demo` and its mock connector (a synthetic-tool surface); the honest no-connector
  `scripts/demo.sh` remains.
### Added
- `.claude-plugin/marketplace.json` for third-party install; `homepage`/`repository` manifest metadata.
- Lint guards: manifest skill-root discovery, config-vs-skill workflow-key drift, stray artifacts.
- Deterministic hook-level tests for the declare-to-govern path and the documented write-as-read residual.

## [0.2.1] - 2026-08-11
- Public-release cleanup; consolidated `eval/tests`; dropped cruft.

## [0.2.0] - 2026-08-10
- Depth pass: 72 deep skills (55 vendor systems across 15 categories + 16 workflows + gating) plus the
  gate / autonomy-dial harness (core + config + commands + eval + tests + CI).

## [0.1.0] - 2026-08-10
- Phase 1 tool-agnostic supply-chain plugin: skills + a deterministic PreToolUse gate + native eval.
