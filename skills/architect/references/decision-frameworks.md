# Decision Frameworks — Entscheidungs- und Bewertungsmethoden

Referenz für den C4-Workshop, um Architektur-Entscheidungen fundiert zu treffen, zu dokumentieren, zu bewerten und kontinuierlich zu verbessern.

---

## 1. Architecture Decision Record (ADR)

### Standardvorlage

```markdown
# ADR-NNN: [Titel der Entscheidung]

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-XXX | Rejected

## Kontext
[Welches Problem lösen wir? Welche Kräfte wirken?]

## Entscheidung
[Was wurde entschieden und warum?]

## Alternativen
- [Alternative A] — [Vor-/Nachteile]
- [Alternative B] — [Vor-/Nachteile]

## Begründung
[Warum diese Option? Welche NFRs/Constraints treiben die Entscheidung?]

## Konsequenzen
- Positiv: [...]
- Negativ: [...]
- Risiken: [...]

## Qualitäts-Szenario
Wenn [Stimulus] unter [Bedingung] dann [Reaktion] gemessen an [Metrik].

## Datum
YYYY-MM-DD
```

### ADR-Lifecycle

```
Proposed → Accepted → (Deprecated → Superseded by ADR-XXX)
                   → (Rejected)
```

- **Proposed:** Entwurf, Team-Review ausstehend
- **Accepted:** Gültig und implementiert
- **Deprecated:** Wird langfristig ersetzt
- **Superseded:** Ersetzt durch neuere Entscheidung (Link!)
- **Rejected:** Wurde abgelehnt (trotzdem dokumentieren — warum nicht!)

### Y-Statement (Kurzform)

```
Im Kontext von [Kontext],
weil [Kräfte/Constraints],
entscheiden wir uns für [Entscheidung],
um [Ziel] zu erreichen,
wobei wir [Trade-off] akzeptieren.
```

### Decision Log

| ID | Titel | Status | Datum | Ersetzt | Bezug |
|---|---|---|---|---|---|
| ADR-001 | REST für API-Kommunikation | Accepted | 2024-03-15 | — | — |
| ADR-002 | Istio als Service Mesh | Accepted | 2024-04-02 | — | ADR-005 |
| ADR-003 | Kafka für Event-Streaming | Accepted | 2024-05-10 | — | ADR-006 |
| ADR-004 | gRPC statt REST (intern) | Accepted | 2024-06-22 | ADR-001 | — |

### Decision Radar

Quadranten analog zu Technology Radar:
- **Adopt:** Akzeptiert und bewährt — nutzen
- **Trial:** Pilotierung läuft — evaluieren
- **Assess:** In Prüfung — beobachten
- **Hold:** Veraltet — nicht neu einsetzen

### Integration in C4

Jede Design Decision im C4-Skill IS ein ADR:
- `decision.id` → ADR-ID
- `decision.context` → ADR Kontext
- `decision.decision` → ADR Entscheidung
- `decision.tradeoff` → ADR Konsequenzen (negativ)
- `decision.alternatives` → ADR Alternativen
- `decision.qualityScenario` → ADR Qualitäts-Szenario
- `decision.relatedNfrs` → ADR Begründung (NFR-Link)
- `decision.relatedElements` → ADR Implementation (C4-Element-Link)

---

## 2. Architecture Decision Canvas

Workshop-Tool für komplexe Entscheidungen vor der ADR-Dokumentation.

### Canvas-Felder

| Feld | Frage | Beispiel |
|---|---|---|
| **Kontext** | In welcher Situation entscheiden wir? | "Event-driven Microservice mit hohem Datenvolumen" |
| **Kräfte** | Welche Kräfte wirken? | Latency, Consistency, Team-Autonomie |
| **Optionen** | Welche Alternativen gibt es? | Kafka, Google Pub/Sub, Redis Streams |
| **Bewertung** | Wie schneiden die Optionen ab? | Matrix mit Kriterien (s.u.) |
| **Entscheidung** | Was wählen wir und warum? | "Kafka wegen Schema Evolution & Event History" |
| **Konsequenzen** | Was folgt daraus? | "Mehr Komplexität, aber höhere Resilienz" |

