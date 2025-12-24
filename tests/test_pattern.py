"""
Tests for pattern system.

Tests cover:
- Pattern model creation and validation
- PatternRegistry discovery and loading
- PatternCompiler compilation to MIDI events
- HarmonyContext resolution
"""

import tempfile
from fractions import Fraction
from pathlib import Path

import pytest

from chuk_mcp_music.core import (
    BeatPosition,
    Duration,
    Key,
    PitchClass,
    ScaleType,
    TimeSignature,
)
from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.models.pattern import (
    ParameterType,
    Pattern,
    PatternConstraints,
    PatternEvent,
    PatternMetadata,
    PatternParameter,
    PatternTemplate,
    PatternVariant,
)
from chuk_mcp_music.patterns import (
    CompileContext,
    HarmonyContext,
    PatternCompiler,
    PatternRegistry,
    compile_pattern,
)


class TestPatternParameter:
    """Tests for PatternParameter model."""

    def test_enum_parameter(self) -> None:
        """Create an enum parameter."""
        param = PatternParameter(
            name="density",
            type="enum",
            description="Note density",
            values=["quarter", "eighth", "sixteenth"],
            default="quarter",
        )
        assert param.name == "density"
        assert param.param_type == ParameterType.ENUM
        assert param.validate_value("eighth")
        assert not param.validate_value("invalid")

    def test_float_parameter_with_range(self) -> None:
        """Create a float parameter with range."""
        param = PatternParameter(
            name="velocity",
            type="float",
            description="Note velocity",
            range=(0.0, 1.0),
            default=0.8,
        )
        assert param.validate_value(0.5)
        assert not param.validate_value(1.5)

    def test_int_parameter(self) -> None:
        """Create an int parameter."""
        param = PatternParameter(
            name="octave",
            type="int",
            description="Octave shift",
            range=(-2, 2),
            default=0,
        )
        assert param.validate_value(1)
        assert not param.validate_value(5)

    def test_bool_parameter(self) -> None:
        """Create a bool parameter."""
        param = PatternParameter(
            name="enabled",
            type="bool",
            description="Enable feature",
            default=True,
        )
        assert param.validate_value(True)
        assert param.validate_value(False)


class TestPatternEvent:
    """Tests for PatternEvent model."""

    def test_pitched_event(self) -> None:
        """Create a pitched event with degree."""
        event = PatternEvent(
            beat=0,
            duration="quarter",
            degree="chord.root",
            velocity=0.8,
        )
        assert event.beat == 0
        assert event.duration == "quarter"
        assert event.degree == "chord.root"
        assert event.note is None

    def test_drum_event(self) -> None:
        """Create a drum event with MIDI note."""
        event = PatternEvent(
            beat=0,
            duration=0.25,
            note=36,
            velocity=0.9,
        )
        assert event.note == 36
        assert event.degree is None

    def test_event_with_octave_shift(self) -> None:
        """Create event with octave shift."""
        event = PatternEvent(
            beat=0,
            duration="eighth",
            degree="scale.5",
            octave_shift=1,
        )
        assert event.octave_shift == 1


class TestPatternTemplate:
    """Tests for PatternTemplate model."""

    def test_simple_template(self) -> None:
        """Create a simple template."""
        template = PatternTemplate(
            bars=1,
            loop=True,
            events=[
                PatternEvent(beat=0, duration="quarter", degree="chord.root"),
                PatternEvent(beat=1, duration="quarter", degree="chord.third"),
            ],
        )
        assert template.bars == 1
        assert template.loop
        assert len(template.events) == 2

    def test_multi_bar_template(self) -> None:
        """Create multi-bar template."""
        template = PatternTemplate(
            bars=4,
            loop=False,
            events=[
                PatternEvent(beat=0, duration="whole", degree="chord.root"),
            ],
        )
        assert template.bars == 4
        assert not template.loop


