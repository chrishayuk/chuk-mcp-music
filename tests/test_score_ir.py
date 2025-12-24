"""
Tests for Score IR (Intermediate Representation).

Tests cover:
- Schema versioning and compatibility
- Canonical ordering for deterministic output
- JSON serialization round-trips
- Diff functionality between Score IRs
- Golden file testing for key arrangements
"""

import pytest

from chuk_mcp_music.compiler import ArrangementCompiler
from chuk_mcp_music.compiler.score_ir import (
    SCHEMA_VERSION,
    IRNote,
    IRSectionMarker,
    IRTempoEvent,
    IRTimeSignature,
    ScoreIR,
)
from chuk_mcp_music.models.arrangement import (
    Arrangement,
    ArrangementContext,
    EnergyLevel,
    Harmony,
    Layer,
    LayerRole,
    PatternRef,
    Section,
)
from chuk_mcp_music.models.pattern import (
    Pattern,
    PatternEvent,
    PatternTemplate,
)
from chuk_mcp_music.patterns import PatternRegistry


class TestIRNote:
    """Tests for IRNote."""

    def test_create_note(self) -> None:
        """Create a valid note."""
        note = IRNote(
            start_ticks=0,
            channel=0,
            pitch=60,
            duration_ticks=480,
            velocity=100,
        )
        assert note.pitch == 60
        assert note.velocity == 100

    def test_note_validation_pitch(self) -> None:
        """Pitch must be 0-127."""
        with pytest.raises(ValueError, match="Pitch must be 0-127"):
            IRNote(
                start_ticks=0,
                channel=0,
                pitch=128,
                duration_ticks=480,
                velocity=100,
            )

    def test_note_validation_velocity(self) -> None:
        """Velocity must be 0-127."""
        with pytest.raises(ValueError, match="Velocity must be 0-127"):
            IRNote(
                start_ticks=0,
                channel=0,
                pitch=60,
                duration_ticks=480,
                velocity=128,
            )

    def test_note_validation_channel(self) -> None:
        """Channel must be 0-15."""
        with pytest.raises(ValueError, match="Channel must be 0-15"):
            IRNote(
                start_ticks=0,
                channel=16,
                pitch=60,
                duration_ticks=480,
                velocity=100,
            )

    def test_note_validation_start_ticks(self) -> None:
        """Start ticks must be >= 0."""
        with pytest.raises(ValueError, match="Start ticks must be >= 0"):
            IRNote(
                start_ticks=-1,
                channel=0,
                pitch=60,
                duration_ticks=480,
                velocity=100,
            )

    def test_note_validation_duration(self) -> None:
        """Duration ticks must be >= 0."""
        with pytest.raises(ValueError, match="Duration ticks must be >= 0"):
            IRNote(
                start_ticks=0,
                channel=0,
                pitch=60,
                duration_ticks=-1,
                velocity=100,
            )

    def test_note_with_source_metadata(self) -> None:
        """Note can include source traceability metadata."""
        note = IRNote(
            start_ticks=480,
            channel=1,
            pitch=48,
            duration_ticks=240,
            velocity=90,
            source_layer="bass",
            source_pattern="bass/root-pulse",
            source_section="verse",
            bar=1,
            beat=0.0,
        )
        assert note.source_layer == "bass"
        assert note.source_pattern == "bass/root-pulse"
        assert note.source_section == "verse"

    def test_note_ordering(self) -> None:
        """Notes are ordered by (start_ticks, channel, pitch)."""
        note1 = IRNote(start_ticks=0, channel=0, pitch=60, duration_ticks=480, velocity=100)
        note2 = IRNote(start_ticks=0, channel=0, pitch=62, duration_ticks=480, velocity=100)
        note3 = IRNote(start_ticks=0, channel=1, pitch=60, duration_ticks=480, velocity=100)
        note4 = IRNote(start_ticks=480, channel=0, pitch=60, duration_ticks=480, velocity=100)

        notes = [note4, note3, note2, note1]
        sorted_notes = sorted(notes)

        assert sorted_notes == [note1, note2, note3, note4]

    def test_note_to_dict(self) -> None:
        """Note serializes to dictionary."""
        note = IRNote(
            start_ticks=0,
            channel=1,
            pitch=48,
            duration_ticks=480,
            velocity=90,
            source_layer="bass",
        )
        d = note.to_dict()

        assert d["start_ticks"] == 0
        assert d["channel"] == 1
        assert d["pitch"] == 48
        assert d["duration_ticks"] == 480
        assert d["velocity"] == 90
        assert d["source_layer"] == "bass"
        assert "source_pattern" not in d  # Optional fields omitted if None

    def test_note_from_dict(self) -> None:
        """Note deserializes from dictionary."""
        d = {
            "start_ticks": 960,
            "channel": 9,
            "pitch": 36,
            "duration_ticks": 120,
            "velocity": 100,
            "source_layer": "drums",
        }
        note = IRNote.from_dict(d)

        assert note.start_ticks == 960
        assert note.channel == 9
        assert note.pitch == 36
        assert note.source_layer == "drums"


