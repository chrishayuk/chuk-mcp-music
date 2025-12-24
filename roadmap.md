# CHUK Music MCP Server — Roadmap

## Vision

**Music as a design system, not a DAW.**

LLMs operate at the intent level — structure, energy, arrangement. The system handles music theory. Composers own their patterns.

This is **shadcn/ui for music**: you copy patterns into your project, you own them, you modify them. The library provides correct primitives and well-designed starting points, not a black box.

---

## Core Philosophy

### The shadcn Model Applied to Music

```
Radix UI        →  Music Primitives (intervals, scales, durations)
shadcn/ui       →  Pattern Library (basslines, progressions, drum patterns)
Your Project    →  Your Composition (owned, modifiable, forkable)
```

You're not generating music. You're **composing with owned patterns**.

### The Producer Mental Model

Producers think in layers and sections:

```
┌─────────────────────────────────────────────────────────┐
│  FX / Ear Candy    ░░░░░░░░░░░████░░░░░░████████░░░░░░ │
│  Lead / Melody     ░░░░░░░░████████░░░░████████████░░░░ │
│  Pads / Harmony    ░░░░████████████░░██████████████░░░░ │
│  Bass              ░░░░████████████░░██████████████████ │
│  Drums             ░░██████████████░░██████████████████ │
│                    ├──────┼───────┼──┼────────┼────────┤
│                    intro  verse  brk  chorus   outro    │
└─────────────────────────────────────────────────────────┘
```

Each horizontal band is a **layer**. Each layer has **patterns** that play during **sections**. That's the whole model.

### Why This Is Different

| Traditional Music AI | This Approach |
|---------------------|---------------|
| Generate notes | Compose with patterns |
| Black box output | Inspectable YAML |
| One-shot generation | Iterative layering |
| No ownership | You own your patterns |
| Style = prompt words | Style = constraint bundle |
| Audio-first | Structure-first |

---

## Architecture Overview

### The Stack

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

### Two Coordinate Systems

Music theory has two parallel systems — conflating them causes pain:

| Absolute | Relative |
|----------|----------|
| Pitch classes, MIDI numbers, Hz | Scale degrees, intervals, Roman numerals |
| C4 = 60 | "The tonic" |
| 440 Hz | "The fifth" |

Musicians think in relative coordinates. "The four chord" means something regardless of key. **That's the design token layer.**

---

## Project Structure

```
chuk-mcp-music/
├── src/chuk_mcp_music/
│   ├── server.py                 # Entry point with transport detection
│   ├── async_server.py           # MCP server instance + tool registration
│   │
│   ├── core/                     # Primitives (the Radix layer)
│   │   ├── pitch.py              # PitchClass, Interval
│   │   ├── scale.py              # ScaleType, ScaleDegree, Key
│   │   ├── chord.py              # ChordQuality, RomanNumeral, Chord
│   │   ├── rhythm.py             # Duration, BeatPosition, TimeSignature
│   │   └── dynamics.py           # Velocity, dynamics curves
│   │
│   ├── models/                   # Pydantic models
│   │   ├── arrangement.py        # Arrangement, Layer, Section
│   │   ├── pattern.py            # Pattern, PatternMetadata
│   │   └── responses.py          # MCP response models
│   │
│   ├── patterns/                 # Pattern system (the shadcn layer)
│   │   ├── registry.py           # Pattern discovery and loading
│   │   ├── compiler.py           # Pattern → ScoreIR
│   │   └── library/              # Built-in pattern definitions
│   │       ├── bass/
│   │       ├── drums/
│   │       ├── harmony/
│   │       ├── melody/
│   │       └── fx/
│   │
│   ├── arrangement/              # Arrangement management
│   │   ├── manager.py            # ArrangementManager (like PresentationManager)
│   │   ├── arranger.py           # Layer arrangement logic
│   │   └── validator.py          # Structure validation
│   │
│   ├── compiler/                 # IR → MIDI compilation
│   │   ├── ir.py                 # Score IR definitions
│   │   ├── midi.py               # MIDI generation
│   │   └── voicing.py            # Chord voicing rules
│   │
│   ├── styles/                   # Style system (constraint bundles)
│   │   ├── loader.py             # Style discovery
│   │   └── library/              # Built-in styles
│   │       ├── ambient.yaml
│   │       ├── melodic-techno.yaml
│   │       └── cinematic.yaml
│   │
│   ├── tokens/                   # Design tokens
│   │   ├── tempo.py              # BPM scales
│   │   ├── energy.py             # Energy levels → constraints
│   │   └── register.py           # Frequency/register ranges
│   │
│   ├── tools/                    # MCP tool implementations
│   │   ├── arrangement/          # Arrangement lifecycle
│   │   ├── structure/            # Sections, layer arrangement
│   │   ├── layers/               # Layer management
│   │   ├── patterns/             # Pattern operations
│   │   └── compilation/          # Export tools
│   │
│   └── constants.py              # Enums, error messages
│
├── tests/
│   ├── conftest.py
│   ├── core/                     # Primitive tests
│   ├── patterns/                 # Pattern tests
│   └── tools/                    # Tool tests
│
└── pyproject.toml
```

---

## Phase 0: Music Primitives (Foundation)

**Goal:** Build the invariant math layer that everything else composes on.

### Primitives to Implement

