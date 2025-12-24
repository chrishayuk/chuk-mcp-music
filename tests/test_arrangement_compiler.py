"""
Tests for ArrangementCompiler.

Tests cover:
- Full arrangement compilation to MIDI
- Section-by-section compilation
- Layer muting and soloing
- Velocity level adjustment
- Harmony context resolution
"""

import tempfile
from pathlib import Path

import pytest

from chuk_mcp_music.compiler import ArrangementCompiler, compile_arrangement
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


class TestArrangementCompiler:
    """Tests for ArrangementCompiler."""

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
                    PatternEvent(beat=1, duration="quarter", degree="chord.third"),
                    PatternEvent(beat=2, duration="quarter", degree="chord.fifth"),
                    PatternEvent(beat=3, duration="quarter", degree="chord.root"),
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
                    PatternEvent(beat=1, duration=0.25, note=38),  # Snare
                    PatternEvent(beat=2, duration=0.25, note=36),  # Kick
                    PatternEvent(beat=3, duration=0.25, note=38),  # Snare
                ],
            ),
        )
        registry.register_pattern(drum_pattern, "drums/test-drums")

        return registry

    @pytest.fixture
    def simple_arrangement(self) -> Arrangement:
        """Create a simple test arrangement."""
        return Arrangement(
            name="test-arrangement",
            context=ArrangementContext(
                key="C_major",
                tempo=120,
                time_signature="4/4",
            ),
            harmony=Harmony(
                default_progression=["I", "IV", "V", "I"],
                harmonic_rhythm="1bar",
            ),
            sections=[
                Section(name="intro", bars=4, energy=EnergyLevel.LOW),
                Section(name="verse", bars=8, energy=EnergyLevel.MEDIUM),
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
                        "intro": None,
                        "verse": "main",
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
                        "verse": "main",
                    },
                ),
            },
        )

    def test_compile_arrangement(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Compile a complete arrangement."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(simple_arrangement)

        assert result.total_bars == 12  # 4 + 8
        assert result.total_events > 0
        assert "bass" in result.layers_compiled
        assert "drums" in result.layers_compiled
        assert "intro" in result.sections_compiled
        assert "verse" in result.sections_compiled

    def test_compile_section(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Compile a single section."""
        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile_section(simple_arrangement, "verse")

        assert result.total_bars == 8
        assert result.total_events > 0
        assert "verse" in result.sections_compiled

    def test_muted_layer_excluded(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Muted layers are excluded from compilation."""
        simple_arrangement.layers["bass"].muted = True

        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(simple_arrangement)

        assert "bass" not in result.layers_compiled
        assert "drums" in result.layers_compiled

    def test_solo_layer(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Solo mode only includes soloed layers."""
        simple_arrangement.layers["bass"].solo = True

        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(simple_arrangement)

        assert "bass" in result.layers_compiled
        assert "drums" not in result.layers_compiled

    def test_layer_level_affects_velocity(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Layer level adjusts event velocity."""
        # Set bass to half volume
        simple_arrangement.layers["bass"].level = 0.5
        # Ensure bass is in a section where it plays
        simple_arrangement.layers["bass"].arrangement = {"intro": "main", "verse": "main"}

        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile(simple_arrangement)

        # Find a bass event (channel 1) and check velocity is reduced
        bass_events = [e for e in _get_events_from_midi(result.midi_file) if e["channel"] == 1]
        assert len(bass_events) > 0
        # Velocities should be at most half of 127
        assert all(e["velocity"] <= 64 for e in bass_events)

    def test_empty_section_no_events(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """A section with no active patterns produces no events."""
        # Remove all patterns from intro
        simple_arrangement.layers["drums"].arrangement["intro"] = None

        compiler = ArrangementCompiler(pattern_registry)
        result = compiler.compile_section(simple_arrangement, "intro")

        assert result.total_events == 0

    def test_deterministic_output(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Same arrangement produces identical MIDI output."""
        compiler = ArrangementCompiler(pattern_registry)

        result1 = compiler.compile(simple_arrangement)
        result2 = compiler.compile(simple_arrangement)

        # Save to temp files and compare bytes
        with (
            tempfile.NamedTemporaryFile(suffix=".mid") as f1,
            tempfile.NamedTemporaryFile(suffix=".mid") as f2,
        ):
            result1.midi_file.save(f1.name)
            result2.midi_file.save(f2.name)

            with open(f1.name, "rb") as a, open(f2.name, "rb") as b:
                assert a.read() == b.read()

    def test_invalid_section_raises(
        self, pattern_registry: PatternRegistry, simple_arrangement: Arrangement
    ) -> None:
        """Compiling a nonexistent section raises ValueError."""
        compiler = ArrangementCompiler(pattern_registry)

        with pytest.raises(ValueError, match="Section not found"):
            compiler.compile_section(simple_arrangement, "nonexistent")


class TestCompileArrangementFunction:
    """Tests for the compile_arrangement convenience function."""

    @pytest.fixture
    def library_path(self) -> Path:
        """Get the pattern library path."""
        return Path(__file__).parent.parent / "src/chuk_mcp_music/patterns/library"

    @pytest.fixture
    def registry(self, library_path: Path) -> PatternRegistry:
        """Create a registry with library patterns."""
        return PatternRegistry(library_path=library_path)

    @pytest.fixture
    def full_arrangement(self) -> Arrangement:
        """Create an arrangement using library patterns."""
        return Arrangement(
            name="full-test",
            context=ArrangementContext(
                key="D_minor",
                tempo=124,
                time_signature="4/4",
            ),
            harmony=Harmony(
                default_progression=["i", "VI", "III", "VII"],
                harmonic_rhythm="1bar",
            ),
            sections=[
                Section(name="intro", bars=4),
                Section(name="verse", bars=8),
            ],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    channel=9,
                    patterns={
                        "main": PatternRef(ref="drums/four-on-floor"),
                    },
                    arrangement={
                        "intro": "main",
                        "verse": "main",
                    },
                ),
                "bass": Layer(
                    name="bass",
                    role=LayerRole.BASS,
                    channel=1,
                    patterns={
                        "main": PatternRef(ref="bass/root-pulse"),
                    },
                    arrangement={
                        "intro": None,
                        "verse": "main",
                    },
                ),
            },
        )

    def test_compile_with_library_patterns(
        self, registry: PatternRegistry, full_arrangement: Arrangement
    ) -> None:
        """Compile using library patterns."""
        result = compile_arrangement(full_arrangement, registry)

        assert result.total_bars == 12
        assert result.total_events > 0
        assert "drums" in result.layers_compiled
        assert "bass" in result.layers_compiled

    def test_compile_and_save(
        self, registry: PatternRegistry, full_arrangement: Arrangement
    ) -> None:
        """Compile and save to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mid"
            result = compile_arrangement(full_arrangement, registry, output_path)

            assert output_path.exists()
            assert result.total_events > 0


def _get_events_from_midi(midi_file) -> list[dict]:
    """Extract note events from a MIDI file for testing."""
    events = []
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                events.append(
                    {
                        "channel": msg.channel,
                        "note": msg.note,
                        "velocity": msg.velocity,
                    }
                )
    return events