class TestIRTimeSignature:
    """Tests for IRTimeSignature."""

    def test_create_time_signature(self) -> None:
        """Create a time signature."""
        ts = IRTimeSignature(4, 4)
        assert ts.numerator == 4
        assert ts.denominator == 4

    def test_time_signature_to_dict(self) -> None:
        """Time signature serializes."""
        ts = IRTimeSignature(6, 8)
        d = ts.to_dict()
        assert d == {"numerator": 6, "denominator": 8}

    def test_time_signature_from_dict(self) -> None:
        """Time signature deserializes."""
        ts = IRTimeSignature.from_dict({"numerator": 3, "denominator": 4})
        assert ts.numerator == 3
        assert ts.denominator == 4


class TestScoreIR:
    """Tests for ScoreIR."""

    def test_create_empty_ir(self) -> None:
        """Create an empty Score IR with defaults."""
        ir = ScoreIR()
        assert ir.schema == SCHEMA_VERSION
        assert ir.name == ""
        assert ir.tempo == 120
        assert ir.notes == []

    def test_create_ir_with_notes(self) -> None:
        """Create Score IR with notes."""
        notes = [
            IRNote(start_ticks=0, channel=0, pitch=60, duration_ticks=480, velocity=100),
            IRNote(start_ticks=480, channel=0, pitch=62, duration_ticks=480, velocity=100),
        ]
        ir = ScoreIR(
            name="test",
            key="C_major",
            tempo=120,
            notes=notes,
        )
        assert len(ir.notes) == 2
        assert ir.note_count() == 2

    def test_canonicalize_sorts_notes(self) -> None:
        """Canonicalize sorts notes in deterministic order."""
        note1 = IRNote(start_ticks=480, channel=0, pitch=60, duration_ticks=480, velocity=100)
        note2 = IRNote(start_ticks=0, channel=0, pitch=62, duration_ticks=480, velocity=100)
        note3 = IRNote(start_ticks=0, channel=0, pitch=60, duration_ticks=480, velocity=100)

        ir = ScoreIR(notes=[note1, note2, note3])
        canonical = ir.canonicalize()

        assert canonical.notes == [note3, note2, note1]

    def test_to_json_deterministic(self) -> None:
        """Same IR produces identical JSON output."""
        notes = [
            IRNote(start_ticks=480, channel=0, pitch=60, duration_ticks=480, velocity=100),
            IRNote(start_ticks=0, channel=0, pitch=62, duration_ticks=480, velocity=100),
        ]
        ir1 = ScoreIR(name="test", notes=notes)
        ir2 = ScoreIR(name="test", notes=list(reversed(notes)))

        json1 = ir1.to_json()
        json2 = ir2.to_json()

        assert json1 == json2  # Same after canonicalization

    def test_json_round_trip(self) -> None:
        """IR survives JSON serialization round-trip."""
        original = ScoreIR(
            name="test-arrangement",
            key="D_minor",
            tempo=124,
            time_signature=IRTimeSignature(4, 4),
            ticks_per_beat=480,
            total_ticks=5760,
            total_bars=12,
            notes=[
                IRNote(
                    start_ticks=0,
                    channel=1,
                    pitch=50,
                    duration_ticks=480,
                    velocity=90,
                    source_layer="bass",
                    source_section="verse",
                ),
            ],
            sections=[
                IRSectionMarker(name="verse", start_ticks=0, end_ticks=5760, bars=12),
            ],
            tempo_events=[IRTempoEvent(ticks=0, bpm=124)],
            layers={"bass": {"role": "bass", "channel": 1}},
        )

        json_str = original.to_json()
        restored = ScoreIR.from_json(json_str)

        assert restored.name == original.name
        assert restored.key == original.key
        assert restored.tempo == original.tempo
        assert len(restored.notes) == 1
        assert restored.notes[0].pitch == 50

    def test_notes_by_layer(self) -> None:
        """Group notes by source layer."""
        ir = ScoreIR(
            notes=[
                IRNote(
                    start_ticks=0,
                    channel=1,
                    pitch=48,
                    duration_ticks=480,
                    velocity=90,
                    source_layer="bass",
                ),
                IRNote(
                    start_ticks=0,
                    channel=9,
                    pitch=36,
                    duration_ticks=120,
                    velocity=100,
                    source_layer="drums",
                ),
                IRNote(
                    start_ticks=480,
                    channel=1,
                    pitch=50,
                    duration_ticks=480,
                    velocity=90,
                    source_layer="bass",
                ),
            ]
        )

        by_layer = ir.notes_by_layer()
        assert len(by_layer["bass"]) == 2
        assert len(by_layer["drums"]) == 1

    def test_notes_by_section(self) -> None:
        """Group notes by source section."""
        ir = ScoreIR(
            notes=[
                IRNote(
                    start_ticks=0,
                    channel=1,
                    pitch=48,
                    duration_ticks=480,
                    velocity=90,
                    source_section="intro",
                ),
                IRNote(
                    start_ticks=1920,
                    channel=1,
                    pitch=50,
                    duration_ticks=480,
                    velocity=90,
                    source_section="verse",
                ),
            ]
        )

        by_section = ir.notes_by_section()
        assert len(by_section["intro"]) == 1
        assert len(by_section["verse"]) == 1

    def test_summary(self) -> None:
        """Generate summary statistics."""
        ir = ScoreIR(
            name="test",
            key="C_major",
            tempo=120,
            total_bars=8,
            notes=[
                IRNote(
                    start_ticks=0,
                    channel=1,
                    pitch=48,
                    duration_ticks=480,
                    velocity=80,
                    source_layer="bass",
                ),
                IRNote(
                    start_ticks=0,
                    channel=9,
                    pitch=36,
                    duration_ticks=120,
                    velocity=100,
                    source_layer="drums",
                ),
            ],
        )

        summary = ir.summary()
        assert summary["name"] == "test"
        assert summary["total_notes"] == 2
        assert summary["layers"]["bass"] == 1
        assert summary["layers"]["drums"] == 1
        assert summary["pitch_range"] == (36, 48)
        assert summary["velocity_range"] == (80, 100)

    def test_diff_summary(self) -> None:
        """Diff between two Score IRs."""
        ir1 = ScoreIR(
            name="v1",
            tempo=120,
            key="C_major",
            total_bars=8,
            notes=[
                IRNote(start_ticks=0, channel=0, pitch=60, duration_ticks=480, velocity=100),
                IRNote(start_ticks=480, channel=0, pitch=62, duration_ticks=480, velocity=100),
            ],
        )

        ir2 = ScoreIR(
            name="v2",
            tempo=120,
            key="C_major",
            total_bars=8,
            notes=[
                IRNote(start_ticks=0, channel=0, pitch=60, duration_ticks=480, velocity=100),
                IRNote(
                    start_ticks=480, channel=0, pitch=64, duration_ticks=480, velocity=100
                ),  # Changed
            ],
        )

        diff = ir1.diff_summary(ir2)
        assert diff["notes_added"] == 1
        assert diff["notes_removed"] == 1
        assert diff["notes_unchanged"] == 1
        assert diff["tempo_changed"] is False


