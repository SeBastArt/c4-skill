# C4 Architecture JSON Schema

## Top-Level Structure

```json
{
  "version": "2.2",
  "project": { ... },
  "functionalRequirements": [ ... ],
  "nfrs": [ ... ],
  "designDecisions": [ ... ],
  "context": { "elements": [], "relationships": [], "groups": [] },
  "containers": {
    "<system-id>": { "elements": [], "relationships": [], "groups": [] }
  },
  "components": {
    "<container-id>": { "elements": [], "relationships": [], "groups": [] }
  },
  "code": { "snippets": [] }
}
```

### Migration von v1.0 / v2.0

Falls ein `"component"` (Singular) Objekt existiert, wird es automatisch migriert:
1. Finde den Container mit `drillDown: "component"` im Container-Level
2. Verschiebe das `component`-Objekt unter `components["<container-id>"]`
3. Entferne das alte `component`-Feld

### Migration von v2.1 → v2.2

Falls ein `"container"` (Singular) Objekt existiert, wird es automatisch migriert:
1. Finde das `system`-Element im Context-Level mit `drillDown: "container"`
2. Erstelle `"containers": { "<system-id>": <old-container-data> }` wobei `<system-id>` die ID dieses System-Elements ist
3. Falls kein Element mit `drillDown: "container"` gefunden wird, verwende den Schlüssel `"_default"`
4. Entferne das alte `container`-Feld
5. Aktualisiere `version` auf `"2.2"`

## Project

```json
{
  "name": "string (required)",
  "description": "string (required) — one-sentence purpose",
  "author": "string",
  "date": "string (ISO 8601)"
}
```

## Functional Requirements (FRs)

```json
{
  "id": "fr-01",
  "title": "string (required) — short name (e.g., 'Sitzplatz reservieren')",
  "description": "string (required) — what the system must do, from the actor's perspective",
  "actor": "string (required) — element ID of the primary actor (e.g., 'ctx-customer')",
  "priority": "must | should | could | wont",
  "acceptanceCriteria": ["string (required) — testable conditions that define 'done'"]
}
```

**Rules:**
- Every FR must have at least one acceptance criterion — untestable requirements are rejected
- `actor` must reference an existing context-level `person` or `external_person` element
- `priority` follows MoSCoW: `must` = mandatory for MVP, `should` = important, `could` = nice-to-have, `wont` = explicitly excluded (documented for clarity)
- Typical projects have 5-15 FRs

## NFRs

```json
{
  "id": "nfr-01",
  "category": "Performance | Availability | Latency | Consistency | Scalability | Security | Observability | Auditability",
  "title": "string — short name (e.g., 'Peak Load')",
  "metric": "string (required) — measurable target (e.g., '20k TPS weltweit')",
  "approach": "string — how the architecture addresses this",
  "details": ["string — additional bullet points"]
}
```

**Rule:** Every NFR must have a non-empty `metric`. Vague NFRs are rejected by validation.

## Design Decisions

```json
{
  "id": "dd-01",
  "title": "string (required)",
  "context": "string — what problem does this solve?",
  "decision": "string — what was chosen and why?",
  "tradeoff": "string (required) — what are the downsides?",
  "alternatives": ["string — what else was considered?"],
  "qualityScenario": "string — testable quality scenario: 'Wenn [Stimulus] unter [Bedingung] dann [Reaktion] gemessen an [Metrik]'",
  "relatedNfrs": ["nfr-01"],
  "relatedFrs": ["fr-01"],
  "relatedElements": ["container-id or component-id"]
}
```

**Rule:** Every design decision must have a non-empty `tradeoff` and reference at least one NFR or FR. Quality scenarios are strongly recommended for pattern-based decisions.

## C4 Levels: Elements

### Context Level Element Types

| Type | Use For |
|---|---|
| `person` | Human actor internal to the organization |
| `external_person` | Human actor outside the organization |
| `system` | A system being described (one or more allowed) |
| `external_system` | Systems outside the boundary |

### Container Level Element Types