```python
# pitch.py — Absolute but octave-independent
class PitchClass(Enum):
    C = 0; Cs = 1; D = 2; Ds = 3; E = 4; F = 5
    Fs = 6; G = 7; Gs = 8; A = 9; As = 10; B = 11

    def transpose(self, semitones: int) -> PitchClass: ...

# Interval — The real primitive
@dataclass(frozen=True)
class Interval:
    semitones: int

    UNISON = 0; MINOR_SECOND = 1; MAJOR_SECOND = 2
    MINOR_THIRD = 3; MAJOR_THIRD = 4; PERFECT_FOURTH = 5
    TRITONE = 6; PERFECT_FIFTH = 7; MINOR_SIXTH = 8
    MAJOR_SIXTH = 9; MINOR_SEVENTH = 10; MAJOR_SEVENTH = 11
    OCTAVE = 12

    def invert(self) -> Interval: ...
    def __add__(self, other: Interval) -> Interval: ...

# scale.py — Relative to key
@dataclass(frozen=True)
class ScaleDegree:
    degree: int          # 1-7
    alteration: int = 0  # -1 = flat, +1 = sharp

    def resolve(self, key: Key) -> PitchClass: ...

@dataclass(frozen=True)
class ScaleType:
    intervals: tuple[Interval, ...]

    MAJOR = ScaleType((M2, M2, m2, M2, M2, M2, m2))
    NATURAL_MINOR = ScaleType((M2, m2, M2, M2, m2, M2, M2))
    DORIAN = ScaleType(...)
    # ... modes

@dataclass(frozen=True)
class Key:
    root: PitchClass
    scale: ScaleType

    def degree_to_pitch(self, degree: ScaleDegree) -> PitchClass: ...
    def pitch_to_degree(self, pitch: PitchClass) -> ScaleDegree | None: ...

# chord.py — Interval stacks
@dataclass(frozen=True)
class ChordQuality:
    intervals: frozenset[Interval]

    MAJOR = ChordQuality({UNISON, MAJOR_THIRD, PERFECT_FIFTH})
    MINOR = ChordQuality({UNISON, MINOR_THIRD, PERFECT_FIFTH})
    DOMINANT_7 = ChordQuality({UNISON, MAJOR_THIRD, PERFECT_FIFTH, MINOR_SEVENTH})
    # ...

@dataclass(frozen=True)
class RomanNumeral:
    """Key-independent chord reference — the design token"""
    degree: ScaleDegree
    quality: ChordQuality
    inversion: int = 0

    I = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR)
    ii = RomanNumeral(ScaleDegree(2), ChordQuality.MINOR)
    V7 = RomanNumeral(ScaleDegree(5), ChordQuality.DOMINANT_7)
    # ...

    def resolve(self, key: Key) -> Chord: ...

# rhythm.py — Time primitives
@dataclass(frozen=True)
class Duration:
    beats: Fraction

    WHOLE = Duration(Fraction(1))
    HALF = Duration(Fraction(1, 2))
    QUARTER = Duration(Fraction(1, 4))
    EIGHTH = Duration(Fraction(1, 8))
    SIXTEENTH = Duration(Fraction(1, 16))

    def dotted(self) -> Duration: ...
    def triplet(self) -> Duration: ...

@dataclass(frozen=True)
class TimeSignature:
    beats_per_bar: int
    beat_unit: Duration

    COMMON_TIME = TimeSignature(4, Duration.QUARTER)
    WALTZ = TimeSignature(3, Duration.QUARTER)

@dataclass(frozen=True)
class BeatPosition:
    bar: int
    beat: Fraction
```

### What's NOT in Primitives

- MIDI numbers (compilation target)
- Frequencies (audio domain)
- Velocity curves (expression layer)
- Instruments (orchestration layer)
- Audio (rendering layer)

**Primitives are symbolic and mathematical.** Everything else is downstream.

### Deliverables

- [ ] `core/pitch.py` — PitchClass, Interval
- [ ] `core/scale.py` — ScaleDegree, ScaleType, Key
- [ ] `core/chord.py` — ChordQuality, RomanNumeral, Chord
- [ ] `core/rhythm.py` — Duration, TimeSignature, BeatPosition
- [ ] Full test coverage for all primitives
- [ ] Round-trip serialization (YAML ↔ objects)

---

## Phase 1: Arrangement & Layer Model

**Goal:** Implement the producer mental model — arrangements contain layers, layers contain patterns.

Note: We use "Arrangement" (not "Session") to align with producer vocabulary. A Project contains patterns and styles; an Arrangement is one song structure.

### Core Models

```python
# models/arrangement.py

class LayerRole(Enum):
    """Frequency/function hierarchy"""
    SUB = "sub"           # Sub bass (20-60 Hz)
    BASS = "bass"         # Bass (60-250 Hz)
    DRUMS = "drums"       # Rhythm section
    HARMONY = "harmony"   # Chords, pads
    MELODY = "melody"     # Lead lines
    FX = "fx"             # Risers, impacts
    VOCAL = "vocal"       # Voice

@dataclass
class Layer:
    """A single track/stem in the composition"""
    name: str
    role: LayerRole
    patterns: dict[str, Pattern]           # pattern_id → Pattern
    arrangement: dict[str, str | None]     # section_id → pattern_id or None

    muted: bool = False
    solo: bool = False
    level: float = 1.0

@dataclass
class Section:
    """A structural segment"""
    name: str
    bars: int
    energy: str | None = None  # semantic token

@dataclass
class Arrangement:
    """A complete composition"""
    # Global tokens
    key: Key
    tempo: int
    time_signature: TimeSignature
    style: str | None = None

    # Structure
    sections: list[Section]

    # Layers
    layers: dict[str, Layer]

    def get_active_patterns(self, section: str) -> dict[str, Pattern]: ...
    def total_bars(self) -> int: ...
    def validate(self) -> list[ValidationError]: ...
```

### Arrangement YAML Format

```yaml
# my-track.arrangement.yaml
schema: arrangement/v1
key: D_minor
tempo: 124
time_signature: 4/4
style: melodic-techno

sections:
  - name: intro
    bars: 8
    energy: low
  - name: verse
    bars: 16
    energy: medium
  - name: breakdown
    bars: 8
    energy: low
  - name: chorus
    bars: 16
    energy: high
  - name: outro
    bars: 8
    energy: medium

layers:
  drums:
    role: drums
    patterns:
      main: four-on-floor
      sparse: four-on-floor@sparse
    arrangement:
      intro: null
      verse: main
      breakdown: null
      chorus: main
      outro: sparse

  bass:
    role: bass
    patterns:
      pulse: root-pulse
      rolling: rolling-sixteenths
    arrangement:
      intro: null
      verse: pulse
      breakdown: null
      chorus: rolling
      outro: pulse
```

### ArrangementManager

```python
class ArrangementManager:
    """Manages arrangements with artifact store integration"""

    async def create(
        self,
        name: str,
        key: str,
        tempo: int,
        style: str | None = None
    ) -> Arrangement: ...

    async def get(self, name: str) -> Arrangement | None: ...
    async def save(self, name: str) -> None: ...
    async def list(self) -> list[ArrangementMetadata]: ...
```

### Deliverables

