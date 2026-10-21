#!/usr/bin/env python3
"""Code evidence of a C4 model (architecture.json) checked against its repository.

    py c4_evidence.py check  <model> --root <repo>               # format, ranges, unanchored items (no Node needed)
    py c4_evidence.py stamp  <model> --root <repo>               # add OpenWiki versions to unversioned evidence
    py c4_evidence.py verify <model> --root <repo> [--fix-moved] [--accept-changed ITEM ...]
                                                             # unchanged | moved | accepted | changed | gone | unstamped | error
    py c4_evidence.py pairs  <model> --claims <repo>/openwiki/.claims  # per model item: OpenWiki claims on the same lines
    py c4_evidence.py show   <model> ITEM ...                    # an item's lines in the model file, quoted exactly

Evidence is a list on elements, relationships, snippets, design decisions, NFRs, FRs and sequence messages. Each entry
is {"resource": "repo://<path>#L<a>-L<b>", "supports": "<field>", "version": "..."}; a bare string
is accepted as {"resource": ...}. `stamp` and `verify` use OpenWiki's resolver through resolve.mjs
(Node; OpenWiki from %LOCALAPPDATA%/Programs/openwiki or OPENWIKI_CLI), so evidence relocates and goes stale exactly like
OpenWiki claims. Output is JSON (UTF-8) on stdout. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote

RESOURCE = re.compile(r"^repo://(?P<path>[^#]+)#L(?P<a>\d+)-L(?P<b>\d+)$")
RESOLVER = Path(__file__).with_name("resolve.mjs")
FAILING = ("changed", "gone")
PINNED_VERSION = os.environ.get("OPENWIKI_PINNED_VERSION", "0.7.2")


class ToolError(Exception):
    """The check itself could not run (Node, OpenWiki version, resolver) — not a finding."""


@dataclass
class Item:
    kind: str
    id: str
    origin: str = "derived"
    evidence: list[dict] = field(default_factory=list)
    unanchored: str | None = None  # why nothing in the code can carry the item
    obj: dict = field(default_factory=dict, repr=False)  # the model entry, for the text an agent amends

    @property
    def ref(self) -> str:
        return f"{self.kind}:{self.id}"


def parse_resource(r: str) -> tuple[str, int, int]:
    m = RESOURCE.match(r)
    if not m:
        raise ValueError(f"not a repo:// line range: {r}")
    return unquote(m["path"]), int(m["a"]), int(m["b"])  # the resolver writes paths percent-encoded


def _evidence(obj: dict) -> list[dict]:
    """The evidence entries of obj, normalized in place to objects."""
    entries = obj.get("evidence") or []
    for i, e in enumerate(entries):
        if isinstance(e, str):
            entries[i] = {"resource": e}
    if "evidence" in obj:
        obj["evidence"] = entries
    return entries


def _item(kind: str, iid: str, obj: dict) -> Item:
    return Item(kind, iid, obj.get("origin", "derived"), _evidence(obj), obj.get("unanchored"), obj)


def iter_items(model: dict) -> Iterator[Item]:
    views = [model.get("context") or {}, *(model.get("containers") or {}).values(),
             *(model.get("components") or {}).values()]
    for view in views:
        for e in view.get("elements", []):
            yield _item("element", e["id"], e)
        for r in view.get("relationships", []):
            yield _item("relationship", f"{r['from']}->{r['to']}:{r.get('label', '')}", r)
    for s in (model.get("code") or {}).get("snippets", []):
        yield _item("snippet", s["id"], s)
    for kind, key in (("decision", "designDecisions"), ("nfr", "nfrs"), ("fr", "functionalRequirements")):
        for d in model.get(key, []):
            yield _item(kind, d["id"], d)
    for s in model.get("sequences", []):
        for n, msg in enumerate(s.get("messages", []), 1):
            yield _item("message", f"{s['id']}#{n}", msg)


def _status(root: Path, resource: str) -> str:
    try:
        path, a, b = parse_resource(resource)
    except ValueError:
        return "bad-format"
    file = root / path
    if not file.is_file():
        return "missing-file"
    n = len(file.read_text(encoding="utf-8", errors="replace").splitlines())
    return "ok" if 1 <= a <= b <= n else "out-of-range"


def check(model: dict, root: Path) -> dict:
    items = list(iter_items(model))
    results = [{"item": i.ref, "resource": e["resource"], "status": _status(Path(root), e["resource"])}
               for i in items for e in i.evidence]
    unanchored = {i.ref: i.unanchored for i in items if not i.evidence}
    by_kind: dict[str, dict] = {}
    for i in items:
        counts = by_kind.setdefault(i.kind, {"withEvidence": 0, "withoutEvidence": 0})
        counts["withEvidence" if i.evidence else "withoutEvidence"] += 1
    return {"results": results, "unanchored": unanchored,
            "summary": {"items": len(items), "withEvidence": len(items) - len(unanchored),
                        "withoutEvidence": len(unanchored), "byKind": by_kind}}


def cli_path() -> str | None:
    """OpenWiki's dist/cli/cli.js: OPENWIKI_CLI, else the default installation, else None."""
    if os.environ.get("OPENWIKI_CLI"):
        return os.environ["OPENWIKI_CLI"]
    default = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "openwiki" / "node_modules" / "openwiki" \
        / "dist" / "cli" / "cli.js"
    return str(default) if os.environ.get("LOCALAPPDATA") and default.is_file() else None


