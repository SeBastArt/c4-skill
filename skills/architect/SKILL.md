# C4 Architecture Skill

## Trigger

Activate when the user asks to:
- Create, design, or model a software architecture
- Generate C4 diagrams or architecture visualizations
- Render an existing architecture.json to HTML
- Validate or review an architecture model
- Keywords: "C4", "Architektur", "architecture", "system design", "Systemarchitektur"

## Overview

This skill creates **interactive C4 architecture diagrams** as self-contained HTML files with embedded SVG. It covers the full pipeline: guided discovery, structured data model (JSON), validation, and rendering.

**Load references on-demand per phase — NOT all at once:**

### Tier 1 — Always (minimal baseline):
- `references/json-schema.md` — Data model definition (v2.1, multi-component, FRs + NFRs)
- `references/quality.md` — Validation rules (42 rules, 7 categories)

### Tier 2 — Phase 3 (NFR collection):
- `references/pattern-catalog.md` — Navigator: NFR→Pattern Quick-Reference, Pattern-Stacks

### Tier 3 — Phase 5-6 (Container & Component decomposition):
- `references/paradigms-guide.md` — Load when choosing decomposition strategy (DDD, EDA, CQRS, etc.)
- `references/pattern-deep-dive.md` — Load when applying specific patterns to containers/components

### Tier 4 — Phase 8 (Design Decisions):
- `references/decision-frameworks.md` — ADR, Canvas, ATAM, TARA, Quality Scenarios, Scorecards

### Tier 5 — Phase 10 (Render):
- `references/render-spec.md` — SVG, CSS, JS, layout, colors, accessibility
- `references/engine.js.md` — Complete rendering engine reference code
- `templates/base.html` — HTML skeleton template

### On-demand (only when explicitly needed):
- `references/example.json` — Load only to check format/structure when unsure
- `references/structurizr-export.md` — Load only in Export Mode

**Rule:** Never load Tier 3-5 references in Phase 1-2. Never load Tier 5 before Phase 10. This preserves context window for the actual architecture discussion.

## Output

A single self-contained `.html` file containing:
- SVG canvases: Context, Container, 1-N Component views (one per decomposed container), Code
- Tab navigation with breadcrumbs (component tabs show container name)
- Requirements panel (collapsible right sidebar: FRs, NFRs, Design Decisions)
- Code snippet overlays (dark theme, Catppuccin Mocha syntax highlighting)
- Drill-down navigation between levels (double-click)
- Rich tooltips on elements (why, pattern, decisions) and arrows (payload, why, detail)
- Keyboard navigation (Tab between elements, Enter to drill-down, 1-N for levels)
- Accessibility (ARIA labels, skip-link, print CSS)
- All CSS and JS embedded inline — no external dependencies

## Process: Guided Architecture Workshop

Work through these phases **sequentially**. Each phase ends with a confirmation from the user before proceeding. Ask focused questions — do not overwhelm. Summarize your understanding after each phase.

---

### Phase 1: Project Scope

**Goal:** Understand what we are building and for whom.

Ask the user:
1. **System name** — What is this system called?
2. **Core purpose** — What does it do in one sentence?
3. **Primary actors** — Who or what uses the system? (Users, admins, external systems, scheduled jobs)
4. **Key capabilities** — What are the 3-5 most important things the system does? (These become inputs for Phase 2: FRs)
5. **External dependencies** — What external systems does it integrate with? (Payment providers, auth, email, third-party APIs)

**Output:** A summary paragraph that the user confirms.

---

### Phase 2: Functional Requirements (FRs)

**Goal:** Capture what the system must do — structured and testable.

Transform the key use cases from Phase 1 into structured Functional Requirements. For each FR, ask:

1. **Title** — Short name (e.g., "Sitzplatz reservieren")
2. **Description** — What does the system do, from the actor's perspective?
3. **Actor** — Which person/external system triggers this? (Must reference a context-level element ID)
4. **Priority** — MoSCoW: must / should / could / wont
5. **Acceptance Criteria** — 2-5 testable conditions per FR (e.g., "Sitz wechselt zu Status HELD", "Reservierung hat eine TTL von 8 Minuten")