### Bewertungsmatrix

| Kriterium | Option A | Option B | Option C |
|---|---|---|---|
| Performance | Grün | Grün | Orange |
| Betriebskomplexität | Rot | Grün | Grün |
| Persistenz & Replay | Grün | Teilweise | Nein |
| Kosten | Orange | Grün | Grün |
| Community & Tooling | Grün | Grün | Orange |

→ Farb-Bewertung: Grün = gut, Orange = akzeptabel, Rot = problematisch

---

## 3. Architecture Inception Canvas (AIC)

Workshop-Tool für Projektstart — definiert Rahmenbedingungen bevor die Architektur beginnt.

### 9 Felder

| Feld | Leitfrage | Beispiel |
|---|---|---|
| Purpose & Vision | Warum existiert das System? | "Digitale Bestellplattform mit <2s Response" |
| Stakeholder | Wer ist betroffen? | "Kunde: Performance, DevOps: Observability" |
| Key Drivers | Welche Kräfte formen die Architektur? | "GDPR, Skalierbarkeit, Echtzeit" |
| Solution Context | Welche Systeme/Grenzen existieren? | "ERP, CRM, PaymentProvider via REST/Kafka" |
| Quality Goals | Welche Qualitätsattribute sind entscheidend? | "99.9% Uptime, <200ms Response, PCI DSS" |
| Constraints | Welche Einschränkungen gelten? | "Oracle Cloud, Kubernetes, Corporate Design" |
| Architecture Hypotheses | Welche Architektur-Ideen? | "Event-driven Microservices mit Kafka" |
| Risks & Open Questions | Was könnte schiefgehen? | "Unklare Ownership für shared Events" |
| Next Steps | Was tun wir als nächstes? | "arc42 aufsetzen, erster ADR zu Event Bus" |

→ Output fließt direkt in C4-Workshop Phase 1 (Scope) + Phase 2 (NFRs)

---

## 4. Architecture Evaluation Methods

### Methoden-Übersicht

| Methode | Ziel | Aufwand | Wann nutzen |
|---|---|---|---|
| **ATAM** | Quality Attribute Trade-offs bewerten | Hoch (2-4 Tage) | Strategische Entscheidungen |
| **TARA** | Schnelle Peer-Reviews | Niedrig (30-60 min) | Sprint-basiert, pro ADR |
| **DCAR** | Datenflüsse und -ownership analysieren | Mittel (1-2h) | Daten-intensive Systeme |
| **LASR** | Regelmäßige System-Reviews | Niedrig (1-2h) | Monatlich/quartalsweise |
| **Risk Storming** | Architektur-Risiken sichtbar machen | Mittel (1-2h) | Vor Major Releases |

### ATAM — Quality Attribute Scenario Template

| Quality Attribute | Stimulus | Umgebung | Reaktion | Metrik |
|---|---|---|---|---|
| Performance | 1.000 gleichzeitige API-Requests | Produktion unter Last | Response <200ms | 95th Percentile |
| Security | Angriff via gefälschtem JWT | Auth-Service aktiv | Zugriff verweigert, Audit-Log | 100% Block Rate |
| Availability | Datenbank fällt aus | Normalbetrieb | System weiterhin funktionsfähig | Recovery <60s |

### TARA — Lightweight Review Template

| Feld | Inhalt |
|---|---|
| **Thema/Fokus** | Was wird geprüft? |
| **Review-Team** | 2-5 Personen (Dev, Architect, QA) |
| **Kriterien** | Welche Quality Attributes? |
| **Bewertung** | Grün/Gelb/Rot pro Kriterium |
| **Maßnahmen** | Verbesserungsschritte |
| **Follow-up** | Ticket-Nr., Sprint |

### LASR — Continuous Review Checklist