- [ ] `models/arrangement.py` — Arrangement, Layer, Section, LayerRole
- [ ] `arrangement/manager.py` — ArrangementManager with artifact store
- [ ] `arrangement/validator.py` — Structure validation
- [ ] YAML serialization/deserialization
- [ ] Tests for arrangement operations

---

## Phase 2: Pattern System (The shadcn Layer)

**Goal:** Implement copyable, ownable, modifiable patterns.

### Pattern Definition

```yaml
# patterns/library/bass/root-pulse.yaml
name: root-pulse
role: bass
description: Simple root note pulse, foundation of most genres
version: 1.0.0

parameters:
  density:
    type: enum
    values: [sparse, quarter, eighth, sixteenth]
    default: quarter
  register:
    type: enum
    values: [sub, low, mid]
    default: low
  variation:
    type: float
    range: [0.0, 1.0]
    default: 0.2

constraints:
  requires: [key, tempo, time_signature]
  frequency_range: [40, 250]
  compatible_styles: [electronic, ambient, techno, house]

template:
  bars: 1
  loop: true
  notes:
    - degree: 1
      beat: 0
      duration: $density
      velocity: 0.8
    - degree: 1
      beat: 0.5
      duration: $density
      velocity: 0.6
```

### Pattern Registry

```python
class PatternRegistry:
    """Discovers and loads patterns from library and project"""

    def __init__(self, library_path: Path, project_path: Path | None = None):
        self.library_path = library_path
        self.project_path = project_path

    def list_patterns(
        self,
        role: LayerRole | None = None,
        style: str | None = None
    ) -> list[PatternMetadata]: ...

    def get_pattern(self, pattern_id: str) -> Pattern | None: ...

    def copy_to_project(self, pattern_id: str) -> Path:
        """The shadcn 'add' moment — copy pattern to project"""
        ...
```

### Built-in Pattern Library

```
patterns/library/
├── bass/
│   ├── root-pulse.yaml
│   ├── octave-bounce.yaml
│   ├── rolling-sixteenths.yaml
│   └── syncopated-funk.yaml
├── drums/
│   ├── four-on-floor.yaml
│   ├── breakbeat-simple.yaml
│   ├── minimal-techno.yaml
│   └── trap-hihat.yaml
├── harmony/
│   ├── pad-sustained.yaml
│   ├── chord-stabs.yaml
│   ├── arpeggio-up.yaml
│   └── arpeggio-random.yaml
├── melody/
│   ├── call-response.yaml
│   └── sequence-rising.yaml
└── fx/
    ├── riser-white-noise.yaml
    ├── impact-sub-drop.yaml
    └── sweep-filter.yaml
```

### Deliverables

- [ ] `models/pattern.py` — Pattern, PatternMetadata, PatternParameter
- [ ] `patterns/registry.py` — PatternRegistry
- [ ] `patterns/compiler.py` — Pattern → ScoreIR with parameter resolution
- [ ] 3-5 patterns per role (bass, drums, harmony, melody, fx)
- [ ] Pattern validation and constraint checking
- [ ] Tests for pattern loading and compilation

---

## Phase 3: Style System (Constraint Bundles)

**Goal:** Styles narrow the solution space without forcing specific choices.

### Style Definition

```yaml
# styles/library/melodic-techno.yaml
name: melodic-techno
description: Driving, melodic electronic music with emotional depth

tokens:
  tempo:
    range: [120, 128]
    default: 124
  key_preference: minor
  time_signature: 4/4

energy_mapping:
  low:
    layers: [1, 2]
    percussion: minimal
    harmony_density: sparse
  medium:
    layers: [3, 4]
    percussion: standard
    harmony_density: moderate
  high:
    layers: [5, 6]
    percussion: full
    harmony_density: rich

layer_hints:
  drums:
    suggested: [four-on-floor, minimal-techno]
    avoid: [breakbeat-*, trap-*]
  bass:
    suggested: [rolling-sixteenths, root-pulse]
    register: low
  harmony:
    suggested: [pad-sustained, arpeggio-*]
    density: sparse

structure_hints:
  breakdown_required: true
  typical_length_minutes: [5, 8]
  intro_bars: [8, 16]
  outro_bars: [8, 16]

forbidden:
  patterns: [trap-hihat, wobble-bass]
  progressions: [ii-V-I]  # Too jazz
```

### Style Resolver

```python
class StyleResolver:
    """Resolves semantic tokens using style constraints"""

    def __init__(self, style: Style):
        self.style = style

    def resolve_energy(self, energy: str) -> EnergyConstraints:
        """Convert 'high' → specific layer/density constraints"""
        ...

    def suggest_patterns(
        self,
        role: LayerRole,
        energy: str
    ) -> list[PatternMetadata]:
        """Get style-appropriate patterns for a role"""
        ...

    def validate_pattern(
        self,
        pattern: Pattern,
        role: LayerRole
    ) -> list[StyleViolation]:
        """Check if pattern fits style constraints"""
        ...
```

### Deliverables

- [ ] `models/style.py` — Style, EnergyMapping, LayerHint
- [ ] `styles/loader.py` — Style discovery and loading
- [ ] `styles/resolver.py` — StyleResolver
- [ ] 3 built-in styles (ambient, melodic-techno, cinematic)
- [ ] Style validation in session creation
- [ ] Tests for style resolution

---

## Phase 4: Score IR & MIDI Compilation

**Goal:** Deterministic compilation from symbolic score to MIDI.

### Score IR

```python
@dataclass
class ScoreEvent:
    """A single note event in absolute time"""
    pitch: int              # MIDI note number
    start: Fraction         # Position in bars
    duration: Fraction      # Length in bars
    velocity: int           # 0-127
    channel: int            # MIDI channel

@dataclass
class ScoreIR:
    """Intermediate representation — symbolic but concrete"""
    tempo: int
    time_signature: TimeSignature
    events: list[ScoreEvent]

    # Metadata for debugging
    source_session: str
    source_patterns: dict[str, str]  # layer → pattern_id

    def to_midi(self) -> MidiFile: ...
```

### Compilation Pipeline

```
Session
   ↓ (arrange)
Active Patterns per Section
   ↓ (compile patterns)
Pattern Events (relative)
   ↓ (resolve to key)
Score Events (absolute pitch)
   ↓ (merge layers)
ScoreIR
   ↓ (voice allocation)
Voiced ScoreIR
   ↓ (timing engine)
MIDI Events
   ↓ (write)
MIDI File
```

