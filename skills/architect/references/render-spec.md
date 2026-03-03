# C4 Render Specification

## Architecture Principle

**Dynamic Rendering** — All SVG content is generated at runtime from a JavaScript data structure (`C4.levels` and `C4.code`). No hardcoded SVG paths. This enables:
- Drag & Drop for all elements
- Arrows auto-recalculate on element move
- Group boundaries auto-resize
- Single source of truth for positions

## HTML Structure

```
<!DOCTYPE html>
<html>
<head>
  <style>/* ALL CSS inline */</style>
</head>
<body>
  <nav class="nav-bar"><!-- Tabs + Breadcrumbs --></nav>
  <!-- SHARED DEFS: single hidden SVG contains filter + marker used by ALL diagrams -->
  <svg style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">
    <defs>
      <filter id="ds" ...><feDropShadow .../></filter>
      <marker id="af" ...><polygon .../></marker>
    </defs>
  </svg>
  <div class="canvas-area">
    <svg id="svg-context">
      <!-- NO local defs — uses shared #ds and #af -->
      <g class="arrows-layer"></g>    <!-- rendered dynamically -->
      <g class="elements-layer"></g>  <!-- rendered dynamically -->
    </svg>
    <svg id="svg-container">
      <!-- NO local defs — uses shared #ds and #af -->
      <g class="groups-layer"></g>    <!-- rendered dynamically -->
      <g class="arrows-layer"></g>
      <g class="elements-layer"></g>
    </svg>
    <svg id="svg-component-XYZ"><!-- same structure, NO local defs --></svg>
    <svg id="svg-code">
      <g class="elements-layer"></g>  <!-- foreignObject code cards -->
    </svg>
  </div>
  <aside class="nfr-panel"><!-- NFRs + Design Decisions --></aside>
  <div class="tooltip"></div>
  <div class="code-overlay">...</div>
  <div class="legend">...</div>
  <div class="drag-hint">...</div>
  <script>
    const C4 = { colors: {...}, levels: {...}, code: {...} };
    /* Rendering engine + Drag & Drop + Navigation + Tooltip */
  </script>
</body>
</html>
```

**Render order within each SVG (back to front):**
1. Groups layer (background rectangles)
2. Arrows layer (lines + labels)
3. Elements layer (shapes on top)

---

## Data Structure (JavaScript)

The architecture data is embedded as a `C4` object:

```javascript
const C4 = {
  colors: { /* type -> { fill, stroke, text? } */ },
  levels: {
    context: {
      elements: [
        {
          id,            // string — unique element ID
          type,          // string — element type (person, system, etc.)
          name,          // string — display name (max 30 chars)
          desc,          // string — description
          tech,          // string? — technology
          drillDown,     // string? — "container" or "component:<container-id>"
          why,           // string? — why does this element exist?
          pattern,       // string? — architectural pattern implemented
          relatedDecisions, // string[]? — decision IDs
          codeSnippets,  // string[]? — snippet IDs
          x, y, w, h    // number — position and dimensions (mutable)
        }
      ],
      relationships: [
        {
          from,          // string — source element ID
          to,            // string — target element ID
          label,         // string — short label on the line (max 40 chars)
          async,         // boolean — if true, renders dashed line
          detail,        // string? — longer description for tooltip
          payload,       // string? — event/message structure for async arrows
          why,           // string? — why does this communication exist?
          relatedDecision // string? — decision ID
        }
      ],
      groups: [ // optional
        {
          name,          // string — group title
          color,         // string? — CSS color (defaults to first member's color)
          ids            // string[] — element IDs in this group
        }
      ]
    },
    container: { /* same structure as context */ },
    components: {
      // keyed by container ID — one entry per decomposed container
      "<container-id>": { /* same structure: elements, relationships, groups */ }
    }
  },
  code: {
    snippets: [
      {
        id,            // string — snippet ID
        title,         // string — what does this snippet show?
        lang,          // string — language (sql, typescript, java, etc.)
        code,          // string — the actual code
        parentElement, // string — element ID this belongs to
        annotations    // { line: number, text: string }[]? — line annotations
      }
    ]
  },
  nfrs: [
    {
      id,              // string — NFR ID
      category,        // string — Performance, Availability, etc.
      title,           // string — short name
      metric,          // string — measurable target
      approach,        // string? — how the architecture addresses this
      details          // string[]? — additional bullet points
    }
  ],
  designDecisions: [
    {
      id,              // string — decision ID
      title,           // string — what was decided?
      context,         // string? — what problem does this solve?
      decision,        // string? — what was chosen and why?
      tradeoff,        // string — what are the downsides?
      relatedNfrs,     // string[] — NFR IDs
      relatedElements  // string[] — element IDs
    }
  ]
};
```