def openwiki_available() -> bool:
    cli = cli_path()
    return bool(cli and Path(cli).is_file() and shutil.which("node"))


def _resolve(root: Path, entries: list[dict]) -> list[dict]:
    if not entries:
        return []
    if not openwiki_available():
        raise ToolError("stamp/verify need Node and OpenWiki " + PINNED_VERSION + " (default installation under %LOCALAPPDATA%/Programs/openwiki, or OPENWIKI_CLI)")
    payload = {"root": str(Path(root).resolve()),
               "items": [{"resource": e["resource"], "version": e.get("version")} for e in entries]}
    out = subprocess.run(["node", str(RESOLVER)], input=json.dumps(payload), capture_output=True,
                         text=True, encoding="utf-8",
                         env={**os.environ, "OPENWIKI_PINNED_VERSION": PINNED_VERSION, "OPENWIKI_CLI": cli_path()})
    if out.returncode != 0:
        raise ToolError("resolve.mjs: " + (out.stderr.strip()[-500:] or f"exit {out.returncode}"))
    return json.loads(out.stdout)


def stamp(model: dict, root: Path) -> dict:
    pending = [e for i in iter_items(model) for e in i.evidence if not e.get("version")]
    failed = []
    for e, r in zip(pending, _resolve(root, pending)):
        if r.get("current"):
            e["resource"], e["version"] = r["current"]["resource"], r["current"]["version"]
        else:
            failed.append({"resource": e["resource"], "error": r.get("error", "range not found")})
    return {"stamped": len(pending) - len(failed), "failed": failed}


def verify(model: dict, root: Path, fix_moved: bool = False, accept_changed: list[str] | None = None) -> dict:
    """Status of every evidence entry. fix_moved rewrites line numbers of moved code; accept_changed
    names the items (refs like element:cmp-x) whose changed evidence is re-stamped at its current
    location — only items that were re-read and amended."""
    accept = set(accept_changed or [])
    pairs = [(i, e) for i in iter_items(model) for e in i.evidence]
    stamped = [(i, e) for i, e in pairs if e.get("version")]
    resolved = dict(zip((id(e) for _, e in stamped), _resolve(root, [e for _, e in stamped])))
    results = []
    for item, e in pairs:
        r = resolved.get(id(e))
        current = (r or {}).get("current")
        if r is None:
            status = "unstamped"
        elif "error" in r:
            status = "error"
        elif current is None:
            status = "gone"
        elif current["version"] != e["version"]:
            status = "accepted" if item.ref in accept else "changed"
        elif current["resource"] != e["resource"]:
            status = "moved"
        else:
            status = "unchanged"
        results.append({"item": item.ref, "supports": e.get("supports"), "resource": e["resource"],
                        "status": status, "current": current["resource"] if current else None,
                        **({"error": r["error"]} if status == "error" else {}),
                        **(_amend(item, e, status) if status in FAILING else {})})
        if status == "moved" and fix_moved:
            e["resource"] = current["resource"]
        if status == "accepted":
            e["resource"], e["version"] = current["resource"], current["version"]
    summary = {s: sum(1 for r in results if r["status"] == s)
               for s in ("unchanged", "moved", "accepted", "changed", "gone", "unstamped", "error")}
    return {"results": results, "summary": summary}


