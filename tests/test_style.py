"""
Tests for the style system.

Tests cover:
- Style model and types
- StyleLoader discovery and loading
- StyleResolver constraint resolution and pattern suggestions
"""

import tempfile
from pathlib import Path

import pytest

from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.models.pattern import Pattern, PatternEvent, PatternTemplate
from chuk_mcp_music.models.style import (
    EnergyConstraints,
    EnergyMapping,
    ForbiddenElements,
    HarmonyDensity,
    KeyPreference,
    LayerHint,
    PercussionDensity,
    StructureHints,
    Style,
    StyleMetadata,
    TempoRange,
)
from chuk_mcp_music.styles import StyleLoader, StyleResolver, ViolationSeverity


class TestTempoRange:
    """Tests for TempoRange model."""

    def test_default_range(self):
        """Default tempo range should be reasonable."""
        tempo = TempoRange()
        assert tempo.min_bpm == 60
        assert tempo.max_bpm == 200
        assert tempo.default_bpm == 120

    def test_custom_range(self):
        """Can create custom tempo range."""
        tempo = TempoRange(min_bpm=120, max_bpm=130, default_bpm=125)
        assert tempo.min_bpm == 120
        assert tempo.max_bpm == 130
        assert tempo.default_bpm == 125

    def test_is_valid(self):
        """Validates tempo correctly."""
        tempo = TempoRange(min_bpm=120, max_bpm=130, default_bpm=125)
        assert tempo.is_valid(125) is True
        assert tempo.is_valid(120) is True
        assert tempo.is_valid(130) is True
        assert tempo.is_valid(119) is False
        assert tempo.is_valid(131) is False


class TestEnergyConstraints:
    """Tests for EnergyConstraints model."""

    def test_default_constraints(self):
        """Default constraints should be reasonable."""
        ec = EnergyConstraints()
        assert ec.layers == (1, 5)
        assert ec.percussion == PercussionDensity.STANDARD
        assert ec.harmony_density == HarmonyDensity.MODERATE

    def test_custom_constraints(self):
        """Can create custom energy constraints."""
        ec = EnergyConstraints(
            layers=(2, 3),
            percussion=PercussionDensity.SPARSE,
            harmony_density=HarmonyDensity.RICH,
            velocity_range=(0.6, 0.8),
        )
        assert ec.layers == (2, 3)
        assert ec.percussion == PercussionDensity.SPARSE
        assert ec.velocity_range == (0.6, 0.8)


class TestEnergyMapping:
    """Tests for EnergyMapping model."""

    def test_default_mapping(self):
        """Default mapping covers all energy levels."""
        em = EnergyMapping()
        assert em.lowest is not None
        assert em.low is not None
        assert em.medium is not None
        assert em.high is not None
        assert em.highest is not None

    def test_get_constraints(self):
        """Can retrieve constraints for energy levels."""
        em = EnergyMapping()
        assert em.get_constraints("lowest") == em.lowest
        assert em.get_constraints("medium") == em.medium
        assert em.get_constraints("highest") == em.highest
        # Unknown energy returns medium
        assert em.get_constraints("unknown") == em.medium


class TestLayerHint:
    """Tests for LayerHint model."""

    def test_default_hint(self):
        """Default hint has empty lists."""
        hint = LayerHint()
        assert hint.suggested == []
        assert hint.avoid == []
        assert hint.pitch_register is None
        assert hint.density is None

    def test_custom_hint(self):
        """Can create hint with suggestions and avoids."""
        # Use alias "register" when creating from YAML-like dict
        hint = LayerHint.model_validate(
            {
                "suggested": ["bass/root-pulse", "bass/octave-*"],
                "avoid": ["bass/rolling-*"],
                "register": "low",  # Uses alias
                "density": "sparse",
            }
        )
        assert "bass/root-pulse" in hint.suggested
        assert "bass/rolling-*" in hint.avoid
        assert hint.pitch_register == "low"