class TestGoldenFileIR:
    """Golden file tests for Score IR.

    These tests compile known arrangements and verify the Score IR
    matches expected output. This catches any regression in the
    compilation pipeline.
    """

    @pytest.fixture
    def pattern_registry(self) -> PatternRegistry:
        """Create a registry with test patterns."""
        registry = PatternRegistry()

        # Register a simple bass pattern
        bass_pattern = Pattern(
            name="test-bass",
            role=LayerRole.BASS,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration="quarter", degree="chord.root"),
                    PatternEvent(beat=2, duration="quarter", degree="chord.fifth"),
                ],
            ),
        )
        registry.register_pattern(bass_pattern, "bass/test-bass")

        # Register a simple drum pattern
        drum_pattern = Pattern(
            name="test-drums",
            role=LayerRole.DRUMS,
            pitched=False,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration=0.25, note=36),  # Kick
                    PatternEvent(beat=2, duration=0.25, note=38),  # Snare
                ],
            ),
        )
        registry.register_pattern(drum_pattern, "drums/test-drums")

        return registry

    @pytest.fixture
    def golden_arrangement(self) -> Arrangement:
        """Create a deterministic arrangement for golden file testing."""
        return Arrangement(
            name="golden-test",
            context=ArrangementContext(
                key="C_major",
                tempo=120,
                time_signature="4/4",
            ),
            harmony=Harmony(
                default_progression=["I", "V"],
                harmonic_rhythm="1bar",
            ),
            sections=[
                Section(name="intro", bars=2, energy=EnergyLevel.LOW),
            ],
            layers={
                "bass": Layer(
                    name="bass",
                    role=LayerRole.BASS,
                    channel=1,
                    patterns={
                        "main": PatternRef(ref="bass/test-bass"),
                    },
                    arrangement={
                        "intro": "main",
                    },
                ),
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    channel=9,
                    patterns={
                        "main": PatternRef(ref="drums/test-drums"),
                    },
                    arrangement={
                        "intro": "main",
                    },
                ),
            },
        )

    def test_score_ir_schema_version(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Score IR includes schema version."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(golden_arrangement)

        assert result.score_ir.schema == "score_ir/v1"

    def test_score_ir_contains_all_notes(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Score IR contains expected notes from all layers."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(golden_arrangement)

        ir = result.score_ir
        # 2 bars, 2 notes per bar per layer = 8 total
        # Bass: 2 notes/bar * 2 bars = 4
        # Drums: 2 notes/bar * 2 bars = 4
        assert ir.note_count() == 8

    def test_score_ir_notes_have_source(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """All notes have source traceability."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(golden_arrangement)

        for note in result.score_ir.notes:
            assert note.source_layer is not None
            assert note.source_pattern is not None
            assert note.source_section is not None
            assert note.bar is not None

    def test_score_ir_deterministic(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Same arrangement produces identical Score IR."""
        compiler = ArrangementCompiler(pattern_registry)

        result1 = compiler.compile(golden_arrangement)
        result2 = compiler.compile(golden_arrangement)

        json1 = result1.score_ir.to_json()
        json2 = result2.score_ir.to_json()

        assert json1 == json2

    def test_score_ir_golden_structure(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Score IR structure matches expected golden output."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(golden_arrangement)

        ir = result.score_ir
        d = ir.to_dict()

        # Verify structure
        assert d["schema"] == "score_ir/v1"
        assert d["name"] == "golden-test"
        assert d["key"] == "C_major"
        assert d["tempo"] == 120
        assert d["time_signature"] == {"numerator": 4, "denominator": 4}
        assert d["ticks_per_beat"] == 480
        assert d["total_bars"] == 2

        # Verify sections
        assert len(d["sections"]) == 1
        assert d["sections"][0]["name"] == "intro"
        assert d["sections"][0]["bars"] == 2

        # Verify layers info
        assert "bass" in d["layers"]
        assert "drums" in d["layers"]
        assert d["layers"]["bass"]["channel"] == 1
        assert d["layers"]["drums"]["channel"] == 9

    def test_score_ir_bass_notes_correct(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Bass notes have correct pitch values from chord degrees."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(golden_arrangement)

        bass_notes = [n for n in result.score_ir.notes if n.source_layer == "bass"]
        # Sort by start time
        bass_notes.sort(key=lambda n: n.start_ticks)

        assert len(bass_notes) == 4

        # Bar 0: I chord (C major), root=C, fifth=G
        # Bass role uses octave 2: C2=36, G2=43
        # Bar 1: V chord (G major), root=G, fifth=D
        # G2=43, D3=38
        pitches = [n.pitch for n in bass_notes]
        assert pitches[0] == 36  # C2 (root of I)
        assert pitches[1] == 43  # G2 (fifth of I)
        assert pitches[2] == 43  # G2 (root of V)
        assert pitches[3] == 38  # D3 (fifth of V)

    def test_score_ir_drum_notes_correct(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Drum notes have correct MIDI numbers."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(golden_arrangement)

        drum_notes = [n for n in result.score_ir.notes if n.source_layer == "drums"]
        drum_notes.sort(key=lambda n: n.start_ticks)

        assert len(drum_notes) == 4

        # Pattern: Kick on beat 0, Snare on beat 2
        pitches = [n.pitch for n in drum_notes]
        assert pitches[0] == 36  # Kick (bar 0)
        assert pitches[1] == 38  # Snare (bar 0)
        assert pitches[2] == 36  # Kick (bar 1)
        assert pitches[3] == 38  # Snare (bar 1)

    def test_score_ir_section_compile(
        self, pattern_registry: PatternRegistry, golden_arrangement: Arrangement
    ) -> None:
        """Section compilation produces correct Score IR."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile_section(golden_arrangement, "intro")

        ir = result.score_ir
        assert ir.name == "golden-test:intro"
        assert ir.total_bars == 2
        assert ir.note_count() == 8