**Rules:**
- Every FR MUST have at least one acceptance criterion — if it's not testable, it's not a requirement
- Use the actor's perspective: "Der Kunde kann..." not "Das System soll..."
- Focus on the "what", not the "how" — implementation details come in later phases
- Group related use cases into one FR when they share the same actor and domain concept
- Mark FRs as `wont` to explicitly document what is out of scope
- Typical projects have 5-15 FRs

**Output:** A numbered FR list with id, title, description, actor, priority, and acceptance criteria.

---

### Phase 3: Non-Functional Requirements (NFRs)

**Goal:** Identify the quality attributes that drive architectural decisions.

Walk through each category and ask if it is relevant. For each relevant NFR, get a **measurable metric**:

| Category | Example Question |
|---|---|
| **Performance** | What peak load do you expect? (requests/sec, concurrent users) |
| **Availability** | What uptime is required? (99.9%? 99.99%?) |
| **Latency** | What response times are acceptable? (p95, p99) |
| **Consistency** | Are there invariants that must never be violated? (e.g., no overselling) |
| **Scalability** | How should the system grow? (horizontal, vertical, auto-scaling) |
| **Security** | Compliance requirements? (PCI-DSS, GDPR, SOC2) Auth model? |
| **Observability** | What must be monitored? (metrics, traces, logs, alerts) |
| **Auditability** | Must actions be traceable? (audit logs, immutable records) |

**Rules:**
- Every NFR MUST have a measurable metric — no vague statements like "should be fast"
- Identify which NFRs will drive architectural decisions (these become inputs for Phase 8)
- Typical projects have 3-7 relevant NFRs

**Pattern-Hinweis:** Nach dem Erfassen aller NFRs, schlage relevante Patterns aus `references/pattern-catalog.md` vor:
- Performance/Latency → CQRS, Cache-aside, CDN, Read Replicas
- Availability → Circuit Breaker, Bulkhead, Retry & Backoff
- Consistency → Outbox, Idempotency, Saga, Event Sourcing
- Scalability → CQRS, EDA, Horizontal Scaling, SCS
- Security → API Gateway, mTLS (Sidecar), ACL
- Observability → Sidecar (OpenTelemetry), Structured Logging
- Auditability → Event Sourcing, Append-only Logs

Frage den User: "Basierend auf den NFRs schlage ich folgende Patterns vor: [...]. Welche davon sind relevant?" Diese Vorauswahl beschleunigt Phasen 5-8.

**Output:** A numbered NFR list with id, category, title, metric, and approach.

---

### Phase 4: Context Level (C4 Level 1)

**Goal:** Define the system boundary — who interacts with the system and what external systems exist.

Build the context diagram by placing:
- **Persons** (human actors) — from Phase 1 actors
- **The main system** (one box representing the entire system)
- **External systems** — from Phase 1 dependencies

For each relationship, define:
- Direction (who initiates?)
- Label (short: what data/action flows?)
- **Detail** (longer: what happens in this communication?)
- **Payload** (for async: what is the event/message structure?)
- **Why** (why does this communication exist?)
- Sync vs. async
- Protocol if known (REST, gRPC, webhook, email)

**Rules:**
- Maximum 8-10 elements at context level
- Every person and external system must have at least one relationship
- The main system is always present
- No internal details — this is the 30,000-foot view
- Every async relationship MUST have a payload description

**Output:** Present the context diagram as a structured list for confirmation.

---

### Phase 5: Container Level (C4 Level 2)

**Goal:** Decompose the main system into deployable containers.

Guide the decomposition by asking about:
1. **API layer** — How do clients reach the system? (API Gateway, Load Balancer, CDN)
2. **Core services** — What are the main processing units? (microservices, monolith modules)
3. **Data stores** — What databases, caches, and queues are needed?
4. **Async infrastructure** — Message brokers, schedulers, background workers?
5. **External integrations** — How does each external system connect?

For each container, capture:
- Name, type, technology choice
- Read-heavy vs. write-heavy
- Stateful vs. stateless
- **Why does this container exist?** — Which NFR or business need drives it?
- **Pattern** — What architectural pattern does it implement? (cache-aside, outbox, CQRS, etc.)

For each relationship:
- Source, target, label, protocol
- Sync (solid line) vs. async (dashed line)
- **Detail** — What happens in this communication?
- **Payload** — For async: what is the event structure? (e.g., `{ type: SeatReserved, eventId, seatId }`)
- **Why** — Why is this communication needed? Link to design decision if applicable.