REBIND = ("the cited lines no longer exist: find the code again, set resource to its new lines, delete its "
          "version, then run stamp (or remove the entry when the statement no longer holds)")


def _amend(item: Item, e: dict, status: str) -> dict:
    """Name and supported text of an item whose code changed: enough to find and amend it."""
    text = item.obj.get(e.get("supports") or "description")
    return {"name": item.obj.get("name") or item.obj.get("label") or item.obj.get("title"),
            "text": text if isinstance(text, str) else json.dumps(text, ensure_ascii=False),
            **({"hint": REBIND} if status == "gone" else {})}


def actionable(result: dict, fixed_moved: bool) -> dict:
    """verify output for the command line: only entries an agent acts on, the counts stay complete.
    Moved evidence that --fix-moved rewrote needs nothing more."""
    skip = {"unchanged", "accepted", *(("moved",) if fixed_moved else ())}
    return {"results": [r for r in result["results"] if r["status"] not in skip], "summary": result["summary"]}


def _block(lines: list[str], anchor: int) -> tuple[int, int] | None:
    """The 0-based first and last line of the JSON object that holds line `anchor` (indent 2)."""
    indent = len(lines[anchor]) - len(lines[anchor].lstrip()) - 2
    start = next((i for i in range(anchor, -1, -1) if lines[i].strip() == "{"
                  and len(lines[i]) - len(lines[i].lstrip()) == indent), None)
    end = next((i for i in range(anchor, len(lines)) if lines[i].strip() in ("}", "},")
                and len(lines[i]) - len(lines[i].lstrip()) == indent), None)
    return None if start is None or end is None else (start, end)


def _norm_obj(obj: dict) -> dict:
    """An item object with bare-string evidence written as {"resource": ...}, for comparison."""
    out = dict(obj)
    if isinstance(out.get("evidence"), list):
        out["evidence"] = [{"resource": e} if isinstance(e, str) else e for e in out["evidence"]]
    return out


def locate(text: str, model: dict, ref: str) -> tuple[int, int] | None:
    """1-based first and last line of an item (element:x, relationship:a->b:label, snippet:x,
    decision:x, nfr:x, fr:x) in the model file as written with indent 2. A candidate block counts
    only when its JSON is the item itself (not a sequence participant with the same id); None when
    the item is not in the model or its block cannot be found in this layout."""
    target = next((i.obj for i in iter_items(model) if i.ref == ref), None)
    if target is None:
        return None
    kind, _, key = ref.partition(":")
    needle = (f'"from": {json.dumps(key.partition("->")[0], ensure_ascii=False)}' if kind == "relationship"
              else f'"id": {json.dumps(key, ensure_ascii=False)}')
    lines = text.splitlines()
    want = _norm_obj(target)
    for i, line in enumerate(lines):
        if not line.strip().startswith(needle):
            continue
        block = _block(lines, i)
        if not block:
            continue
        try:
            found = json.loads("\n".join(lines[block[0]:block[1] + 1]).rstrip().rstrip(","))
        except ValueError:
            continue
        if isinstance(found, dict) and _norm_obj(found) == want:
            return block[0] + 1, block[1] + 1
    return None