class TestPattern:
    """Tests for Pattern model."""

    @pytest.fixture
    def simple_pattern(self) -> Pattern:
        """Create a simple test pattern."""
        return Pattern(
            name="test-pattern",
            role=LayerRole.BASS,
            description="Test bass pattern",
            parameters={
                "density": PatternParameter(
                    name="density",
                    type="enum",
                    values=["quarter", "eighth"],
                    default="quarter",
                )
            },
            variants={
                "driving": PatternVariant(
                    name="driving",
                    description="Driving variant",
                    params={"density": "eighth"},
                )
            },
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration="quarter", degree="chord.root"),
                ],
            ),
        )

    def test_create_pattern(self, simple_pattern: Pattern) -> None:
        """Create a pattern."""
        assert simple_pattern.name == "test-pattern"
        assert simple_pattern.role == LayerRole.BASS
        assert simple_pattern.pitched

    def test_get_resolved_params_defaults(self, simple_pattern: Pattern) -> None:
        """Get resolved parameters with defaults."""
        params = simple_pattern.get_resolved_params()
        assert params["density"] == "quarter"

    def test_get_resolved_params_variant(self, simple_pattern: Pattern) -> None:
        """Get resolved parameters with variant."""
        params = simple_pattern.get_resolved_params(variant="driving")
        assert params["density"] == "eighth"

    def test_get_resolved_params_overrides(self, simple_pattern: Pattern) -> None:
        """Get resolved parameters with overrides."""
        params = simple_pattern.get_resolved_params(overrides={"density": "eighth"})
        assert params["density"] == "eighth"

    def test_validate_params_valid(self, simple_pattern: Pattern) -> None:
        """Validate valid parameters."""
        errors = simple_pattern.validate_params({"density": "quarter"})
        assert len(errors) == 0

    def test_validate_params_invalid(self, simple_pattern: Pattern) -> None:
        """Validate invalid parameters."""
        errors = simple_pattern.validate_params({"density": "invalid"})
        assert len(errors) == 1

    def test_validate_params_unknown(self, simple_pattern: Pattern) -> None:
        """Validate unknown parameter."""
        errors = simple_pattern.validate_params({"unknown": "value"})
        assert len(errors) == 1
        assert "Unknown parameter" in errors[0]


class TestPatternMetadata:
    """Tests for PatternMetadata model."""

    def test_from_pattern(self) -> None:
        """Create metadata from pattern."""
        pattern = Pattern(
            name="test",
            role=LayerRole.DRUMS,
            description="Test drums",
            pitched=False,
            variants={
                "minimal": PatternVariant(name="minimal", params={}),
            },
            template=PatternTemplate(bars=1, events=[]),
        )
        metadata = PatternMetadata.from_pattern(pattern, path="/test/path.yaml")

        assert metadata.name == "test"
        assert metadata.role == LayerRole.DRUMS
        assert not metadata.pitched
        assert "minimal" in metadata.variants
        assert metadata.path == "/test/path.yaml"


class TestHarmonyContext:
    """Tests for HarmonyContext."""

    @pytest.fixture
    def context(self) -> HarmonyContext:
        """Create a harmony context."""
        return HarmonyContext(
            key=Key(PitchClass.D, ScaleType.NATURAL_MINOR),
            progression=["i", "VI", "III", "VII"],
            harmonic_rhythm=Duration.WHOLE,
        )

    def test_chord_at_position(self, context: HarmonyContext) -> None:
        """Get chord at different positions."""
        time_sig = TimeSignature.COMMON_TIME

        # Bar 0 = i
        chord0 = context.chord_at(BeatPosition(0, Fraction(0)), time_sig)
        assert chord0.degree.degree == 1  # i

        # Bar 1 = VI
        chord1 = context.chord_at(BeatPosition(1, Fraction(0)), time_sig)
        assert chord1.degree.degree == 6  # VI

        # Bar 2 = III
        chord2 = context.chord_at(BeatPosition(2, Fraction(0)), time_sig)
        assert chord2.degree.degree == 3  # III

    def test_resolve_chord_root(self, context: HarmonyContext) -> None:
        """Resolve chord.root to MIDI pitch."""
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))  # Bar 0, i chord (D minor)

        pitch = context.resolve_degree("chord.root", position, time_sig, LayerRole.BASS)
        # Should resolve to D in bass register
        assert 36 <= pitch <= 52  # Bass register

    def test_resolve_scale_degree(self, context: HarmonyContext) -> None:
        """Resolve scale degree to MIDI pitch."""
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))

        pitch = context.resolve_degree("scale.1", position, time_sig, LayerRole.MELODY)
        # Scale degree 1 in D minor is D
        assert 60 <= pitch <= 84  # Melody register

    def test_resolve_with_octave_shift(self, context: HarmonyContext) -> None:
        """Resolve with octave shift."""
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))

        pitch_base = context.resolve_degree(
            "chord.root", position, time_sig, LayerRole.BASS, octave_shift=0
        )
        pitch_up = context.resolve_degree(
            "chord.root", position, time_sig, LayerRole.BASS, octave_shift=1
        )
        # Octave up should be 12 semitones higher (or clamped)
        assert pitch_up >= pitch_base