class TestStyle:
    """Tests for Style model."""

    def test_minimal_style(self):
        """Can create style with just a name."""
        style = Style(name="test-style")
        assert style.name == "test-style"
        assert style.description == ""
        assert style.key_preference == KeyPreference.ANY
        assert style.time_signature == "4/4"

    def test_full_style(self):
        """Can create a fully configured style."""
        style = Style(
            name="melodic-techno",
            description="Melodic electronic dance music",
            tempo=TempoRange(min_bpm=120, max_bpm=128, default_bpm=124),
            key_preference=KeyPreference.MINOR,
            time_signature="4/4",
            layer_hints={
                "bass": LayerHint(suggested=["bass/root-pulse"]),
                "drums": LayerHint(avoid=["drums/breakbeat-*"]),
            },
            structure_hints=StructureHints(breakdown_required=True),
            forbidden=ForbiddenElements(patterns=["drums/trap-*"]),
        )
        assert style.name == "melodic-techno"
        assert style.tempo.min_bpm == 120
        assert style.key_preference == KeyPreference.MINOR

    def test_get_layer_hint(self):
        """Returns correct layer hints or default."""
        style = Style(
            name="test",
            layer_hints={
                "bass": LayerHint(suggested=["bass/test"]),
            },
        )
        bass_hint = style.get_layer_hint(LayerRole.BASS)
        assert "bass/test" in bass_hint.suggested

        # Non-existent role returns empty hint
        drums_hint = style.get_layer_hint(LayerRole.DRUMS)
        assert drums_hint.suggested == []

    def test_is_pattern_suggested(self):
        """Correctly identifies suggested patterns."""
        style = Style(
            name="test",
            layer_hints={
                "bass": LayerHint(suggested=["bass/root-*", "bass/octave-bounce"]),
            },
        )
        # Exact match
        assert style.is_pattern_suggested("bass/octave-bounce", LayerRole.BASS) is True
        # Wildcard match
        assert style.is_pattern_suggested("bass/root-pulse", LayerRole.BASS) is True
        # Not suggested
        assert style.is_pattern_suggested("bass/rolling-sixteenths", LayerRole.BASS) is False

    def test_is_pattern_avoided(self):
        """Correctly identifies patterns to avoid."""
        style = Style(
            name="test",
            layer_hints={
                "drums": LayerHint(avoid=["drums/trap-*"]),
            },
        )
        assert style.is_pattern_avoided("drums/trap-hihat", LayerRole.DRUMS) is True
        assert style.is_pattern_avoided("drums/minimal-techno", LayerRole.DRUMS) is False

    def test_is_pattern_forbidden(self):
        """Correctly identifies forbidden patterns."""
        style = Style(
            name="test",
            forbidden=ForbiddenElements(patterns=["drums/trap-*", "bass/dubstep-*"]),
        )
        assert style.is_pattern_forbidden("drums/trap-hihat") is True
        assert style.is_pattern_forbidden("bass/dubstep-wobble") is True
        assert style.is_pattern_forbidden("bass/root-pulse") is False

    def test_validate_tempo(self):
        """Validates tempo against style range."""
        style = Style(
            name="test",
            tempo=TempoRange(min_bpm=120, max_bpm=130, default_bpm=125),
        )
        assert style.validate_tempo(125) is True
        assert style.validate_tempo(100) is False

    def test_to_yaml_dict(self):
        """Converts to YAML-compatible dictionary."""
        style = Style(
            name="test",
            description="Test style",
            tempo=TempoRange(min_bpm=120, max_bpm=128, default_bpm=124),
        )
        yaml_dict = style.to_yaml_dict()
        assert yaml_dict["name"] == "test"
        assert yaml_dict["description"] == "Test style"
        assert yaml_dict["tokens"]["tempo"]["range"] == [120, 128]
        assert yaml_dict["tokens"]["tempo"]["default"] == 124


