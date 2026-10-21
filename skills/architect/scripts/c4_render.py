#!/usr/bin/env python3
"""Render architecture.json to the interactive HTML page (Phase 10) without hand assembly.

    py c4_render.py <model> <out.html>

Takes the engine code and CSS from references/engine.js.md, the colour palette from
references/render-spec.md and the skeleton from templates/base.html, so the page always matches
the skill's references. Evidence, origin and decidedIn are passed through to the page (tooltips).
Standard library only.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ELEMENT_FIELDS = [("technology", "tech"), ("drillDown", "drillDown"), ("why", "why"), ("pattern", "pattern"),
                  ("relatedDecisions", "relatedDecisions"), ("relatedFrs", "relatedFrs"), ("position", "position"),
                  ("evidence", "evidence"), ("origin", "origin"), ("decidedIn", "decidedIn")]
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
PLAIN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
PALETTE_ROW = re.compile(r"^\|\s*([a-z_ /]+?)\s*\|\s*(#[0-9A-Fa-f]{6})\s*\|\s*(#[0-9A-Fa-f]{6})\s*\|\s*(#[0-9A-Fa-f]{6})\s*\|")
esc = html.escape


def palette(render_spec: str) -> dict:
    """Type -> {fill, stroke, text} from the Color Palette tables; later tables win (component adapter)."""
    section = render_spec.split("## Color Palette", 1)[1].split("### UI Chrome", 1)[0]
    colors = {}
    for line in section.splitlines():
        m = PALETTE_ROW.match(line)
        if m:
            for key in (k.strip() for k in m[1].split("/")):
                colors[key] = {"fill": m[2], "stroke": m[3], "text": m[4]}
    return colors


def _engine(skill: Path) -> tuple[str, str]:
    text = (skill / "references" / "engine.js.md").read_text(encoding="utf-8")
    js = re.search(r"## Complete Engine Code.*?```javascript\n(.*?)\n```", text, re.S)[1]
    css = re.search(r"## CSS to Include.*?```css\n(.*?)\n```", text, re.S)[1]
    return js, css


def _element(e: dict) -> dict:
    out = {"id": e["id"], "type": e["type"], "name": e["name"], "desc": e.get("description", "")}
    out.update({b: e[a] for a, b in ELEMENT_FIELDS if a in e})
    return out


def _level(level: dict) -> dict:
    return {"elements": [_element(e) for e in level.get("elements", [])],
            "relationships": [{k: v for k, v in r.items() if k != "protocol"} for r in level.get("relationships", [])],
            "groups": [{"name": g["name"], "ids": g["elementIds"]} for g in level.get("groups", [])]}


def _data(m: dict, colors: dict) -> dict:
    snippets = (m.get("code") or {}).get("snippets", [])
    return {"colors": colors,
            "levels": {"context": _level(m["context"]),
                       "containers": {k: _level(v) for k, v in (m.get("containers") or {}).items()},
                       "components": {k: _level(v) for k, v in (m.get("components") or {}).items()}},
            "code": {"snippets": [{"id": s["id"], "title": s["title"], "lang": s.get("language", ""), "code": s["code"],
                                   "parentElement": s["parentElement"], "annotations": s.get("annotations", []),
                                   "why": s.get("why"), "evidence": s.get("evidence", [])} for s in snippets]},
            "frs": [dict({k: v for k, v in f.items() if k != "description"}, desc=f.get("description", ""))
                    for f in m.get("functionalRequirements", [])],
            "nfrs": m.get("nfrs", []), "designDecisions": m.get("designDecisions", []),
            "sequences": m.get("sequences", [])}


def _svg(kind: str, key: str, label: str, title: str, box: str) -> str:
    return (f'<svg id="svg-{kind}-{key}" role="img" aria-label="{esc(label)}" viewBox="{box}" '
            f'xmlns="http://www.w3.org/2000/svg"><title>{esc(title)}</title><g class="groups-layer"></g>'
            f'<g class="arrows-layer"></g><g class="elements-layer"></g></svg>')


def _tab(level: str, label: str) -> str:
    return (f'<button class="tab" role="tab" aria-selected="false" data-level="{level}" '
            f"onclick=\"switchLevel('{level}')\">{esc(label)}</button>")


def _panels(m: dict) -> tuple[str, str, str]:
    fr = "<h3>Functional Requirements</h3>\n" + "\n".join(
        f'<div class="fr-item"><div class="fr-title">{esc(f["id"])} {esc(f.get("title", ""))}'
        f'<span class="fr-priority {esc(f.get("priority", ""))}">{esc(f.get("priority", ""))}</span></div>'
        f'<div class="fr-desc">{esc(f.get("description", ""))}</div><ul class="fr-criteria">'
        + "".join(f"<li>{esc(c)}</li>" for c in f.get("acceptanceCriteria", [])) + "</ul></div>"
        for f in m.get("functionalRequirements", []))
    nfr = "<h3>Non-Functional Requirements</h3>\n" + "\n".join(
        f'<div class="nfr-item"><div class="nfr-category">{esc(n.get("category", ""))}</div>'
        f'<div class="nfr-title">{esc(n["id"])} {esc(n.get("title", ""))}</div>'
        f'<div class="nfr-metric">{esc(n.get("metric", ""))}</div>'
        f'<div class="nfr-approach">{esc(n.get("approach", ""))}</div></div>' for n in m.get("nfrs", []))
    dd = "<h3>Design Decisions</h3>\n" + "\n".join(
        f'<div class="dd-item" data-elements="{esc(",".join(d.get("relatedElements", [])))}">'
        f'<div class="dd-title">{esc(d["id"])} {esc(d.get("title", ""))}'
        + (' <span class="fr-priority should">beschlossen</span>' if d.get("origin") == "decided" else "")
        + f'</div><div class="fr-desc">{esc(d.get("decision", ""))}</div>'
        f'<div class="dd-tradeoff">Trade-off: {esc(d.get("tradeoff", ""))}</div></div>'
        for d in m.get("designDecisions", []))
    return fr, nfr, dd


def render(model: dict, skill: Path = SKILL) -> str:
    js, css = _engine(skill)
    colors = palette((skill / "references" / "render-spec.md").read_text(encoding="utf-8"))
    template = (skill / "templates" / "base.html").read_text(encoding="utf-8")
    m = model
    systems = {e["id"]: e["name"] for e in m["context"].get("elements", [])}
    containers = {e["id"]: e["name"] for v in (m.get("containers") or {}).values() for e in v.get("elements", [])}
    sequences = m.get("sequences", [])
    fr, nfr, dd = _panels(m)
    snippets = len((m.get("code") or {}).get("snippets", []))
    _require_plain_ids(m)
    # No "<" in the inline script at all: no </script>, no <!-- that would change script parsing.
    data = json.dumps(_data(m, colors), ensure_ascii=False, indent=1).replace("<", "\\u003c")
    values = {
        "{{PROJECT_NAME}}": esc(m["project"]["name"]), "{{CSS_THEME}}": css, "{{ENGINE_JS}}": js,
        "{{C4_DATA_OBJECT}}": data, "{{CTX_W}}": "1100", "{{CTX_H}}": "700", "{{CODE_W}}": "1100",
        "{{CODE_H}}": str(max(600, ((snippets + 2) // 3) * 320 + 40)),
        "{{CONTAINER_SVGS}}": "\n".join(
            _svg("container", k, f"C4 Container: {systems.get(k, k)}", f"Container Level — {systems.get(k, k)}",
                 "0 0 1500 1100") for k in (m.get("containers") or {})),
        "{{CONTAINER_TABS}}": "\n".join(
            _tab(f"container:{k}", f"Container: {systems.get(k, k)}" if len(m["containers"]) > 1 else "Container")
            for k in (m.get("containers") or {})),
        "{{COMPONENT_SVGS}}": "\n".join(
            _svg("component", k, f"C4 Komponenten: {containers.get(k, k)}", f"Component Level — {containers.get(k, k)}",
                 "0 0 1200 800") for k in (m.get("components") or {})),
        "{{COMPONENT_TABS}}": "\n".join(_tab(f"component:{k}", f"Komponenten: {containers.get(k, k)}")
                                        for k in (m.get("components") or {})),
        "{{SEQUENCE_SVGS}}": "\n".join(
            f'<svg id="svg-sequence-{s["id"]}" role="img" aria-label="Sequenz: {esc(s["title"])}" viewBox="0 0 100 100" '
            f'xmlns="http://www.w3.org/2000/svg"></svg>' for s in sequences),
        "{{SEQUENCE_TABS}}": "\n".join(_tab(f"sequence:{s['id']}", s.get("tabLabel") or s["title"]) for s in sequences),
        "{{FR_PANEL_HTML}}": fr, "{{NFR_PANEL_HTML}}": nfr, "{{DESIGN_DECISIONS_HTML}}": dd,
    }
    missing = sorted(set(PLACEHOLDER.findall(template)) - {k.strip("{}") for k in values})
    if missing:
        raise ValueError(f"template placeholders without value: {missing}")
    # One pass over the template only: placeholder-like text inside model values stays as it is.
    return PLACEHOLDER.sub(lambda match: values["{{" + match[1] + "}}"], template)


def _require_plain_ids(m: dict) -> None:
    """Ids go into HTML attributes and onclick handlers; refuse anything but plain tokens."""
    ids = [e["id"] for level in [m["context"], *(m.get("containers") or {}).values(),
                                 *(m.get("components") or {}).values()] for e in level.get("elements", [])]
    ids += list((m.get("containers") or {}).keys()) + list((m.get("components") or {}).keys())
    ids += [s["id"] for s in (m.get("code") or {}).get("snippets", [])]
    ids += [s["id"] for s in m.get("sequences", [])] + [d["id"] for d in m.get("designDecisions", [])]
    bad = [i for i in ids if not PLAIN_ID.match(str(i))]
    if bad:
        raise ValueError(f"ids must be plain tokens (run c4_validate.py, rule S-18): {bad[:5]}")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    page = render(json.loads(Path(args[0]).read_text(encoding="utf-8")))
    Path(args[1]).write_text(page, encoding="utf-8")
    print(f"written {args[1]} ({len(page.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
