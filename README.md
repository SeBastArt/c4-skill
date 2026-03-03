# C4 Architecture Skill for Claude Code

Interactive C4 architecture diagrams as self-contained HTML files — from NFRs to deployable visualization in a guided workshop.

## Features

- **9-Phase Workshop**: Scope → NFRs → Context → Container → Component → Code → Decisions → Validate → Render
- **Self-contained HTML output**: SVG diagrams with drag & drop, zoom/pan, tooltips, drill-down — zero dependencies
- **Architecture knowledge**: 25+ patterns, 10 paradigms, decision frameworks (ATAM, TARA, ADR)
- **Code annotations**: Every code snippet explains *why* it's architecturally relevant
- **38 validation rules**: Structural integrity, completeness, cross-level consistency, traceability
- **6 modes**: Full Workshop, Quick, Render-Only, Validate-Only, Amend, Export (Structurizr DSL)

## Installation

### As Claude Code Plugin (recommended)

```bash
# Add marketplace
/plugin marketplace add SeBastArt/c4-skill

# Install plugin
/plugin install c4@SeBastArt-c4-skill
```

Then use: `/c4:architect` to start the workshop.

### As Standalone Skill

Copy the `skills/architect/` folder into your project or personal skills directory:

```bash
# Personal (all projects)
cp -r skills/architect ~/.claude/skills/c4

# Project-specific
cp -r skills/architect .claude/skills/c4
```

Then use: `/c4` to start the workshop.

## Usage

### Full Workshop
```
/c4:architect Design a payment processing system
```

### Quick Mode (compressed phases 1-7)
```
/c4:architect quick — Build a Dutch auction platform with real-time countdown
```

### Render existing architecture.json
```
/c4:architect render Architecture/output/my-architecture.json
```

### Validate existing architecture.json
```
/c4:architect validate Architecture/output/my-architecture.json
```

### Amend existing architecture
```
/c4:architect amend — Add a notification service to Architecture/output/my-architecture.json
```

## Output

A single `.html` file with:
- **Context diagram** (C4 Level 1): Actors + external systems
- **Container diagram** (C4 Level 2): Deployable units with groups
- **Component diagrams** (C4 Level 3): Internal structure per container
- **Code level** (C4 Level 4): Annotated code snippets with syntax highlighting
- **NFR panel**: Non-functional requirements + design decisions with hover highlighting
- **Interactions**: Drag & drop, zoom/pan, drill-down, rich tooltips, keyboard navigation

## License

MIT
