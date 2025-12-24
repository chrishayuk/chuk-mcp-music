# CHUK Music MCP Server

A music design system for MCP — **shadcn/ui for music composition**.

You copy patterns into your project, you own them, you modify them. The library provides correct primitives and well-designed starting points, not a black box.

## Vision

**Music as a design system, not a DAW.**

LLMs operate at the intent level — structure, energy, arrangement. The system handles music theory. Composers own their patterns.

## Features

- **Pattern System**: Copyable, ownable pattern templates (drums, bass, harmony, melody, fx)
- **Style System**: Constraint bundles (melodic-techno, ambient, cinematic) that guide composition
- **Arrangement Model**: Layers × Sections structure with energy curves and harmony
- **MIDI Export**: Deterministic compilation from YAML to playable MIDI files
- **MCP Integration**: Full MCP server with 30+ tools for AI-assisted composition

## Quick Start

```bash
# Install (development mode)
git clone https://github.com/chuk-ai/chuk-mcp-music
cd chuk-mcp-music
pip install -e ".[dev]"

# Run examples
python examples/generate_midi.py           # Basic MIDI generation
python examples/compile_arrangement.py     # Full arrangement compilation
python examples/use_styles.py              # Style system demo

# Run tests
make check    # Linting, type checking, security, tests
pytest        # Just tests
```

## The Stack

```
Intent (LLM)
    ↓
Tokens (semantic constraints)
    ↓
Structure (sections, energy curves)
    ↓
Layers (drums, bass, harmony, melody, fx)
    ↓
Patterns (owned, modifiable recipes)
    ↓
Score IR (symbolic, inspectable)
    ↓
MIDI (deterministic compilation)
    ↓
Audio (optional, downstream)
```

## Key Concepts

### Patterns (The shadcn Layer)

Patterns are copyable, ownable, modifiable templates:

```yaml
# patterns/bass/root-pulse.yaml
schema: pattern/v1
name: root-pulse
role: bass
pitched: true

parameters:
  density:
    type: enum
    values: [half, quarter, eighth]
    default: quarter

variants:
  driving:
    density: eighth

template:
  events:
    - degree: chord.root
      beat: 0
      velocity: $velocity_base
```

### Arrangements (Your Composition)

```yaml
# arrangements/demo.arrangement.yaml
schema: arrangement/v1
key: D_minor
tempo: 124

harmony:
  default_progression: [i, VI, III, VII]

sections:
  - name: intro
    bars: 8
  - name: verse
    bars: 16

layers:
  bass:
    role: bass
    patterns:
      pulse:
        ref: bass/root-pulse
        variant: driving
    arrangement:
      intro: null
      verse: pulse
```

### Styles (Constraint Bundles)

Styles narrow the solution space without forcing specific choices:

```yaml
# styles/library/melodic-techno.yaml
schema: style/v1
name: melodic-techno
description: Driving, melodic electronic music

tokens:
  tempo:
    range: [120, 128]
    default: 124
  key_preference: minor

structure_hints:
  breakdown_required: true
  section_multiples: 8

layer_hints:
  bass:
    suggested: [bass/rolling-sixteenths, bass/root-pulse]
    register: low

forbidden:
  patterns: [drums/trap-*]
```

### Deterministic Compilation

Same arrangement → same MIDI. Always.

```
Arrangement YAML → PatternInstance (diffable) → EventList (deterministic) → MIDI
```

## MCP Tools

The server provides 30+ tools organized by domain:

**Arrangement Tools** (6):
- `music_create_arrangement` - Create a new arrangement
- `music_get_arrangement` - Get arrangement details
- `music_list_arrangements` - List all arrangements
- `music_save_arrangement` - Save to YAML
- `music_delete_arrangement` - Delete an arrangement
- `music_duplicate_arrangement` - Clone an arrangement

**Structure Tools** (11):
- `music_add_section`, `music_remove_section`, `music_reorder_sections`
- `music_set_section_energy`, `music_add_layer`, `music_remove_layer`
- `music_arrange_layer`, `music_mute_layer`, `music_solo_layer`
- `music_set_layer_level`, `music_set_harmony`

**Pattern Tools** (6):
- `music_list_patterns`, `music_describe_pattern`
- `music_add_pattern`, `music_remove_pattern`
- `music_update_pattern_params`, `music_copy_pattern_to_project`

**Style Tools** (6):
- `music_list_styles`, `music_describe_style`
- `music_suggest_patterns`, `music_validate_style`
- `music_apply_style`, `music_copy_style_to_project`

**Compilation Tools** (4):
- `music_compile_midi`, `music_preview_section`
- `music_export_yaml`, `music_validate`

## Development

```bash
# Clone and install
git clone https://github.com/chuk-ai/chuk-mcp-music
cd chuk-mcp-music
pip install -e ".[dev]"

# Run full check suite
make check    # Linting, types, security, tests

# Run tests with coverage
pytest --cov=src/chuk_mcp_music

# Format code
ruff format .
ruff check --fix .
```

## Project Structure

```
src/chuk_mcp_music/
├── core/           # Music primitives (pitch, rhythm, chord, scale)
├── models/         # Pydantic models (arrangement, pattern, style)
├── arrangement/    # Arrangement management
├── patterns/       # Pattern system and library
├── styles/         # Style system and library
├── compiler/       # MIDI compilation
├── tools/          # MCP tool implementations
└── async_server.py # MCP server entry point
```

## Architecture

See [roadmap.md](roadmap.md) for the full design document.

## License

MIT
