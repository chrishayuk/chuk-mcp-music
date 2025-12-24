"""
Tests for arrangement model and management.

Tests cover:
- Arrangement creation and manipulation
- YAML serialization/deserialization
- Validation
- ArrangementManager operations
"""

import tempfile
from pathlib import Path

import pytest

from chuk_mcp_music.arrangement import (
    ArrangementManager,
    validate_arrangement,
)
from chuk_mcp_music.models import (
    Arrangement,
    ArrangementContext,
    EnergyLevel,
    Harmony,
    HarmonyProgression,
    Layer,
    LayerRole,
    PatternRef,
    Section,
)


class TestSection:
    """Tests for Section model."""

    def test_create_section(self) -> None:
        """Create a simple section."""
        section = Section(name="intro", bars=8)
        assert section.name == "intro"
        assert section.bars == 8
        assert section.energy is None

    def test_section_with_energy(self) -> None:
        """Create a section with energy level."""
        section = Section(name="chorus", bars=16, energy=EnergyLevel.HIGH)
        assert section.energy == EnergyLevel.HIGH

    def test_section_name_normalized(self) -> None:
        """Section names are normalized."""
        section = Section(name="Verse-1", bars=8)
        assert section.name == "verse_1"

    def test_invalid_section_bars(self) -> None:
        """Invalid bar count raises error."""
        with pytest.raises(ValueError):
            Section(name="intro", bars=0)


class TestLayer:
    """Tests for Layer model."""

    def test_create_layer(self) -> None:
        """Create a simple layer."""
        layer = Layer(name="drums", role=LayerRole.DRUMS)
        assert layer.name == "drums"
        assert layer.role == LayerRole.DRUMS
        assert layer.channel == 0

    def test_layer_with_patterns(self) -> None:
        """Create layer with patterns."""
        layer = Layer(
            name="bass",
            role=LayerRole.BASS,
            patterns={
                "main": PatternRef(ref="bass/root-pulse"),
                "driving": PatternRef(ref="bass/root-pulse", variant="driving"),
            },
        )
        assert len(layer.patterns) == 2
        assert layer.patterns["driving"].variant == "driving"

    def test_get_pattern_for_section(self) -> None:
        """Get pattern for a section."""
        layer = Layer(
            name="bass",
            role=LayerRole.BASS,
            patterns={"main": PatternRef(ref="bass/root-pulse")},
            arrangement={"verse": "main", "intro": None},
        )
        assert layer.get_pattern_for_section("verse") is not None
        assert layer.get_pattern_for_section("intro") is None
        assert layer.get_pattern_for_section("unknown") is None


class TestPatternRef:
    """Tests for PatternRef model."""

    def test_simple_ref(self) -> None:
        """Create a simple pattern reference."""
        ref = PatternRef(ref="drums/four-on-floor")
        assert ref.ref == "drums/four-on-floor"
        assert ref.variant is None
        assert ref.params == {}

    def test_ref_with_variant(self) -> None:
        """Create a reference with variant."""
        ref = PatternRef(ref="bass/root-pulse", variant="driving")
        assert ref.variant == "driving"

    def test_ref_with_params(self) -> None:
        """Create a reference with parameters."""
        ref = PatternRef(ref="bass/root-pulse", params={"density": "eighth"})
        assert ref.params["density"] == "eighth"


class TestHarmony:
    """Tests for Harmony model."""

    def test_default_harmony(self) -> None:
        """Default harmony configuration."""
        harmony = Harmony()
        assert harmony.default_progression == ["I"]
        assert harmony.harmonic_rhythm == "1bar"

    def test_custom_harmony(self) -> None:
        """Custom harmony with section overrides."""
        harmony = Harmony(
            default_progression=["i", "VI", "III", "VII"],
            sections={
                "chorus": HarmonyProgression(progression=["i", "VII", "VI", "VII"]),
            },
        )
        assert harmony.get_progression_for_section("verse") == ["i", "VI", "III", "VII"]
        assert harmony.get_progression_for_section("chorus") == ["i", "VII", "VI", "VII"]