class TestStyleMetadata:
    """Tests for StyleMetadata."""

    def test_from_style(self):
        """Creates metadata from style."""
        style = Style(
            name="melodic-techno",
            description="Melodic electronic dance music",
            tempo=TempoRange(min_bpm=120, max_bpm=128, default_bpm=124),
            key_preference=KeyPreference.MINOR,
        )
        meta = StyleMetadata.from_style(style)
        assert meta.name == "melodic-techno"
        assert meta.description == "Melodic electronic dance music"
        assert meta.tempo_range == (120, 128)
        assert meta.key_preference == KeyPreference.MINOR


class TestStyleLoader:
    """Tests for StyleLoader."""

    def test_list_library_styles(self):
        """Lists built-in library styles."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            styles = loader.list_styles()
            names = [s.name for s in styles]
            # Should have the built-in styles
            assert "melodic-techno" in names
            assert "ambient" in names
            assert "cinematic" in names

    def test_get_style(self):
        """Loads a specific style."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("melodic-techno")
            assert style is not None
            assert style.name == "melodic-techno"
            assert style.tempo.min_bpm == 120
            assert style.tempo.max_bpm == 128
            assert style.key_preference == KeyPreference.MINOR

    def test_get_nonexistent_style(self):
        """Returns None for non-existent style."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("nonexistent-style")
            assert style is None

    def test_copy_to_project(self):
        """Copies library style to project."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            loader = StyleLoader(library_path=library_path, project_path=project_path)

            # Copy style
            copied_path = loader.copy_to_project("melodic-techno")
            assert copied_path is not None
            assert copied_path.exists()
            assert copied_path.name == "melodic-techno.yaml"

            # Now can load from project
            style = loader.get_style("melodic-techno")
            assert style is not None

    def test_copy_nonexistent_style(self):
        """Returns None when copying non-existent style."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            path = loader.copy_to_project("nonexistent")
            assert path is None


class TestStyleResolver:
    """Tests for StyleResolver."""

    @pytest.fixture
    def melodic_techno_style(self):
        """Create a melodic techno style for testing."""
        return Style(
            name="melodic-techno",
            description="Melodic electronic dance music",
            tempo=TempoRange(min_bpm=120, max_bpm=128, default_bpm=124),
            key_preference=KeyPreference.MINOR,
            layer_hints={
                "bass": LayerHint(
                    suggested=["bass/root-pulse", "bass/octave-bounce"],
                    avoid=["bass/rolling-*"],
                ),
                "drums": LayerHint(
                    suggested=["drums/minimal-techno"],
                    avoid=["drums/trap-*", "drums/breakbeat-*"],
                ),
            },
            structure_hints=StructureHints(
                breakdown_required=True,
                section_multiples=8,
            ),
            forbidden=ForbiddenElements(patterns=["drums/trap-*"]),
        )

    @pytest.fixture
    def sample_pattern(self):
        """Create a sample pattern for testing."""
        return Pattern(
            id="bass/root-pulse",
            name="root-pulse",
            description="Simple root note pulse",
            role=LayerRole.BASS,
            template=PatternTemplate(
                bars=1,
                events=[
                    PatternEvent(beat=0, duration=0.5, pitch="root", velocity=0.8),
                    PatternEvent(beat=2, duration=0.5, pitch="root", velocity=0.7),
                ],
            ),
        )

    def test_resolve_energy(self, melodic_techno_style):
        """Resolves energy level to constraints."""
        resolver = StyleResolver(melodic_techno_style)
        constraints = resolver.resolve_energy("medium")
        assert isinstance(constraints, EnergyConstraints)
        assert constraints == melodic_techno_style.energy_mapping.medium

    def test_validate_tempo_in_range(self, melodic_techno_style):
        """Validates tempo within range."""
        resolver = StyleResolver(melodic_techno_style)
        violations = resolver.validate_tempo(124)
        assert len(violations) == 0

    def test_validate_tempo_out_of_range(self, melodic_techno_style):
        """Reports warning for tempo out of range."""
        resolver = StyleResolver(melodic_techno_style)
        violations = resolver.validate_tempo(100)
        assert len(violations) == 1
        assert violations[0].severity == ViolationSeverity.WARNING
        assert "tempo" in violations[0].message.lower()

    def test_validate_structure_with_breakdown(self, melodic_techno_style):
        """Validates structure with required breakdown."""
        resolver = StyleResolver(melodic_techno_style)
        sections = {"intro": 8, "breakdown": 16, "drop": 32}
        violations = resolver.validate_structure(sections, has_breakdown=True)
        # Should have no violations
        assert len([v for v in violations if v.severity == ViolationSeverity.ERROR]) == 0

    def test_validate_structure_missing_breakdown(self, melodic_techno_style):
        """Reports warning for missing breakdown."""
        resolver = StyleResolver(melodic_techno_style)
        sections = {"intro": 8, "drop": 32}
        violations = resolver.validate_structure(sections, has_breakdown=False)
        warnings = [v for v in violations if v.severity == ViolationSeverity.WARNING]
        assert len(warnings) > 0
        assert any("breakdown" in w.message.lower() for w in warnings)

    def test_validate_structure_odd_section_length(self, melodic_techno_style):
        """Reports warning for non-standard section lengths."""
        resolver = StyleResolver(melodic_techno_style)
        sections = {"intro": 7}  # Not a multiple of 8
        violations = resolver.validate_structure(sections, has_breakdown=True)
        warnings = [v for v in violations if v.severity == ViolationSeverity.WARNING]
        assert len(warnings) > 0

    def test_validate_pattern_suggested(self, melodic_techno_style, sample_pattern):
        """No violations for suggested pattern."""
        resolver = StyleResolver(melodic_techno_style)
        violations = resolver.validate_pattern(sample_pattern, LayerRole.BASS)
        assert len(violations) == 0

    def test_validate_pattern_forbidden(self, melodic_techno_style):
        """Reports error for forbidden pattern."""
        resolver = StyleResolver(melodic_techno_style)
        forbidden_pattern = Pattern(
            id="drums/trap-hihat",
            name="trap-hihat",
            description="Trap-style hi-hat pattern",
            role=LayerRole.DRUMS,
            template=PatternTemplate(bars=1, events=[]),
        )
        violations = resolver.validate_pattern(forbidden_pattern, LayerRole.DRUMS)
        errors = [v for v in violations if v.severity == ViolationSeverity.ERROR]
        assert len(errors) > 0
        assert any("forbidden" in e.message.lower() for e in errors)

    def test_validate_pattern_avoided(self, melodic_techno_style):
        """Reports warning for avoided pattern."""
        resolver = StyleResolver(melodic_techno_style)
        avoided_pattern = Pattern(
            id="bass/rolling-sixteenths",
            name="rolling-sixteenths",
            description="Rolling 16th note bass",
            role=LayerRole.BASS,
            template=PatternTemplate(bars=1, events=[]),
        )
        violations = resolver.validate_pattern(avoided_pattern, LayerRole.BASS)
        warnings = [v for v in violations if v.severity == ViolationSeverity.WARNING]
        assert len(warnings) > 0
        # The message says "discouraged" not "avoid"
        assert any("discouraged" in w.message.lower() for w in warnings)

    def test_suggest_patterns(self, melodic_techno_style, sample_pattern):
        """Suggests patterns with scores."""
        resolver = StyleResolver(melodic_techno_style)
        suggestions = resolver.suggest_patterns(
            [sample_pattern],
            LayerRole.BASS,
            energy=None,
        )
        assert len(suggestions) == 1
        assert suggestions[0].pattern_id == "bass/root-pulse"
        assert suggestions[0].score > 0.5  # Should be suggested

    def test_suggest_patterns_filters_forbidden(self, melodic_techno_style):
        """Filters out forbidden patterns from suggestions."""
        resolver = StyleResolver(melodic_techno_style)
        forbidden_pattern = Pattern(
            id="drums/trap-hihat",
            name="trap-hihat",
            description="Trap-style hi-hat",
            role=LayerRole.DRUMS,
            template=PatternTemplate(bars=1, events=[]),
        )
        suggestions = resolver.suggest_patterns(
            [forbidden_pattern],
            LayerRole.DRUMS,
            energy=None,
        )
        # Forbidden patterns should not appear in suggestions
        assert len(suggestions) == 0


class TestStyleYamlLoading:
    """Tests for loading styles from YAML files."""

    def test_load_melodic_techno(self):
        """Loads melodic-techno style from library."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("melodic-techno")

            assert style is not None
            assert style.name == "melodic-techno"
            assert style.tempo.min_bpm == 120
            assert style.tempo.max_bpm == 128
            assert style.key_preference == KeyPreference.MINOR
            assert style.structure_hints.breakdown_required is True

    def test_load_ambient(self):
        """Loads ambient style from library."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("ambient")

            assert style is not None
            assert style.name == "ambient"
            assert style.tempo.min_bpm == 60
            assert style.tempo.max_bpm == 100
            assert "drums/four-on-floor" in style.forbidden.patterns

    def test_load_cinematic(self):
        """Loads cinematic style from library."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("cinematic")

            assert style is not None
            assert style.name == "cinematic"
            assert style.tempo.min_bpm == 70
            assert style.tempo.max_bpm == 140
            # Cinematic has wide dynamic range
            assert style.energy_mapping.lowest.percussion == PercussionDensity.NONE
            assert style.energy_mapping.highest.percussion == PercussionDensity.FULL


