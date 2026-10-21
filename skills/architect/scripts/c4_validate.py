#!/usr/bin/env python3
"""Mechanical checks of an architecture.json against references/quality.md.

    py c4_validate.py <model>

Covers the rules a script can decide (structure, references, counts, evidence format). Rules that
need judgement (is a `why` convincing, does an evidence range carry its statement) stay with the
reader. Exit 1 when any ERROR is found. Output: JSON {errors, warnings, info}, each a list of
{rule, msg}. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESOURCE = re.compile(r"^repo://[^#]+#L(\d+)-L(\d+)$")
DERIVED_VIEWS = ("repo://doc/architecture/", "repo://openwiki/")
EVIDENCE_KINDS = ("defines", "registers", "calls", "configures", "tests")
# Ids end up in HTML attributes and JS strings of the rendered page: plain tokens only.
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
REQUIRED = {"element": ("id", "type", "name"), "relationship": ("from", "to"),
            "snippet": ("id", "title", "code", "parentElement"), "sequence": ("id", "title"),
            "group": ("name", "elementIds"), "decision": ("id",), "nfr": ("id",), "fr": ("id",)}
LIMITS = {"context": ("V-01", 12), "container": ("V-02", 18), "component": ("V-03", 15)}


class Report:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.info: list[dict] = []

    def error(self, rule: str, msg: str) -> None:
        self.errors.append({"rule": rule, "msg": msg})

    def warn(self, rule: str, msg: str) -> None:
        self.warnings.append({"rule": rule, "msg": msg})

    def note(self, rule: str, msg: str) -> None:
        self.info.append({"rule": rule, "msg": msg})

    def as_dict(self) -> dict:
        return {"errors": self.errors, "warnings": self.warnings, "info": self.info}


def _levels(m: dict) -> dict[str, dict]:
    levels = {"context": m.get("context") or {"elements": [], "relationships": []}}
    for k, v in (m.get("containers") or {}).items():
        levels[f"container:{k}"] = v
    for k, v in (m.get("components") or {}).items():
        levels[f"component:{k}"] = v
    return levels


def _evidence_resources(obj: dict) -> list[str]:
    return [e if isinstance(e, str) else e.get("resource", "") for e in obj.get("evidence") or []]


def _check_structure(m: dict, r: Report) -> dict[str, tuple[str, dict]]:
    levels = _levels(m)
    ids: dict[str, tuple[str, dict]] = {}
    for name, level in levels.items():
        for e in level.get("elements", []):
            if e["id"] in ids:
                r.error("S-01", f"duplicate id {e['id']}")
            ids[e["id"]] = (name, e)
    for name, level in levels.items():
        local = {e["id"] for e in level.get("elements", [])}
        connected = set()
        for rel in level.get("relationships", []):
            connected |= {rel["from"], rel["to"]}
            if rel["from"] not in local:
                r.error("S-02", f"{name}: from {rel['from']} not in this level")
            if rel["to"] not in local:
                r.error("S-03", f"{name}: to {rel['to']} not in this level")
            if rel["from"] == rel["to"]:
                r.error("S-06", f"{name}: self reference {rel['from']}")
            if not isinstance(rel.get("async"), bool):
                r.error("S-09", f"{name}: async is not boolean on '{rel.get('label')}'")
            if not rel.get("label"):
                r.error("C-06", f"{name}: relationship {rel['from']}->{rel['to']} without label")
            elif len(rel["label"]) > 40:
                r.note("V-05", f"label longer than 40: {rel['label']}")
            if rel.get("async") is True and not rel.get("payload"):
                r.warn("W-01", f"async relationship without payload: {rel.get('label')}")
            if rel.get("relatedDecision") and not rel.get("why"):
                r.warn("W-03", f"relationship with decision but no why: {rel.get('label')}")
        kind = name.split(":")[0]
        rule, limit = LIMITS[kind]
        if len(level.get("elements", [])) > limit:
            r.warn(rule, f"{name}: {len(level['elements'])} elements (max {limit})")
        for e in level.get("elements", []):
            if e["id"] not in connected:
                r.warn("V-07", f"isolated element {e['id']}")
            if len(e.get("name", "")) > 30:
                r.note("V-04", f"name longer than 30: {e['name']}")
            dd = e.get("drillDown")
            if dd and ":" in dd:
                target_kind, key = dd.split(":", 1)
                if key not in (m.get("containers" if target_kind == "container" else "components") or {}):
                    r.error("S-04", f"{e['id']}: drillDown {dd} has no view")
    for key in m.get("components") or {}:
        if key not in ids:
            r.error("S-07", f"component view {key} has no container element")
    for key in m.get("containers") or {}:
        if key != "_default" and (key not in ids or ids[key][1].get("type") != "system"):
            r.error("S-13", f"container view {key} has no system element")
    if m.get("version") not in ("2.2", "2.3"):
        r.error("S-08", f"version {m.get('version')} (expected 2.2 or 2.3)")
    return ids


def _check_requirements(m: dict, ids: dict, r: Report) -> None:
    frs = {f["id"] for f in m.get("functionalRequirements", [])}
    nfrs = {n["id"] for n in m.get("nfrs", [])}
    dds = {d["id"] for d in m.get("designDecisions", [])}
    elements = [e for _, e in ids.values()]
    rels = [rel for level in _levels(m).values() for rel in level.get("relationships", [])]
    for f in m.get("functionalRequirements", []):
        actor = ids.get(f.get("actor"))
        if not actor or actor[0] != "context" or actor[1].get("type") not in ("person", "external_person"):
            r.error("S-10", f"{f['id']}: actor {f.get('actor')} is not a context person")
        if not f.get("acceptanceCriteria"):
            r.warn("F-02", f"{f['id']}: no acceptance criteria")
        if not f.get("priority"):
            r.warn("F-05", f"{f['id']}: no priority")
        if f.get("priority") == "must" and not any(f["id"] in e.get("relatedFrs", []) for e in elements):
            r.warn("F-01", f"{f['id']}: must-FR not referenced by any element")
    for e in elements:
        for x in e.get("relatedFrs", []):
            if x not in frs:
                r.error("S-12", f"{e['id']}: unknown FR {x}")
        for x in e.get("relatedDecisions", []):
            if x not in dds:
                r.error("T-02", f"{e['id']}: unknown decision {x}")
        if e.get("relatedDecisions") and not e.get("why"):
            r.note("W-02", f"{e['id']}: decisions but no why")
        if e.get("type") == "database" and not any(s.get("parentElement") == e["id"]
                                                   for s in (m.get("code") or {}).get("snippets", [])):
            r.warn("C-05", f"{e['id']}: database without schema snippet")
    for d in m.get("designDecisions", []):
        for x in d.get("relatedFrs", []):
            if x not in frs:
                r.error("S-11", f"{d['id']}: unknown FR {x}")
        for x in d.get("relatedElements", []):
            if x not in ids:
                r.warn("T-02", f"{d['id']}: unknown element {x}")
        if not d.get("tradeoff"):
            r.warn("C-08", f"{d['id']}: no tradeoff")
        if not d.get("relatedNfrs"):
            r.note("T-03", f"{d['id']}: no related NFR")
        used = any(d["id"] in e.get("relatedDecisions", []) for e in elements) or \
            any(rel.get("relatedDecision") == d["id"] for rel in rels)
        if not used:
            r.warn("T-04", f"{d['id']}: not referenced by any element or relationship")
    for n in m.get("nfrs", []):
        if not n.get("metric"):
            r.warn("C-07", f"{n['id']}: no metric")
        if not any(n["id"] in d.get("relatedNfrs", []) for d in m.get("designDecisions", [])):
            r.warn("T-01", f"{n['id']}: no decision addresses it")
    snippets = (m.get("code") or {}).get("snippets", [])
    for s in snippets:
        if s.get("parentElement") not in ids:
            r.error("S-05", f"snippet {s.get('id')}: unknown parentElement {s.get('parentElement')}")
        if not s.get("why"):
            r.warn("W-05", f"snippet {s.get('id')}: no why")
    if len(snippets) > 10:
        r.note("V-08", f"{len(snippets)} snippets (max 10)")
    if not m.get("sequences"):
        r.warn("C-09", "no sequence diagram")


def _check_sequences(m: dict, r: Report) -> None:
    seen = set()
    for s in m.get("sequences", []):
        if s["id"] in seen:
            r.error("S-15", f"duplicate sequence id {s['id']}")
        seen.add(s["id"])
        parts = [p["id"] for p in s.get("participants", [])]
        if len(parts) != len(set(parts)):
            r.error("S-15", f"{s['id']}: duplicate participant id")
        msgs = s.get("messages", [])
        for msg in msgs:
            if msg.get("from") not in parts or msg.get("to") not in parts:
                r.error("S-16", f"{s['id']}: message {msg.get('from')}->{msg.get('to')} has unknown participant")
        for f in s.get("fragments", []):
            ok = f.get("from") in parts and f.get("to") in parts and \
                0 <= f.get("startMessage", -1) <= f.get("endMessage", -1) < len(msgs)
            if not ok:
                r.error("S-17", f"{s['id']}: invalid fragment {f.get('type', '')}")


def _check_evidence(m: dict, ids: dict, r: Report) -> None:
    items = [("element", e["id"], e) for _, e in ids.values()]
    items += [("relationship", f"{rel['from']}->{rel['to']}", rel)
              for level in _levels(m).values() for rel in level.get("relationships", [])]
    items += [("snippet", s.get("id"), s) for s in (m.get("code") or {}).get("snippets", [])]
    items += [("decision", d["id"], d) for d in m.get("designDecisions", [])]
    items += [("nfr", n["id"], n) for n in m.get("nfrs", [])]
    items += [("fr", f["id"], f) for f in m.get("functionalRequirements", [])]
    items += [("message", f"{s['id']}#{i}", msg) for s in m.get("sequences", [])
              for i, msg in enumerate(s.get("messages", []), 1)]
    code_mode = any(o.get("evidence") for _, _, o in items)
    for kind, iid, obj in items:
        if obj.get("origin") == "decided" and not obj.get("decidedIn"):
            r.error("E-04", f"{kind} {iid}: decided without decidedIn")
        for e in obj.get("evidence") or []:
            if isinstance(e, dict) and e.get("kind") is not None and e["kind"] not in EVIDENCE_KINDS:
                r.error("E-01", f"{kind} {iid}: evidence kind '{e['kind']}' not in {', '.join(EVIDENCE_KINDS)}")
        for res in _evidence_resources(obj):
            match = RESOURCE.match(res)
            if not match:
                r.error("E-01", f"{kind} {iid}: bad resource {res}")
                continue
            if res.startswith(DERIVED_VIEWS):
                r.error("E-03", f"{kind} {iid}: evidence points to a derived view {res}")
            lines = int(match[2]) - int(match[1]) + 1
            if not 3 <= lines <= 40:
                r.warn("E-09", f"{kind} {iid}: range of {lines} lines (3-40) {res}")
        if code_mode and kind in ("element", "relationship", "nfr") and not obj.get("evidence") \
                and obj.get("origin") != "decided" and not obj.get("unanchored"):
            r.warn("E-05", f"{kind} {iid}: no evidence (bind it or list it as unbelegt with a reason)")
    if code_mode and m.get("version") != "2.3":
        r.error("S-08", "evidence fields need version 2.3")


def _check_required(m: dict, r: Report) -> None:
    """S-19 required fields, S-18 id format. Later checks rely on both."""
    if not (m.get("project") or {}).get("name"):
        r.error("S-19", "project.name missing")
    if not isinstance(m.get("context"), dict):
        r.error("S-19", "context level missing")
    objects = []
    for level in _levels(m).values():
        objects += [("element", e) for e in level.get("elements", [])]
        objects += [("relationship", rel) for rel in level.get("relationships", [])]
        objects += [("group", g) for g in level.get("groups", [])]
    objects += [("snippet", s) for s in (m.get("code") or {}).get("snippets", [])]
    objects += [("sequence", s) for s in m.get("sequences", [])]
    objects += [("decision", d) for d in m.get("designDecisions", [])]
    objects += [("nfr", n) for n in m.get("nfrs", [])]
    objects += [("fr", f) for f in m.get("functionalRequirements", [])]
    for kind, obj in objects:
        missing = [f for f in REQUIRED[kind] if not obj.get(f)]
        if missing:
            r.error("S-19", f"{kind} {obj.get('id', '?')}: missing {', '.join(missing)}")
    tokens = [obj.get("id") for kind, obj in objects if kind not in ("relationship", "group")]
    tokens += list((m.get("containers") or {}).keys()) + list((m.get("components") or {}).keys())
    tokens += [p.get("id") for s in m.get("sequences", []) for p in s.get("participants", [])]
    for token in tokens:
        if token is not None and not ID.match(str(token)):
            r.error("S-18", f"id {token!r} is not a plain token (letters, digits, - _ .)")


def validate(model: dict) -> dict:
    r = Report()
    _check_required(model, r)
    if r.errors:
        return r.as_dict()  # the remaining checks need ids and required fields
    ids = _check_structure(model, r)
    _check_requirements(model, ids, r)
    _check_sequences(model, r)
    _check_evidence(model, ids, r)
    return r.as_dict()


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = argv if argv is not None else sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    result = validate(json.loads(Path(args[0]).read_text(encoding="utf-8")))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
