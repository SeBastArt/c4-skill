# Pattern Deep-Dive — Architektur-Patterns für den C4-Workshop

Umfassende Referenz für alle relevanten Architektur-Patterns. Der Skill nutzt diese Datei, um Patterns nicht nur zu **benennen**, sondern zu **erklären**, **abzuwägen** und **konkret zu empfehlen**.

---

## 1. Resilienz & Stabilität

### 1.1 Circuit Breaker

**Ziel:** Downstream-Ausfälle erkennen, schnell scheitern (Fail-Fast), System vor Kaskaden-Ausfällen schützen.

**State Machine:**
```
CLOSED ──(N Fehler in Zeitfenster)──→ OPEN
  ↑                                      │
  │                               (Timeout, z.B. 30s)
  │                                      ↓
  └────(Test erfolgreich)──── HALF-OPEN
                                 │
                          (Test fehlgeschlagen)
                                 ↓
                               OPEN
```

**Konfigurationsparameter:**
- `failureThreshold`: Anzahl Fehler bis OPEN (typisch: 3-5)
- `successThreshold`: Erfolge in HALF-OPEN bis CLOSED (typisch: 1-2)
- `timeout`: Dauer im OPEN-State bevor HALF-OPEN (typisch: 15-60s)
- `monitorWindow`: Zeitfenster für Fehlerzählung (typisch: 10-30s)