class TestArrangement:
    """Tests for Arrangement model."""

    def test_create_arrangement(self) -> None:
        """Create a simple arrangement."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
        )
        assert arrangement.name == "test"
        assert arrangement.context.key == "D_minor"
        assert arrangement.context.tempo == 124
        assert arrangement.total_bars() == 0

    def test_add_section(self) -> None:
        """Add sections to arrangement."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
        )
        arrangement.add_section("intro", 8)
        arrangement.add_section("verse", 16, EnergyLevel.MEDIUM)

        assert len(arrangement.sections) == 2
        assert arrangement.total_bars() == 24
        assert arrangement.get_section("verse") is not None

    def test_remove_section(self) -> None:
        """Remove a section."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
        )
        arrangement.add_section("intro", 8)
        arrangement.add_section("verse", 16)

        assert arrangement.remove_section("intro")
        assert len(arrangement.sections) == 1
        assert not arrangement.remove_section("unknown")

    def test_add_layer(self) -> None:
        """Add layers to arrangement."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
        )
        layer = arrangement.add_layer("drums", LayerRole.DRUMS)

        assert "drums" in arrangement.layers
        assert layer.channel == 9  # GM drums

    def test_get_active_patterns(self) -> None:
        """Get active patterns for a section."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    patterns={"main": PatternRef(ref="drums/four-on-floor")},
                    arrangement={"verse": "main"},
                ),
                "bass": Layer(
                    name="bass",
                    role=LayerRole.BASS,
                    patterns={"pulse": PatternRef(ref="bass/root-pulse")},
                    arrangement={"verse": None},  # Silent in verse
                ),
            },
        )

        active = arrangement.get_active_patterns("verse")
        assert "drums" in active
        assert "bass" not in active


class TestArrangementYaml:
    """Tests for YAML serialization."""

    def test_to_yaml_dict(self) -> None:
        """Convert arrangement to YAML dict."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="intro", bars=8)],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    channel=9,
                    patterns={"main": PatternRef(ref="drums/four-on-floor")},
                    arrangement={"intro": "main"},
                ),
            },
        )

        yaml_dict = arrangement.to_yaml_dict()

        assert yaml_dict["schema"] == "arrangement/v1"
        assert yaml_dict["name"] == "test"
        assert yaml_dict["context"]["key"] == "D_minor"
        assert yaml_dict["context"]["tempo"] == 124
        assert len(yaml_dict["sections"]) == 1
        assert "drums" in yaml_dict["layers"]

    def test_from_yaml_dict(self) -> None:
        """Create arrangement from YAML dict."""
        yaml_dict = {
            "schema": "arrangement/v1",
            "name": "test",
            "context": {
                "key": "C_major",
                "tempo": 120,
                "time_signature": "4/4",
            },
            "harmony": {
                "default_progression": ["I", "IV", "V", "I"],
            },
            "sections": [
                {"name": "verse", "bars": 16, "energy": "medium"},
            ],
            "layers": {
                "bass": {
                    "role": "bass",
                    "channel": 1,
                    "patterns": {
                        "main": {"ref": "bass/root-pulse"},
                    },
                    "arrangement": {"verse": "main"},
                },
            },
        }

        arrangement = Arrangement.from_yaml_dict(yaml_dict)

        assert arrangement.name == "test"
        assert arrangement.context.key == "C_major"
        assert arrangement.sections[0].energy == EnergyLevel.MEDIUM
        assert "bass" in arrangement.layers

    def test_yaml_round_trip(self) -> None:
        """YAML dict round-trips correctly."""
        original = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124, style="melodic-techno"),
            harmony=Harmony(
                default_progression=["i", "VI", "III", "VII"],
                sections={
                    "chorus": HarmonyProgression(progression=["i", "VII"]),
                },
            ),
            sections=[
                Section(name="intro", bars=8, energy=EnergyLevel.LOW),
                Section(name="verse", bars=16),
            ],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    patterns={"main": PatternRef(ref="drums/four-on-floor")},
                    arrangement={"intro": None, "verse": "main"},
                ),
            },
        )

        yaml_dict = original.to_yaml_dict()
        restored = Arrangement.from_yaml_dict(yaml_dict)

        assert restored.name == original.name
        assert restored.context.key == original.context.key
        assert restored.context.tempo == original.context.tempo
        assert len(restored.sections) == len(original.sections)
        assert len(restored.layers) == len(original.layers)