### MIDI Compiler

```python
class MidiCompiler:
    """Deterministic MIDI generation"""

    def __init__(
        self,
        channel_map: dict[LayerRole, int] | None = None,
        humanization: float = 0.0,
        swing: float = 0.0
    ):
        self.channel_map = channel_map or DEFAULT_CHANNEL_MAP
        self.humanization = humanization
        self.swing = swing

    def compile(self, ir: ScoreIR) -> MidiFile:
        """Same IR → same MIDI, always"""
        ...

    def compile_section(
        self,
        session: Session,
        section: str
    ) -> MidiFile:
        """Preview a single section"""
        ...
```

### Deliverables

- [ ] `compiler/ir.py` — ScoreEvent, ScoreIR
- [ ] `compiler/pattern_compiler.py` — Pattern → events
- [ ] `compiler/arranger.py` — Session → ScoreIR
- [ ] `compiler/midi.py` — ScoreIR → MIDI
- [ ] `compiler/voicing.py` — Chord voicing rules
- [ ] Determinism tests (same input → same output)
- [ ] Round-trip tests

---

## Phase 5: MCP Tool Surface

**Goal:** Minimal, composable tool set for LLM interaction.

### Arrangement Tools

```python
# tools/arrangement/management.py

@mcp.tool
async def music_create_arrangement(
    name: str,
    key: str,
    tempo: int,
    time_signature: str = "4/4",
    style: str | None = None
) -> str:
    """Create a new music arrangement."""

@mcp.tool
async def music_get_arrangement(name: str) -> str:
    """Get arrangement details."""

@mcp.tool
async def music_list_arrangements() -> str:
    """List all arrangements."""
```

### Structure Tools

```python
# tools/structure/sections.py

@mcp.tool
async def music_add_section(
    arrangement: str,
    name: str,
    bars: int,
    energy: str | None = None
) -> str:
    """Add a section to the arrangement."""

@mcp.tool
async def music_remove_section(arrangement: str, name: str) -> str:
    """Remove a section."""

@mcp.tool
async def music_reorder_sections(arrangement: str, order: list[str]) -> str:
    """Reorder sections."""
```

### Layer Tools

```python
# tools/layers/management.py

@mcp.tool
async def music_add_layer(
    arrangement: str,
    name: str,
    role: str  # drums, bass, harmony, melody, fx
) -> str:
    """Add a layer to the arrangement."""

@mcp.tool
async def music_mute_layer(arrangement: str, name: str) -> str:
    """Mute a layer."""

@mcp.tool
async def music_solo_layer(arrangement: str, name: str) -> str:
    """Solo a layer."""
```

### Pattern Tools

```python
# tools/patterns/management.py

@mcp.tool
async def music_list_patterns(
    role: str | None = None,
    style: str | None = None
) -> str:
    """List available patterns."""

@mcp.tool
async def music_add_pattern(
    arrangement: str,
    layer: str,
    pattern_id: str,
    alias: str | None = None,
    **params
) -> str:
    """Add a pattern to a layer."""

@mcp.tool
async def music_describe_pattern(pattern_id: str) -> str:
    """Get pattern details and parameters."""
```

### Layer Arrangement Tools

```python
# tools/structure/layer_arrangement.py

@mcp.tool
async def music_arrange_layer(
    arrangement: str,
    layer: str,
    section_patterns: dict[str, str | None]  # section → pattern_alias or null
) -> str:
    """Set what patterns play in which sections."""

@mcp.tool
async def music_set_section_energy(
    arrangement: str,
    section: str,
    energy: str
) -> str:
    """Set energy level for a section."""
```

### Compilation Tools

```python
# tools/compilation/export.py

@mcp.tool
async def music_compile_midi(arrangement: str) -> str:
    """Compile arrangement to MIDI file."""

@mcp.tool
async def music_preview_section(arrangement: str, section: str) -> str:
    """Preview a single section as MIDI."""

@mcp.tool
async def music_export_yaml(arrangement: str) -> str:
    """Export arrangement as YAML."""

@mcp.tool
async def music_validate(arrangement: str) -> str:
    """Validate arrangement structure and constraints."""
```

### Deliverables

- [ ] `tools/arrangement/` — Arrangement lifecycle tools
- [ ] `tools/structure/` — Section and layer arrangement tools
- [ ] `tools/layers/` — Layer management tools
- [ ] `tools/patterns/` — Pattern discovery and assignment
- [ ] `tools/compilation/` — MIDI export tools
- [ ] Comprehensive docstrings with examples
- [ ] Tool tests

---

## Phase 6: Iteration & Variation (Future)

**Goal:** Enable controlled musical evolution.

### Variation Tools

```python
@mcp.tool
async def music_mutate_pattern(
    arrangement: str,
    layer: str,
    pattern_alias: str,
    mutations: dict[str, Any]
) -> str:
    """Mutate pattern parameters."""

@mcp.tool
async def music_fork_arrangement(
    arrangement: str,
    new_name: str
) -> str:
    """Create a variation of an arrangement."""

@mcp.tool
async def music_suggest_variation(
    arrangement: str,
    target: str,  # "energy", "density", "complexity"
    direction: str  # "more", "less"
) -> str:
    """Get suggestions for variation."""
```

---

## Phase 7: Audio Rendering (Optional, Downstream)

**Goal:** Hear the output (not the core value).

### Rendering Adapters

```python
class Renderer(Protocol):
    async def render(self, midi: MidiFile) -> AudioBuffer: ...

class FluidSynthRenderer(Renderer):
    """SoundFont-based rendering"""
    ...

class CloudRenderer(Renderer):
    """External rendering service"""
    ...
```

### Recommendation

Start with FluidSynth + GM SoundFont. Good enough to validate, cheap to run.

---

## Hello World Demo

**Input:**
```
"Create a melancholic 32-bar piece in D minor, slow energy build"
```

**What the system does:**

1. Create session with `melodic-techno` style, D minor, 124 BPM
2. Infer structure: intro (8) → verse (16) → chorus (8)
3. Add layers: drums, bass, harmony
4. Select patterns based on style + energy hints
5. Arrange: drums enter in verse, full in chorus
6. Validate structure and constraints
7. Compile to MIDI