Regelmäßig (monatlich) bewerten:
- [ ] Maintainability — Ist der Code wartbar?
- [ ] Performance — Erfüllen wir die Latency-Ziele?
- [ ] Security — Sind alle Policies durchgesetzt?
- [ ] Observability — Können wir Fehler schnell finden?
- [ ] Complexity — Wächst die Komplexität unkontrolliert?
- [ ] Consistency — Gibt es Daten-Drift oder Inkonsistenzen?

### Architecture Risk Storming

**Workshop-Ablauf (60-90 min):**
1. C4-Container-Diagramm als Basis an die Wand
2. Jeder klebt Risiko-Zettel auf betroffene Elemente
3. Gemeinsam clustern und priorisieren (Likelihood × Impact)
4. Top-3-Risiken → ADRs oder Tickets erstellen

**Risiko-Kategorien:**

| Kategorie | Beispiel | Typische Maßnahme |
|---|---|---|
| Security | Unverschlüsselte API | Service Mesh einführen |
| Availability | Single Point of Failure | Cluster/Replica |
| Performance | Bottleneck im Gateway | Autoscaling |
| Maintainability | Zu viele Module | Refactoring + BCs |
| Data Consistency | Doppelte Quellen | CDC/Outbox klären |
| Observability | Fehlende Traces | OpenTelemetry |

---

## 5. Pre-Mortem Analysis

**Vor dem Go-Live fragen: "Angenommen das System ist in 12 Monaten gescheitert — warum?"**

### Workshop-Ablauf (60-90 min)

| Schritt | Ziel | Dauer |
|---|---|---|
| 1. Szenario setzen | "System ist gescheitert — warum?" | 5 min |
| 2. Brainstorming | Jeder schreibt Ursachen auf | 15 min |
| 3. Clustern | Themen gruppieren | 10 min |
| 4. Priorisieren | Likelihood × Impact Matrix | 15 min |
| 5. Maßnahmen | Top-Risiken → ADRs, Tickets, Tests | 15 min |

### Risiko-Matrix

| Risiko | Wahrscheinlichkeit | Impact | Rating | Maßnahme |
|---|---|---|---|---|
| Fehlende Idempotenz | Hoch | Hoch | Kritisch | ADR + Retry-Strategie prüfen |
| Kein Alerting | Mittel | Hoch | Mittel | OpenTelemetry + PagerDuty |
| Schema-Drift | Niedrig | Mittel | Niedrig | Schema Registry einführen |

### Integration in C4

Pre-Mortem-Ergebnisse werden zu:
- **Design Decisions** (NFR-adressierend)
- **Quality Scenarios** (testbare Metriken)
- **Risk-Annotations** auf Elementen (im Why-Layer sichtbar)

---

## 6. Architecture Fitness Functions

**Automatisierte Tests für Architektur-Prinzipien.**

### Typen

| Typ | Prüft | Beispiel | Tool |
|---|---|---|---|
| **Statisch** | Code-Struktur, Abhängigkeiten | "Domain darf nicht Infrastructure importieren" | ArchUnit, NetArchTest |
| **Dynamisch** | Laufzeit-Verhalten | "p95 < 200ms unter Last" | K6, Gatling, Locust |
| **Security** | Sicherheits-Policies | "TLS überall, keine offenen Ports" | OWASP ZAP, Trivy, nmap |
| **Daten** | Datenqualität, Schema-Kompatibilität | "Schema backward-compatible" | Schema Registry, Custom |
| **Prozess** | Architektur-Praktiken | "Jeder ADR < 6 Monate alt" | Custom Scripts |

### Beispiele

**Layer-Check (Python):**
```python
def test_domain_has_no_infrastructure_imports():
    domain_files = glob("src/domain/**/*.py")
    for f in domain_files:
        content = open(f).read()
        assert "from infrastructure" not in content, f"Violation in {f}"
```

**Performance (K6):**
```javascript
import http from 'k6/http';
import { check } from 'k6';
export const options = { vus: 100, duration: '30s' };
export default function () {
  const res = http.get('https://api.example.com/orders');
  check(res, { 'p95 < 200ms': (r) => r.timings.duration < 200 });
}
```