class TestPatternCompiler:
    """Tests for PatternCompiler."""

    @pytest.fixture
    def compiler(self) -> PatternCompiler:
        """Create a compiler."""
        return PatternCompiler()

    @pytest.fixture
    def bass_pattern(self) -> Pattern:
        """Create a bass pattern."""
        return Pattern(
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

    @pytest.fixture
    def drum_pattern(self) -> Pattern:
        """Create a drum pattern."""
        return Pattern(
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

    def test_compile_bass_pattern(self, compiler: PatternCompiler, bass_pattern: Pattern) -> None:
        """Compile a bass pattern."""
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(
            key=key,
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.BASS,
            channel=1,
        )

        events = compiler.compile(bass_pattern, context, bars=1)

        assert len(events) == 4
        # All events should be on channel 1
        assert all(e.channel == 1 for e in events)
        # Events should be in bass register
        assert all(36 <= e.pitch <= 52 for e in events)

    def test_compile_drum_pattern(self, compiler: PatternCompiler, drum_pattern: Pattern) -> None:
        """Compile a drum pattern."""
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(
            key=key,
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.DRUMS,
            channel=9,
        )

        events = compiler.compile(drum_pattern, context, bars=1)

        assert len(events) == 4
        # Drums on channel 9
        assert all(e.channel == 9 for e in events)
        # Check specific drum notes
        assert events[0].pitch == 36  # Kick
        assert events[1].pitch == 38  # Snare

    def test_compile_multiple_bars(self, compiler: PatternCompiler, bass_pattern: Pattern) -> None:
        """Compile pattern for multiple bars."""
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(
            key=key,
            progression=["I", "IV"],
            harmonic_rhythm=Duration.WHOLE,
        )
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.BASS,
            channel=1,
        )

        events = compiler.compile(bass_pattern, context, bars=2)

        # 4 events per bar, 2 bars
        assert len(events) == 8


class TestCompilePatternFunction:
    """Tests for compile_pattern convenience function."""

    def test_compile_pattern(self) -> None:
        """Use compile_pattern function."""
        pattern = Pattern(
            name="test",
            role=LayerRole.HARMONY,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration="whole", degree="chord.root"),
                ],
            ),
        )

        events = compile_pattern(
            pattern=pattern,
            key=Key(PitchClass.G, ScaleType.MAJOR),
            tempo=100,
            time_sig=TimeSignature.COMMON_TIME,
            progression=["I", "V", "vi", "IV"],
            role=LayerRole.HARMONY,
            channel=2,
            bars=4,
        )

        assert len(events) == 4  # One per bar


