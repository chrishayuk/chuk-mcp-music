"""
Score IR - the intermediate representation between arrangement and MIDI.

This is the stable, inspectable, diffable representation of a compiled arrangement.
The IR is versioned and designed to be:
- Deterministic: same arrangement → same IR
- Serializable: JSON/YAML for inspection and golden-file testing
- Diffable: canonical ordering for meaningful diffs
- Extensible: version field allows schema evolution

Schema version: score_ir/v1
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

# Current schema version
SCHEMA_VERSION = "score_ir/v1"


@dataclass(frozen=True, order=True)
class IRNote:
    """
    A single note in the Score IR.

    Ordered by: (start_ticks, channel, pitch) for deterministic sorting.
    All fields are immutable for hashability.
    """

    start_ticks: int  # Absolute position in ticks
    channel: int  # MIDI channel (0-15)
    pitch: int  # MIDI note number (0-127)
    duration_ticks: int  # Duration in ticks
    velocity: int  # 0-127

    # Optional metadata for traceability
    source_layer: str | None = field(default=None, compare=False)
    source_pattern: str | None = field(default=None, compare=False)
    source_section: str | None = field(default=None, compare=False)
    bar: int | None = field(default=None, compare=False)
    beat: float | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        """Validate MIDI ranges."""
        if not 0 <= self.pitch <= 127:
            raise ValueError(f"Pitch must be 0-127, got {self.pitch}")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"Velocity must be 0-127, got {self.velocity}")
        if not 0 <= self.channel <= 15:
            raise ValueError(f"Channel must be 0-15, got {self.channel}")
        if self.start_ticks < 0:
            raise ValueError(f"Start ticks must be >= 0, got {self.start_ticks}")
        if self.duration_ticks < 0:
            raise ValueError(f"Duration ticks must be >= 0, got {self.duration_ticks}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d: dict[str, Any] = {
            "start_ticks": self.start_ticks,
            "channel": self.channel,
            "pitch": self.pitch,
            "duration_ticks": self.duration_ticks,
            "velocity": self.velocity,
        }
        # Only include source metadata if present
        if self.source_layer:
            d["source_layer"] = self.source_layer
        if self.source_pattern:
            d["source_pattern"] = self.source_pattern
        if self.source_section:
            d["source_section"] = self.source_section
        if self.bar is not None:
            d["bar"] = self.bar
        if self.beat is not None:
            d["beat"] = self.beat
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IRNote:
        """Create from dictionary."""
        return cls(
            start_ticks=d["start_ticks"],
            channel=d["channel"],
            pitch=d["pitch"],
            duration_ticks=d["duration_ticks"],
            velocity=d["velocity"],
            source_layer=d.get("source_layer"),
            source_pattern=d.get("source_pattern"),
            source_section=d.get("source_section"),
            bar=d.get("bar"),
            beat=d.get("beat"),
        )


@dataclass(frozen=True)
class IRSectionMarker:
    """A section boundary marker in the IR."""

    name: str
    start_ticks: int
    end_ticks: int
    bars: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IRSectionMarker:
        """Create from dictionary."""
        return cls(**d)


@dataclass(frozen=True)
class IRTempoEvent:
    """A tempo change event."""

    ticks: int
    bpm: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IRTempoEvent:
        """Create from dictionary."""
        return cls(**d)


@dataclass(frozen=True)
class IRTimeSignature:
    """Time signature information."""

    numerator: int
    denominator: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IRTimeSignature:
        """Create from dictionary."""
        return cls(**d)

    @classmethod
    def from_time_sig(cls, time_sig: Any) -> IRTimeSignature:
        """
        Create from a TimeSignature object.

        Converts the beat_unit Duration to a standard denominator.
        """
        from fractions import Fraction

        # Convert beat unit to denominator
        denominator_map = {
            Fraction(4): 1,  # whole note
            Fraction(2): 2,  # half note
            Fraction(1): 4,  # quarter note
            Fraction(1, 2): 8,  # eighth note
            Fraction(1, 4): 16,  # sixteenth note
        }
        denominator = denominator_map.get(time_sig.beat_unit.beats, 4)
        return cls(time_sig.beats_per_bar, denominator)


@dataclass
class ScoreIR:
    """
    The complete Score Intermediate Representation.

    This is the canonical representation of a compiled arrangement,
    before MIDI encoding. It's designed for:
    - Inspection: human-readable when serialized
    - Diffing: canonical ordering makes diffs meaningful
    - Testing: golden-file tests can compare IR directly
    - Debugging: source traceability back to layers/patterns
    """

    # Schema version for forward compatibility
    schema: str = SCHEMA_VERSION

    # Arrangement metadata
    name: str = ""
    key: str = ""
    tempo: int = 120
    time_signature: IRTimeSignature = field(default_factory=lambda: IRTimeSignature(4, 4))
    ticks_per_beat: int = 480

    # Total duration
    total_ticks: int = 0
    total_bars: int = 0

    # The notes (canonical ordered)
    notes: list[IRNote] = field(default_factory=list)

    # Section markers
    sections: list[IRSectionMarker] = field(default_factory=list)

    # Tempo events (for tempo changes mid-piece)
    tempo_events: list[IRTempoEvent] = field(default_factory=list)

    # Layer summary (for inspection)
    layers: dict[str, dict[str, Any]] = field(default_factory=dict)

    def canonicalize(self) -> ScoreIR:
        """
        Return a new ScoreIR with canonical ordering.

        Notes are sorted by (start_ticks, channel, pitch).
        Sections are sorted by start_ticks.
        This ensures deterministic serialization.
        """
        return ScoreIR(
            schema=self.schema,
            name=self.name,
            key=self.key,
            tempo=self.tempo,
            time_signature=self.time_signature,
            ticks_per_beat=self.ticks_per_beat,
            total_ticks=self.total_ticks,
            total_bars=self.total_bars,
            notes=sorted(self.notes),  # IRNote has __lt__ via order=True
            sections=sorted(self.sections, key=lambda s: s.start_ticks),
            tempo_events=sorted(self.tempo_events, key=lambda t: t.ticks),
            layers=dict(sorted(self.layers.items())),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to a dictionary for JSON/YAML serialization.

        The output is always canonicalized for deterministic diffs.
        """
        ir = self.canonicalize()
        return {
            "schema": ir.schema,
            "name": ir.name,
            "key": ir.key,
            "tempo": ir.tempo,
            "time_signature": ir.time_signature.to_dict(),
            "ticks_per_beat": ir.ticks_per_beat,
            "total_ticks": ir.total_ticks,
            "total_bars": ir.total_bars,
            "notes": [n.to_dict() for n in ir.notes],
            "sections": [s.to_dict() for s in ir.sections],
            "tempo_events": [t.to_dict() for t in ir.tempo_events],
            "layers": ir.layers,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScoreIR:
        """Create from dictionary."""
        return cls(
            schema=d.get("schema", SCHEMA_VERSION),
            name=d.get("name", ""),
            key=d.get("key", ""),
            tempo=d.get("tempo", 120),
            time_signature=IRTimeSignature.from_dict(
                d.get("time_signature", {"numerator": 4, "denominator": 4})
            ),
            ticks_per_beat=d.get("ticks_per_beat", 480),
            total_ticks=d.get("total_ticks", 0),
            total_bars=d.get("total_bars", 0),
            notes=[IRNote.from_dict(n) for n in d.get("notes", [])],
            sections=[IRSectionMarker.from_dict(s) for s in d.get("sections", [])],
            tempo_events=[IRTempoEvent.from_dict(t) for t in d.get("tempo_events", [])],
            layers=d.get("layers", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ScoreIR:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def note_count(self) -> int:
        """Total number of notes."""
        return len(self.notes)

    def notes_by_layer(self) -> dict[str, list[IRNote]]:
        """Group notes by source layer."""
        result: dict[str, list[IRNote]] = {}
        for note in self.notes:
            layer = note.source_layer or "_unknown"
            if layer not in result:
                result[layer] = []
            result[layer].append(note)
        return result

    def notes_by_section(self) -> dict[str, list[IRNote]]:
        """Group notes by source section."""
        result: dict[str, list[IRNote]] = {}
        for note in self.notes:
            section = note.source_section or "_unknown"
            if section not in result:
                result[section] = []
            result[section].append(note)
        return result

    def summary(self) -> dict[str, Any]:
        """Generate a summary for quick inspection."""
        notes_by_layer = self.notes_by_layer()
        notes_by_section = self.notes_by_section()

        return {
            "name": self.name,
            "key": self.key,
            "tempo": self.tempo,
            "total_bars": self.total_bars,
            "total_notes": self.note_count(),
            "layers": {layer: len(notes) for layer, notes in sorted(notes_by_layer.items())},
            "sections": {
                section: len(notes) for section, notes in sorted(notes_by_section.items())
            },
            "pitch_range": (
                min(n.pitch for n in self.notes) if self.notes else 0,
                max(n.pitch for n in self.notes) if self.notes else 0,
            ),
            "velocity_range": (
                min(n.velocity for n in self.notes) if self.notes else 0,
                max(n.velocity for n in self.notes) if self.notes else 0,
            ),
        }

    def diff_summary(self, other: ScoreIR) -> dict[str, Any]:
        """
        Generate a summary of differences between two IRs.

        Useful for understanding what changed between compilations.
        """
        self_notes = set(self.notes)
        other_notes = set(other.notes)

        added = other_notes - self_notes
        removed = self_notes - other_notes
        unchanged = self_notes & other_notes

        return {
            "notes_added": len(added),
            "notes_removed": len(removed),
            "notes_unchanged": len(unchanged),
            "tempo_changed": self.tempo != other.tempo,
            "key_changed": self.key != other.key,
            "bars_changed": self.total_bars != other.total_bars,
            "sections_changed": [s.name for s in self.sections] != [s.name for s in other.sections],
        }
