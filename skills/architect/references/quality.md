# C4 Architecture Validation Rules

## Overview

42 rules in 7 categories. Each rule has a severity:
- **ERROR** — Must fix. Architecture is broken without it.
- **WARNING** — Should fix. Quality is degraded.
- **INFO** — Nice to have. Improves polish.

Validation levels:
- **Quick** — S-rules only (structural integrity)
- **Standard** — S + C + X rules (recommended before rendering)
- **Thorough** — All rules (recommended for final output)

---

## Category S: Structural Integrity (all ERROR)

| Rule | Check | Fix |
|---|---|---|
| S-01 | All element IDs are unique across all levels (context, container, all component views) | Rename duplicate IDs with level prefix (`ctx-`, `cnt-`, `cmp-<container>-`) |
| S-02 | Every relationship `from` references an existing element in the same level | Remove or fix the relationship |
| S-03 | Every relationship `to` references an existing element in the same level | Remove or fix the relationship |
| S-04 | Every `drillDown` value is valid: `"container:<system-id>"` where system-id exists in `containers`, or `"component:<container-id>"` where container-id exists in `components`. Legacy `"container"` (bare) is acceptable. | Remove or correct the drillDown |
| S-05 | Every code snippet `parentElement` references an existing element ID | Fix element reference or remove snippet |
| S-06 | No self-referencing relationships (`from` !== `to`) | Remove the self-reference |
| S-07 | Every key in `components` references an existing container-level element ID. Every key in `containers` references an existing context-level system element ID (or is `"_default"`). | Remove the orphaned component view or add the container |
| S-08 | Version field is `"2.2"` | Update version |
| S-09 | Every relationship has `async` as boolean (not string, not `protocol: "async"`) | Convert `protocol: "async"` to `async: true` |
| S-10 | Every FR `actor` references an existing context-level `person` or `external_person` element | Fix actor reference |
| S-11 | Every `relatedFrs` in design decisions references an existing FR ID | Fix FR reference or remove |
| S-12 | Every `relatedFrs` in elements references an existing FR ID | Fix FR reference or remove |
| S-13 | Every key in `containers` references an existing context-level system element ID (or is `"_default"`) | Fix key or add system element |
| S-14 | Every system element with `drillDown` starting with `"container"` must have a corresponding entry in `containers` | Add containers entry or remove drillDown |

---

## Category C: Completeness (WARNING/ERROR)

| Rule | Severity | Check | Fix |
|---|---|---|---|
| C-01 | ERROR | Context level has at least one `person` or `external_person` | Add the primary actor |
| C-02 | ERROR | Context level has at least one `system` element | Add at least one main system |
| C-03 | ERROR | Every `containers` entry has at least one element | Add containers — decompose the system |
| C-04 | WARNING | At least one container has `drillDown` starting with `"component"` | Add component decomposition for key container |
| C-05 | WARNING | Every database element has at least one code snippet with matching `parentElement` (schema) | Add schema snippet with `parentElement` referencing the database |
| C-06 | ERROR | Every relationship has a non-empty `label` | Add a descriptive label |
| C-07 | WARNING | Every NFR has a non-empty `metric` | Add a measurable metric |
| C-08 | WARNING | Every design decision has a non-empty `tradeoff` | Document the trade-off |

---

## Category X: Cross-Level Consistency (WARNING/INFO)

| Rule | Severity | Check | Fix |
|---|---|---|---|
| X-01 | WARNING | Every context `person` appears in at least one container-level relationship across any container view (directly or via gateway) | Add the missing relationship or remove the person |
| X-02 | WARNING | Every context `external_system` has a corresponding container-level element or relationship | Add the external service container |
| X-03 | INFO | Every container with `drillDown: "component:..."` has actual component-level elements in `components[containerId]` | Add components or remove drillDown |
| X-04 | INFO | Container-level relationship directions are reflected at component level | Verify component relationships match |
| X-05 | WARNING | Every `components` key has a corresponding container with `drillDown: "component:<key>"`. Every `containers` key should have a corresponding system element with `drillDown: "container:<key>"`. | Add drillDown to the container/system or remove the component/container view |

---

## Category T: NFR & Decision Traceability (WARNING/INFO)

| Rule | Severity | Check | Fix |
|---|---|---|---|
| T-01 | WARNING | Every NFR is referenced by at least one design decision (`relatedNfrs`) | Add a decision that addresses the NFR |
| T-02 | WARNING | Every `relatedElements` in decisions references an existing element (in any level) | Fix element reference or remove |
| T-03 | INFO | No design decisions without `relatedNfrs` (orphan decisions) | Link decision to relevant NFR |
| T-04 | WARNING | Every design decision is referenced by at least one element `relatedDecisions` or relationship `relatedDecision` | Add references from implementing elements/relationships |

