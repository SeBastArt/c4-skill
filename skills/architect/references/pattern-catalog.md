# Architecture Knowledge — Navigator

Dieser Katalog verweist auf die drei Deep-Dive-Referenzen. Lade sie kontextuell:

## Referenz-Dateien

| Datei | Inhalt | Wann laden |
|---|---|---|
| `pattern-deep-dive.md` | 25+ Patterns mit Mechanismen, Code, Tools, Failure Modes | Phase 4 (Container), Phase 5 (Component) |
| `paradigms-guide.md` | 10 Paradigmen mit Entscheidungsbaum, C4-Mapping, Anti-Patterns | Phase 1 (Scope), Phase 4 (Container) |
| `decision-frameworks.md` | ADR, Canvas, ATAM, Fitness Functions, Scorecards, Pre-Mortem | Phase 7 (Decisions), Amend Mode, Validate Mode |

## Quick-Reference: NFR → Pattern

| NFR | Primäre Patterns | Paradigma |
|---|---|---|
| **Performance** | Cache-aside, CDN, CQRS, Read Replicas | CQRS, EDA |
| **Availability** | Circuit Breaker, Bulkhead, Retry, Redundanz | — |
| **Latency** | Cache-aside, CDN, Async Processing, CQRS | CQRS |
| **Consistency** | Outbox, Idempotency, Saga, Event Sourcing | EDA, DDD |
| **Scalability** | CQRS, EDA, Horizontal Scaling, SCS, Competing Consumers | CQRS, SCS |
| **Security** | API Gateway, mTLS (Sidecar/Service Mesh), ACL | Hexagonal |
| **Observability** | Sidecar (OTel), Structured Logging, Correlation ID, Health Check | — |
| **Auditability** | Event Sourcing, Append-only Logs | Event Sourcing |
| **Maintainability** | Strangler Fig, ACL, Clean Architecture, Hexagonal | DDD, Clean |
| **Testability** | Testpyramide, Consumer-Driven Contracts, Fitness Functions | Hexagonal, Clean |

## Quick-Reference: Pattern-Stacks

| Stack | Patterns | Trigger |
|---|---|---|
| **Event-Driven Consistency** | Outbox + Idempotency + Retry + DLQ | Async mit guaranteed delivery |
| **Resilience** | Circuit Breaker + Retry + Bulkhead | Service-to-Service mit Ausfallrisiko |
| **CQRS + Event Sourcing** | CQRS + ES + EDA + Projections | Audit + unterschiedliche Read/Write |
| **Migration** | Strangler Fig + ACL + CDC | Legacy-Ablösung |
| **Distributed Transactions** | Saga + Outbox + Idempotency | Multi-Service-Workflows |
| **Service Mesh** | Sidecar + Ambassador + mTLS | Zero-Trust, >5 Services |

## Quick-Reference: Evaluation → Methode

| Situation | Methode | Aufwand |
|---|---|---|
| Strategische Entscheidung | ATAM | 2-4 Tage |
| Sprint-Review einer ADR | TARA | 30-60 min |
| Daten-intensive Systeme | DCAR | 1-2h |
| Regelmäßige System-Review | LASR | 1-2h |
| Risiko-Workshop | Risk Storming | 1-2h |
| Vor Go-Live | Pre-Mortem | 60-90 min |
| Kontinuierliche Prüfung | Fitness Functions | Automatisiert |
