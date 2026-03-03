# Paradigmen-Guide — Architektur-Denkmodelle für den C4-Workshop

Dieses Dokument hilft dem Skill, das **richtige Architektur-Paradigma** für ein System zu empfehlen und die **Konsequenzen für die C4-Modellierung** zu erklären.

---

## Entscheidungsbaum: Welches Paradigma?

```
Ist das System fachlich komplex mit mehreren Domänen?
├── Ja → DDD (Bounded Contexts → Container-Grenzen)
│         ├── Mehrere Teams? → DDD + SCS (Self-Contained Systems)
│         ├── Async Workflows? → DDD + EDA
│         └── Read/Write sehr unterschiedlich? → DDD + CQRS
└── Nein (technisch getrieben)
    ├── Viele externe Integrationen? → Hexagonal Architecture
    ├── Event-getriebene Workflows? → EDA
    ├── Volle Auditierbarkeit nötig? → Event Sourcing + CQRS
    ├── Monolith → Microservices? → Strangler Fig + Clean Architecture
    └── Einfaches CRUD? → Layered Architecture (kein spezielles Paradigma)
```

---

## 1. Domain-Driven Design (DDD)

### Kernkonzepte

| Konzept | Erklärung | C4-Mapping |
|---|---|---|
| **Ubiquitous Language** | Eine Sprache für Fachbereich und Code | Element-Namen = fachliche Begriffe |
| **Bounded Context** | Abgeschlossene Fachdomäne mit eigenem Modell | → Container-Grenze |
| **Aggregate** | Konsistenzgrenze innerhalb eines Bounded Context | → Component-Grenze |
| **Domain Event** | Fachliches Ereignis ("OrderPlaced", "SeatReserved") | → Async Relationship mit Payload |
| **Repository** | Zugriff auf Aggregate | → Repository-Component |
| **Domain Service** | Logik die keinem Aggregate gehört | → Service-Component |
| **Anti-Corruption Layer** | Übersetzung zwischen Bounded Contexts | → Adapter-Container/Component |
| **Context Map** | Beziehungen zwischen Bounded Contexts | → Context-Level Relationships |

### Context Map Patterns (Beziehungen zwischen BCs)

| Pattern | Bedeutung | C4-Darstellung |
|---|---|---|
| **Shared Kernel** | Gemeinsamer Code/Modell | Shared Library (kein eigener Container) |
| **Customer/Supplier** | Upstream liefert, Downstream konsumiert | Sync Relationship mit Richtungspfeil |
| **Conformist** | Downstream übernimmt Upstream-Modell 1:1 | Relationship ohne Transformation |
| **ACL** | Downstream schützt sich vor Upstream | Adapter-Component/Container |
| **Open Host Service** | Upstream bietet stabile API | API-Container mit Versioning |
| **Published Language** | Gemeinsames Austauschformat (JSON Schema, Protobuf) | Schema Registry Container |
| **Separate Ways** | Kein Integration — komplett entkoppelt | Keine Relationship |

### Wann DDD NICHT

- Einfaches CRUD ohne fachliche Komplexität → Over-Engineering
- Prototyp / MVP → DDD erst ab Phase 2
- Single-Team, Single-Domain → unnötige Abstraktionslayer
- Reines Daten-Pipeline-System → EDA besser geeignet

### Strategic Design → C4 Mapping

```
Bounded Context "Reservierungen"    → Container: cnt-reservation-svc
  Aggregate "Seat"                  → Component: cmp-res-seat-repo + cmp-res-service
  Domain Event "SeatReserved"       → Async Relationship: payload { type: SeatReserved, ... }
  Repository "SeatRepository"       → Component: cmp-res-seat-repo

Bounded Context "Bestellungen"      → Container: cnt-order-svc
  Aggregate "Order"                 → Component: cmp-ord-order-repo + cmp-ord-service
```

---

## 2. Event-Driven Architecture (EDA)

### Kernkonzepte

| Konzept | Erklärung |
|---|---|
| **Event** | Immutable Fakt: "etwas ist passiert" (SeatReserved, PaymentConfirmed) |
| **Command** | Anforderung: "tu etwas" (ReserveSeat, ProcessPayment) |
| **Event Notification** | Leichtgewichtig: nur Signal + ID, Consumer holt Details selbst |
| **Event-Carried State Transfer** | Schwergewichtig: Event enthält alle Daten, Consumer braucht keinen Callback |
| **Event Sourcing** | Zustand = Sequenz aller Events (kein aktueller State gespeichert) |

### Event Design — Crucial Details

**Naming Convention:** Vergangenheitsform + Fachbegriff
```
✓ SeatReserved, PaymentConfirmed, OrderCancelled
✗ ReserveSeat, ConfirmPayment, CancelOrder (das sind Commands!)
```

