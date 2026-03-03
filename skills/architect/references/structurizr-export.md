# Structurizr DSL Export

## Overview

Converts `architecture.json` (v2.0) to [Structurizr DSL](https://docs.structurizr.com/dsl) format for interoperability with Structurizr, PlantUML C4, and other C4 tools.

## Mapping Rules

### Element Type → Structurizr Keyword

| JSON Type | Structurizr DSL | Notes |
|---|---|---|
| `person` | `person` | |
| `external_person` | `person` | Add `tags "External"` |
| `system` | `softwareSystem` | Main system, contains containers |
| `external_system` | `softwareSystem` | Add `tags "External"` |
| `gateway` | `container` | Add `tags "Gateway"` |
| `webapp` | `container` | Add `tags "WebApp"` |
| `api` | `container` | Add `tags "API"` |
| `service` | `container` | |
| `database` | `container` | Add `tags "Database"` and `technology "..."` |
| `cache` | `container` | Add `tags "Cache"` |
| `message_broker` | `container` | Add `tags "MessageBroker"` |
| `cdn` | `container` | Add `tags "CDN"` |
| `scheduler` | `container` | Add `tags "Scheduler"` |
| `queue` | `container` | Add `tags "Queue"` |
| `external_service` | `softwareSystem` | Add `tags "External"` (promoted to system level) |
| `controller` | `component` | |
| `service_class` | `component` | |
| `repository` | `component` | |
| `event_handler` | `component` | Add `tags "EventHandler"` |
| `background_worker` | `component` | Add `tags "BackgroundWorker"` |
| `adapter` | `component` | Add `tags "Adapter"` |

### Relationships

```
<source> -> <target> "<label>" "<technology/protocol>"
```

- `async: true` → Add `tags "Async"` to the relationship
- `bidirectional: true` → Generate two relationships (A→B and B→A)

### Groups

Structurizr DSL supports `group "<name>" { ... }` — map directly from JSON groups.

## Output Template

```structurizr
workspace "<project.name>" "<project.description>" {

    model {
        // Context-level persons and external systems
        <ctx-person-id> = person "<name>" "<description>"
        <ctx-ext-system-id> = softwareSystem "<name>" "<description>" {
            tags "External"
        }

        // Main system with containers
        <ctx-system-id> = softwareSystem "<name>" "<description>" {
            // Container-level elements
            <cnt-id> = container "<name>" "<description>" "<technology>" {
                tags "<type-tag>"

                // Component-level elements (if decomposed)
                <cmp-id> = component "<name>" "<description>" "<technology>"
            }
        }

        // Context-level relationships
        <from> -> <to> "<label>" "<protocol>"

        // Container-level relationships
        <from> -> <to> "<label>" "<protocol>"

        // Component-level relationships
        <from> -> <to> "<label>" "<protocol>"
    }

    views {
        systemContext <system-id> "Context" {
            include *
            autoLayout
        }

        container <system-id> "Container" {
            include *
            autoLayout
        }

        // One component view per decomposed container
        component <container-id> "Component-<container-name>" {
            include *
            autoLayout
        }

        styles {
            element "External" {
                background #999999
                color #ffffff
            }
            element "Database" {
                shape Cylinder
                background #E8524A
                color #ffffff
            }
            element "MessageBroker" {
                background #FF6B35
                color #ffffff
            }
            element "Cache" {
                background #F5A623
                color #ffffff
            }
            relationship "Async" {
                style dashed
            }
        }
    }

}
```

## Export Process

1. Read `architecture.json`
2. Collect all element IDs across levels — build ID → variable-name map (sanitize: lowercase, replace non-alphanumeric with `_`)
3. Emit `model` block:
   - Context persons and external systems as top-level declarations
   - Main system as `softwareSystem` containing all containers
   - Each container with `drillDown` contains its components
4. Emit all relationships grouped by level
5. Emit `views` block with one view per level
6. Emit `styles` block mapping tags to colors from `C4.colors`
7. Write to `<project-name>.dsl`

## Limitations

- Position hints are lost (Structurizr uses `autoLayout` or its own positioning)
- Code snippets are not exported (no Structurizr equivalent)
- Design decisions are exported as documentation pages if Structurizr workspace supports it
- NFRs are exported as properties on the main system element
- Why-annotations and payload descriptions are added as relationship descriptions
