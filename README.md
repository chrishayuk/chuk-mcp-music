# CHUK Music MCP Server

A music design system for MCP — **shadcn/ui for music composition**.

You copy patterns into your project, you own them, you modify them. The library provides correct primitives and well-designed starting points, not a black box.

## Vision

**Music as a design system, not a DAW.** This is a control-plane for composition.

LLMs operate at the intent level — structure, energy, arrangement. The system handles music theory. Composers own their patterns.

## Features

- **Pattern System**: Copyable, ownable pattern templates (drums, bass, harmony, melody, fx)
- **Style System**: Constraint bundles that **constrain**, **suggest**, and **validate**
- **Arrangement Model**: Layers × Sections structure with energy curves and harmony
- **Score IR**: Versioned intermediate representation — golden-file testable, diffable, round-trippable
- **MIDI Export**: Deterministic compilation from YAML to playable MIDI files
- **MCP Integration**: Full MCP server with 37+ tools for AI-assisted composition

## Quick Start

```bash
# Install
git clone https://github.com/chuk-ai/chuk-mcp-music
cd chuk-mcp-music
pip install -e ".[dev]"

# Compile an arrangement
python examples/compile_arrangement.py

# Verify determinism
shasum output/demo.mid
# e3b0c442...  (always the same for the same input)
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
Score IR (symbolic, inspectable, versioned)
    ↓
MIDI (deterministic compilation)
    ↓
Audio (optional, downstream)
```

## What You Own vs What the Library Owns

| You Own | Library Owns |
|---------|--------------|
| Patterns you copy to your project | Schema definitions (`pattern/v1`, `score_ir/v1`) |
| Arrangement YAML files | Compiler pipeline |
| Style overrides and customizations | Validation rules |
| Project-specific pattern libraries | Default pattern/style libraries |
| Output MIDI files | IR specification and canonicalization |

The boundary is clear: **you own the content, the library owns the machinery**.

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

Styles do three things:

1. **Constrain** — tempo ranges, forbidden patterns, key preferences
2. **Suggest** — pattern shortlists per layer, register hints
3. **Validate** — lint errors with actionable fixes

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

Validation output:
```json
{
  "valid": false,
  "errors": [
    {"message": "Tempo 140 outside style range [120, 128]", "severity": "error"},
    {"message": "Pattern drums/trap-hat forbidden by style", "severity": "error"}
  ],
  "suggestions": [
    {"message": "Consider drums/four-on-floor for drums layer", "severity": "info"}
  ]
}
```

### Score IR (Intermediate Representation)

The Score IR is the **stable, inspectable contract** between arrangement and MIDI:

```
Arrangement YAML → Score IR (diffable, versioned) → MIDI
```

**Same arrangement → same Score IR → same MIDI. Always.**

#### Schema Excerpt (`score_ir/v1`)

```json
{
  "schema": "score_ir/v1",
  "name": "my-track",
  "key": "D_minor",
  "tempo": 124,
  "time_signature": {"numerator": 4, "denominator": 4},
  "ticks_per_beat": 480,
  "total_bars": 24,
  "notes": [
    {
      "start_ticks": 0,
      "pitch": 50,
      "duration_ticks": 480,
      "velocity": 90,
      "channel": 1,
      "source_layer": "bass",
      "source_pattern": "bass/root-pulse",
      "source_section": "verse",
      "bar": 0,
      "beat": 0.0
    }
  ],
  "sections": [
    {"name": "intro", "start_ticks": 0, "end_ticks": 15360, "bars": 8}
  ]
}
```

#### Canonicalization Rules

- Notes sorted by `(start_ticks, channel, pitch)`
- Sections sorted by `start_ticks`
- All times in ticks (480 ticks per beat)
- Source traceability on every note

#### Usage

```python
# Compile and inspect
result = compiler.compile(arrangement)
print(result.score_ir.summary())
# {'name': 'my-track', 'total_bars': 32, 'total_notes': 256,
#  'layers': {'drums': 128, 'bass': 64, 'harmony': 64},
#  'pitch_range': (36, 72), 'velocity_range': (60, 110)}

# Compare two versions
diff = old_ir.diff_summary(new_ir)
# {'notes_added': 12, 'notes_removed': 8, 'notes_unchanged': 244,
#  'tempo_changed': False, 'key_changed': False}

# Debug: "Why is this note here?"
for note in result.score_ir.notes:
    if note.pitch == 50 and note.bar == 3:
        print(f"From {note.source_layer}/{note.source_pattern} in {note.source_section}")
```