**Event-Schema (Envelope):**
```json
{
  "eventId": "uuid",
  "eventType": "SeatReserved",
  "aggregateId": "seat-A15",
  "aggregateType": "Seat",
  "timestamp": "2025-03-02T14:30:00Z",
  "version": 1,
  "correlationId": "request-uuid",
  "causationId": "previous-event-uuid",
  "payload": {
    "eventId": "evt-123",
    "seatId": "A-15",
    "userId": "user-456",
    "orderId": "order-789"
  }
}
```

**Schema Registry (Avro):**
```json
{
  "type": "record",
  "name": "SeatReserved",
  "namespace": "com.tickets.events",
  "fields": [
    { "name": "eventId", "type": "string" },
    { "name": "seatId", "type": "string" },
    { "name": "userId", "type": "string" },
    { "name": "orderId", "type": "string" },
    { "name": "timestamp", "type": "long", "logicalType": "timestamp-millis" }
  ]
}
```

**Schema-Evolution-Regeln:**
- Neue Felder: immer mit Default-Wert → backward compatible
- Felder entfernen: erst deprecated, dann nach 2 Releases entfernen
- Typ ändern: NIEMALS → neues Event-Typ erstellen

### Technology Stack

| Funktion | Tools |
|---|---|
| Event Broker | Kafka, RabbitMQ, NATS, Google Pub/Sub, AWS SNS/SQS |
| CDC | Debezium, Oracle GoldenGate, AWS DMS |
| Streaming | Kafka Streams, ksqlDB, Apache Flink, Spark Streaming |
| Schema | Confluent Schema Registry, AWS Glue Schema Registry |
| Monitoring | Kafdrop, Kafka UI, Prometheus + Grafana, Datadog |

### C4-Impact
- **Message Broker** als Container (Typ: `message_broker`)
- **Async Relationships** immer mit `async: true`, `payload`, `why`
- **Event Handlers** als Component (Typ: `event_handler`)
- **Schema Registry** als Container wenn formales Schema-Management nötig

---

## 3. CQRS (Command Query Responsibility Segregation)

### Architektur

```
[Client]
  ├── POST /commands → [Command Service] → [Write DB] ──(Event)──→ [Projection Service]
  └── GET /queries  → [Query Service]   → [Read DB]  ←──────────── [Projection Service]
```

### Wann CQRS einsetzen

| Indikator | Erklärung |
|---|---|
| Read/Write-Ratio > 10:1 | Reads dominieren → eigenes optimiertes Model |
| Komplexe Queries | Denormalisierte Read-Modelle für spezifische Views |
| Unterschiedliche Skalierung | Read = horizontal, Write = vertikal |
| Verschiedene Konsistenz-Anforderungen | Write = strong, Read = eventual OK |
| Multi-Tenant mit verschiedenen Views | Tenant-spezifische Read-Modelle |

### Wann NICHT

- Einfaches CRUD → Over-Engineering
- Strong Consistency überall nötig → Eventual Consistency ist CQRS-inherent
- Kleine Datenmenge → Read-Modelle lohnen sich nicht
- Single-User-App → kein Skalierungsbedarf

### Projection-Mechanismus

```typescript
class SeatProjectionHandler {
  // Event → Read Model Update
  async handle(event: SeatReserved) {
    await readDB.query(`
      UPDATE seat_availability
      SET available = available - 1, status = 'HELD'
      WHERE event_id = $1 AND seat_id = $2
    `, [event.eventId, event.seatId]);
  }
}
```

**Eventual Consistency Window:** Typisch 10ms-2s je nach Broker + Projection-Latency.

### C4-Impact
- **Command Service** + **Query Service** als getrennte Container
- **Write DB** + **Read DB** als separate Datenbank-Container
- **Projection Service** als Background-Worker-Container
- Events über Broker verbinden Write → Read Seite

---

## 4. Event Sourcing

### Kernprinzip

**Statt aktuellen State zu speichern, speichere alle Events die zum State geführt haben.**

```
Traditional: UPDATE seats SET state = 'BOOKED' WHERE id = 'A-15'
              → Alter Zustand verloren

Event Sourcing: INSERT INTO events VALUES
  ('SeatCreated',  {seatId: 'A-15', state: 'FREE'})
  ('SeatReserved', {seatId: 'A-15', userId: 'u-1', expiresAt: '...'})
  ('SeatBooked',   {seatId: 'A-15', orderId: 'o-1'})
  → Zustand = Replay aller Events
```

### Event Store Schema

```sql
CREATE TABLE events (
    event_id     uuid PRIMARY KEY,
    aggregate_id text NOT NULL,
    aggregate_type text NOT NULL,
    event_type   text NOT NULL,
    version      integer NOT NULL,
    payload      jsonb NOT NULL,
    metadata     jsonb,
    created_at   timestamptz DEFAULT now(),
    UNIQUE (aggregate_id, version)  -- Optimistic Concurrency
);
```