**Code-Sketch (C# mit Polly):**
```csharp
var circuitBreaker = Policy
    .Handle<HttpRequestException>()
    .CircuitBreakerAsync(
        exceptionsAllowedBeforeBreaking: 3,
        durationOfBreak: TimeSpan.FromSeconds(30),
        onBreak: (ex, duration) => logger.Warn($"Circuit OPEN for {duration}"),
        onReset: () => logger.Info("Circuit CLOSED"),
        onHalfOpen: () => logger.Info("Circuit HALF-OPEN")
    );
```

**Istio/Kubernetes Config:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      http:
        h2UpgradePolicy: DEFAULT
        maxRequestsPerConnection: 100
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**Failure Modes:**
- Circuit bleibt dauerhaft OPEN → Downstream ist tatsächlich tot → Alerting + Fallback nötig
- Circuit flattert (OPEN→HALF-OPEN→OPEN→...) → Threshold zu niedrig → anpassen
- Latenz-basierte Fehler werden nicht erkannt → Timeout-basierte Variante ergänzen

**Tools:** Polly (.NET), Resilience4j (Java), Istio (Service Mesh), Envoy Proxy

**C4-Impact:** Service-Component mit `pattern: "Circuit Breaker: 3 Fehler/30s → OPEN → 30s Timeout → HALF-OPEN"` oder Sidecar-Container (Istio/Envoy)

**Kombinationen:** Retry & Backoff (Retry VOR Circuit Breaker), Bulkhead (Isolation), API Gateway (zentral)

---

### 1.2 Bulkhead

**Ziel:** Ressourcen-Isolation — Fehler in einem Subsystem dürfen andere nicht beeinträchtigen.

**Varianten:**
1. **Thread-Pool Bulkhead:** Separate Thread-Pools pro Downstream-Dependency
2. **Connection-Pool Bulkhead:** Separate DB/HTTP-Connection-Pools
3. **Process Bulkhead:** Separate Deployments (Container/Pods) pro Kritikalität
4. **Semaphore Bulkhead:** Maximalanzahl gleichzeitiger Calls (leichtgewichtig)

**Dimensionierung:**
```
Pool-Größe = (Peak RPS × Avg Latency in Sekunden) × Safety Factor
Beispiel: 100 RPS × 0.2s × 1.5 = 30 Threads
```

**Code-Sketch (C# mit Polly):**
```csharp
var bulkhead = Policy.BulkheadAsync(
    maxParallelization: 30,         // max gleichzeitige Calls
    maxQueuingActions: 50,          // Warteschlange
    onBulkheadRejectedAsync: (ctx) => {
        logger.Warn("Bulkhead rejected — backpressure!");
        return Task.CompletedTask;
    }
);
```

**C4-Impact:** Annotation auf Service-Element: `pattern: "Bulkhead: 30 Threads Payment, 20 Threads Inventory"`

**Failure Modes:**
- Pool zu klein → Requests werden rejected unter Last → Monitoring + dynamische Skalierung
- Pool zu groß → Kein Schutzeffekt → Isolation geht verloren

---

### 1.3 Retry & Backoff

**Ziel:** Transiente Fehler durch Wiederholung überwinden, ohne das Zielsystem zu überlasten.

**Strategie: Exponential Backoff mit Jitter**
```
delay = min(baseDelay × 2^attempt + random(0, jitter), maxDelay)

Attempt 1: 100ms + jitter
Attempt 2: 200ms + jitter
Attempt 3: 400ms + jitter
Attempt 4: 800ms + jitter (→ maxDelay cap)
```

**Konfiguration:**
- `maxRetries`: 3-5 (nie unbegrenzt!)
- `baseDelay`: 100-500ms
- `maxDelay`: 5-30s
- `jitter`: 0-50% von delay (verhindert Thundering Herd)
- `retryableErrors`: 429, 503, 504, Timeout, ConnectionRefused

**NICHT retryable:** 400, 401, 403, 404, 409, 422 — das sind Business-Fehler!

**Code-Sketch (C# mit Polly):**
```csharp
var retry = Policy
    .Handle<HttpRequestException>()
    .OrResult<HttpResponseMessage>(r => r.StatusCode == HttpStatusCode.ServiceUnavailable)
    .WaitAndRetryAsync(
        retryCount: 3,
        sleepDurationProvider: attempt =>
            TimeSpan.FromMilliseconds(Math.Pow(2, attempt) * 100)
            + TimeSpan.FromMilliseconds(Random.Shared.Next(0, 50)),
        onRetry: (outcome, delay, attempt, ctx) =>
            logger.Warn($"Retry {attempt} after {delay}")
    );
```

**C4-Impact:** Adapter-Component oder Gateway mit `pattern: "Retry: 3× exponential backoff 100ms-5s + jitter"`

**Kombinationen:** Circuit Breaker (Retry → CB → Fallback), Idempotency (Retry sicher machen)

---

### 1.4 Sidecar Pattern

**Ziel:** Cross-cutting Concerns (mTLS, Tracing, Retry, Metrics) aus dem Service extrahieren in einen Begleit-Container.

**Funktionsweise:**
```
[Pod]
  ├── [App-Container] ←→ localhost ←→ [Sidecar-Container]
  │     (Business Logic)                (mTLS, Retry, Tracing)
  └── Shared Network Namespace
```

**Typische Sidecar-Funktionen:**
- **Istio Envoy Proxy:** mTLS, Circuit Breaker, Retry, Load Balancing, Traffic Splitting
- **OpenTelemetry Collector:** Traces + Metrics + Logs sammeln und exportieren
- **Fluentd/Fluent Bit:** Log-Shipping
- **Vault Agent:** Secret Injection

**Istio Sidecar Injection:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    istio-injection: enabled   # automatische Sidecar-Injection
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "true"
```

**C4-Impact:** Sidecar als eigener Container neben dem Service-Container, oder als Annotation `pattern: "Sidecar: Istio Envoy für mTLS + Observability"`

**Wann NICHT:** Latency-kritische Paths (Sidecar adds ~1-3ms per Hop), einfache Monolith-Deployments

---

### 1.5 Ambassador Pattern

**Ziel:** Outbound-Proxy für Calls zu externen Systemen — Security, Retry, Tracing ohne App-Änderung.

**Unterschied zu Sidecar:** Ambassador = speziell für **ausgehende** Calls (External APIs, Datenbanken). Sidecar = allgemeiner (ein/ausgehend).

**Typische Funktionen:**
- TLS Termination / Client-Zertifikat-Injection
- Request-Signing (HMAC, JWT)
- Retry & Circuit Breaker für externe APIs
- Request/Response-Logging
- Rate Limiting (Outbound)

**C4-Impact:** Ambassador-Container vor External-Service-Beziehung

---

## 2. Konsistenz & Datenfluss

### 2.1 Outbox Pattern

**Ziel:** Atomare Persistierung von Domain-Daten UND Events — kein Dual-Write-Problem.

**Mechanismus:**
```
1. BEGIN TRANSACTION
2.   UPDATE business_table (domain data)
3.   INSERT INTO outbox_table (event)
4.   INSERT INTO audit_log (optional)
5. COMMIT

--- Outbox Relay (separater Prozess) ---
6. SELECT * FROM outbox WHERE published = false LIMIT 100
7. PUBLISH to Kafka/RabbitMQ
8. UPDATE outbox SET published = true WHERE id IN (...)
```

**Outbox-Schema:**
```sql
CREATE TABLE outbox (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type  text NOT NULL,
    aggregate_id    text NOT NULL,
    event_type      text NOT NULL,
    payload         jsonb NOT NULL,
    idempotency_key text UNIQUE,
    published       boolean DEFAULT false,
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX idx_outbox_unpublished ON outbox(created_at) WHERE published = false;
```

**Relay-Sketch (TypeScript):**
```typescript
async function relayOutboxEvents() {
  const events = await db.query(
    `SELECT * FROM outbox WHERE published = false
     ORDER BY created_at LIMIT 100 FOR UPDATE SKIP LOCKED`
  );
  for (const event of events) {
    await kafka.produce(event.event_type, event.payload);
    await db.query(`UPDATE outbox SET published = true WHERE id = $1`, [event.id]);
  }
}
// Run every 100ms
setInterval(relayOutboxEvents, 100);
```

**Alternative: CDC mit Debezium (statt Relay)**
```
PostgreSQL WAL → Debezium Connector → Kafka Topic
```
- Vorteil: Kein Polling, nahezu Echtzeit
- Nachteil: Infrastruktur-Komplexität (Debezium + Kafka Connect)

**Failure Modes:**
- Relay crasht → Events bleiben in Outbox → Restart holt nach (at-least-once)
- Broker down → Relay kann nicht publishen → Outbox wächst → Alerting auf Outbox-Size
- Duplikate möglich → Consumer MUSS idempotent sein

**Tools:** Debezium (CDC), Kafka Connect, eigener Relay-Service

**C4-Impact:** Outbox-DB als Container, Outbox-Relay als Container, `pattern: "Outbox Pattern: Transactional Write → Relay → Publish"`

---

### 2.2 Idempotency Strategy

**Ziel:** Sicherstellen, dass doppelte Verarbeitung identisch zum einmaligen Ergebnis ist (Exactly-once Semantik).

**4 Implementierungsvarianten:**

| Variante | Mechanismus | Latenz | Konsistenz |
|---|---|---|---|
| **DB Primary Key** | `ON CONFLICT DO NOTHING` | Niedrig | Stark |
| **Redis Dedup** | `SET key NX EX ttl` | Sehr niedrig | Eventual (TTL) |
| **Message Hash** | SHA256 über Payload | Niedrig | Stark |
| **Outbox Check** | `findByIdempotencyKey` in Outbox-Table | Niedrig | Stark |

**DB-basiert (PostgreSQL):**
```sql
CREATE TABLE processed_events (
    event_id    text PRIMARY KEY,
    processed_at timestamptz DEFAULT now(),
    result      jsonb
);

-- Idempotent Insert
INSERT INTO processed_events (event_id, result)
VALUES ($1, $2)
ON CONFLICT (event_id) DO NOTHING
RETURNING *;
```

**Redis-basiert:**
```typescript
async function isProcessed(eventId: string): Promise<boolean> {
  const result = await redis.set(`processed:${eventId}`, '1', 'NX', 'EX', 86400);
  return result === null; // null = key existiert bereits
}
```

**REST-Idempotency:**
| HTTP Methode | Idempotent? | Strategie |
|---|---|---|
| GET | Ja (natürlich) | Keine Maßnahme nötig |
| PUT | Ja (natürlich) | Keine Maßnahme nötig |
| DELETE | Ja (natürlich) | Keine Maßnahme nötig |
| POST | **Nein** | Idempotency-Key Header erforderlich |
| PATCH | **Nein** | Versionscheck (ETag/If-Match) |

**Failure Modes:**
- TTL zu kurz bei Redis → Late Duplicates durchgelassen → TTL > 2× max Retry-Fenster
- Processed-Table wächst unbegrenzt → Retention Policy (z.B. 30 Tage, Partitioning)

**C4-Impact:** Service-Component mit `pattern: "Idempotency: DB-basiert via processed_events + ON CONFLICT"`

---

### 2.3 Saga Pattern

**Ziel:** Verteilte Transaktionen ohne 2-Phase-Commit — über Kompensationslogik.

**Zwei Varianten:**

#### Choreographierte Saga (dezentral)
```
OrderService ──(OrderCreated)──→ Kafka
    PaymentService ←── consume ──→ (PaymentCaptured) ──→ Kafka
        InventoryService ←── consume ──→ (StockReserved) ──→ Kafka
            ShippingService ←── consume ──→ (OrderShipped)

Bei Fehler (z.B. StockReserveFailed):
    InventoryService ──(StockReserveFailed)──→ Kafka
        PaymentService ←── consume ──→ RefundPayment ──→ (PaymentRefunded)
            OrderService ←── consume ──→ CancelOrder
```

- **Vorteil:** Kein Single Point of Failure, einfache Services
- **Nachteil:** Schwer nachvollziehbar, kein zentraler Überblick, zyklische Abhängigkeiten möglich

#### Orchestrierte Saga (zentral)
```
SagaOrchestrator:
  Step 1: CreateOrder(orderId)          → Compensation: CancelOrder(orderId)
  Step 2: CapturePayment(orderId, amt)  → Compensation: RefundPayment(orderId, amt)
  Step 3: ReserveStock(orderId, items)  → Compensation: ReleaseStock(orderId, items)
  Step 4: ShipOrder(orderId)            → Compensation: CancelShipment(orderId)
```

- **Vorteil:** Zentraler Überblick, klare Kompensationslogik, einfaches Debugging
- **Nachteil:** Orchestrator = SPOF (muss hochverfügbar sein), Coupling

**Kompensationstabelle (MUSS pro Saga dokumentiert werden):**

| Schritt | Service | Aktion | Kompensation |
|---|---|---|---|
| 1 | OrderService | CreateOrder | CancelOrder |
| 2 | PaymentService | CapturePayment | RefundPayment |
| 3 | InventoryService | ReserveStock | ReleaseStock |
| 4 | ShippingService | ShipOrder | CancelShipment |

**Tools:**
- **Temporal.io / Cadence:** Workflow-basiert, Go/Java/TypeScript SDKs
- **Axon Framework:** Java, Event Sourcing + Saga built-in
- **MassTransit / NServiceBus:** .NET, Message-basiert
- **Camunda / Zeebe:** BPMN-basiert, visueller Workflow-Editor

**Failure Modes:**
- Kompensation schlägt fehl → Retry + DLQ + manueller Eingriff
- Orchestrator crasht → State muss persistiert sein (DB/Event Store)
- Timeout → wie lange warten? → Explicit Timeouts pro Step

**C4-Impact:** Orchestrator als Container oder choreographiert via Broker

---

### 2.4 Change Data Capture (CDC)

**Ziel:** Datenänderungen in Echtzeit aus einer Datenbank erfassen und als Events publizieren.

**Mechanismus (Log-basiert):**
```
PostgreSQL WAL / Oracle Redo Log / MySQL Binlog
  → Debezium Connector (Kafka Connect)
    → Kafka Topic (pro Tabelle)
      → Consumer Services
```

**Debezium-Config:**
```json
{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "db.example.com",
    "database.port": "5432",
    "database.dbname": "orders",
    "database.user": "debezium",
    "table.include.list": "public.orders,public.payments",
    "topic.prefix": "cdc",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_slot",
    "publication.name": "debezium_pub"
  }
}
```

**Event-Format (Debezium Envelope):**
```json
{
  "before": { "id": 1, "status": "PENDING" },
  "after":  { "id": 1, "status": "PAID" },
  "op": "u",
  "ts_ms": 1709456789000,
  "source": { "table": "orders", "lsn": "0/1A2B3C4" }
}
```

**Reconciliation (Abgleich):**
- Periodischer Batch-Job vergleicht Source und Target DB
- Korrigiert Drift durch verlorene Events
- Typisch: 1x täglich oder nach Incident

**Wann CDC statt Outbox?**
- CDC: wenn du KEINE Kontrolle über die Source-DB hast (Legacy)
- Outbox: wenn du die Source-App kontrollierst (Greenfield)

**C4-Impact:** CDC-Connector als Container, Kafka als Broker, `pattern: "CDC: Debezium → Kafka → Consumer"`

---

### 2.5 Dead Letter Queue (DLQ) — *MasterPlan-Lücke*

**Ziel:** Nicht-verarbeitbare Messages isolieren, statt die Queue zu blockieren (Poison Pill Prevention).

**Mechanismus:**
```
Main Queue → Consumer → Verarbeitung erfolgreich? → ACK
                      → Fehlgeschlagen (N Retries)?  → DLQ
                                                         ↓
                                                    DLQ-Consumer
                                                    (Alerting, Logging, Manual Replay)
```

**Konfiguration (Kafka):**
```
max.retries = 3
retry.backoff.ms = 1000
dead.letter.topic = <topic>.DLQ
```

**DLQ-Handling-Strategien:**
1. **Alert + Manual Review:** DLQ-Depth > 0 → PagerDuty Alert
2. **Auto-Retry nach Fix:** Bug fixen → DLQ-Messages re-publishen
3. **Discard + Log:** Für nicht-kritische Events (Analytics)

**C4-Impact:** DLQ als eigener Queue-Container oder als Topic im Broker, DLQ-Consumer als Component

---

### 2.6 Competing Consumers — *MasterPlan-Lücke*

**Ziel:** Horizontale Skalierung der Event-Verarbeitung durch parallele Consumer.

**Mechanismus (Kafka Consumer Groups):**
```
Topic: seat-reservations (6 Partitionen)
  Consumer Group "reservation-processors":
    Consumer 1 → Partition 0, 1
    Consumer 2 → Partition 2, 3
    Consumer 3 → Partition 4, 5
```

**Regeln:**
- Max Consumer pro Group = Anzahl Partitionen
- Partitioning Key bestimmt Ordering-Garantie (z.B. eventId)
- Rebalancing bei Consumer-Ausfall (~30s)

**C4-Impact:** Annotation auf Consumer: `pattern: "Competing Consumers: 3 Instanzen, partitioned by eventId"`

---

### 2.7 Claim Check — *MasterPlan-Lücke*

**Ziel:** Große Payloads nicht über den Broker senden — nur eine Referenz (Claim Token).

**Mechanismus:**
```
Producer: Upload payload to S3 → Publish { claimToken: "s3://bucket/key" } to Kafka
Consumer: Read message → Download from S3 → Process
```

**Wann nutzen:** Payloads > 1MB (Kafka default max: 1MB), Bilder, PDFs, Reports

**C4-Impact:** Object Storage (S3) als Container, Claim Token in Event-Payload

---

## 3. Migration & Evolution

### 3.1 Strangler Fig

**Ziel:** Legacy-System schrittweise ablösen bei Zero-Downtime.

**Mechanismus:**
```
Phase 1: [Client] → [Proxy/Gateway] → [Legacy System] (100% Traffic)
Phase 2: [Client] → [Proxy/Gateway] ──→ [New Service A] (Feature A)
                                    └──→ [Legacy System] (Rest)
Phase 3: [Client] → [Proxy/Gateway] ──→ [New Service A]
                                    ──→ [New Service B]
                                    └──→ [Legacy System] (immer weniger)
Phase N: [Client] → [Proxy/Gateway] → [New Services] (Legacy abgeschaltet)
```

**Routing-Strategien:**
- **Path-basiert:** `/api/v2/orders` → New, `/api/v1/*` → Legacy
- **Header-basiert:** `X-Feature-Flag: new-orders` → New
- **User-basiert:** 10% der User → New (Canary)

**C4-Impact:** Gateway als Router, Legacy + New als parallele Container

---

### 3.2 Anti-Corruption Layer (ACL)

**Ziel:** Eigenes Domain-Modell vor fremdem/Legacy-Modell schützen.

**Mechanismus:**
```
[Eigenes System] → [ACL Adapter] → [Legacy/Fremdsystem]
                      ↓
              Translation Layer:
              - Mapping: LegacyOrder → Order
              - Validation: Daten prüfen
              - Enrichment: fehlende Felder ergänzen
```

**Code-Sketch:**
```typescript
class OrderACL {
  mapFromLegacy(legacyOrder: LegacyOrderDTO): Order {
    return {
      id: legacyOrder.ORDER_NUM,
      customer: this.mapCustomer(legacyOrder.CUST_ID),
      items: legacyOrder.LINE_ITEMS.map(this.mapLineItem),
      status: this.mapStatus(legacyOrder.STAT_CD), // "A" → "ACTIVE"
      createdAt: parseDate(legacyOrder.CRT_DT, 'YYYYMMDD')
    };
  }
}
```

**C4-Impact:** ACL als Adapter-Component oder als eigener Container zwischen Systemen

---

## 4. Kommunikation & Integration

### 4.1 API Gateway

**Ziel:** Zentraler Einstiegspunkt mit Auth, Rate Limiting, Routing, Aggregation.

**Funktionen:**
1. **Authentication:** JWT-Validierung, OAuth2 Token-Exchange
2. **Authorization:** RBAC/ABAC Policy-Enforcement
3. **Rate Limiting:** Sliding Window, Token Bucket
4. **Routing:** Path-basiert, Header-basiert, Weight-basiert
5. **Aggregation:** Multiple Backend-Calls zu einer Response zusammenfassen
6. **Transformation:** Request/Response-Mapping, Protocol Translation
7. **Caching:** Response-Cache für GET-Requests
8. **Observability:** Access Logs, Metriken, Tracing Propagation

**Kong Rate Limiting Config:**
```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 1000
      hour: 20000
      policy: redis
      redis_host: redis.example.com
  - name: jwt
    config:
      key_claim_name: kid
      claims_to_verify:
        - exp
```

**Tools:**
- **Open Source:** Kong, Traefik, Envoy, HAProxy
- **Cloud Native:** AWS API Gateway, Google Cloud Endpoints, Azure API Management
- **Service Mesh:** Istio (Gateway + Mesh), Linkerd

**C4-Impact:** Gateway als Container (Typ: `gateway`), `pattern: "API Gateway: Kong mit JWT + Rate Limiting 20k TPS"`

---

### 4.2 Backend for Frontend (BFF) — *MasterPlan-Lücke*

**Ziel:** Spezialisierte API-Schicht pro Client-Typ (Web, Mobile, IoT).

**Wann nutzen:**
- Unterschiedliche Datenmengen pro Client (Mobile braucht weniger als Web)
- Unterschiedliche Auth-Flows (Web = Cookie, Mobile = Token)
- Unterschiedliche Aggregation (Mobile = 1 Call, Web = Parallel-Calls OK)

**Mechanismus:**
```
[Web App]    → [Web BFF]    → [Services]
[Mobile App] → [Mobile BFF] → [Services]
[IoT Device] → [IoT BFF]   → [Services]
```

**C4-Impact:** Pro Client-Typ ein BFF-Container (Typ: `api`)

---

### 4.3 Adapter Pattern (Integration)

**Ziel:** Fremde API-Formate auf eigenes Domain-Modell übersetzen.

**Varianten:**
- **Inbound Adapter:** Externe Requests → interne Commands
- **Outbound Adapter:** Interne Queries → externe API-Calls
- **Protocol Adapter:** REST → gRPC, SOAP → REST, AMQP → HTTP

**C4-Impact:** Adapter als Component (Typ: `adapter`) oder Container

---

### 4.4 Service Mesh — *MasterPlan-Lücke*

**Ziel:** Netzwerk-Funktionalität (mTLS, Retry, Circuit Breaker, Observability) als Infrastruktur-Layer.

**Architektur:**
```
Data Plane:  Sidecar-Proxies (Envoy) neben jedem Service
Control Plane: Istio (istiod) konfiguriert alle Proxies zentral
```

**Wann nutzen:** > 5 Services, wenn mTLS/Zero-Trust erforderlich, heterogene Sprachen

**Wann NICHT:** < 5 Services, einzige Sprache (Library reicht), Latency-kritisch (adds ~1-3ms)

**C4-Impact:** Service Mesh als Infrastructure-Group, Sidecar-Proxies als implizite Container

---

## 5. Caching Patterns — *MasterPlan-Lücke*

### 5.1 Cache-aside (Lazy Loading)

**Mechanismus:**
```
1. App prüft Cache
2. Cache Hit → Return cached data
3. Cache Miss → Lade aus DB → Schreibe in Cache → Return
```

**Failure Modes:**
- Stale Data → TTL setzen (typisch 5s-5min je nach Use Case)
- Cache Stampede → Locking (Mutex) oder Probabilistic Early Expiration
- Cold Start → Kein Cache warm → Pre-warming bei Deployment

### 5.2 Read-Through Cache

**Wie Cache-aside, aber der Cache selbst lädt bei Miss.**
```
App → Cache → (Miss) → Cache lädt aus DB → Return
```

### 5.3 Write-Through Cache

**Jeder Write geht durch den Cache in die DB.**
```
App → Cache → DB (synchron)
```
- Vorteil: Cache immer aktuell
- Nachteil: Write-Latency steigt

### 5.4 Write-Behind (Write-Back) Cache

**Write geht nur in den Cache, DB wird asynchron aktualisiert.**
```
App → Cache → (async) → DB
```
- Vorteil: Schnelle Writes
- Nachteil: Datenverlust bei Cache-Crash vor DB-Write

### 5.5 Cache Invalidation Strategies

| Strategie | Wann | Nachteil |
|---|---|---|
| **TTL** | Einfach, gut genug | Stale Window |
| **Event-basiert** | Wenn Schreiber bekannt | Komplexität |
| **Version-basiert** | Optimistic Concurrency | Extra DB-Spalte |

**C4-Impact:** Cache als Container (Typ: `cache`), `pattern: "Cache-aside: Redis TTL 5s, Event-basierte Invalidierung für Writes"`

---

## 6. Observability Patterns — *MasterPlan-Lücke*

### 6.1 Correlation ID / Distributed Tracing

**Ziel:** Einen Request über alle Services hinweg nachverfolgbar machen.

**Mechanismus:**
```
Client → Gateway: X-Correlation-ID: uuid-123
Gateway → Service A: X-Correlation-ID: uuid-123
Service A → Service B: X-Correlation-ID: uuid-123
Service B → Kafka: header.correlationId: uuid-123
Kafka → Service C: header.correlationId: uuid-123
```

**Tools:** OpenTelemetry, Jaeger, Zipkin, Datadog APM

### 6.2 Health Check Pattern

**Ziel:** Automatische Erkennung von unhealthy Instances.

**Endpoints:**
- `/health/live` — Ist der Prozess am Laufen? (Liveness)
- `/health/ready` — Kann der Service Requests annehmen? (Readiness)
- `/health/startup` — Ist die Initialisierung fertig? (Startup)

### 6.3 Structured Logging

**Format:** JSON-Logs mit fixen Feldern für maschinelle Auswertung.
```json
{
  "timestamp": "2025-03-02T14:30:00Z",
  "level": "ERROR",
  "service": "reservation-svc",
  "correlationId": "uuid-123",
  "message": "Seat already held",
  "error": { "type": "ConflictException", "seatId": "A-15" }
}
```

---

## 7. Deployment Patterns — *MasterPlan-Lücke*

### 7.1 Blue/Green Deployment

```
Load Balancer → [Blue: v1.0 (aktiv)]
                [Green: v2.0 (bereit)]
Switch: LB zeigt auf Green → Green ist aktiv → Blue wird Rollback-Target
```

### 7.2 Canary Deployment

```
Load Balancer → 95% → [v1.0]
              →  5% → [v2.0 (Canary)]
Monitoring: Error-Rate, Latency → OK? → schrittweise 10%, 25%, 50%, 100%
```

### 7.3 Feature Flags

**Ziel:** Code deployen ohne Feature zu aktivieren. Trennung von Deploy und Release.

**Tools:** LaunchDarkly, Unleash, Flagsmith, eigene DB-basierte Flags

---

## 8. Qualitätssicherung

### 8.1 Consumer-Driven Contracts

**Ziel:** API-Verträge aus Consumer-Perspektive definieren und testen.

**Workflow:**
```
1. Consumer definiert Contract (was er braucht)
2. Contract → Contract Broker (Pact, Spring Cloud Contract)
3. Provider läuft Contract-Tests in CI
4. Bei Bruch → Build fails → Provider muss anpassen oder Consumer informieren
```

**Tools:** Pact, Spring Cloud Contract, Specmatic

### 8.2 Testpyramide

```
         /  E2E Tests  \        5-10%  (Selenium, Playwright, Cypress)
        / Integration    \     15-25%  (Testcontainers, API Tests)
       /   Unit Tests     \   70-80%  (Jest, xUnit, JUnit)
```

**C4-Relevanz:** Im Code-Level können Test-Snippets gezeigt werden (z.B. Contract-Test, Integration-Test)

### 8.3 Architecture Fitness Functions — *MasterPlan-Ergänzung*

**Ziel:** Automatisierte Tests, die Architektur-Prinzipien überprüfen.

**Beispiele:**
```
- Dependency Check: "Service A darf NICHT direkt auf Service B's DB zugreifen"
- Size Check: "Kein Container-Image > 500MB"
- Coupling Check: "Max 3 synchrone Hops pro Request"
- Latency Check: "p99 < 500ms end-to-end"
```

**Tools:** ArchUnit (Java), NetArchTest (.NET), Fitness Function Frameworks
