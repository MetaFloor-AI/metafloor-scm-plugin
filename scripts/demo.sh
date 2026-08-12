#!/usr/bin/env bash
# One-command demo: watch the plugin route a real decision and reason safely.
# No tools are executed and nothing is faked — the plugin only supplies knowledge + safety policy.
set -uo pipefail
cd "$(dirname "$0")/.."

echo "== MetaFloor Supply-Chain plugin demo =="
echo "Scenario: a buyer wants to cancel a whole PO, but part of it is already received."
echo "Expected: the sap-mm + supply-chain-gating skills engage; the agent separates received from"
echo "open quantity, refuses to over-cancel, and flags the change as L4 needing recorded approval."
echo

PROMPT='Operating in SAP. The buyer says: cancel all 10,000 units of PO-12831. State for PO-12831: ordered 10,000, goods received 4,000. How do you handle it? State what is cancellable, the risk level (L0-L5), and whether human approval is required. Do not fabricate any state beyond what is given.'

echo "--- agent output ---"
echo "$PROMPT" | claude -p --plugin-dir . 2>&1 | sed 's/^/  /'