### Aggregate-Rebuild

```typescript
class SeatAggregate {
  state: SeatState = { status: 'FREE' };

  apply(event: DomainEvent) {
    switch (event.type) {
      case 'SeatCreated':  this.state = { status: 'FREE', ...event.payload }; break;
      case 'SeatReserved': this.state.status = 'HELD'; this.state.expiresAt = event.payload.expiresAt; break;
      case 'SeatBooked':   this.state.status = 'BOOKED'; this.state.orderId = event.payload.orderId; break;
      case 'SeatReleased': this.state.status = 'FREE'; this.state.expiresAt = null; break;
    }
  }

  static fromEvents(events: DomainEvent[]): SeatAggregate {
    const agg = new SeatAggregate();
    events.forEach(e => agg.apply(e));
    return agg;
  }
}
```

### Snapshots

**Problem:** Bei 10.000 Events dauert Replay zu lang.
**Lösung:** Periodisch Snapshot speichern.

```sql
CREATE TABLE snapshots (
    aggregate_id   text NOT NULL,
    aggregate_type text NOT NULL,
    version        integer NOT NULL,
    state          jsonb NOT NULL,
    created_at     timestamptz DEFAULT now(),
    PRIMARY KEY (aggregate_id, version)
);
```

**Rebuild:** Letzter Snapshot + Events seit Snapshot-Version.

### Schema-Evolution (Upcasting)

```typescript
function upcast(event: StoredEvent): DomainEvent {
  if (event.type === 'SeatReserved' && event.version === 1) {
    // v1 hatte kein expiresAt → Default setzen
    return { ...event, payload: { ...event.payload, expiresAt: null } };
  }
  return event;
}
```

### Wann Event Sourcing NICHT

- Einfaches CRUD → Massive Over-Engineering
- Daten müssen gelöscht werden (GDPR Right to Erasure) → Crypto-Shredding nötig
- Team hat keine ES-Erfahrung → Lernkurve sehr steil
- Reporting braucht aktuellen State → Read Models / Projections nötig (Komplexität)

### C4-Impact
- **Event Store** als zentraler Container (Typ: `database`)
- **Aggregate Service** als Container mit Commands → Events
- **Projection Services** als Background-Worker
- Meistens kombiniert mit CQRS

---

## 5. Hexagonal Architecture (Ports & Adapters)

### Architektur

```
[Inbound Adapter]  →  [Inbound Port]  →  [Domain Core]  →  [Outbound Port]  →  [Outbound Adapter]
 (REST Controller)    (Interface)         (Business Logic)   (Interface)         (DB Repository)
 (Kafka Consumer)     (UseCase)           (Domain Model)     (EventPublisher)    (Kafka Producer)
 (CLI)                                    (Domain Service)                       (HTTP Client)
```

**Dependency Rule:** Adapters hängen von Ports ab, Ports hängen vom Core ab, Core hängt von NICHTS ab.

### Mapping auf Components

```
Inbound Adapters  → controller, event_handler
Inbound Ports     → Interface/UseCase (in service_class integriert)
Domain Core       → service_class (Business Logic)
Outbound Ports    → Interface (Repository-Interface)
Outbound Adapters → repository, adapter
```

### Wann Hexagonal NICHT

- Prototyp / MVP → zu viel Boilerplate
- Einfaches CRUD → Repository-Pattern reicht
- Team kennt nur Layered Architecture → Confusion

---

## 6. Clean Architecture

### Layer-Modell (innen → außen)

```
[Entities]           — Enterprise Business Rules (domain model)
  ↓ depends on nothing
[Use Cases]          — Application Business Rules (orchestration)
  ↓ depends on Entities
[Interface Adapters] — Controllers, Presenters, Gateways
  ↓ depends on Use Cases
[Frameworks]         — Web, DB, UI, External APIs
  ↓ depends on Interface Adapters
```

**Dependency Rule:** Abhängigkeiten zeigen IMMER nach innen. Äußere Layer kennen innere, nicht umgekehrt.

### Unterschied zu Hexagonal

- Hexagonal: 2 Seiten (Inbound/Outbound), keine Layer-Hierarchie
- Clean: 4 konzentrische Layer, strikte Dependency Rule
- Praxis: Oft identisch implementiert, unterschiedliche Terminologie

---

## 7. Self-Contained Systems (SCS)

### Kernprinzip

**Jedes SCS ist ein vertikaler Schnitt: eigene UI, eigene API, eigene DB.**

```
[SCS: Reservierungen]     [SCS: Bestellungen]     [SCS: Analytics]
  ├── Web-UI                ├── Web-UI               ├── Dashboard
  ├── API                   ├── API                  ├── API
  ├── Business Logic        ├── Business Logic       ├── ETL
  └── Database              └── Database             └── Data Warehouse
```