class TestPatternRegistry:
    """Tests for PatternRegistry."""

    @pytest.fixture
    def library_path(self) -> Path:
        """Get the pattern library path."""
        return Path(__file__).parent.parent / "src/chuk_mcp_music/patterns/library"

    def test_list_patterns(self, library_path: Path) -> None:
        """List all patterns."""
        registry = PatternRegistry(library_path=library_path)
        patterns = registry.list_patterns()

        # Should find patterns we created
        assert len(patterns) > 0

    def test_list_patterns_by_role(self, library_path: Path) -> None:
        """List patterns by role."""
        registry = PatternRegistry(library_path=library_path)

        drums = registry.list_patterns(role=LayerRole.DRUMS)
        bass = registry.list_patterns(role=LayerRole.BASS)

        assert all(p.role == LayerRole.DRUMS for p in drums)
        assert all(p.role == LayerRole.BASS for p in bass)

    def test_get_pattern(self, library_path: Path) -> None:
        """Get a specific pattern."""
        registry = PatternRegistry(library_path=library_path)
        pattern = registry.get_pattern("drums/four-on-floor")

        assert pattern is not None
        assert pattern.name == "four-on-floor"
        assert pattern.role == LayerRole.DRUMS
        assert not pattern.pitched

    def test_get_nonexistent_pattern(self, library_path: Path) -> None:
        """Get a pattern that doesn't exist."""
        registry = PatternRegistry(library_path=library_path)
        pattern = registry.get_pattern("drums/nonexistent")

        assert pattern is None

    def test_get_pattern_metadata(self, library_path: Path) -> None:
        """Get pattern metadata."""
        registry = PatternRegistry(library_path=library_path)
        metadata = registry.get_pattern_metadata("bass/root-pulse")

        assert metadata is not None
        assert metadata.name == "root-pulse"
        assert metadata.role == LayerRole.BASS

    def test_register_pattern_programmatically(self) -> None:
        """Register a pattern programmatically."""
        registry = PatternRegistry()

        pattern = Pattern(
            name="dynamic-pattern",
            role=LayerRole.MELODY,
            template=PatternTemplate(bars=1, events=[]),
        )

        pattern_id = registry.register_pattern(pattern)

        assert pattern_id == "melody/dynamic-pattern"
        assert registry.get_pattern(pattern_id) is not None

    def test_copy_to_project(self, library_path: Path) -> None:
        """Copy a pattern to project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            registry = PatternRegistry(
                library_path=library_path,
                project_path=project_path,
            )

            # Copy pattern to project
            result_path = registry.copy_to_project("drums/four-on-floor")

            assert result_path is not None
            assert result_path.exists()
            assert result_path.name == "four-on-floor.yaml"

            # Reload and verify
            registry._cache.clear()
            registry._metadata_cache.clear()
            pattern = registry.get_pattern("drums/four-on-floor")

            assert pattern is not None


class TestPatternConstraints:
    """Tests for PatternConstraints model."""

    def test_default_constraints(self) -> None:
        """Default constraints."""
        constraints = PatternConstraints()
        assert constraints.requires_harmony

    def test_drum_constraints(self) -> None:
        """Drum pattern constraints."""
        constraints = PatternConstraints(
            requires_harmony=False,
            compatible_styles=["house", "techno"],
        )
        assert not constraints.requires_harmony
        assert "house" in (constraints.compatible_styles or [])


class TestHarmonyContextAdditional:
    """Additional tests for HarmonyContext edge cases."""

    def test_empty_progression_defaults_to_tonic(self) -> None:
        """Empty progression defaults to I chord."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=[],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        chord = context.chord_at(BeatPosition(0, Fraction(0)), time_sig)
        assert chord.degree.degree == 1  # Should default to I

    def test_resolve_chord_third(self) -> None:
        """Resolve chord.third to MIDI pitch."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))
        pitch = context.resolve_degree("chord.third", position, time_sig, LayerRole.HARMONY)
        # E in major chord
        assert 48 <= pitch <= 72  # Harmony register

    def test_resolve_chord_fifth(self) -> None:
        """Resolve chord.fifth to MIDI pitch."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))
        pitch = context.resolve_degree("chord.fifth", position, time_sig, LayerRole.HARMONY)
        # G in major chord
        assert 48 <= pitch <= 72

    def test_resolve_chord_seventh(self) -> None:
        """Resolve chord.seventh to MIDI pitch."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))
        pitch = context.resolve_degree("chord.seventh", position, time_sig, LayerRole.HARMONY)
        # Should resolve to a seventh
        assert 48 <= pitch <= 72

    def test_resolve_unknown_chord_tone(self) -> None:
        """Resolve unknown chord tone defaults to root."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))
        pitch = context.resolve_degree("chord.unknown", position, time_sig, LayerRole.HARMONY)
        # Should default to root
        assert 48 <= pitch <= 72

    def test_resolve_numeric_degree(self) -> None:
        """Resolve numeric degree (just a number)."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))
        pitch = context.resolve_degree("5", position, time_sig, LayerRole.MELODY)
        # Scale degree 5 (G)
        assert 60 <= pitch <= 84

    def test_resolve_unknown_format_defaults_to_root(self) -> None:
        """Unknown format defaults to key root."""
        context = HarmonyContext(
            key=Key(PitchClass.C, ScaleType.MAJOR),
            progression=["I"],
            harmonic_rhythm=Duration.WHOLE,
        )
        time_sig = TimeSignature.COMMON_TIME
        position = BeatPosition(0, Fraction(0))
        pitch = context.resolve_degree("unknown_format", position, time_sig, LayerRole.MELODY)
        assert 60 <= pitch <= 84


class TestPatternCompilerAdditional:
    """Additional tests for PatternCompiler edge cases."""

    def test_compile_pattern_no_pitch_returns_none(self) -> None:
        """Compile event with no pitch or degree returns None."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="empty",
            role=LayerRole.HARMONY,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration="quarter"),  # No degree or note
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.HARMONY,
            channel=1,
        )
        events = compiler.compile(pattern, context, bars=1)
        assert len(events) == 0  # No events compiled

    def test_compile_with_non_looping_pattern(self) -> None:
        """Compile non-looping pattern."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="non-loop",
            role=LayerRole.MELODY,
            template=PatternTemplate(
                bars=1,
                loop=False,  # Does not loop
                events=[
                    PatternEvent(beat=0, duration="quarter", degree="chord.root"),
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.MELODY,
            channel=1,
        )
        events = compiler.compile(pattern, context, bars=4)
        # Should only produce 1 event since loop=False
        assert len(events) == 1

    def test_compile_with_parameter_reference_duration(self) -> None:
        """Compile with parameter reference in duration."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="param-dur",
            role=LayerRole.BASS,
            parameters={
                "note_length": PatternParameter(
                    name="note_length",
                    type="enum",
                    values=["quarter", "eighth"],
                    default="quarter",
                )
            },
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(
                        beat=0,
                        duration="$note_length",  # Parameter reference
                        degree="chord.root",
                    ),
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.BASS,
            channel=1,
            params={"note_length": "eighth"},
        )
        events = compiler.compile(pattern, context, bars=1)
        assert len(events) == 1
        # Duration should be eighth note (240 ticks at 480 PPQ)
        assert events[0].duration_ticks == 240

    def test_compile_with_velocity_parameter_reference(self) -> None:
        """Compile with parameter reference in velocity."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="param-vel",
            role=LayerRole.BASS,
            parameters={
                "vel": PatternParameter(
                    name="vel",
                    type="float",
                    range=(0.0, 1.0),
                    default=0.8,
                )
            },
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(
                        beat=0,
                        duration="quarter",
                        degree="chord.root",
                        velocity="$vel",  # Parameter reference
                    ),
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.BASS,
            channel=1,
            params={"vel": 0.5},
        )
        events = compiler.compile(pattern, context, bars=1)
        assert len(events) == 1
        assert events[0].velocity == 63  # 0.5 * 127

    def test_compile_with_float_duration(self) -> None:
        """Compile with float duration value."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="float-dur",
            role=LayerRole.DRUMS,
            pitched=False,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration=0.5, note=36),  # Float duration
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.DRUMS,
            channel=9,
        )
        events = compiler.compile(pattern, context, bars=1)
        assert len(events) == 1
        assert events[0].duration_ticks == 240  # 0.5 * 480

    def test_compile_with_unparseable_duration_defaults(self) -> None:
        """Compile with unparseable duration defaults to quarter note."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="bad-dur",
            role=LayerRole.BASS,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(
                        beat=0,
                        duration="invalid_duration",  # Unparseable
                        degree="chord.root",
                    ),
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.BASS,
            channel=1,
        )
        events = compiler.compile(pattern, context, bars=1)
        assert len(events) == 1
        assert events[0].duration_ticks == 480  # Default quarter note

    def test_resolve_velocity_string_returns_default(self) -> None:
        """Velocity string that's not a param ref returns default."""
        compiler = PatternCompiler()
        pattern = Pattern(
            name="str-vel",
            role=LayerRole.BASS,
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(
                        beat=0,
                        duration="quarter",
                        degree="chord.root",
                        velocity="not_a_number",  # Invalid velocity
                    ),
                ],
            ),
        )
        key = Key(PitchClass.C, ScaleType.MAJOR)
        harmony = HarmonyContext(key=key, progression=["I"], harmonic_rhythm=Duration.WHOLE)
        context = CompileContext(
            key=key,
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            harmony=harmony,
            role=LayerRole.BASS,
            channel=1,
        )
        events = compiler.compile(pattern, context, bars=1)
        assert len(events) == 1
        assert events[0].velocity == 100  # Default

    def test_compile_pattern_convenience_function_with_variant(self) -> None:
        """Use compile_pattern function with variant."""
        pattern = Pattern(
            name="variant-test",
            role=LayerRole.BASS,
            parameters={
                "density": PatternParameter(
                    name="density",
                    type="enum",
                    values=["quarter", "eighth"],
                    default="quarter",
                )
            },
            variants={
                "dense": PatternVariant(
                    name="dense",
                    description="Denser version",
                    params={"density": "eighth"},
                )
            },
            template=PatternTemplate(
                bars=1,
                loop=True,
                events=[
                    PatternEvent(beat=0, duration="quarter", degree="chord.root"),
                ],
            ),
        )

        events = compile_pattern(
            pattern=pattern,
            key=Key(PitchClass.C, ScaleType.MAJOR),
            tempo=120,
            time_sig=TimeSignature.COMMON_TIME,
            progression=["I"],
            role=LayerRole.BASS,
            channel=1,
            bars=1,
            variant="dense",
        )
        assert len(events) == 1