Organize containers into **groups** (logical clusters):
- Core Services
- Persistence / Data Stores
- Async Infrastructure
- External

**Pattern-Stacks anwenden:** Basierend auf den in Phase 3 vorausgewählten Patterns, schlage bewährte Kombinationen vor (siehe `references/pattern-catalog.md`):
- **Event-Driven Consistency:** Outbox + Idempotency + Retry → Service + Outbox-DB + Relay + Broker
- **Resilience:** Circuit Breaker + Retry + Bulkhead → in Services oder als Sidecar
- **CQRS + Event Sourcing:** Command Service + Event Store + Projection + Read DB + Broker
- **Migration:** Strangler Fig + ACL + CDC → Gateway + Legacy + New Services + CDC-Connector
- **Distributed Transactions:** Saga + Outbox + Idempotency → Orchestrator + Services + Broker

Für jeden eingesetzten Pattern:
1. Setze `element.pattern` mit konkreter Beschreibung (z.B. "Outbox Pattern: Poll → Publish → Mark Published")
2. Setze `element.why` mit NFR-Begründung
3. Verknüpfe mit `element.relatedDecisions`

**Rules:**
- Maximum 15-18 elements
- Every container must have at least one inbound or outbound relationship
- Technology choices should be justified by NFRs (e.g., Redis cache because of latency NFR)
- Groups help visual readability — use 3-5 groups
- Every async relationship MUST have a payload and a why
- Every element that implements a pattern MUST document it

**Output:** Present the container diagram as a structured list with groups.

---

### Phase 6: Component Level (C4 Level 3)

**Goal:** Show the internal structure of 1-3 key containers. Each gets its own component view.

Ask the user: **Which containers are architecturally interesting?** (Usually the ones with the most business logic or the most complex patterns.)

For each selected container:
- Set `drillDown: "component:<container-id>"` on the container element
- Create a `components["<container-id>"]` entry with its own elements, relationships, and groups
- Use `cmp-<container-short>-` prefix for component IDs to avoid collisions

Decompose each container into layers:
1. **API Layer** — Controllers, route handlers, input validation
2. **Business Layer** — Domain services, use cases, business rules
3. **Background Workers** — Event consumers, scheduled jobs, relay processes
4. **Data Access Layer** — Repositories, data mappers, cache strategies

For each component, capture:
- Name, type (controller, service_class, repository, event_handler, background_worker, adapter)
- Key methods/responsibilities (as bullet list)
- Error handling strategy (what HTTP codes, what exceptions)

**Rules:**
- Maximum 12-15 elements per container decomposition
- Every component must connect to at least one other component
- Show the flow: API -> Service -> Repository -> DB
- Include error handling paths (e.g., OptimisticLockError -> 409 Conflict)

**Output:** Present each container's components as a layered list.

---

### Phase 7: Code Level (C4 Level 4)

**Goal:** Show concrete implementation for critical paths.

Identify code snippets for:
1. **Database schemas** — Table definitions, indexes, constraints that enforce NFRs
2. **Critical operations** — The core write path (e.g., reserve, book, release)
3. **Patterns** — Idempotency, caching, outbox, saga — whatever the architecture uses
4. **Error handling** — How does the system handle failures?

For each snippet:
- Language (SQL, TypeScript, Java, Go, etc.)
- Title describing what it shows
- **Why (required)** — One sentence explaining WHY this code is architecturally relevant. What design decision does it prove? What NFR does it enforce? Example: "Zeigt UNIQUE constraint der Idempotency-Key-Duplikate verhindert (DD-01)"
- **Annotations** — Mark 2-4 key lines with inline explanations (shown as `← hint` in the code overlay). Focus on the lines that implement the pattern or enforce the NFR.
- Link to the parent element it belongs to

**Rules:**
- Code snippets must be realistic and runnable (not pseudo-code)
- Every database container should have at least one schema snippet
- Every snippet MUST have a `why` field — code without context is useless
- Every snippet SHOULD have 2-4 line annotations for the architecturally significant lines
- Show the patterns that justify design decisions
- Maximum 8-10 snippets — focus on the interesting parts

**Output:** Present code snippets for review.

---

### Phase 8: Design Decisions

**Goal:** Document the key architectural decisions with trade-offs.