**Output artifacts:**
- `session.yaml` — inspectable, editable
- `score.ir.json` — symbolic score
- `output.mid` — playable MIDI

The LLM never touches notes. It operates at intent level.

---

## Key Architectural Decisions

### Pydantic Native
All models use Pydantic for validation and serialization.

### Async Native
All I/O operations are async. Use `asyncio.to_thread()` for blocking operations.

### No Dictionary Goop
Type-safe models throughout. No `dict[str, Any]` for structured data.

### No Magic Strings
Use enums and Literal types for constrained values.

### Deterministic Compilation
Same arrangement → same MIDI. Always. Seed randomness explicitly.

### Artifact Store Integration
Arrangements persist via chuk-artifacts. Multi-instance safe.

### Pattern Ownership
Patterns are copied, not referenced. Users own their modifications.

---

## Testing Strategy

### Unit Tests
- All primitives (intervals, scales, chords)
- Pattern compilation
- Session validation

### Integration Tests
- Full session → MIDI pipeline
- MCP tool registration and execution
- Artifact store round-trips

### Property Tests
- Interval math (closure, associativity)
- Transpose invariants
- Serialization round-trips

### Determinism Tests
- Same arrangement → same MIDI (byte-identical)
- Pattern compilation is reproducible

---

## Architectural Decisions (Locked)

These decisions are final for v1. Don't revisit.

### 1. Enharmonic Equivalence

PitchClass is the 12-tone chromatic space (0-11). Spelling is a display concern.

```python
class PitchClass(IntEnum):
    C = 0; Cs = 1; D = 2; Ds = 3; E = 4; F = 5
    Fs = 6; G = 7; Gs = 8; A = 9; As = 10; B = 11

# Spelling at serialization only
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
```

Defer proper enharmonic context to v2. Sharps are default.

### 2. Drums Use Absolute MIDI Notes

Drums are special-cased. No harmony resolution.

```yaml
# patterns/drums/four-on-floor.yaml
schema: pattern/v1
name: four-on-floor
role: drums
pitched: false  # Disables harmony resolution

template:
  events:
    - note: 36  # Kick (absolute MIDI)
      beat: 0
      velocity: 0.9
```

Add `DrumKit` vocabulary in Phase 6 if needed. Don't block MVP.

### 3. Octave Specification

Use `+N` / `-N` suffix for octave shifts from layer default.

```yaml
template:
  events:
    - degree: chord.root      # Default octave for layer role
    - degree: chord.root+1    # Up one octave
    - degree: chord.fifth-1   # Down one octave
```

### 4. Voice Leading

V1 voicing is dumb stacking. No voice leading consideration.

```python
def voice_chord(chord: Chord, register: tuple[int, int]) -> list[int]:
    """Stack intervals from root, no voice leading"""
    root_midi = closest_in_range(chord.root, register)
    return sorted([root_midi + i.semitones for i in chord.quality.intervals])
```

Voice leading is Phase 7+. Explicitly out of scope.

### 5. Template Expression Language

**Killed.** No expressions. Only direct substitution.

```yaml
# NO - Don't do this:
velocity: $velocity_base * 0.85

# YES - Use variants instead:
velocity: $velocity_base

variants:
  soft:
    velocity_base: 0.68
  normal:
    velocity_base: 0.8
```

No DSL. No math. Just `$param` → value.

### 6. Two-Stage Compilation

PatternInstance has resolved params but no pitches. EventList has actual MIDI.

```
Session YAML
    ↓ parse
Session (in-memory)
    ↓ resolve params + variants
PatternInstance (JSON)  ← No pitches, just resolved params
    ↓ compile with (HarmonyContext + Key + LayerContract)
EventList (JSON)        ← Actual MIDI pitches
    ↓ write
MIDI File
```

---

## Schema Versions (Frozen for v1)

Every YAML/JSON file starts with `schema: <type>/v1`. This is the contract.

```yaml
# Schema versions for v1 - do not change during implementation
schemas:
  project: project/v1
  arrangement: arrangement/v1
  pattern: pattern/v1
  pattern-instance: instance/v1
  events: events/v1
  harmony: harmony/v1
  style: style/v1
  operation: operation/v1
  pattern-test: pattern-test/v1
```

If you need to break compatibility, bump to v2. This avoids migration nightmares.

---

## Explicit Deferrals

| Feature | Status | When |
|---------|--------|------|
| Enharmonic spelling context | Deferred | v2 |
| DrumKit vocabulary | Deferred | Phase 6 |
| Voice leading | Deferred | Phase 7+ |
| Template expressions | Killed | Never |
| Groove/swing | Deferred | Phase 6 |
| Modulation (key changes) | Deferred | v2 |
| Tempo changes | Deferred | v2 |
| Audio rendering | Deferred | Phase 7 |
| Real-time preview | Deferred | v2 |

---

## Open Questions (Remaining)

| Question | Options | Recommendation |
|----------|---------|----------------|
| Pattern variation: random or deterministic? | Deterministic with explicit seed | Reproducibility |
| How many layers in v1? | 5 (drums, bass, harmony, melody, fx) | Covers most use cases |

---

## Success Criteria

### Phase 0-1 Complete When:
- [x] Can create a session with key, tempo, sections
- [x] Session serializes to readable YAML
- [x] Session validates structure

### Phase 2 Complete When:
- [x] Can list and describe patterns
- [x] Can add patterns to layers
- [x] Pattern compilation works end-to-end

### Phase 3 Complete When:
- [ ] Style constraints narrow pattern suggestions
- [ ] 3 built-in styles (ambient, melodic-techno, cinematic)

### Phase 4-5 Complete When:
- [x] Session compiles to valid MIDI
- [x] MIDI is deterministic
- [x] MCP tools work end-to-end

### Hello World Complete When:
- [x] Arrangement YAML → Playable MIDI (demonstrated with examples/compile_arrangement.py)
- [x] Output is inspectable YAML + playable MIDI
- [x] No note-level interaction required

---

## Timeline Philosophy

No time estimates. Focus on what needs to be done, not when.

---

## Critical Path (Build Order)

**Strategy: Skeleton first, then harden.** Prove the pipeline works before perfecting primitives.

### Step 1: Prove MIDI Export Works