| Type | Use For | Visual |
|---|---|---|
| `gateway` | API Gateway, Load Balancer | Hexagon/shield |
| `webapp` | Frontend, SPA, SSR app | Rounded rect |
| `api` | REST/GraphQL API service | Rounded rect |
| `service` | Backend service, microservice | Rounded rect |
| `database` | Relational/NoSQL database | Cylinder |
| `cache` | Redis, Memcached | Rounded rect + bolt |
| `message_broker` | Kafka, RabbitMQ, SQS | Dashed rounded rect |
| `cdn` | Content delivery network | Rounded rect |
| `scheduler` | Cron jobs, scheduled tasks | Rounded rect |
| `queue` | Task queue, job queue | Dashed rounded rect |
| `external_service` | External API, PSP, auth provider | Gray rounded rect |

### Component Level Element Types

| Type | Use For |
|---|---|
| `controller` | REST controllers, route handlers |
| `service_class` | Domain services, use cases |
| `repository` | Data access, ORM wrappers |
| `event_handler` | Event consumers, subscribers |
| `background_worker` | Outbox relay, pollers, cron handlers |
| `adapter` | External system adapters, notification channels |
| `validator` | Input validators, business rule checks |
| `factory` | Object creation, builder patterns |
| `facade` | Simplified interfaces to subsystems |

## Element Schema

```json
{
  "id": "string (required) — unique across ALL levels (e.g., 'ctx-customer', 'cnt-reservation-svc', 'cmp-seat-repo')",
  "type": "string (required) — from type tables above",
  "name": "string (required) — max 30 characters",
  "description": "string (required) — what does this element do?",
  "technology": "string — tech stack (e.g., 'Node.js / Express', 'PostgreSQL 15', 'Redis 7')",
  "drillDown": "string — target level: 'container:<system-id>' (system→containers), 'component:<container-id>' (container→components). Legacy: bare 'container' redirects to first container view.",
  "relatedDecisions": ["string — decision IDs"],
  "relatedFrs": ["string — functional requirement IDs this element implements"],
  "why": "string — WHY does this element exist? Which NFR or business need drives it?",
  "pattern": "string — what architectural pattern does this implement and how? (e.g., 'Cache-aside with TTL 5s')",
  "position": {
    "zone": "top | center | bottom",
    "row": 0,
    "col": 0
  }
}
```

### ID Naming Convention

Use prefixes to avoid collisions across levels:
- Context: `ctx-` (e.g., `ctx-customer`, `ctx-auth-provider`)
- Container: `cnt-` (e.g., `cnt-reservation-svc`, `cnt-seats-db`)
- Component: `cmp-<container-short>-` (e.g., `cmp-res-seat-repo`, `cmp-ord-payment-handler`)

Component IDs include a short container identifier to avoid collisions when multiple containers are decomposed. Example: `cmp-res-` for Reservation Service components, `cmp-ord-` for Order Service components.

### Position Hints

The `position` field guides initial layout placement. The renderer translates these hints to pixel coordinates using the layout algorithm below.

- `zone: "top"` — Persons, clients, entry points
- `zone: "center"` — Core services, business logic
- `zone: "bottom"` — Data stores, external systems, infrastructure

`row` and `col` are relative positions within a zone (0-based).

### Layout Algorithm (Position Hints → Pixel Coordinates)

The `calculateInitialPositions(level, elements)` function converts position hints to `{x, y, w, h}`:

**Default Element Dimensions by Type:**

| Type | Width | Height |
|---|---|---|
| `person`, `external_person` | 120 | 155 |
| `system` | 240 | 100 |
| `external_system` | 180 | 80 |
| `gateway` | 180 | 90 |
| `service`, `api`, `webapp` | 180 | 90 |
| `database` | 160 | 80 |
| `cache`, `cdn`, `scheduler` | 160 | 75 |
| `message_broker`, `queue` | 180 | 75 |
| `external_service`, `adapter` | 160 | 75 |
| `controller`, `service_class`, `repository` | 170 | 70 |
| `event_handler`, `background_worker` | 170 | 70 |
| `validator`, `factory`, `facade` | 150 | 65 |