For each important decision:
1. **Title** — What was decided? (e.g., "Outbox Pattern for Event Publishing")
2. **Context** — What problem does this solve?
3. **Decision** — What was chosen and why?
4. **Trade-off** — What are the downsides?
5. **Alternatives** — What else was considered?
6. **Related NFRs** — Which NFRs drive this decision?
7. **Related FRs** — Which FRs does this decision support?
8. **Related Elements** — Which containers/components implement this?

**Rules:**
- Every NFR should be addressed by at least one design decision
- Every `must`-priority FR should be traceable to at least one element
- Decisions must reference concrete elements (not abstract concepts)
- Trade-offs must be honest — every decision has downsides
- Typical projects have 3-7 design decisions
- Every pattern used in Phase 5/6 MUST have a corresponding design decision

**Qualitäts-Szenario pro Decision:** Für jede Design Decision, formuliere mindestens ein Qualitäts-Szenario nach dem Template:
```
Wenn [Stimulus] unter [Bedingung] dann [erwartete Reaktion] gemessen an [Metrik]
```
Beispiel: "Wenn der Kafka-Broker ausfällt, unter normaler Last, dann bleiben Events in der Outbox und werden nach Recovery innerhalb von < 5s published, gemessen an Event-Delivery-Rate = 100%."

**Output:** Present decisions with quality scenarios for confirmation.

---

### Phase 9: Assembly & Validation

**Goal:** Assemble everything into `architecture.json` and validate.

1. Build the complete JSON following `references/json-schema.md` (v2.1 format)
2. Use `components` dictionary (not singular `component`) for component views
3. Ensure all IDs use correct prefixes (`ctx-`, `cnt-`, `cmp-<container>-`)
4. Ensure all relationships use `async: true/false` (boolean, not `protocol: "async"`)
5. Run ALL validation rules from `references/quality.md` (42 rules, 7 categories)
6. Fix any errors, warn about warnings
7. Write the validated `architecture.json` to disk

**Validation is not optional.** Every architecture must pass at minimum:
- All structural integrity rules (S-01 to S-12) — zero errors
- All completeness rules (C-01 to C-08) — zero errors, warnings acceptable
- All cross-level consistency rules (X-01 to X-05) — warnings acceptable

---

### Phase 10: Render

**Goal:** Generate an interactive, draggable HTML visualization.

**Architecture:** All SVG content is rendered dynamically from a JavaScript `C4` data object. No hardcoded SVG paths. This enables drag & drop with auto-updating arrows and groups.

**Steps:**
1. Load `templates/base.html` as skeleton
2. Load `references/engine.js.md` — use the **complete rendering engine code** from this reference
3. Follow `references/render-spec.md` for all visual and interaction decisions
4. Build the `C4` JavaScript data object from architecture.json:
   - `C4.colors` — type-to-color mapping (from render-spec color palette)
   - `C4.levels.context` — elements with ALL fields (see render-spec JS data structure)
   - `C4.levels.container` — same structure
   - `C4.levels.components["<container-id>"]` — one entry per decomposed container, same structure
   - `C4.code.snippets` — code cards with `{id, title, lang, code, parentElement, annotations}`
   - `C4.frs` — FR data for the panel
   - `C4.nfrs` — NFR data for the panel
   - `C4.designDecisions` — decision data for the panel and Why-Layer
5. Calculate initial element positions using the layout algorithm from json-schema.md
6. Generate one `<svg id="svg-component-<container-id>">` per component view (NO local `<defs>` — shared defs SVG provides filter `#ds` and marker `#af`)
7. Generate component tabs dynamically (one per component view, labeled with container name)
8. Embed the rendering engine from `references/engine.js.md` — do NOT rewrite, copy the reference code
9. Replace ALL template placeholders:
   - `{{PROJECT_NAME}}` — from `project.name`
   - `{{CSS_THEME}}` — full CSS from engine.js.md "CSS to Include" section
   - `{{ENGINE_JS}}` — full JS from engine.js.md "Complete Engine Code" section
   - `{{C4_DATA_OBJECT}}` — the C4 JavaScript data object
   - `{{CTX_W}}` / `{{CTX_H}}` — context viewBox (default: 1100 x 700)
   - `{{CNT_W}}` / `{{CNT_H}}` — container viewBox (default: 1500 x 1100)
   - `{{CODE_W}}` / `{{CODE_H}}` — code viewBox (auto-calculated, default: 1100 x 600)
   - `{{COMPONENT_SVGS}}` — one `<svg>` per component view (NO local defs)
   - `{{COMPONENT_TABS}}` — one `<button>` per component view
   - `{{FR_PANEL_HTML}}` — FR items HTML
   - `{{NFR_PANEL_HTML}}` — NFR items HTML
   - `{{DESIGN_DECISIONS_HTML}}` — DD items HTML with `data-elements` attribute