**ADR-Freshness (Bash):**
```bash
find docs/adr -name "*.md" -mtime +180 -exec echo "STALE: {}" \;
```

### Integration in CI/CD

```
Developer Push → CI → Fitness Function Suite → Pass/Fail → Dashboard → Alert
```

---

## 7. Architecture Scorecards & Governance

### Scorecard Template

| Quality Attribute | Gewicht | Bewertung (1-5) | Score |
|---|---|---|---|
| Maintainability | 25% | 4 | 1.0 |
| Performance | 20% | 3 | 0.6 |
| Security | 25% | 5 | 1.25 |
| Observability | 15% | 2 | 0.3 |
| Scalability | 15% | 4 | 0.6 |
| **Gesamt** | **100%** | | **3.75/5.0** |

**Schwellenwert:** < 3.0 → Review erforderlich

### Governance-Struktur

| Ebene | Methode | Zweck |
|---|---|---|
| **Team** | TARA, LASR, Fitness Functions | Kontinuierliche Qualitätsprüfung |
| **Domain/Produkt** | DCAR, ATAM, Scorecards | Systematische Risiko-Steuerung |
| **Organisation** | Governance Board, Reflection | Strategisches Lernen |

---

## 8. Architecture Reflection & Learning

### Learning Canvas

| Bereich | Leitfrage | Erkenntnis | Maßnahme |
|---|---|---|---|
| Decisions | Welche Entscheidung war effektiv? | Event Sourcing verbessert Integrität | Als Standard adoptieren |
| Process | Welche Methode war hilfreich? | LASR alle 4 Wochen stabilisiert Qualität | Beibehalten |
| Communication | Wo stockte es? | Fehlendes Alignment zwischen Teams | Cross-Team-Review einführen |
| Technology | Wo gab es wiederkehrende Risiken? | API-Latenzen durch Gateway | Fitness Function erweitern |
| Knowledge | Was sollte dokumentiert werden? | Retry-Strategie für externe APIs | Neues Playbook-Thema |

### Architecture Learning Cycle

```
Entscheidung (ADR) → Evaluation (ATAM/TARA/LASR)
  → Governance (Scorecards, Fitness Functions)
    → Reflection Workshop
      → Lessons Learned Repository
        → Architektur-Prinzipien aktualisiert
          → zurück zu Entscheidung
```

---

## 9. arc42 Integration

Das C4-Modell des Skills deckt arc42-Abschnitte ab:

| arc42-Abschnitt | C4-Skill Mapping |
|---|---|
| 1. Einführung & Ziele | Phase 1 (Scope) |
| 2. Randbedingungen | Phase 2 (NFRs) als Constraints |
| 3. Kontextabgrenzung | Phase 3 (Context Level) |
| 4. Lösungsstrategie | Design Decisions |
| 5. Bausteinsicht | Phase 4 (Container) + Phase 5 (Component) |
| 6. Laufzeitsicht | Relationships mit Detail + Payload |
| 7. Verteilungssicht | Technology-Felder auf Containern |
| 8. Querschnittliche Konzepte | Patterns (pattern-deep-dive.md) |
| 9. Architekturentscheidungen | Design Decisions (= ADRs) |
| 10. Qualitätsanforderungen | NFRs + Quality Scenarios |
| 11. Risiken & Technische Schulden | Pre-Mortem + Risk Storming |
| 12. Glossar | Element-Names (Ubiquitous Language) |

---

## 10. Zusammenhänge — Integrierter Prozess

```
Projekt-Start:
  AIC Workshop → Phase 1 (Scope) + Phase 2 (NFRs)

Architektur-Design:
  Pattern-Catalog → Phase 4 (Container) + Phase 5 (Component)
  Decision Canvas → Phase 7 (Design Decisions)

Validierung:
  Risk Storming auf C4-Diagramm → Pre-Mortem → Quality Scenarios
  TARA/LASR für bestehende Architektur → Amend Mode

Messung:
  Fitness Functions in CI/CD → Scorecard

Lernen:
  Reflection Workshop → ADR-Updates → Amend Mode
```