### Element Position Fields
- `x`, `y` — top-left corner in SVG coordinates
- `w`, `h` — width and height of the element bounding box
- These are **mutable** — drag & drop updates them at runtime
- Calculated from `position` hints in architecture.json using the layout algorithm (see json-schema.md)

### Relationship Fields
- `from`, `to` — element IDs (must exist in same level)
- `label` — text displayed at midpoint of arrow
- `async` — if true, renders dashed line
- `detail` — longer tooltip text (shown on arrow hover)
- `payload` — event structure, rendered in monospace in tooltip (required for async)
- `why` — design rationale, shown in tooltip (italic, blue)
- `relatedDecision` — links to a design decision, shown as clickable reference in tooltip

### Data Flow: architecture.json → C4 Object

The rendering engine transforms `architecture.json` fields to the C4 JS object:

| JSON field | C4 JS field | Notes |
|---|---|---|
| `element.description` | `desc` | Shortened key name |
| `element.technology` | `tech` | Shortened key name |
| `element.position` | `x, y, w, h` | Computed by layout algorithm |
| `relationship.async` | `async` | Boolean, NOT protocol string |
| `relationship.protocol` | _(not in JS)_ | Used only for Structurizr export |
| `group.elementIds` | `ids` | Shortened key name |
| `group.style` | _(not in JS)_ | All groups render the same way |
| All other fields | Same name | Passed through directly |

---

## Color Palette

### Context Level
| Type | Fill | Stroke | Text |
|---|---|---|---|
| person | #4A90D9 | #3A7BC8 | #FFFFFF |
| external_person | #7B8D9E | #6A7C8D | #FFFFFF |
| system | #1168BD | #0D5CA8 | #FFFFFF |
| external_system | #999999 | #888888 | #FFFFFF |

### Container Level
| Type | Fill | Stroke | Text |
|---|---|---|---|
| gateway | #1F4E79 | #183D5E | #FFFFFF |
| api / service / webapp | #438DD5 | #3A7BC8 | #FFFFFF |
| database | #E8524A | #D4453E | #FFFFFF |
| cache | #F5A623 | #E09520 | #FFFFFF |
| message_broker | #FF6B35 | #E55A2B | #FFFFFF |
| queue | #FF6B35 | #E55A2B | #FFFFFF |
| cdn | #8BC34A | #7CB342 | #FFFFFF |
| scheduler | #9C27B0 | #8E24AA | #FFFFFF |
| external_service | #999999 | #888888 | #FFFFFF |
| adapter | #999999 | #888888 | #FFFFFF |

### Component Level
| Type | Fill | Stroke | Text |
|---|---|---|---|
| controller | #BBDEFB | #90CAF9 | #1A1A1A |
| service_class | #FFF9C4 | #FFF176 | #1A1A1A |
| repository | #BBDEFB | #90CAF9 | #1A1A1A |
| event_handler | #FFE0B2 | #FFCC80 | #1A1A1A |
| background_worker | #FFE0B2 | #FFCC80 | #1A1A1A |
| validator | #C8E6C9 | #A5D6A7 | #1A1A1A |
| factory | #D1C4E9 | #B39DDB | #1A1A1A |
| facade | #B3E5FC | #81D4FA | #1A1A1A |
| adapter | #E0E0E0 | #BDBDBD | #1A1A1A |

### Infrastructure (component-level context elements)
| Type Key | Fill | Stroke | Text |
|---|---|---|---|
| db_detail | #FFCDD2 | #EF9A9A | #1A1A1A |
| cache_detail | #FFE0B2 | #FFCC80 | #1A1A1A |
| broker_detail | #FFE0B2 | #FFCC80 | #1A1A1A |

### UI Chrome
| Element | Color |
|---|---|
| Canvas background | #FFFFFF |
| Arrow lines | #555555 |
| Arrow label bg | #FFFFFF (92% opacity), #ddd 0.5px stroke |
| Nav bar background | #FAFAFA |
| Tab active | #1168BD text #FFFFFF |
| Tab inactive | #F5F5F5 text #333333 |
| NFR panel bg | #FFF9E6, border #F0E0A0 |
| Tooltip bg | #333333, text #FFFFFF |
| Arrow tooltip bg | #2A2A2A, max-width 360px |
| Group boundary | Element color at 5% fill, 30% stroke, dashed |