10. Write the single HTML file to disk

**Key rendering functions:**
- `getConnectionPoint(element, targetCenter)` — finds nearest edge intersection for arrow endpoints
- `renderArrows(svgId, levelData)` — clears and re-renders all arrows from relationship data
- `renderGroups(svgId, levelData)` — auto-calculates group bounding boxes from member elements
- `svgShape(element, colors)` — returns SVG markup for element type (person, database, gateway, etc.)
- `highlightCode(code, lang)` — regex-based syntax highlighting

**Quality checks before delivery:** See full checklist in `references/render-spec.md` → "Quality Checklist". All items must pass.

---

## Quick Mode

If the user says "quick" or provides a very detailed specification upfront, compress Phases 1-8 into a single analysis step. Still validate (Phase 9) and render (Phase 10) with full rigor.

## Render-Only Mode

If an `architecture.json` already exists:
- Skip Phases 1-8
- Load the JSON
- Validate (Phase 9)
- Render (Phase 10)

Trigger: User says "render", "visualize", or provides a path to an existing architecture.json.

## Validate-Only Mode

If the user wants to check an existing architecture.json:
- Load the JSON
- Run all validation rules
- Present report with fixes

Trigger: User says "validate", "check", or "review" with an architecture.json.

## Amend Mode

If the user wants to modify an existing architecture:
1. **Load** the existing `architecture.json`
2. **Scope** — Ask: What should change? (new container, new FR, new NFR, changed relationship, new component view, etc.)
3. **Impact Analysis** — Show which elements, relationships, decisions, and NFRs are affected by the change
4. **Apply** — Make the targeted changes, preserving everything else
5. **Cascade Check** — Verify cross-level consistency:
   - New container → Does it need component decomposition?
   - Removed relationship → Are elements now orphaned?
   - New FR → Which elements implement it? Is priority set?
   - New NFR → Is there a design decision addressing it?
   - Changed element → Do related decisions/snippets need updating?
6. **Validate** (Phase 9) — Run full validation
7. **Diff Summary** — Present a before/after diff of changed elements
8. **Render** (Phase 10) — Re-render the updated HTML

**Rules:**
- Never delete elements without explicit user confirmation
- Show the diff before writing to disk
- Preserve all positions/coordinates of unchanged elements
- If a change invalidates existing design decisions, flag them

Trigger: User says "erweitern", "ändern", "amend", "update", "hinzufügen", "entfernen" with an existing architecture.

## Export Mode

Export the architecture to external formats for interoperability with other tools.

Trigger: User says "export", "exportieren", "Structurizr", "PlantUML".

See `references/structurizr-export.md` for Structurizr DSL export specification.

## Language

- Follow the user's language. If they speak German, respond in German.
- Element names in the architecture should match the project's domain language.
- Technical terms (NFR, REST, API, etc.) stay in English.

## Critical Quality Principles

1. **Every element answers three questions:** What is it? (name) What technology? How does it fit? (relationships)
2. **FRs define what, NFRs define how well, decisions drive elements** — Both chains must be traceable
3. **No orphans** — Every element must be connected
4. **Levels tell different stories** — Context = who, Container = what, Component = how, Code = proof
5. **Honest trade-offs** — Every decision has downsides. Document them.
6. **Measurable over vague** — "20k TPS" not "high performance"
7. **Self-contained output** — One HTML file, zero dependencies, works offline
8. **Every arrow explains what flows and why** — Labels show the "what", tooltips show the payload structure and the "why". Async arrows always describe their event payload.
9. **Architecture is self-documenting** — A viewer should understand every design choice without asking the architect. Elements have "why" tooltips, arrows have payloads, code snippets explain their architectural relevance, and the NFR panel links decisions to elements.