class TestValidation:
    """Tests for arrangement validation."""

    def test_valid_arrangement(self) -> None:
        """A valid arrangement passes validation."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    patterns={"main": PatternRef(ref="drums/four-on-floor")},
                    arrangement={"verse": "main"},
                ),
            },
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid

    def test_duplicate_section_error(self) -> None:
        """Duplicate section names are errors."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[
                Section(name="verse", bars=16),
                Section(name="verse", bars=8),  # Duplicate!
            ],
        )

        result = validate_arrangement(arrangement)
        assert not result.is_valid
        assert any(i.code == "DUPLICATE_SECTION" for i in result.errors)

    def test_invalid_section_ref_error(self) -> None:
        """Invalid section reference in layer is error."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    patterns={"main": PatternRef(ref="drums/four-on-floor")},
                    arrangement={"chorus": "main"},  # chorus doesn't exist!
                ),
            },
        )

        result = validate_arrangement(arrangement)
        assert not result.is_valid
        assert any(i.code == "INVALID_SECTION_REF" for i in result.errors)

    def test_invalid_pattern_ref_error(self) -> None:
        """Invalid pattern reference is error."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            layers={
                "drums": Layer(
                    name="drums",
                    role=LayerRole.DRUMS,
                    patterns={},  # No patterns defined
                    arrangement={"verse": "main"},  # but main is referenced!
                ),
            },
        )

        result = validate_arrangement(arrangement)
        assert not result.is_valid
        assert any(i.code == "INVALID_PATTERN_REF" for i in result.errors)

    def test_channel_conflict_warning(self) -> None:
        """Channel conflicts are warnings."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            layers={
                "bass1": Layer(name="bass1", role=LayerRole.BASS, channel=1),
                "bass2": Layer(name="bass2", role=LayerRole.BASS, channel=1),  # Same channel
            },
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid  # Warnings don't fail validation
        assert any(i.code == "CHANNEL_CONFLICT" for i in result.warnings)


class TestArrangementManager:
    """Tests for ArrangementManager."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory for arrangements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_create_arrangement(self, temp_dir: Path) -> None:
        """Create a new arrangement."""
        manager = ArrangementManager(temp_dir)

        arrangement = await manager.create(
            name="test",
            key="D_minor",
            tempo=124,
        )

        assert arrangement.name == "test"
        assert arrangement.context.key == "D_minor"
        assert arrangement.context.tempo == 124

    @pytest.mark.asyncio
    async def test_save_and_load(self, temp_dir: Path) -> None:
        """Save and load an arrangement."""
        manager = ArrangementManager(temp_dir)

        # Create and modify
        arrangement = await manager.create(name="test", key="D_minor", tempo=124)
        arrangement.add_section("intro", 8)
        arrangement.add_layer("drums", LayerRole.DRUMS)

        # Save
        path = await manager.save(arrangement)
        assert path.exists()

        # Clear cache and reload
        manager._cache.clear()
        loaded = await manager.get("test")

        assert loaded is not None
        assert loaded.name == "test"
        assert len(loaded.sections) == 1
        assert "drums" in loaded.layers

    @pytest.mark.asyncio
    async def test_list_arrangements(self, temp_dir: Path) -> None:
        """List arrangements in directory."""
        manager = ArrangementManager(temp_dir)

        # Create and save two arrangements
        arr1 = await manager.create(name="first", key="C_major", tempo=120)
        await manager.save(arr1)

        arr2 = await manager.create(name="second", key="D_minor", tempo=124)
        await manager.save(arr2)

        # List
        arrangements = await manager.list_arrangements()
        assert len(arrangements) == 2

    @pytest.mark.asyncio
    async def test_delete_arrangement(self, temp_dir: Path) -> None:
        """Delete an arrangement."""
        manager = ArrangementManager(temp_dir)

        arrangement = await manager.create(name="test", key="D_minor", tempo=124)
        await manager.save(arrangement)

        assert await manager.delete("test")
        assert not (temp_dir / "test.arrangement.yaml").exists()
        assert await manager.get("test") is None

    @pytest.mark.asyncio
    async def test_add_section_via_manager(self, temp_dir: Path) -> None:
        """Add section through manager."""
        manager = ArrangementManager(temp_dir)

        await manager.create(name="test", key="D_minor", tempo=124)
        arrangement = await manager.add_section("test", "intro", 8, "low")

        assert len(arrangement.sections) == 1
        assert arrangement.sections[0].energy == EnergyLevel.LOW

    @pytest.mark.asyncio
    async def test_assign_pattern_via_manager(self, temp_dir: Path) -> None:
        """Assign pattern through manager."""
        manager = ArrangementManager(temp_dir)

        await manager.create(name="test", key="D_minor", tempo=124)
        await manager.add_layer("test", "bass", "bass")
        arrangement = await manager.assign_pattern(
            "test", "bass", "main", "bass/root-pulse", variant="driving"
        )

        layer = arrangement.get_layer("bass")
        assert layer is not None
        assert "main" in layer.patterns
        assert layer.patterns["main"].variant == "driving"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, temp_dir: Path) -> None:
        """Get returns None for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        result = await manager.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, temp_dir: Path) -> None:
        """Delete returns False for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        result = await manager.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_duplicate_arrangement(self, temp_dir: Path) -> None:
        """Duplicate an arrangement with new name."""
        manager = ArrangementManager(temp_dir)

        arr = await manager.create(name="original", key="D_minor", tempo=124)
        arr.add_section("intro", 8)
        arr.add_layer("bass", LayerRole.BASS)

        duplicate = await manager.duplicate("original", "copy")
        assert duplicate.name == "copy"
        assert duplicate.context.key == "D_minor"
        assert len(duplicate.sections) == 1

    @pytest.mark.asyncio
    async def test_duplicate_nonexistent(self, temp_dir: Path) -> None:
        """Duplicate raises ValueError for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        with pytest.raises(ValueError, match="not found"):
            await manager.duplicate("nonexistent", "copy")

    @pytest.mark.asyncio
    async def test_add_section_nonexistent(self, temp_dir: Path) -> None:
        """Add section raises ValueError for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        with pytest.raises(ValueError, match="not found"):
            await manager.add_section("nonexistent", "intro", 8)

    @pytest.mark.asyncio
    async def test_add_layer_nonexistent(self, temp_dir: Path) -> None:
        """Add layer raises ValueError for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        with pytest.raises(ValueError, match="not found"):
            await manager.add_layer("nonexistent", "bass", "bass")

    @pytest.mark.asyncio
    async def test_assign_pattern_nonexistent_arrangement(self, temp_dir: Path) -> None:
        """Assign pattern raises ValueError for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        with pytest.raises(ValueError, match="not found"):
            await manager.assign_pattern("nonexistent", "bass", "main", "bass/root-pulse")

    @pytest.mark.asyncio
    async def test_assign_pattern_nonexistent_layer(self, temp_dir: Path) -> None:
        """Assign pattern raises ValueError for nonexistent layer."""
        manager = ArrangementManager(temp_dir)
        await manager.create(name="test", key="D_minor", tempo=124)
        with pytest.raises(ValueError, match="Layer not found"):
            await manager.assign_pattern("test", "bass", "main", "bass/root-pulse")

    @pytest.mark.asyncio
    async def test_arrange_layer(self, temp_dir: Path) -> None:
        """Arrange layer sets section patterns."""
        manager = ArrangementManager(temp_dir)
        await manager.create(name="test", key="D_minor", tempo=124)
        await manager.add_section("test", "intro", 8)
        await manager.add_section("test", "verse", 16)
        await manager.add_layer("test", "bass", "bass")
        await manager.assign_pattern("test", "bass", "main", "bass/root-pulse")

        arrangement = await manager.arrange_layer("test", "bass", {"intro": None, "verse": "main"})
        layer = arrangement.get_layer("bass")
        assert layer is not None
        assert layer.arrangement["intro"] is None
        assert layer.arrangement["verse"] == "main"

    @pytest.mark.asyncio
    async def test_arrange_layer_nonexistent_arrangement(self, temp_dir: Path) -> None:
        """Arrange layer raises ValueError for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        with pytest.raises(ValueError, match="not found"):
            await manager.arrange_layer("nonexistent", "bass", {})

    @pytest.mark.asyncio
    async def test_arrange_layer_nonexistent_layer(self, temp_dir: Path) -> None:
        """Arrange layer raises ValueError for nonexistent layer."""
        manager = ArrangementManager(temp_dir)
        await manager.create(name="test", key="D_minor", tempo=124)
        with pytest.raises(ValueError, match="Layer not found"):
            await manager.arrange_layer("test", "bass", {})

    @pytest.mark.asyncio
    async def test_set_harmony_default(self, temp_dir: Path) -> None:
        """Set default harmony progression."""
        manager = ArrangementManager(temp_dir)
        await manager.create(name="test", key="D_minor", tempo=124)

        arrangement = await manager.set_harmony("test", None, ["i", "VI", "III", "VII"], "1bar")
        assert arrangement.harmony.default_progression == ["i", "VI", "III", "VII"]

    @pytest.mark.asyncio
    async def test_set_harmony_section(self, temp_dir: Path) -> None:
        """Set harmony for specific section."""
        manager = ArrangementManager(temp_dir)
        await manager.create(name="test", key="D_minor", tempo=124)
        await manager.add_section("test", "chorus", 16)

        arrangement = await manager.set_harmony("test", "chorus", ["i", "VII"], "half")
        assert "chorus" in arrangement.harmony.sections
        assert arrangement.harmony.sections["chorus"].progression == ["i", "VII"]

    @pytest.mark.asyncio
    async def test_set_harmony_nonexistent(self, temp_dir: Path) -> None:
        """Set harmony raises ValueError for nonexistent arrangement."""
        manager = ArrangementManager(temp_dir)
        with pytest.raises(ValueError, match="not found"):
            await manager.set_harmony("nonexistent", None, ["i"])

    @pytest.mark.asyncio
    async def test_list_empty_dir(self, temp_dir: Path) -> None:
        """List arrangements in non-existent directory returns empty list."""
        manager = ArrangementManager(temp_dir / "nonexistent")
        arrangements = await manager.list_arrangements()
        assert arrangements == []

    @pytest.mark.asyncio
    async def test_create_with_style(self, temp_dir: Path) -> None:
        """Create arrangement with style."""
        manager = ArrangementManager(temp_dir)
        arrangement = await manager.create(
            name="test",
            key="D_minor",
            tempo=124,
            style="melodic-techno",
        )
        assert arrangement.context.style == "melodic-techno"

    def test_arrangement_metadata_repr(self) -> None:
        """ArrangementMetadata has correct repr."""
        from datetime import datetime

        from chuk_mcp_music.arrangement.manager import ArrangementMetadata

        meta = ArrangementMetadata(
            name="test",
            path=Path("/tmp/test.yaml"),
            key="D_minor",
            tempo=124,
            total_bars=56,
            layer_count=3,
            modified=datetime.now(),
        )
        assert "test" in repr(meta)
        assert "D_minor" in repr(meta)
        assert "124" in repr(meta)


class TestValidationAdditional:
    """Additional tests for validation to increase coverage."""

    def test_validation_issue_str(self) -> None:
        """ValidationIssue __str__ works correctly."""
        from chuk_mcp_music.arrangement.validator import (
            ValidationIssue,
            ValidationSeverity,
        )

        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error message",
            location="test/location",
        )
        result = str(issue)
        assert "[ERROR]" in result
        assert "TEST_ERROR" in result
        assert "Test error message" in result
        assert "at test/location" in result

    def test_validation_issue_str_no_location(self) -> None:
        """ValidationIssue __str__ works without location."""
        from chuk_mcp_music.arrangement.validator import (
            ValidationIssue,
            ValidationSeverity,
        )

        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code="TEST_WARN",
            message="Warning message",
        )
        result = str(issue)
        assert "[WARNING]" in result
        assert "at" not in result

    def test_validation_result_bool(self) -> None:
        """ValidationResult __bool__ returns is_valid."""
        from chuk_mcp_music.arrangement.validator import (
            ValidationResult,
        )

        result = ValidationResult()
        assert bool(result)  # Empty is valid

        # Add warning - still valid
        result.add_warning("WARN", "Warning message")
        assert bool(result)

        # Add error - no longer valid
        result.add_error("ERR", "Error message")
        assert not bool(result)

    def test_validation_result_str_empty(self) -> None:
        """ValidationResult __str__ for empty result."""
        from chuk_mcp_music.arrangement.validator import ValidationResult

        result = ValidationResult()
        assert "no issues" in str(result)

    def test_validation_result_str_with_issues(self) -> None:
        """ValidationResult __str__ for result with issues."""
        from chuk_mcp_music.arrangement.validator import ValidationResult

        result = ValidationResult()
        result.add_error("ERR", "Error 1")
        result.add_warning("WARN", "Warning 1")
        result_str = str(result)
        assert "ERR" in result_str
        assert "WARN" in result_str

    def test_validate_very_long_section(self) -> None:
        """Validation warns about very long sections."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="mega", bars=300)],  # Very long
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid  # Warning only
        assert any(i.code == "LONG_SECTION" for i in result.warnings)

    def test_validate_empty_sections_warning(self) -> None:
        """Validation warns about no sections."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[],
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid  # Warning only
        assert any(i.code == "NO_SECTIONS" for i in result.warnings)

    def test_validate_no_layers_info(self) -> None:
        """Validation reports info about no layers."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="intro", bars=8)],
            layers={},
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        # NO_LAYERS is info, not warning/error
        assert any(i.code == "NO_LAYERS" for i in result.issues)

    def test_validate_unused_pattern_info(self) -> None:
        """Validation reports info about unused patterns."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            layers={
                "bass": Layer(
                    name="bass",
                    role=LayerRole.BASS,
                    patterns={
                        "main": PatternRef(ref="bass/root-pulse"),
                        "unused": PatternRef(ref="bass/root-pulse"),  # Never used
                    },
                    arrangement={"verse": "main"},  # Only main is used
                ),
            },
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        assert any(i.code == "UNUSED_PATTERN" for i in result.issues)

    def test_validate_missing_section_arrangement_info(self) -> None:
        """Validation reports info about sections without patterns."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[
                Section(name="verse", bars=16),
                Section(name="chorus", bars=8),
            ],
            layers={
                "bass": Layer(
                    name="bass",
                    role=LayerRole.BASS,
                    patterns={"main": PatternRef(ref="bass/root-pulse")},
                    arrangement={"verse": "main"},  # No arrangement for chorus
                ),
            },
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        assert any(i.code == "MISSING_SECTION_ARRANGEMENT" for i in result.issues)

    def test_validate_empty_progression_warning(self) -> None:
        """Validation warns about empty progression."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            harmony=Harmony(default_progression=[]),  # Empty
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        assert any(i.code == "EMPTY_PROGRESSION" for i in result.warnings)

    def test_validate_orphan_harmony_warning(self) -> None:
        """Validation warns about harmony for unknown sections."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            harmony=Harmony(
                default_progression=["i"],
                sections={
                    "nonexistent": HarmonyProgression(progression=["i", "VII"]),
                },
            ),
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        assert any(i.code == "ORPHAN_HARMONY" for i in result.warnings)

    def test_validate_very_long_arrangement_info(self) -> None:
        """Validation reports info about very long arrangements."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name=f"part{i}", bars=100) for i in range(15)],  # 1500 bars
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        assert any(i.code == "VERY_LONG_ARRANGEMENT" for i in result.issues)

    def test_validate_multiple_solos_info(self) -> None:
        """Validation reports info about multiple soloed layers."""
        arrangement = Arrangement(
            name="test",
            context=ArrangementContext(key="D_minor", tempo=124),
            sections=[Section(name="verse", bars=16)],
            layers={
                "bass": Layer(name="bass", role=LayerRole.BASS, solo=True),
                "drums": Layer(name="drums", role=LayerRole.DRUMS, solo=True),
            },
        )

        result = validate_arrangement(arrangement)
        assert result.is_valid
        assert any(i.code == "MULTIPLE_SOLOS" for i in result.issues)

    def test_validate_add_info(self) -> None:
        """ValidationResult.add_info works."""
        from chuk_mcp_music.arrangement.validator import (
            ValidationResult,
            ValidationSeverity,
        )

        result = ValidationResult()
        result.add_info("TEST_INFO", "Info message", "location")
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.INFO
        assert result.is_valid  # Info doesn't fail validation
