#!/usr/bin/env python3
"""Kind-aware, tiered consistency validator for the plugin's skills + registries.

Why this exists: the fail-open + dead-refs + template drift a structural review
found all came from renames the test suite never caught. This lints the *class*
of defect so it can't recur silently.

Structure-aware (this repo): skills live nested under
  skills/platforms/<category>/<vendor>/SKILL.md   (expertise; visibility+risk = read-only)
  skills/business-workflows/<name>/SKILL.md        (workflow)
  skills/gating/<name>/SKILL.md                     (gating)
The skill class comes from the PATH, and the skill name is the leaf dir (clean, no
expertise-/workflows- prefix).

Two tiers:
  RED   — safety / correctness (blocks the build): frontmatter sanity, cross-reference
          resolution, workflow autonomy-label validity (dead vocabulary must stay dead),
          registry integrity (basename==app, one class per op).
  WARN  — cosmetic / structure. Printed; `--strict` promotes WARN to a non-zero exit.

Usage:
  python3 eval/lint_skills.py            # RED gates; WARN prints
  python3 eval/lint_skills.py --strict   # WARN also gates (merge/CI gate)
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
REGISTRIES = os.path.join(ROOT, "core", "registries")
TEMPLATE = "the skill authoring guide (expertise / workflow structure)"

# categories whose vendors are read-only (no destructive writes; a different, sanctioned
# Operations heading is correct, not a defect).
READONLY_CATS = {"visibility", "risk"}
ALLOWED_OPS_HEADINGS = {
    "## Operations: read / write / destructive",
    "## Operations: read / write / by data sensitivity and egress",
}
DIAL_LEVELS = ("observe", "suggest", "gated", "bounded-auto", "auto", "yolo")
DEAD_VOCAB = re.compile(r"(?m)(^\s*`?mode:\s|(?<![a-z])egress:|gate:\s*(Recommend|Execute)|"
                        r"Execute within limits|approver:\s*named|The harness enforces this\.)")
# residue guard: the prefixed forms must never reappear after the clean-name rename.
PREFIX_RESIDUE = re.compile(r"\b(?:expertise|workflows)-[a-z0-9-]+")
# a backticked kebab token that looks like a sibling skill reference (vendor/workflow stem).
BACKTICK = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`")
REF_STEMS = ("sap-", "oracle-", "manhattan-", "blueyonder-", "dynamics", "siemens-", "veeva",
             "labware", "mastercontrol", "kinaxis", "coupa", "ariba", "jaggaer", "ivalua", "gep",
             "icertis", "docusign", "netsuite", "infor", "anaplan", "o9", "korber", "fluent",
             "fourkites", "project44", "everstream", "resilinc", "interos", "ptc-", "descartes",
             "e2open", "onesource", "rockwell", "aveva", "ibm-maximo", "gts",
             "-reschedule", "-slip", "recall-", "shortage", "linedown", "match", "disposition",
             "cyclecount", "cycle-count", "rebalance", "positioning", "rfx", "atp-", "customs",
             "stock-split", "expedite", "forecast")


class Findings:
    def __init__(self):
        self.red, self.warn = [], []

    def r(self, path, rule, what, fix):
        self.red.append((path, rule, what, fix))

    def w(self, path, rule, what, fix):
        self.warn.append((path, rule, what, fix))


def discover():
    """name -> (abs SKILL.md path, rel path, class). Class from the folder layer."""
    out = {}
    plat = os.path.join(SKILLS, "platforms")
    if os.path.isdir(plat):
        for cat in sorted(os.listdir(plat)):
            catp = os.path.join(plat, cat)
            if not os.path.isdir(catp):
                continue
            kls = "expertise-readonly" if cat in READONLY_CATS else "expertise"
            for vend in sorted(os.listdir(catp)):
                sp = os.path.join(catp, vend, "SKILL.md")
                if os.path.isfile(sp):
                    out[vend] = (sp, f"skills/platforms/{cat}/{vend}/SKILL.md", kls)
    for layer, kls in (("business-workflows", "workflow"), ("gating", "gating")):
        lp = os.path.join(SKILLS, layer)
        if os.path.isdir(lp):
            for name in sorted(os.listdir(lp)):
                sp = os.path.join(lp, name, "SKILL.md")
                if os.path.isfile(sp):
                    out[name] = (sp, f"skills/{layer}/{name}/SKILL.md", kls)
    return out


def _frontmatter(text):
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end == -1:
        return None, None
    block = text[3:end]
    name = None
    m = re.search(r"(?m)^name:\s*(.+)$", block)
    if m:
        name = m.group(1).strip().strip('"').strip("'")
    dm = re.search(r"(?m)^description:\s*", block)
    desc = block[dm.end():].strip() if dm else ""
    desc = re.sub(r"\s+", " ", desc.strip().strip('"').strip("'"))
    return name, desc


def check(f: Findings, skills):
    real_names = set(skills)
    for name in sorted(skills):
        path, rel, kls = skills[name]
        text = open(path, encoding="utf-8").read()
        headings = re.findall(r"(?m)^## .+$", text)

        # --- RED: frontmatter sanity ---
        fmname, desc = _frontmatter(text)
        desc = desc or ""
        if fmname is None:
            f.r(rel, "frontmatter", "no valid --- frontmatter block", TEMPLATE)
        else:
            if fmname != name:
                f.r(rel, "frontmatter:name", f"name '{fmname}' != dir '{name}'", "make name == dir")
            if not re.fullmatch(r"[a-z0-9-]{1,64}", fmname):
                f.r(rel, "frontmatter:name", f"'{fmname}' not lowercase-hyphen <=64", "rename")
            if len(desc) > 1024:
                f.r(rel, "frontmatter:desc", f"description {len(desc)} chars > 1024", "shorten")
            if len(desc) < 40:
                f.w(rel, "frontmatter:desc", f"description only {len(desc)} chars — thin trigger surface", "enrich triggers")

        # --- RED: no prefixed-name residue (clean-name invariant) ---
        for tok in sorted(set(PREFIX_RESIDUE.findall(text))):
            f.r(rel, "prefix-residue", f"stale prefixed reference '{tok}'", "use the clean skill name")

        # --- RED: cross-reference resolution (backticked sibling-skill refs must resolve) ---
        for tok in sorted(set(BACKTICK.findall(text))):
            if tok == name or tok in real_names or tok.startswith("uc-"):
                continue  # uc-* are use-case ids cited in the body, not skill names
            if any(s in tok for s in REF_STEMS):
                f.r(rel, "dead-xref", f"refs '{tok}' which is not an installed skill",
                    "fix the name or remove the pointer")

        # --- RED: workflow autonomy-label validity ---
        if kls == "workflow":
            m = DEAD_VOCAB.search(text)
            if m:
                f.r(rel, "autonomy-vocab", f"deleted vocabulary present: '{m.group(0).strip()}'",
                    "re-express in dial terms (gated/bounded-auto ...)")
            aut = re.search(r"(?ms)^## Autonomy\b.*?(?=^## |\Z)", text)
            if not aut:
                f.r(rel, "autonomy-missing", "no ## Autonomy section", "add one (dial terms)")
            elif not any(lvl in aut.group(0) for lvl in DIAL_LEVELS):
                f.r(rel, "autonomy-level", "## Autonomy states no dial level", "name the L0-L5 level")
            # a workflow must carry the operating method (numbers) + a recovery playbook
            if not re.search(r"(?i)worked example", text):
                f.r(rel, "workflow-example", "no worked example", "add a worked example with real numbers")
            if not re.search(r"\d,\d{3}|\$\s?\d|\d+\s?%", text):
                f.r(rel, "workflow-numbers", "no concrete numbers in the method/example",
                    "show the computation with real numbers")
            if not re.search(r"(?i)failure|recover", text):
                f.r(rel, "workflow-recovery", "no failure -> recovery playbook",
                    "add a failure -> recovery section")

        # --- WARN: cosmetic / structure (kind-aware) ---
        if "—" in text:  # em-dash
            f.w(rel, "em-dash", "contains em-dash (house style is em-dash-free)", "use ' - ' or ','")
        if kls in ("expertise", "expertise-readonly", "gating"):
            if not re.search(r"(?m)^## Contents\b", text):
                f.w(rel, "toc", "no ## Contents table of contents", "add ## Contents")
            for h in [h for h in headings if h.startswith("## Operations")]:
                if h.strip() not in ALLOWED_OPS_HEADINGS:
                    f.w(rel, "ops-heading", f"non-canonical Operations heading: '{h.strip()}'",
                        "use a sanctioned form (see ALLOWED_OPS_HEADINGS)")
        if kls == "expertise":
            for need in ("## Operations", "## Guardrails"):
                if not any(h.startswith(need) for h in headings):
                    f.w(rel, "section", f"missing '{need}' section", TEMPLATE)
        if kls == "workflow":
            for need in ("## Systems", "## Flow"):
                if not any(h.startswith(need) for h in headings):
                    f.w(rel, "section", f"missing '{need}' section", TEMPLATE)


STRAY_TAGS = ("</content>", "</invoke>", "</function_calls>", "<function_calls>")


def check_stray_artifacts(f: Findings):
    """No leaked generation tool-call XML anywhere under skills/ (SKILL.md + references)."""
    for dirpath, _dirs, files in os.walk(SKILLS):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT)
            try:
                text = open(p, encoding="utf-8").read()
            except OSError:
                continue
            for tag in STRAY_TAGS:
                if tag in text:
                    f.r(rel, "stray-artifact", f"leaked generation tag '{tag}'", "strip the artifact")


def check_autonomy_configs(f: Findings, workflow_names):
    """Every override `workflow:` key in the shipped autonomy configs must resolve to an
    installed workflow skill — else the dial silently falls through to the default
    (the exact defect the DX review caught: `workflows-<x>` keys never matched `<x>`)."""
    key = re.compile(r"^\s*-?\s*workflow:\s*(.+?)\s*(?:#.*)?$")
    for cfgrel in ("config/autonomy.example.yaml", "config/autonomy.default.yaml"):
        p = os.path.join(ROOT, cfgrel)
        if not os.path.isfile(p):
            continue
        for line in open(p, encoding="utf-8"):
            m = key.match(line)
            if not m:
                continue
            wf = m.group(1).strip().strip('"').strip("'")
            if wf and wf not in workflow_names:
                f.r(cfgrel, "autonomy-workflow-key",
                    f"override workflow '{wf}' is not an installed workflow skill",
                    "use the bare workflow dir name (what /scm-run sets)")


def check_manifest_skill_roots(f: Findings):
    """Every skills[] root in plugin.json must resolve to a dir with >=1 <name>/SKILL.md.

    `claude plugin validate` checks manifest schema, NOT that skills load. A skills[]
    root that points at a dir with no <name>/SKILL.md under it means those skills
    silently vanish at runtime while validate still passes. This is the structural
    guard for the nested-category layout (skills/platforms/<cat> as multi-skill roots)."""
    manifest = os.path.join(ROOT, ".claude-plugin", "plugin.json")
    try:
        data = json.load(open(manifest, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        f.r(".claude-plugin/plugin.json", "manifest-json", f"unreadable: {e}", "fix JSON")
        return
    roots = data.get("skills")
    roots = [roots] if isinstance(roots, str) else (roots or [])
    for r in roots:
        p = os.path.join(ROOT, r.lstrip("./"))
        if not os.path.isdir(p):
            f.r(".claude-plugin/plugin.json", "skill-root",
                f"skills[] root '{r}' is not a directory", "fix the path")
            continue
        if not any(os.path.isfile(os.path.join(p, sub, "SKILL.md")) for sub in os.listdir(p)):
            f.r(".claude-plugin/plugin.json", "skill-root-empty",
                f"skills[] root '{r}' has no <name>/SKILL.md under it - those skills will not load",
                "point at a dir whose immediate children are skill dirs")


def check_agents(f: Findings):
    """Each agents/<name>.md must have frontmatter whose name matches the file and a real
    description (the field Claude Code uses to decide when to delegate)."""
    adir = os.path.join(ROOT, "agents")
    if not os.path.isdir(adir):
        return
    for fn in sorted(os.listdir(adir)):
        if not fn.endswith(".md"):
            continue
        rel = f"agents/{fn}"
        expected = fn[:-3]
        text = open(os.path.join(adir, fn), encoding="utf-8").read()
        nm, desc = _frontmatter(text)
        if nm is None:
            f.r(rel, "agent-frontmatter", "no valid --- frontmatter", "add name + description")
            continue
        if nm != expected:
            f.r(rel, "agent-name", f"name '{nm}' != file '{expected}'", "make name == filename")
        if len(desc or "") < 40:
            f.r(rel, "agent-desc", f"description only {len(desc or '')} chars", "describe role + when to invoke")


def check_registries(f: Findings):
    if not os.path.isdir(REGISTRIES):
        f.r("core/registries/", "registry-dir", "core/registries/ missing", "ship canonical manifests")
        return
    for fn in sorted(os.listdir(REGISTRIES)):
        if not fn.endswith(".json"):
            continue
        rel = f"core/registries/{fn}"
        app = fn[:-5]
        try:
            spec = json.load(open(os.path.join(REGISTRIES, fn), encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            f.r(rel, "registry-json", f"unparseable: {e}", "fix JSON")
            continue
        if spec.get("app") and spec["app"] != app:
            f.r(rel, "registry-basename", f"app '{spec['app']}' != filename '{app}'",
                "rename file or field so they match")
        sets = {k: set(spec.get(k, [])) for k in ("reads", "writes", "destructive", "outbound")}
        keys = list(sets)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                dup = sets[keys[i]] & sets[keys[j]]
                if dup:
                    f.r(rel, "registry-class", f"op in two classes {keys[i]}/{keys[j]}: {dup}",
                        "put each op in exactly one class")


def main():
    strict = "--strict" in sys.argv
    skills = discover()
    f = Findings()
    check(f, skills)
    check_stray_artifacts(f)
    workflow_names = {n for n, (_p, _r, kls) in skills.items() if kls == "workflow"}
    check_autonomy_configs(f, workflow_names)
    check_manifest_skill_roots(f)
    check_agents(f)
    check_registries(f)

    def show(rows, tag):
        for path, rule, what, fix in rows:
            print(f"{tag}  {path} — {rule} — {what} — fix: {fix}")

    show(f.red, "RED ")
    show(f.warn, "WARN")
    nreg = len([x for x in os.listdir(REGISTRIES) if x.endswith(".json")]) if os.path.isdir(REGISTRIES) else 0
    print(f"\n{len(skills)} skills, {nreg} registries — RED {len(f.red)}, WARN {len(f.warn)}"
          + ("  [--strict: WARN gates]" if strict else ""))
    if f.red:
        print("FAIL: correctness violations (RED) must be fixed.")
        return 1
    if strict and f.warn:
        print("FAIL (--strict): cosmetic violations (WARN) must be zero at merge.")
        return 1
    print("OK" if not f.warn else "OK (RED clean; WARN outstanding — clear before merge)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