## Common Workflows

### 1. Create Track from Style

```python
# Apply style → suggest patterns → add sections → arrange → compile
music_apply_style(arrangement="my-track", style="melodic-techno")
music_suggest_patterns(arrangement="my-track", role="bass")
# Returns: ["bass/rolling-sixteenths", "bass/root-pulse"]

music_add_section(arrangement="my-track", name="intro", bars=8)
music_add_section(arrangement="my-track", name="verse", bars=16)
music_arrange_layer(arrangement="my-track", layer="bass",
                    section_patterns={"intro": None, "verse": "main"})
music_compile_midi(arrangement="my-track")
```

### 2. Iterate on Bassline

```python
# Preview → tweak → diff → compile
music_preview_section(arrangement="my-track", section="verse")
music_update_pattern_params(arrangement="my-track", layer="bass",
                            params={"density": "eighth"})
music_diff_ir(arrangement="my-track-v1", other_arrangement="my-track-v2")
# {'notes_added': 32, 'notes_removed': 16, ...}

music_compile_midi(arrangement="my-track")
```

### 3. Debug a Bad Result

```python
# Compile to IR → inspect provenance → validate → fix
result = music_compile_to_ir(arrangement="my-track")
# Inspect which pattern produced the wrong notes
# Each note has: source_layer, source_pattern, source_section, bar, beat

music_validate(arrangement="my-track")
# {"valid": false, "errors": [{"message": "Channel conflict on channel 1"}]}

# Fix the issue
music_set_layer_level(arrangement="my-track", name="bass", level=0.8)
```

### 4. Extract Stems (IR Round-Trip)

```python
# Compile → modify IR → emit separate MIDI files
ir = music_compile_to_ir(arrangement="my-track")

# Extract just the bass layer
bass_ir = music_modify_ir(ir_json=ir["score_ir"], filter_layers=["bass"])
music_emit_midi_from_ir(ir_json=bass_ir["score_ir"], output_name="bass-stem")

# Extract drums, reduce velocity
drums_ir = music_modify_ir(ir_json=ir["score_ir"],
                           filter_layers=["drums"],
                           velocity_scale=0.8)
music_emit_midi_from_ir(ir_json=drums_ir["score_ir"], output_name="drums-stem")

# Transpose harmony up an octave
harmony_ir = music_modify_ir(ir_json=ir["score_ir"],
                             filter_layers=["harmony"],
                             transpose=12)
music_emit_midi_from_ir(ir_json=harmony_ir["score_ir"], output_name="harmony-high")
```

## MCP Tools

The server provides 37+ tools organized by domain:

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

**Compilation Tools** (8):
- `music_compile_midi`, `music_preview_section`
- `music_compile_to_ir`, `music_diff_ir`
- `music_modify_ir`, `music_emit_midi_from_ir`
- `music_export_yaml`, `music_validate`

## Humanization (Planned)

Determinism doesn't mean robotic. Humanization is **seeded and explicit**:

```yaml
# In arrangement
humanize:
  timing_ms: 8      # ±8ms timing drift
  velocity: 6       # ±6 velocity variation
  seed: 42          # Reproducible randomness
```

Same seed → same humanization → still deterministic. Change the seed to explore variations.

## Development

```bash
# Clone and install
git clone https://github.com/chuk-ai/chuk-mcp-music
cd chuk-mcp-music
pip install -e ".[dev]"

# Run full check suite
make check    # Linting, types, security, tests (532 tests)

# Run tests with coverage
make test-cov  # Currently at 89% coverage

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
│   └── library/    # Built-in patterns (copy these!)
├── styles/         # Style system and library
│   └── library/    # Built-in styles
├── compiler/       # Compilation pipeline
│   ├── arranger.py # Arrangement → Score IR → MIDI
│   ├── score_ir.py # Intermediate representation (versioned, diffable)
│   └── midi.py     # MIDI file generation
├── tools/          # MCP tool implementations
└── async_server.py # MCP server entry point
```

## Roadmap

See [roadmap.md](roadmap.md) for the full design document.

**Next up:**
- Export profiles (GM, Ableton, Logic drum maps)
- CC automation lanes (filter sweeps, sidechain ducking)
- Real-time preview via Web MIDI
- Pattern learning from MIDI import

## License

MIT