**Calculation:**

```
ViewBox per level:
  context:   1100 x 700
  container: 1500 x 1100
  component: 1200 x 800
  code:      auto (3 columns, 340x250 cards, 20px gap)

Zone Y-offsets (base Y for each zone):
  context:   top=40, center=250, bottom=500
  container: top=30, center=220, bottom=600
  component: top=30, center=200, bottom=500

X calculation:
  x = paddingLeft + col * (defaultWidth + horizontalGap)
  paddingLeft = 60
  horizontalGap: context=200, container=150, component=140

Y calculation:
  y = zoneBaseY + row * (defaultHeight + verticalGap)
  verticalGap: context=40, container=50, component=40

Centering:
  After calculating all positions, center the entire layout horizontally
  within the viewBox if total width < viewBox width.
```

Elements are **never** placed overlapping. If two elements would overlap after calculation, the later element shifts right by `defaultWidth + horizontalGap`.

After initial placement, positions are stored as `{x, y, w, h}` on the element in the C4 JS data object. Drag & Drop updates these values at runtime.

## Relationships

```json
{
  "from": "string (required) — source element ID",
  "to": "string (required) — target element ID",
  "label": "string (required) — short label on the line, max 40 characters",
  "protocol": "string — REST, gRPC, AMQP, SQL, WebSocket, SMTP (Structurizr export only)",
  "bidirectional": false,
  "async": false,
  "detail": "string — longer description of what happens in this communication",
  "payload": "string — data structure that flows (e.g., '{ type: SeatReserved, eventId, seatId, userId, orderId }')",
  "why": "string — WHY does this communication exist? What architectural reason?",
  "relatedDecision": "string — decision ID that explains this design choice"
}
```

**Visual mapping:**
- `async: false` → solid arrow line (synchronous)
- `async: true` → dashed arrow line (asynchronous)
- `bidirectional: true` → arrowheads on both ends

## Groups

```json
{
  "name": "string (required) — displayed as group title",
  "elementIds": ["string — IDs of elements in this group"]
}
```

Groups are visual containers that cluster related elements. They render as a labeled dashed background rectangle. All groups render the same visual style.

## Code Snippets

```json
{
  "id": "string (required)",
  "parentElement": "string (required) — element ID this snippet belongs to",
  "language": "sql | typescript | javascript | java | go | python | yaml | json",
  "title": "string (required) — what does this snippet show?",
  "why": "string (required) — WHY is this code architecturally relevant? What design decision does it prove?",
  "code": "string (required) — the actual code, use \\n for newlines",
  "annotations": [
    {
      "line": 3,
      "text": "Explanation of what this line does"
    }
  ]
}
```

## Consistency Rules (enforced by validation)

1. All element IDs must be unique across ALL levels
2. All relationship `from`/`to` must reference existing element IDs within the same level
3. All `drillDown` targets must be valid: `"container:<system-id>"` where `<system-id>` exists as a key in `containers`, or `"component:<container-id>"` where `<container-id>` exists as a key in `components`
4. All `relatedNfrs` in decisions must reference existing NFR IDs
5. All `relatedElements` in decisions must reference existing element IDs
6. No self-referencing relationships (from === to)
7. Every key in `components` must reference an existing container-level element ID; every key in `containers` must reference an existing context-level system element ID (or `_default` for backward compat)
8. Every container with `drillDown` starting with `"component"` must have a corresponding entry in `components`
9. Every code snippet `parentElement` must reference an existing element ID
10. All `relatedFrs` in decisions must reference existing FR IDs
11. All `relatedFrs` in elements must reference existing FR IDs
12. Every FR `actor` must reference an existing context-level `person` or `external_person` element
13. Every key in `containers` should reference an existing context-level `system` element ID (or be `_default` for backward compat)
14. Every system element with `drillDown` starting with `"container"` must have a corresponding entry in `containers`