```python
# Hardcoded everything, just prove mido works
@dataclass
class HardcodedEvent:
    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int

def make_four_on_floor() -> list[HardcodedEvent]:
    """Hardcoded drum pattern, no abstractions"""
    return [
        HardcodedEvent(36, 0.0, 0.5, 100),   # Kick
        HardcodedEvent(42, 0.0, 0.25, 80),   # HH
        HardcodedEvent(38, 1.0, 0.5, 100),   # Snare
    ]

def events_to_midi(events: list[HardcodedEvent], tempo: int) -> MidiFile:
    """Use mido, just make it work"""

# TEST: Can I make a MIDI file that plays in a DAW?
```

### Step 2: Minimal Primitives

```python
# Only what you need for C major and D minor
class PitchClass(IntEnum):
    C = 0; D = 2; E = 4; F = 5; G = 7; A = 9; B = 11
    Cs = 1; Ds = 3; Fs = 6; Gs = 8; As = 10

@dataclass(frozen=True)
class Interval:
    semitones: int

# Just the intervals you need
MINOR_THIRD = Interval(3)
MAJOR_THIRD = Interval(4)
PERFECT_FIFTH = Interval(7)

# TEST: Can I spell C major and D minor chords?
```

### Step 3: Pattern → Events (One Pattern)

```python
# Make root-pulse work with hardcoded progressions
def compile_root_pulse(
    key: Key,
    progression: list[RomanNumeral],
    bars: int,
    params: dict
) -> list[HardcodedEvent]:

# TEST: Can I generate a bassline that follows i-VI-III-VII?
```

### Step 4: Arrangement YAML → MIDI

```python
# Parse minimal arrangement, compile to MIDI
arrangement = load_arrangement("demo.arrangement.yaml")
events = compile_arrangement(arrangement)
midi = events_to_midi(events)

# TEST: YAML in, playable MIDI out
```

### Step 5: MCP Tool Wrappers

```python
@mcp.tool
async def music_create_arrangement(...) -> str:
    ...

@mcp.tool
async def music_compile_midi(...) -> str:
    ...

# TEST: LLM can create and compile an arrangement
```

At this point: **vertical slice complete**. The whole pipeline works for one narrow case.

Then widen:
- More scales → generalize Key
- More patterns → generalize Pattern loading
- More chord types → generalize ChordQuality

---

## Priority Order

1. **MIDI export** (prove the pipeline endpoint)
2. **Minimal primitives** (just enough for C major, D minor)
3. **One pattern end-to-end** (root-pulse bass)
4. **Arrangement parsing** (YAML → in-memory)
5. **Full compilation** (Arrangement → MIDI)
6. **MCP tools** (the interface)
7. **More patterns** (drums, harmony)
8. **Everything else** (iteration)

---

## Integration Points

| CHUK Component | Music System Use |
|----------------|------------------|
| chuk-artifacts | Arrangement/MIDI storage |
| chuk-virtual-fs | Expose compositions as files |
| chuk-mcp-server | MCP server framework |
| chuk-tool-processor | Idempotent tool wrappers |
| chuk-mcp-solver | Constraint satisfaction for pattern selection |

---

## The "Add" Moment

The shadcn magic, applied to music:

```bash
$ chuk-music add bass/rolling-sixteenths

✓ Added pattern to patterns/bass/rolling-sixteenths.yaml

You can now use this pattern in your arrangement:
  arrangement.layers["bass"].add_pattern("rolling", "rolling-sixteenths")

Customize it by editing patterns/bass/rolling-sixteenths.yaml
```

You didn't install a dependency. You copied a well-designed starting point. **Now it's yours.**

---

## User Project Layout (Canonical)

When a user runs `chuk-music init`, they get this structure:

```
my-project/
├── chuk-music.yaml              # Project manifest (like package.json)
├── primitives/                   # Owned primitives (rarely touched)
│   ├── scales.yaml
│   └── chord-qualities.yaml
├── patterns/                     # Owned patterns (shadcn moment)
│   ├── drums/
│   │   ├── four-on-floor.yaml
│   │   └── four-on-floor.test.yaml
│   ├── bass/
│   │   ├── root-pulse.yaml
│   │   └── root-pulse.test.yaml
│   └── harmony/
│       └── pad-sustained.yaml
├── styles/                       # Constraint bundles
│   └── melodic-techno.yaml
├── arrangements/                 # Compositions
│   ├── demo.arrangement.yaml     # Arrangement definition
│   ├── demo.instance.json        # Resolved (computed)
│   └── demo.events.json          # Rendered (computed)
├── output/                       # Build artifacts
│   ├── demo.mid
│   └── demo.wav                  # Optional
└── .chuk/                        # Internal state
    ├── cache/
    └── history/                  # Diffable operation log
```

---

## Project Manifest

```yaml
# chuk-music.yaml
schema: project/v1
name: my-project
version: 0.1.0

defaults:
  key: C_major
  tempo: 120
  time_signature: 4/4

layer_contracts:
  sub:
    midi_range: [24, 36]      # C1-C2
    max_polyphony: 1
  bass:
    midi_range: [36, 52]      # C2-E3
    max_polyphony: 1
  drums:
    midi_range: [36, 84]      # GM drum map range
    max_polyphony: 8
  harmony:
    midi_range: [48, 72]      # C3-C5
    max_polyphony: 6
  melody:
    midi_range: [60, 84]      # C4-C6
    max_polyphony: 2
  fx:
    midi_range: [0, 127]      # Unconstrained
    max_polyphony: 4

registry:
  remote: https://registry.chuk-music.dev  # Optional pattern registry
```

---

## The IR Stack (Three Clean Layers)

This is crucial. Three distinct representations, each with a clear job:

### Layer 1: PatternDef (Template)

**What**: Ownable template with parameters. Lives in `patterns/`.
**When**: Copied via `chuk-music add`, edited by user.
**Format**: YAML (human-friendly).