def show(text: str, model: dict, refs: list[str]) -> list[dict]:
    lines = text.splitlines()
    out = []
    for ref in refs:
        at = locate(text, model, ref)
        out.append({"item": ref, "at": f"L{at[0]}-L{at[1]}", "text": "\n".join(lines[at[0] - 1:at[1]])}
                   if at else {"item": ref, "error": "in the model, but not locatable in this file's layout"
                               if any(i.ref == ref for i in iter_items(model)) else "not in the model"})
    return out


def _claims(claims_dir: Path) -> Iterator[tuple[dict, str, int, int]]:
    for f in sorted(Path(claims_dir).rglob("*.json")):
        for c in json.loads(f.read_text(encoding="utf-8")).get("claims", []):
            for e in c.get("evidence", []):
                try:
                    yield (c, *parse_resource(e["resource"]))
                except ValueError:
                    continue  # whole-file evidence cannot overlap a line range


def pairs(model: dict, claims_dir: Path) -> list[dict]:
    claims = list(_claims(claims_dir))
    groups = []
    for item in iter_items(model):
        found: dict[str, dict] = {}
        for e in item.evidence:
            try:
                path, s, t = parse_resource(e["resource"])
            except ValueError:
                continue
            for c, cpath, cs, ct in claims:
                if cpath == path and max(s, cs) <= min(t, ct) and c["id"] not in found:
                    found[c["id"]] = {"claimId": c["id"], "statement": c["statement"],
                                      "resource": f"repo://{cpath}#L{cs}-L{ct}"}
        if found:
            groups.append({"item": item.ref, "claims": list(found.values())})
    return groups


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "stamp", "verify", "pairs", "show"):
        sp = sub.add_parser(name)
        sp.add_argument("model")
        if name == "show":
            sp.add_argument("items", nargs="+", metavar="ITEM", help="e.g. element:cmp-x 'relationship:a->b:label' (quote it: > is a redirect in PowerShell)")
        elif name == "pairs":
            sp.add_argument("--claims", required=True)
        else:
            sp.add_argument("--root", required=True)
        if name == "verify":
            sp.add_argument("--fix-moved", action="store_true", help="rewrite line numbers of moved evidence")
            sp.add_argument("--accept-changed", nargs="+", metavar="ITEM", default=[],
                            help="re-stamp changed evidence of these items (e.g. element:cmp-x) after amending them")
    args = p.parse_args(argv)
    path = Path(args.model)
    model = json.loads(path.read_text(encoding="utf-8"))
    code = 0
    # Exit codes: 0 ok, 1 findings, 2 the check could not run (tool error).
    try:
        if args.cmd == "check":
            result = check(model, Path(args.root))
            code = 0 if all(r["status"] == "ok" for r in result["results"]) else 1
        elif args.cmd == "stamp":
            result = stamp(model, Path(args.root))
            code = 1 if result["failed"] else 0
        elif args.cmd == "verify":
            full = verify(model, Path(args.root), args.fix_moved, args.accept_changed)
            code = 2 if full["summary"]["error"] else 1 if any(full["summary"][s] for s in FAILING) else 0
            result = actionable(full, args.fix_moved)
        elif args.cmd == "show":
            result = show(path.read_text(encoding="utf-8"), model, args.items)
            code = 1 if any("error" in r for r in result) else 0
        else:
            result = pairs(model, Path(args.claims))
    except ToolError as exc:
        print(f"c4_evidence: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "stamp" or (args.cmd == "verify" and (args.fix_moved or args.accept_changed)):
        path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.cmd == "verify":
        text = path.read_text(encoding="utf-8")
        for r in result["results"]:
            at = locate(text, model, r["item"])
            if at:
                r["at"] = f"L{at[0]}-L{at[1]}"  # the item's lines in the model file, for a targeted read
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return code


if __name__ == "__main__":
    sys.exit(main())