### Semantic Rules
- **External = Gray** (#999999) — always
- **Internal services = Blue** family
- **Databases = Red** family
- **Caches = Orange/Yellow**
- **Brokers = Warm Orange**
- **Components = Pastels** (lighter = internal detail)

---

## Typography

```css
font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
```

| Element | Size | Weight |
|---|---|---|
| Page title | 16px | 700 |
| Tab labels | 13px | 500 |
| Element name | 14px | 600 |
| Element description | 11px | 400 |
| Element technology | 10px | 400 italic |
| Arrow label | 10px | 400 |
| Group title | 13px | 600 |
| NFR title | 14px | 700 |
| Code | 11-13px | 400 monospace |

Code font: `'Fira Code', 'JetBrains Mono', 'Consolas', monospace`

---

## SVG Element Shapes

Each element type maps to a shape-rendering function. All shapes are generated inside a `<g>` with `transform="translate(x,y)"`.

### Person (stick figure + label box)
- Stick figure: circle head r=16, body lines, legs
- Label: rounded rect (120x45, rx=8) below figure
- Total bounding box: 120 x 155
- Used for: person, external_person

### System / External System / Service / Cache / CDN / Scheduler / Adapter
- Rounded rectangle (rx=8, stroke-width=2)
- 3 text lines: name, description, [technology]
- Dimensions: from element's w/h fields

### Database (cylinder)
- Top ellipse (rx=w/2, ry=12)
- Side rectangle
- Bottom ellipse
- 2 text lines: name, [technology]

### Message Broker
- Same as rounded rect BUT with `stroke-dasharray="6,3"` (dashed border)

### Gateway (hexagon)
- 6-point polygon
- 3 text lines: name, description, [technology]

### Component types (controller, service_class, repository, etc.)
- Rectangle with `rx=4` (sharper corners than container level)
- `stroke-width: 1.5` (thinner than container)
- Text color: #1A1A1A (dark, because pastel backgrounds)

### Infrastructure detail types (db_detail, cache_detail, broker_detail)
- Small rectangle (typically 140x50)
- Pastel red/orange fill
- Used at component level to show container-level stores as context

---

## Dynamic Arrow Rendering

### Connection Point Algorithm

Arrows connect from the **nearest edge** of the source element to the **nearest edge** of the target element. The algorithm:

```javascript
function getConnectionPoint(element, targetCenter) {
  // Calculate which edge (top/bottom/left/right) is closest
  // to the line from element center to target center
  // Return the intersection point on that edge
}
```

This avoids arrows going through elements and creates clean connections.

### Arrow Composition
Each arrow consists of:
1. **Path** — straight line from source edge to target edge
   - `stroke: #555`, `stroke-width: 1.5`
   - `marker-end: url(#arrow-marker)` for arrowhead
   - If `async: true`: `stroke-dasharray: 8,4` (dashed)
2. **Label background** — white rect (92% opacity) at midpoint
   - Width calculated from label text length: `label.length * 5.5 + 8`
   - Height: 16px, rx: 3
   - Thin border: `stroke: #ddd, stroke-width: 0.5`
3. **Label text** — centered on background rect

### Arrowhead Marker
```svg
<marker id="af" viewBox="0 0 10 10" refX="10" refY="5"
        markerWidth="8" markerHeight="8" orient="auto-start-reverse">
  <polygon points="0,0 10,5 0,10" fill="#555"/>
</marker>
```

### Re-rendering
Arrows are **completely re-rendered** on every drag move. This is fast enough because:
- Only the arrows-layer innerHTML is replaced
- Element shapes don't re-render during drag
- Group boundaries also re-render (they depend on element positions)

---

## Dynamic Group Rendering

Groups are background rectangles that encompass their member elements.

### Algorithm
1. For each group, find all member elements by ID
2. Calculate bounding box: min/max of all element x,y,x+w,y+h
3. Add padding (30px on all sides)
4. Render rect with group color at 5% fill opacity, 30% stroke opacity, dashed

### Properties
- `fill-opacity: 0.05`
- `stroke-opacity: 0.3`
- `stroke-dasharray: 8,4`
- `stroke-width: 1.5`
- Title text at top-left inside padding

Groups **auto-resize** when elements are dragged.

---

## Drag & Drop

### Behavior
- **Single click + drag** = move element
- **Double click** on drilldown elements = navigate to target level
- Cursor: `grab` (default) → `grabbing` (while dragging)
- Dragged element gets `opacity: 0.85` and drop-shadow

### Implementation Pattern
```javascript
// On mousedown: record element + offset
// On mousemove: update element data (x,y), update transform,
//               re-render arrows + groups
// On mouseup/mouseleave: clear drag state
```

### Key Details
- Use `svg.createSVGPoint()` + `getScreenCTM().inverse()` to convert mouse coordinates to SVG coordinates
- Update the **data object** (not just the DOM) so arrows recalculate correctly
- Elements layer is NOT re-rendered during drag — only the transform attribute changes
- Arrows layer, groups layer, and **why-layer** ARE re-rendered on every move
- All three must be called in the mousemove handler: `renderArrows()`, `renderGroups()`, `renderWhyAnnotations()` (if active)

---

## Layout Guidelines (Initial Positions)

### Context Level (viewBox ~1100x700)
```
Zone TOP:     Persons left + right, Auth provider center-top
Zone CENTER:  Main System (centered, larger box)
Zone BOTTOM:  External systems spread across bottom
```
Spacing: ~200px between persons, ~180px from system to externals

### Container Level (viewBox ~1500x1100)
```
Row 0 (y~30):    Gateway center, External PSP right
Row 1 (y~220):   Core services spread horizontally (150px+ gaps)
Row 2 (y~420):   Kafka, Redis, Notification services
Row 3 (y~520-580): Background workers (Outbox Relay, Scheduler)
Row 4 (y~700+):  All databases spread across bottom
```
**Key**: Spread elements widely. Minimum 150px horizontal gap between containers. Databases on own row at bottom.

### Component Level (viewBox ~1200x800, per container)

Each container with `drillDown: "component:<id>"` gets its own SVG canvas (`svg#svg-component-<container-id>`). The tab label shows the container name.

```
Row 0: API Layer (controllers)
Row 1: Business Layer (services) — most horizontal space
Row 2: Background Workers (right side)
Row 3: Data Access (repositories)
Row 4: Infrastructure details (DBs, caches — small boxes)
```

### Code Level
Grid layout: 3 columns, 24px gaps. Card dimensions are **auto-calculated** from content:
- Width: longest line × 6.6px (monospace char width) + padding, min 300px
- Height: line count × 16.5px (line height) + header 36px + padding, min 120px
- Column width = max card width in that column (aligned grid)
- Row height = max card height in that row (aligned grid)
- ViewBox auto-calculated from total grid dimensions
- `overflow: hidden` on code div (no scrollbars — cards fit their content)

---

## CSS Theme

The complete CSS is defined in `references/engine.js.md` → "CSS to Include" section. Key design principles:

- **Layout:** `body` is a flex column; `.canvas-area` fills remaining space with auto overflow
- **SVG visibility:** Only `svg.active` is displayed; tab switching toggles this class
- **Drag feedback:** `.c4-element.dragging` gets opacity 0.85 + drop-shadow
- **NFR Panel:** Fixed right sidebar 360px, background #FFF9E6, collapsible via `.collapsed`
- **Code Overlay:** Full-screen modal, dark theme #1E1E2E, Catppuccin Mocha syntax colors
- **Print CSS:** Hides chrome, shows all SVGs, NFR panel becomes static

### Element Tooltip (Rich)
- Dark background (#333), white text, max-width 320px
- Follows mouse cursor (offset +14, +18)
- Structure:
  1. **Name** (bold, white)
  2. **[Technology]** (italic, #AAA)
  3. **Description** (normal, 11px)
  4. **Why?** section (if element has `why` field): italic, #89B4FA (blue), prefixed with "Why: "
  5. **Pattern** section (if element has `pattern` field): monospace, #A6E3A1 (green), prefixed with "Pattern: "
  6. **Decisions** (if element has `relatedDecisions`): small links, #F9E2AF (yellow)

### Arrow Tooltip (Rich)
- Triggered by hover on arrow label background rect or arrow path
- Dark background (#2A2A2A), white text, max-width 360px, slightly larger than element tooltip
- Structure:
  1. **Label** (bold, white, 13px)
  2. **Detail** (if `detail` field): normal description of what happens
  3. **Payload** (if `payload` field): monospace block, #A6E3A1 (green), background #1E1E2E, 4px padding, rounded
  4. **Why?** (if `why` field): italic, #89B4FA (blue), prefixed with "Why: "
  5. **Decision** (if `relatedDecision`): link text, #F9E2AF (yellow), e.g., "→ DD-2: Outbox Pattern"

Implementation: Arrow labels and paths get `data-rel-index` attribute. On hover, look up the relationship from `C4.levels[currentLevel].relationships[index]` and build the rich tooltip HTML.

### Legend
- Fixed bottom-left
- Shows line styles: solid (sync), dashed (async)

### Drag Hint
- Fixed bottom-center
- Shows "Elemente per Drag & Drop verschieben | Tasten 1-4"
- Semi-transparent

### Accessibility

```css
.skip-link {
  position: absolute; left: -9999px; top: auto;
  width: 1px; height: 1px; overflow: hidden;
  z-index: 1000; background: #1168BD; color: #fff;
  padding: 8px 16px; font-size: 14px; text-decoration: none;
}
.skip-link:focus {
  position: fixed; left: 16px; top: 16px;
  width: auto; height: auto; overflow: visible;
}
```

- All SVGs have `role="img"` and `aria-label` describing the diagram level
- Each SVG has a `<title>` element as accessible name
- Tab buttons use `role="tab"` and `aria-selected`
- NFR toggle uses `aria-expanded`
- Elements rendered with `tabindex="0"` for keyboard focus
- On `Enter`/`Space` on focused element: show tooltip (same as hover)
- On `Enter` on drillDown element: navigate to target level
- Focus visible indicator: `outline: 2px solid #1168BD; outline-offset: 2px`

### Print CSS

```css
@media print {
  .nav-bar, .legend, .drag-hint, .tooltip, .code-overlay,
  .nfr-toggle, .why-toggle, .skip-link { display: none; }
  .canvas-area { overflow: visible; padding: 0; }
  .canvas-area svg { display: block !important; page-break-inside: avoid; margin-bottom: 20px; }
  .canvas-area svg:not(.active) { display: block !important; }
  .nfr-panel { position: static; transform: none; width: 100%;
    page-break-before: always; border: 1px solid #ccc; }
  body { height: auto; overflow: visible; }
}
```

---

## Syntax Highlighting

Placeholder-based tokenizer to prevent overlapping highlights:

1. **Phase 1 — Extract literals**: Replace comments (block `/**/`, line `//`/`--`/`#`), double-quoted strings, single-quoted strings, and template literals with placeholders. This prevents keywords inside strings from being highlighted.
2. **Phase 2 — Language keywords**: Apply language-specific keyword/type/function highlighting.
   - Supported: SQL, TypeScript/JavaScript, Java/Kotlin, Go, Python, YAML, JSON
3. **Phase 3 — Numbers**: Highlight numeric literals.
4. **Phase 4 — Restore**: Replace placeholders with highlighted spans.

Color mapping (Catppuccin Mocha):
- Keywords: #CBA6F7 (purple)
- Strings: #A6E3A1 (green)
- Numbers: #FAB387 (peach)
- Functions/names: #89B4FA (blue)
- Comments: #6C7086 (gray italic)
- Types: #F9E2AF (yellow)

---

## Interaction Summary

| Action | Effect |
|---|---|
| Click + Drag element | Move element, arrows/groups follow |
| Double-click drilldown element | Navigate to target level (container or specific component view) |
| Hover element | Rich tooltip: name, tech, desc, **why**, **pattern**, decisions |
| Hover arrow label/path | Rich tooltip: label, detail, **payload**, **why**, decision link |
| Click tab | Switch C4 level (component tabs show container name) |
| Press 1 / 2 / 3+ / last | Switch to Context / Container / Component views / Code |
| Click "NFRs" button | Toggle NFR panel |
| Hover design decision (panel) | Highlight related elements (gold dashed stroke) |
| Click code card (Code level) | Open code overlay |
| Press Escape | Close code overlay |
| Breadcrumb click | Navigate back to level |
| Tab (keyboard) | Focus next element in current SVG |
| Enter/Space on focused element | Show tooltip (same as hover) |
| Enter on focused drillDown element | Navigate to target level |

---

## Quality Checklist (before delivery)

- [ ] File opens in browser without JS errors
- [ ] All 4 levels navigable via tabs and keyboard
- [ ] Drag & Drop works on all 3 diagram levels
- [ ] Arrows follow elements during drag
- [ ] Group boundaries resize during drag
- [ ] Double-click drill-down navigates correctly
- [ ] No initial element overlaps (check all levels)
- [ ] All labels readable (no truncation)
- [ ] NFR panel shows all NFRs with metrics
- [ ] Design decision hover highlights correct elements
- [ ] Code snippets display with syntax highlighting and `why` subtitle
- [ ] Code overlay shows line annotations (if defined)
- [ ] Legend visible and correct
- [ ] Element tooltip shows why + pattern when available
- [ ] Arrow tooltip shows payload + why when available
- [ ] Async arrows all have payload tooltips