```yaml
# patterns/bass/root-pulse.yaml
schema: pattern/v1
name: root-pulse
role: bass
description: Simple root note pulse on chord roots

parameters:
  density:
    type: enum
    values: [whole, half, quarter, eighth, sixteenth]
    default: quarter
  register:
    type: enum
    values: [sub, low, mid]
    default: low
  velocity_base:
    type: float
    range: [0.0, 1.0]
    default: 0.8
  humanize:
    type: float
    range: [0.0, 1.0]
    default: 0.1

variants:
  dark:
    register: sub
    velocity_base: 0.6
    humanize: 0.05
  driving:
    density: eighth
    velocity_base: 0.85
    humanize: 0.15

template:
  events:
    - beat: 0
      degree: chord.root
      duration: $density
      velocity: $velocity_base
    - beat: $density.beats
      degree: chord.root
      duration: $density
      velocity: $velocity_base * 0.85

constraints:
  requires_harmony: true
  max_notes_per_bar: 16
```

### Layer 2: PatternInstance (Resolved)

**What**: Parameters resolved, variant applied, ready for rendering.
**When**: Computed when session is "compiled" (first pass).
**Format**: JSON (machine-friendly, diffable).

```json
{
  "schema": "instance/v1",
  "pattern_ref": "bass/root-pulse",
  "pattern_hash": "sha256:abc123...",
  "resolved_params": {
    "density": "eighth",
    "register": "low",
    "velocity_base": 0.85,
    "humanize": 0.15
  },
  "variant": "driving",
  "context": {
    "key": "D_minor",
    "tempo": 124,
    "time_signature": "4/4"
  }
}
```

This is what you **diff** to see what the LLM changed.

### Layer 3: EventList (Rendered)

**What**: Concrete note events, deterministic output from instance + harmony.
**When**: Computed when session is rendered (second pass).
**Format**: JSON (machine-friendly, MIDI-ready).

```json
{
  "schema": "events/v1",
  "source_instance_hash": "sha256:def456...",
  "layer": "bass",
  "events": [
    {
      "type": "note",
      "start_ticks": 0,
      "duration_ticks": 240,
      "pitch": 38,
      "velocity": 108,
      "channel": 1
    }
  ],
  "meta": {
    "ticks_per_beat": 480,
    "tempo": 124
  }
}
```

This is **deterministic**. Same instance + same harmony → same events. Always.

---

## Harmony as First-Class Layer

Harmony is the song's DNA. Even if it's not a playable track, it's a **global timeline signal**:

```yaml
# In session definition
harmony:
  default_progression: [i, VI, III, VII]
  harmonic_rhythm: 1bar
  sections:
    verse:
      progression: [i, VI, III, VII]
    chorus:
      progression: [i, VII, VI, VII]
    breakdown:
      progression: [i, i, VI, VI]
```

Patterns reference harmony symbolically:

```yaml
template:
  events:
    - degree: chord.root      # Resolved at compile time
      duration: $density
    - degree: chord.fifth
      duration: $density
```

```python
@dataclass
class HarmonyContext:
    """What chord is active at this beat?"""
    progression: list[RomanNumeral]
    harmonic_rhythm: Duration

    def chord_at(self, beat: BeatPosition) -> RomanNumeral:
        """Which chord is active at this beat?"""
        bar_in_progression = beat.bar % len(self.progression)
        return self.progression[bar_in_progression]

    def resolve_degree(
        self,
        degree: str,
        beat: BeatPosition,
        key: Key,
        role: LayerRole
    ) -> int:
        """Resolve 'chord.root', 'chord.third', etc. to MIDI pitch"""
        chord = self.chord_at(beat)
        concrete = chord.resolve(key)

        if degree == "chord.root":
            return concrete.root.to_midi(octave=self.octave_for_role(role))
        elif degree == "chord.third":
            return concrete.third.to_midi(...)
        # etc.
```

This is why patterns are reusable across songs.

---

## Register Contracts (Enforced)

Layer contracts define what's allowed:

```python
@dataclass
class LayerContract:
    midi_range: tuple[int, int]
    max_polyphony: int

    def validate_events(self, events: EventList) -> list[Violation]:
        violations = []
        for event in events:
            if not (self.midi_range[0] <= event.pitch <= self.midi_range[1]):
                violations.append(PitchOutOfRange(event, self.midi_range))

        # Check polyphony at each tick
        # ...

        return violations
```

Validation happens at the EventList stage. Patterns that violate contracts fail to compile.

---

## Pattern Variants (Like Component Variants)

```yaml
variants:
  dark:
    register: sub
    velocity_base: 0.6
    humanize: 0.05
  driving:
    density: eighth
    velocity_base: 0.85
    humanize: 0.15
  sparse:
    density: half
    velocity_base: 0.5
```

Usage:

```yaml
patterns:
  main:
    ref: bass/root-pulse
    variant: driving
  breakdown:
    ref: bass/root-pulse
    variant: sparse
```

---

## Pattern Tests (Golden Tests)

When you `chuk-music add`, also copy the test file:

```yaml
# patterns/bass/root-pulse.test.yaml
schema: pattern-test/v1
pattern: bass/root-pulse

cases:
  - name: default_params_d_minor
    context:
      key: D_minor
      tempo: 120
      time_signature: 4/4
    harmony:
      progression: [i]
      harmonic_rhythm: 1bar
    params: {}

    expect:
      midi_range: [36, 52]
      max_polyphony: 1
      notes_per_bar: 4
      events_hash: "sha256:789abc..."

  - name: driving_variant
    context:
      key: D_minor
      tempo: 124
      time_signature: 4/4
    harmony:
      progression: [i, VI, III, VII]
      harmonic_rhythm: 1bar
    params:
      variant: driving

    expect:
      midi_range: [36, 52]
      max_polyphony: 1
      notes_per_bar: 8
      events_hash: "sha256:def012..."
```

Run with `chuk-music test patterns/`. Deterministic. CI-friendly.

---

## Operation Log (Diffable Agent Actions)

Every agent action becomes a diffable commit:

```yaml
# .chuk/history/2024-01-15T14-22-00.op.yaml
schema: operation/v1
timestamp: 2024-01-15T14:22:00Z
agent: claude-sonnet-4-20250514
session: demo

operation:
  type: arrange_layer
  layer: bass
  changes:
    chorus:
      before: pulse
      after: driving

reasoning: "Increased bass energy in chorus for contrast with breakdown"

diff:
  path: sessions/demo.session.yaml
  patch: |
    @@ -45,7 +45,7 @@ layers:
           breakdown: null
    -      chorus: pulse
    +      chorus: driving
           outro: pulse
```