### Regeln
1. Jedes SCS ist **autonom deploybar**
2. Kein geteilter State zwischen SCS
3. Kommunikation: **async bevorzugt** (Events), sync nur wenn unvermeidbar
4. Ein Team ist verantwortlich für ein SCS (Conway's Law)
5. UI-Komposition via **Micro-Frontends** oder Server-Side Includes

### Wann SCS

- Mehrere Teams (>3) arbeiten am selben Produkt
- Autonome Deployments gewünscht
- Verschiedene Domänen mit unterschiedlichen Lifecycles

### Wann NICHT

- Single Team → unnötige Overhead
- Stark gekoppelte Domänen → erzwungene Asynchronität ist schmerzhaft
- Kleine Anwendung → Monolith reicht

### C4-Impact
- Jedes SCS = eigener Container (oder eigenes System im Context)
- Async Relationships zwischen SCS
- Pro SCS ein Component-View

---

## 8. Microservices vs. Monolith — *MasterPlan-Lücke*

### Entscheidungsmatrix

| Kriterium | Monolith besser | Microservices besser |
|---|---|---|
| Team-Größe | 1-8 Entwickler | > 8, mehrere Teams |
| Deployment-Frequenz | Wöchentlich OK | Täglich/stündlich pro Service nötig |
| Skalierung | Uniform (alles gleich) | Granular (Service-Level) |
| Domänen-Komplexität | Eine Domäne | Mehrere Bounded Contexts |
| Technologie-Vielfalt | Einheitlich | Unterschiedliche Sprachen/Frameworks |
| Transaktions-Bedarf | ACID-Transaktionen | Eventual Consistency OK |
| Betriebskompetenz | Einfach (1 Deployment) | Kubernetes, Service Mesh, Monitoring |

### Modularer Monolith als Zwischenweg

```
[Monolith]
  ├── [Module: Reservierungen] (eigene DB-Schema, eigene API-Routes)
  ├── [Module: Bestellungen]   (eigene DB-Schema, eigene API-Routes)
  └── [Module: Benachrichtigungen]
```

**Regeln:** Module kommunizieren über definierte Interfaces, keine direkten DB-Zugriffe zwischen Modulen.

**Migration zu Microservices:** Module → Container (Strangler Fig)

---

## 9. Serverless — *MasterPlan-Lücke*

### Wann Serverless

- Event-getriebene Workloads mit variabler Last
- Kurze Execution-Times (< 15min)
- Keine persistente Verbindung nötig (kein WebSocket)

### Wann NICHT

- Cold Start inakzeptabel (Latency-kritisch)
- Langlebige Prozesse (> 15min)
- Hohe konstante Last (billiger auf dedizierten Instances)

### C4-Impact
- Serverless Functions als Container (Typ: `service` mit Technology: "AWS Lambda")
- Event-Trigger als async Relationships

---

## 10. Reactive Architecture — *MasterPlan-Lücke*

### Reactive Manifesto — 4 Prinzipien

1. **Responsive:** System antwortet zeitnah
2. **Resilient:** System bleibt funktional bei Fehlern
3. **Elastic:** System skaliert mit Last
4. **Message-Driven:** Async Messaging als Grundlage

### Wann Reactive

- Hohe Concurrency (> 10k gleichzeitige Verbindungen)
- Streaming-Workloads (Real-time Analytics, IoT)
- Back-Pressure nötig (Consumer langsamer als Producer)

### Tools
- **Akka (Java/Scala):** Actor Model
- **Project Reactor (Java):** Reactive Streams
- **RxJS (TypeScript):** Reactive Extensions
- **Vert.x (Java):** Event-Loop-basiert

---

## Paradigmen-Kombinationsmatrix

| Kombination | Wann sinnvoll | C4-Impact |
|---|---|---|
| DDD + EDA | Fachliche Events, Bounded Contexts | Container = BC, Events = Async Relationships |
| DDD + Hexagonal | Saubere Domain-Isolation | Component-Level: Ports + Adapters |
| EDA + CQRS | Getrennte Read/Write-Optimierung | Separate R/W Container, Projections |
| CQRS + Event Sourcing | Volle Auditierbarkeit + Read-Optimierung | Event Store + Projections + Read DB |
| SCS + DDD | Multi-Team, autonome Domänen | 1 SCS = 1 BC = 1 Container-Gruppe |
| SCS + EDA | Async zwischen autonomen Systemen | SCS verbunden via Broker |
| Clean + Hexagonal | Maximale Testbarkeit | Component-Level Layers |
| Monolith + DDD | Vorbereitung auf spätere Zerlegung | Module = Bounded Contexts |