---

## Category W: Why-Traceability (WARNING/INFO)

| Rule | Severity | Check | Fix |
|---|---|---|---|
| W-01 | WARNING | Every async relationship (`async: true`) must have a `payload` field describing the event structure | Add payload (e.g., `{ type: SeatReserved, eventId, seatId }`) |
| W-02 | INFO | Elements with `relatedDecisions` should have a `why` field | Add why (e.g., "NFR Latency requires cache") |
| W-03 | WARNING | Relationships with `relatedDecision` should have a `why` field | Add why (e.g., "Outbox Pattern for atomic DB+Event") |
| W-04 | INFO | Elements with `pattern` in description/name or with `relatedDecisions` referencing a pattern decision should have a `pattern` field | Add pattern description |
| W-05 | WARNING | Every code snippet must have a non-empty `why` field explaining its architectural relevance | Add why (e.g., "Zeigt UNIQUE constraint der Idempotency-Key sicherstellt") |

---

## Category F: Functional Requirement Traceability (WARNING/INFO)

| Rule | Severity | Check | Fix |
|---|---|---|---|
| F-01 | WARNING | Every FR with `priority: "must"` is referenced by at least one element's `relatedFrs` | Add `relatedFrs` to the implementing element(s) |
| F-02 | WARNING | Every FR has at least one non-empty acceptance criterion | Add testable acceptance criteria |
| F-03 | INFO | Every FR with `priority: "must"` or `"should"` is referenced by at least one design decision's `relatedFrs` | Link FR to a design decision |
| F-04 | INFO | No elements with `relatedFrs` referencing a `wont`-priority FR | Remove reference or change FR priority |
| F-05 | WARNING | Every FR has a non-empty `priority` field | Set priority (must/should/could/wont) |

---

## Category V: Visual Quality (INFO/WARNING)

| Rule | Severity | Check | Fix |
|---|---|---|---|
| V-01 | WARNING | Max 12 elements per context level | Aggregate into fewer, higher-level elements |
| V-02 | WARNING | Max 18 elements per container level | Combine related containers or use groups |
| V-03 | WARNING | Max 15 elements per component view | Split into multiple component views |
| V-04 | INFO | All element names are max 30 characters | Shorten names |
| V-05 | INFO | All relationship labels are max 40 characters | Shorten labels |
| V-06 | INFO | Technology is specified for all containers | Add technology field |
| V-07 | WARNING | No isolated elements (at least one relationship per element) | Connect or remove the element |
| V-08 | INFO | Max 10 code snippets | Focus on the most architecturally significant |

---

## Validation Output Format

Present results grouped by severity:

```
## Validation Report: [Project Name]

### ERRORS (must fix)
- S-01: Duplicate ID 'reservation-svc' found in context and container level
  → Fix: Rename to 'ctx-reservation-system' and 'cnt-reservation-svc'

### WARNINGS (should fix)
- C-07: NFR 'nfr-03' has empty metric
  → Fix: Add measurable target (e.g., '< 300ms p95')

### INFO (nice to have)
- V-04: Element 'cnt-notification-adapter-service' name is 35 chars (max 30)
  → Fix: Shorten to 'cnt-notify-adapter'

### Summary
- Errors: 0 | Warnings: 2 | Info: 1
- Status: PASS (no errors)
```

## Auto-Fix Capabilities

For these rules, offer to auto-fix:
- **S-01**: Add level prefix to duplicate IDs and update all references
- **S-09**: Convert `protocol: "async"` to `async: true`, `protocol: "sync"` to `async: false`
- **C-06**: Generate label from element names ("→ calls", "→ reads from")
- **V-04/V-05**: Truncate with ellipsis or suggest abbreviation
- **V-06**: Infer technology from element type (database → "PostgreSQL", cache → "Redis")
- **S-08**: Auto-upgrade version to "2.1"
- **F-05**: Default to `"must"` if priority is empty

## Migration Auto-Fix (v1.0 / v2.0 → v2.1)

When validating an older architecture, offer automatic migration:
1. Rename `"component"` → find container with `drillDown: "component"`, move to `"components": { "<container-id>": ... }`
2. Update `drillDown: "component"` → `drillDown: "component:<container-id>"`
3. Convert `protocol: "async"` → `async: true` on all relationships
4. Add `ctx-`, `cnt-`, `cmp-` prefixes to IDs if missing (and update all references)
5. Add empty `"functionalRequirements": []` if missing (v2.0 → v2.1)
6. Set `version: "2.1"`