class TestStyleLoaderEdgeCases:
    """Additional edge case tests for StyleLoader."""

    def test_project_style_takes_precedence(self):
        """Project style takes precedence over library style."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            loader = StyleLoader(library_path=library_path, project_path=project_path)

            # Copy a style and verify it loads
            loader.copy_to_project("melodic-techno")

            # Clear cache to force reload
            loader._cache.clear()

            # Should still load (from project now)
            style = loader.get_style("melodic-techno")
            assert style is not None

    def test_list_styles_includes_project(self):
        """List styles includes project styles."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            loader = StyleLoader(library_path=library_path, project_path=project_path)

            # Copy a style
            loader.copy_to_project("melodic-techno")

            # List should include it
            styles = loader.list_styles()
            names = [s.name for s in styles]
            assert "melodic-techno" in names

    def test_get_style_metadata_via_style(self):
        """Get style metadata via style object."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("melodic-techno")
            assert style is not None
            meta = StyleMetadata.from_style(style)

            assert meta.name == "melodic-techno"
            assert meta.tempo_range == (120, 128)

    def test_get_nonexistent_style_returns_none(self):
        """Get nonexistent style returns None."""
        library_path = (
            Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"
        )
        with tempfile.TemporaryDirectory() as tmp:
            loader = StyleLoader(library_path=library_path, project_path=Path(tmp))
            style = loader.get_style("nonexistent")

            assert style is None


class TestStyleResolverEdgeCases:
    """Additional edge case tests for StyleResolver."""

    def test_suggest_patterns_with_energy(self):
        """Suggest patterns with energy level."""
        style = Style(
            name="test",
            layer_hints={
                "bass": LayerHint(suggested=["bass/root-pulse"]),
            },
        )
        resolver = StyleResolver(style)

        pattern = Pattern(
            id="bass/root-pulse",
            name="root-pulse",
            description="Simple root pulse",
            role=LayerRole.BASS,
            template=PatternTemplate(bars=1, events=[]),
        )

        suggestions = resolver.suggest_patterns(
            [pattern],
            LayerRole.BASS,
            energy="high",
        )
        assert len(suggestions) == 1

    def test_get_suggested_key_quality_major(self):
        """Get suggested key quality for major preference."""
        style = Style(
            name="test",
            key_preference=KeyPreference.MAJOR,
        )
        resolver = StyleResolver(style)
        assert resolver.get_suggested_key_quality() == "major"

    def test_get_suggested_key_quality_minor(self):
        """Get suggested key quality for minor preference."""
        style = Style(
            name="test",
            key_preference=KeyPreference.MINOR,
        )
        resolver = StyleResolver(style)
        assert resolver.get_suggested_key_quality() == "minor"

    def test_get_suggested_key_quality_any(self):
        """Get suggested key quality for any preference."""
        style = Style(
            name="test",
            key_preference=KeyPreference.ANY,
        )
        resolver = StyleResolver(style)
        assert resolver.get_suggested_key_quality() == "any"

    def test_get_default_tempo(self):
        """Get default tempo from style."""
        style = Style(
            name="test",
            tempo=TempoRange(min_bpm=120, max_bpm=140, default_bpm=125),
        )
        resolver = StyleResolver(style)
        assert resolver.get_default_tempo() == 125

    def test_style_violation_fields(self):
        """StyleViolation has correct fields."""
        from chuk_mcp_music.styles import StyleViolation

        violation = StyleViolation(
            severity=ViolationSeverity.WARNING,
            message="Test warning message",
            element="test/element",
        )
        assert violation.severity == ViolationSeverity.WARNING
        assert violation.message == "Test warning message"
        assert violation.element == "test/element"


class TestEnergyMappingDetails:
    """Additional tests for EnergyMapping."""

    def test_energy_levels_have_appropriate_layer_counts(self):
        """Energy levels have appropriate layer count ranges."""
        em = EnergyMapping()

        # Lowest should have fewer layers
        assert em.lowest.layers[1] <= em.highest.layers[0]

    def test_energy_mapping_custom_levels(self):
        """Can create custom energy mapping with all levels."""
        em = EnergyMapping(
            lowest=EnergyConstraints(layers=(1, 1), percussion=PercussionDensity.NONE),
            low=EnergyConstraints(layers=(1, 2), percussion=PercussionDensity.SPARSE),
            medium=EnergyConstraints(layers=(2, 3), percussion=PercussionDensity.STANDARD),
            high=EnergyConstraints(layers=(3, 4), percussion=PercussionDensity.DENSE),
            highest=EnergyConstraints(layers=(4, 5), percussion=PercussionDensity.FULL),
        )
        assert em.lowest.layers == (1, 1)
        assert em.highest.layers == (4, 5)


class TestForbiddenElements:
    """Tests for ForbiddenElements model."""

    def test_empty_forbidden(self):
        """Empty forbidden elements."""
        fe = ForbiddenElements()
        assert fe.patterns == []
        assert fe.progressions == []

    def test_forbidden_with_patterns(self):
        """Forbidden with patterns."""
        fe = ForbiddenElements(patterns=["drums/trap-*", "bass/dubstep-*"])
        assert "drums/trap-*" in fe.patterns
        assert "bass/dubstep-*" in fe.patterns

    def test_forbidden_with_progressions(self):
        """Forbidden with progressions."""
        fe = ForbiddenElements(progressions=["I-V-vi-IV"])
        assert "I-V-vi-IV" in fe.progressions


class TestStructureHints:
    """Tests for StructureHints model."""

    def test_default_structure_hints(self):
        """Default structure hints."""
        sh = StructureHints()
        assert sh.breakdown_required is False
        assert sh.section_multiples == 4

    def test_custom_structure_hints(self):
        """Custom structure hints."""
        sh = StructureHints(
            breakdown_required=True,
            section_multiples=8,
            intro_bars=(8, 16),
        )
        assert sh.breakdown_required is True
        assert sh.section_multiples == 8
        assert sh.intro_bars == (8, 16)