This makes the system:
- Explainable
- Reversible
- Training-data-friendly

---

## Full Session Definition

```yaml
# sessions/demo.session.yaml
schema: session/v1
name: demo
created: 2024-01-15T10:30:00Z
modified: 2024-01-15T14:22:00Z

context:
  key: D_minor
  tempo: 124
  time_signature: 4/4
  style: melodic-techno

harmony:
  default_progression: [i, VI, III, VII]
  harmonic_rhythm: 1bar
  sections:
    verse:
      progression: [i, VI, III, VII]
    chorus:
      progression: [i, VII, VI, VII]
    breakdown:
      progression: [i, i, VI, VI]

sections:
  - name: intro
    bars: 8

  - name: verse
    bars: 16

  - name: breakdown
    bars: 8

  - name: chorus
    bars: 16

  - name: outro
    bars: 8

layers:
  drums:
    role: drums
    channel: 10
    patterns:
      main:
        ref: drums/four-on-floor
      sparse:
        ref: drums/four-on-floor
        params:
          density: half
          velocity_base: 0.6
    arrangement:
      intro: null
      verse: main
      breakdown: null
      chorus: main
      outro: sparse

  bass:
    role: bass
    channel: 1
    patterns:
      pulse:
        ref: bass/root-pulse
        variant: dark
      driving:
        ref: bass/root-pulse
        variant: driving
    arrangement:
      intro: null
      verse: pulse
      breakdown: null
      chorus: driving
      outro: pulse

  harmony:
    role: harmony
    channel: 2
    patterns:
      pad:
        ref: harmony/pad-sustained
        params:
          attack: slow
          density: sparse
    arrangement:
      intro: pad
      verse: pad
      breakdown: pad
      chorus: pad
      outro: pad
```

---

## Compilation Pipeline (Detailed)

```
┌─────────────────┐
│  Session YAML   │  (human-authored)
└────────┬────────┘
         │ parse + validate
         ▼
┌─────────────────┐
│  Session AST    │  (in-memory)
└────────┬────────┘
         │ resolve patterns + params
         ▼
┌─────────────────┐
│  Instance JSON  │  (diffable, cacheable)
└────────┬────────┘
         │ render with harmony context
         ▼
┌─────────────────┐
│  Events JSON    │  (deterministic)
└────────┬────────┘
         │ compile to MIDI
         ▼
┌─────────────────┐
│  MIDI File      │  (output)
└─────────────────┘
```

Each stage is independently cacheable. Hash-based invalidation.

---

## CLI Commands

```bash
# Project management
chuk-music init my-project
chuk-music validate

# Pattern management (the shadcn moment)
chuk-music list                     # Show registry
chuk-music add drums/four-on-floor  # Copy to project
chuk-music test patterns/           # Run all pattern tests

# Arrangement management
chuk-music new arrangement my-track
chuk-music compile arrangements/my-track.arrangement.yaml
chuk-music preview arrangements/my-track.arrangement.yaml --section chorus

# Inspection
chuk-music show arrangements/my-track.instance.json
chuk-music diff arrangements/my-track.arrangement.yaml
chuk-music history arrangements/my-track
```

---

## Extended MCP Tool Surface

```python
# Project
initialize_project(name: str) -> ProjectInfo
validate_project() -> ValidationResult

# Patterns
list_available_patterns(role: str | None) -> list[PatternInfo]
add_pattern(pattern_ref: str) -> PatternDef
get_pattern(pattern_ref: str) -> PatternDef
customize_pattern(pattern_ref: str, changes: dict) -> PatternDef

# Arrangements
create_arrangement(name: str, key: str, tempo: int) -> Arrangement
get_arrangement(name: str) -> Arrangement
set_harmony(arrangement: str, section: str, progression: list[str]) -> Arrangement

# Structure
add_section(arrangement: str, name: str, bars: int) -> Arrangement
remove_section(arrangement: str, name: str) -> Arrangement
reorder_sections(arrangement: str, order: list[str]) -> Arrangement

# Layers
add_layer(arrangement: str, name: str, role: str) -> Arrangement
assign_pattern(
    arrangement: str,
    layer: str,
    pattern_name: str,
    pattern_ref: str,
    params: dict | None,
    variant: str | None
) -> Arrangement
arrange_layer(arrangement: str, layer: str, section_patterns: dict[str, str | None]) -> Arrangement

# Compilation
compile_arrangement(arrangement: str) -> CompileResult
preview_section(arrangement: str, section: str) -> PreviewResult

# Inspection (critical for agent reasoning)
get_instance(arrangement: str) -> InstanceJSON
get_events(arrangement: str, layer: str | None) -> EventsJSON
get_operation_history(arrangement: str, limit: int) -> list[Operation]
```

---

## The MVP That Proves the Thesis

The MVP isn't "generate a track." It's:

1. `chuk-music init my_project`
2. `chuk-music add drums/four-on-floor`
3. `chuk-music add bass/root-pulse`
4. Create `arrangements/demo.arrangement.yaml` with intro/verse/chorus
5. `chuk-music compile arrangements/demo.arrangement.yaml → demo.mid`
6. Open in Ableton/Logic and **it works immediately**

That's the shadcn moment for music.

---

## The Thesis, Locked

```
┌──────────────────────────────────────────────────────────────┐
│                     CHUK-MUSIC                                │
├──────────────────────────────────────────────────────────────┤
│  Primitives        │  Intervals, scales, durations           │
│  (Radix)           │  Mathematical, immutable, composable    │
├──────────────────────────────────────────────────────────────┤
│  Patterns          │  Ownable templates with parameters      │
│  (shadcn)          │  Copied, not installed. You own them.   │
├──────────────────────────────────────────────────────────────┤
│  Arrangements      │  Compositions = layers × sections       │
│  (Your Project)    │  YAML, diffable, version-controlled     │
├──────────────────────────────────────────────────────────────┤
│  IR Stack          │  PatternDef → Instance → Events → MIDI  │
│                    │  Each layer: cacheable, deterministic   │
├──────────────────────────────────────────────────────────────┤
│  Agent Interface   │  MCP tools operate on structure         │
│                    │  Every action is a diffable operation   │
└──────────────────────────────────────────────────────────────┘
```

This is the foundation. Everything else builds on it.
