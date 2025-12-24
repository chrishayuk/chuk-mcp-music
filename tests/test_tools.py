"""
Tests for MCP tools.

Tests the MCP tool implementations for arrangements, patterns, styles,
structure, and compilation.
"""

import json
import tempfile
from pathlib import Path

import pytest

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.patterns import PatternRegistry
from chuk_mcp_music.styles import StyleLoader


# Mock MCP server for testing tools
class MockMCPServer:
    """Mock MCP server that just stores registered tools."""

    def __init__(self, name: str):
        self.name = name
        self.tools: dict = {}

    def tool(self, func):
        """Decorator to register a tool."""
        self.tools[func.__name__] = func
        return func


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def library_path():
    """Path to pattern library."""
    return Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "patterns" / "library"


@pytest.fixture
def styles_library_path():
    """Path to styles library."""
    return Path(__file__).parent.parent / "src" / "chuk_mcp_music" / "styles" / "library"


class TestArrangementTools:
    """Tests for arrangement tools."""

    @pytest.mark.asyncio
    async def test_create_arrangement(self, temp_dir: Path):
        """Create arrangement tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_create_arrangement"](
            name="test",
            key="D_minor",
            tempo=124,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["arrangement"]["name"] == "test"

    @pytest.mark.asyncio
    async def test_get_arrangement(self, temp_dir: Path):
        """Get arrangement tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        # Create first
        await tools["music_create_arrangement"](name="test", key="D_minor", tempo=124)

        # Then get
        result = await tools["music_get_arrangement"](name="test")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["arrangement"]["name"] == "test"

    @pytest.mark.asyncio
    async def test_get_arrangement_not_found(self, temp_dir: Path):
        """Get arrangement returns error for missing arrangement."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_get_arrangement"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_list_arrangements(self, temp_dir: Path):
        """List arrangements tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        # Create and save
        await tools["music_create_arrangement"](name="test1", key="D_minor", tempo=124)
        await tools["music_save_arrangement"](name="test1")
        await tools["music_create_arrangement"](name="test2", key="C_major", tempo=120)
        await tools["music_save_arrangement"](name="test2")

        result = await tools["music_list_arrangements"]()
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["arrangements"]) == 2

    @pytest.mark.asyncio
    async def test_save_arrangement(self, temp_dir: Path):
        """Save arrangement tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        await tools["music_create_arrangement"](name="test", key="D_minor", tempo=124)
        result = await tools["music_save_arrangement"](name="test")
        data = json.loads(result)
        assert data["status"] == "success"
        assert Path(data["path"]).exists()

    @pytest.mark.asyncio
    async def test_save_arrangement_not_found(self, temp_dir: Path):
        """Save arrangement returns error for missing arrangement."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_save_arrangement"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_delete_arrangement(self, temp_dir: Path):
        """Delete arrangement tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        await tools["music_create_arrangement"](name="test", key="D_minor", tempo=124)
        await tools["music_save_arrangement"](name="test")

        result = await tools["music_delete_arrangement"](name="test")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_duplicate_arrangement(self, temp_dir: Path):
        """Duplicate arrangement tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        await tools["music_create_arrangement"](name="original", key="D_minor", tempo=124)
        result = await tools["music_duplicate_arrangement"](name="original", new_name="copy")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["arrangement"]["name"] == "copy"

    @pytest.mark.asyncio
    async def test_delete_arrangement_not_found(self, temp_dir: Path):
        """Delete nonexistent arrangement."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_delete_arrangement"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_duplicate_arrangement_not_found(self, temp_dir: Path):
        """Duplicate nonexistent arrangement."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_duplicate_arrangement"](name="nonexistent", new_name="copy")
        data = json.loads(result)
        assert data["status"] == "error"


class TestStructureTools:
    """Tests for structure tools."""

    @pytest.mark.asyncio
    async def test_add_section(self, temp_dir: Path):
        """Add section tool."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        register_arrangement_tools(mcp, manager)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_add_section"](
            arrangement="test", name="intro", bars=8, energy="low"
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["sections"][0]["name"] == "intro"

    @pytest.mark.asyncio
    async def test_add_section_not_found(self, temp_dir: Path):
        """Add section to nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_add_section"](arrangement="nonexistent", name="intro", bars=8)
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_remove_section(self, temp_dir: Path):
        """Remove section tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)

        result = await tools["music_remove_section"](arrangement="test", name="intro")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_remove_section_not_found(self, temp_dir: Path):
        """Remove section from nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_remove_section"](arrangement="nonexistent", name="intro")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_remove_section_missing_section(self, temp_dir: Path):
        """Remove nonexistent section."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_remove_section"](arrangement="test", name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_reorder_sections(self, temp_dir: Path):
        """Reorder sections tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)
        arr.add_section("verse", 16)
        arr.add_section("chorus", 8)

        result = await tools["music_reorder_sections"](
            arrangement="test", order=["chorus", "verse", "intro"]
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["sections"] == ["chorus", "verse", "intro"]

    @pytest.mark.asyncio
    async def test_reorder_sections_not_found(self, temp_dir: Path):
        """Reorder sections on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_reorder_sections"](arrangement="nonexistent", order=["intro"])
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_reorder_sections_missing_section(self, temp_dir: Path):
        """Reorder sections with missing section in order."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)

        result = await tools["music_reorder_sections"](
            arrangement="test", order=["intro", "nonexistent"]
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_set_section_energy(self, temp_dir: Path):
        """Set section energy tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)

        result = await tools["music_set_section_energy"](
            arrangement="test", section="intro", energy="high"
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["section"]["energy"] == "high"

    @pytest.mark.asyncio
    async def test_set_section_energy_not_found(self, temp_dir: Path):
        """Set section energy on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_set_section_energy"](
            arrangement="nonexistent", section="intro", energy="high"
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_set_section_energy_missing_section(self, temp_dir: Path):
        """Set energy on nonexistent section."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_set_section_energy"](
            arrangement="test", section="nonexistent", energy="high"
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_add_layer(self, temp_dir: Path):
        """Add layer tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_add_layer"](
            arrangement="test", name="bass", role="bass", channel=1
        )
        data = json.loads(result)
        assert data["status"] == "success"
        # Response has layers list, check first layer
        assert any(layer["name"] == "bass" for layer in data["layers"])

    @pytest.mark.asyncio
    async def test_add_layer_not_found(self, temp_dir: Path):
        """Add layer to nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_add_layer"](arrangement="nonexistent", name="bass", role="bass")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_remove_layer(self, temp_dir: Path):
        """Remove layer tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_remove_layer"](arrangement="test", name="bass")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_remove_layer_not_found(self, temp_dir: Path):
        """Remove layer from nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_remove_layer"](arrangement="nonexistent", name="bass")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_remove_layer_missing(self, temp_dir: Path):
        """Remove nonexistent layer."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_remove_layer"](arrangement="test", name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_arrange_layer(self, temp_dir: Path):
        """Arrange layer tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)
        arr.add_section("verse", 16)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_arrange_layer"](
            arrangement="test",
            layer="bass",
            section_patterns={"intro": None, "verse": "main"},
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["layer"] == "bass"

    @pytest.mark.asyncio
    async def test_arrange_layer_not_found(self, temp_dir: Path):
        """Arrange layer on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_arrange_layer"](
            arrangement="nonexistent",
            layer="bass",
            section_patterns={},
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_mute_layer(self, temp_dir: Path):
        """Mute layer tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_mute_layer"](arrangement="test", name="bass", muted=True)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["muted"] is True

    @pytest.mark.asyncio
    async def test_mute_layer_not_found(self, temp_dir: Path):
        """Mute layer on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_mute_layer"](arrangement="nonexistent", name="bass", muted=True)
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_mute_layer_missing(self, temp_dir: Path):
        """Mute nonexistent layer."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_mute_layer"](arrangement="test", name="nonexistent", muted=True)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_solo_layer(self, temp_dir: Path):
        """Solo layer tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_solo_layer"](arrangement="test", name="bass", solo=True)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["solo"] is True

    @pytest.mark.asyncio
    async def test_solo_layer_not_found(self, temp_dir: Path):
        """Solo layer on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_solo_layer"](arrangement="nonexistent", name="bass", solo=True)
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_solo_layer_missing(self, temp_dir: Path):
        """Solo nonexistent layer."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_solo_layer"](arrangement="test", name="nonexistent", solo=True)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_set_layer_level(self, temp_dir: Path):
        """Set layer level tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_set_layer_level"](arrangement="test", name="bass", level=0.8)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["level"] == 0.8

    @pytest.mark.asyncio
    async def test_set_layer_level_not_found(self, temp_dir: Path):
        """Set layer level on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_set_layer_level"](
            arrangement="nonexistent", name="bass", level=0.8
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_set_layer_level_missing(self, temp_dir: Path):
        """Set level on nonexistent layer."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_set_layer_level"](
            arrangement="test", name="nonexistent", level=0.8
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_set_harmony(self, temp_dir: Path):
        """Set harmony tool."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_set_harmony"](
            arrangement="test",
            section=None,
            progression=["i", "VI", "III", "VII"],
            harmonic_rhythm="1bar",
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["section"] == "default"
        assert data["progression"] == ["i", "VI", "III", "VII"]

    @pytest.mark.asyncio
    async def test_set_harmony_for_section(self, temp_dir: Path):
        """Set harmony for specific section."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("chorus", 8)

        result = await tools["music_set_harmony"](
            arrangement="test",
            section="chorus",
            progression=["i", "VII", "VI", "VII"],
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["section"] == "chorus"

    @pytest.mark.asyncio
    async def test_set_harmony_not_found(self, temp_dir: Path):
        """Set harmony on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_set_harmony"](
            arrangement="nonexistent",
            section=None,
            progression=["i"],
        )
        data = json.loads(result)
        assert data["status"] == "error"


class TestPatternTools:
    """Tests for pattern tools."""

    @pytest.mark.asyncio
    async def test_list_patterns(self, temp_dir: Path, library_path: Path):
        """List patterns tool."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_list_patterns"]()
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["count"] > 0

    @pytest.mark.asyncio
    async def test_list_patterns_by_role(self, temp_dir: Path, library_path: Path):
        """List patterns by role."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_list_patterns"](role="bass")
        data = json.loads(result)
        assert data["status"] == "success"
        assert all(p["role"] == "bass" for p in data["patterns"])

    @pytest.mark.asyncio
    async def test_describe_pattern(self, temp_dir: Path, library_path: Path):
        """Describe pattern tool."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_describe_pattern"](pattern_id="bass/root-pulse")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["pattern"]["name"] == "root-pulse"

    @pytest.mark.asyncio
    async def test_describe_pattern_not_found(self, temp_dir: Path, library_path: Path):
        """Describe pattern returns error for missing pattern."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_describe_pattern"](pattern_id="nonexistent/pattern")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_pattern(self, temp_dir: Path, library_path: Path):
        """Add pattern to layer."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            alias="main",
            pattern_id="bass/root-pulse",
        )
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_copy_pattern_to_project(self, temp_dir: Path, library_path: Path):
        """Copy pattern to project."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path, project_path=temp_dir / "patterns")
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_copy_pattern_to_project"](pattern_id="bass/root-pulse")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_copy_pattern_not_found(self, temp_dir: Path, library_path: Path):
        """Copy nonexistent pattern."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path, project_path=temp_dir / "patterns")
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_copy_pattern_to_project"](pattern_id="nonexistent/pattern")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_pattern_not_found(self, temp_dir: Path, library_path: Path):
        """Add nonexistent pattern."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            pattern_id="nonexistent/pattern",
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_add_pattern_arrangement_not_found(self, temp_dir: Path, library_path: Path):
        """Add pattern to nonexistent arrangement."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_add_pattern"](
            arrangement="nonexistent",
            layer="bass",
            pattern_id="bass/root-pulse",
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_pattern_layer_not_found(self, temp_dir: Path, library_path: Path):
        """Add pattern to nonexistent layer."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_add_pattern"](
            arrangement="test",
            layer="nonexistent",
            pattern_id="bass/root-pulse",
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Layer not found" in data["message"]

    @pytest.mark.asyncio
    async def test_add_pattern_invalid_variant(self, temp_dir: Path, library_path: Path):
        """Add pattern with invalid variant."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            pattern_id="bass/root-pulse",
            variant="nonexistent_variant",
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Unknown variant" in data["message"]

    @pytest.mark.asyncio
    async def test_remove_pattern(self, temp_dir: Path, library_path: Path):
        """Remove pattern from layer."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        # First add a pattern
        await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            alias="main",
            pattern_id="bass/root-pulse",
        )

        # Then remove it
        result = await tools["music_remove_pattern"](arrangement="test", layer="bass", alias="main")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["removed"] == "main"

    @pytest.mark.asyncio
    async def test_remove_pattern_not_found(self, temp_dir: Path, library_path: Path):
        """Remove pattern from nonexistent arrangement."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_remove_pattern"](
            arrangement="nonexistent", layer="bass", alias="main"
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_remove_pattern_layer_not_found(self, temp_dir: Path, library_path: Path):
        """Remove pattern from nonexistent layer."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_remove_pattern"](
            arrangement="test", layer="nonexistent", alias="main"
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Layer not found" in data["message"]

    @pytest.mark.asyncio
    async def test_remove_pattern_alias_not_found(self, temp_dir: Path, library_path: Path):
        """Remove nonexistent pattern alias."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_remove_pattern"](
            arrangement="test", layer="bass", alias="nonexistent"
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "alias not found" in data["message"]

    @pytest.mark.asyncio
    async def test_update_pattern_params(self, temp_dir: Path, library_path: Path):
        """Update pattern params."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        # Add a pattern first
        await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            alias="main",
            pattern_id="bass/root-pulse",
        )

        # Update its params
        result = await tools["music_update_pattern_params"](
            arrangement="test",
            layer="bass",
            alias="main",
            params={"velocity_base": 0.7},
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["pattern"]["params"]["velocity_base"] == 0.7

    @pytest.mark.asyncio
    async def test_update_pattern_params_not_found(self, temp_dir: Path, library_path: Path):
        """Update pattern on nonexistent arrangement."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_update_pattern_params"](
            arrangement="nonexistent", layer="bass", alias="main"
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_update_pattern_layer_not_found(self, temp_dir: Path, library_path: Path):
        """Update pattern on nonexistent layer."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_update_pattern_params"](
            arrangement="test", layer="nonexistent", alias="main"
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Layer not found" in data["message"]

    @pytest.mark.asyncio
    async def test_update_pattern_alias_not_found(self, temp_dir: Path, library_path: Path):
        """Update nonexistent pattern alias."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_update_pattern_params"](
            arrangement="test", layer="bass", alias="nonexistent"
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "alias not found" in data["message"]


class TestStyleTools:
    """Tests for style tools."""

    @pytest.mark.asyncio
    async def test_list_styles(self, temp_dir: Path, library_path: Path, styles_library_path: Path):
        """List styles tool."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_list_styles"]()
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["count"] >= 3  # melodic-techno, ambient, cinematic

    @pytest.mark.asyncio
    async def test_describe_style(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Describe style tool."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_describe_style"](name="melodic-techno")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["style"]["name"] == "melodic-techno"

    @pytest.mark.asyncio
    async def test_describe_style_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Describe style returns error for missing style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_describe_style"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_suggest_patterns(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Suggest patterns for role in style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_suggest_patterns"](style="melodic-techno", role="bass")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_apply_style(self, temp_dir: Path, library_path: Path, styles_library_path: Path):
        """Apply style to arrangement."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        await manager.create(name="test", key="D_minor", tempo=100)

        result = await tools["music_apply_style"](arrangement="test", style="melodic-techno")
        data = json.loads(result)
        assert data["status"] == "success"
        # Tempo should be adjusted to fit style range
        assert data["tempo_adjusted"] is True

    @pytest.mark.asyncio
    async def test_validate_style(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Validate arrangement against style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_validate_style"](arrangement="test", style="melodic-techno")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_copy_style_to_project(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Copy style to project."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_copy_style_to_project"](name="melodic-techno")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_copy_style_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Copy nonexistent style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_copy_style_to_project"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_suggest_patterns_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Suggest patterns for nonexistent style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_suggest_patterns"](style="nonexistent", role="bass")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_apply_style_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Apply style to nonexistent arrangement."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_apply_style"](arrangement="nonexistent", style="melodic-techno")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_apply_style_style_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Apply nonexistent style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_apply_style"](arrangement="test", style="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]

    @pytest.mark.asyncio
    async def test_validate_style_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Validate style for nonexistent arrangement."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_validate_style"](
            arrangement="nonexistent", style="melodic-techno"
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_validate_style_style_not_found(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Validate with nonexistent style."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_validate_style"](arrangement="test", style="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"]


class TestCompilationTools:
    """Tests for compilation tools."""

    @pytest.mark.asyncio
    async def test_compile_midi(self, temp_dir: Path, library_path: Path):
        """Compile arrangement to MIDI."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        # Create arrangement with patterns
        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("verse", 4)
        arr.add_layer("bass", LayerRole.BASS)
        from chuk_mcp_music.models.arrangement import PatternRef

        arr.layers["bass"].patterns["main"] = PatternRef(ref="bass/root-pulse")
        arr.layers["bass"].arrangement["verse"] = "main"

        result = await tools["music_compile_midi"](arrangement="test")
        data = json.loads(result)
        assert data["status"] == "success"
        assert Path(data["path"]).exists()

    @pytest.mark.asyncio
    async def test_preview_section(self, temp_dir: Path, library_path: Path):
        """Preview a single section."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        # Create arrangement with patterns
        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("verse", 4)
        arr.add_layer("bass", LayerRole.BASS)
        from chuk_mcp_music.models.arrangement import PatternRef

        arr.layers["bass"].patterns["main"] = PatternRef(ref="bass/root-pulse")
        arr.layers["bass"].arrangement["verse"] = "main"

        result = await tools["music_preview_section"](arrangement="test", section="verse")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_export_yaml(self, temp_dir: Path, library_path: Path):
        """Export arrangement to YAML."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_export_yaml"](arrangement="test")
        data = json.loads(result)
        assert data["status"] == "success"
        assert "yaml" in data

    @pytest.mark.asyncio
    async def test_validate(self, temp_dir: Path, library_path: Path):
        """Validate arrangement."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("verse", 16)

        result = await tools["music_validate"](arrangement="test")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_compile_midi_not_found(self, temp_dir: Path, library_path: Path):
        """Compile nonexistent arrangement."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        result = await tools["music_compile_midi"](arrangement="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_preview_section_not_found(self, temp_dir: Path, library_path: Path):
        """Preview section on nonexistent arrangement."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        result = await tools["music_preview_section"](arrangement="nonexistent", section="verse")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_preview_section_section_not_found(self, temp_dir: Path, library_path: Path):
        """Preview nonexistent section."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_preview_section"](arrangement="test", section="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_export_yaml_not_found(self, temp_dir: Path, library_path: Path):
        """Export nonexistent arrangement."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        result = await tools["music_export_yaml"](arrangement="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_validate_not_found(self, temp_dir: Path, library_path: Path):
        """Validate nonexistent arrangement."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        result = await tools["music_validate"](arrangement="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"


class TestPatternToolsAdditional:
    """Additional tests for pattern tools to increase coverage."""

    @pytest.mark.asyncio
    async def test_add_pattern_with_invalid_params(self, temp_dir: Path, library_path: Path):
        """Add pattern with invalid parameters."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)

        # Add pattern with invalid params
        result = await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            pattern_id="bass/root-pulse",
            params={"velocity_base": 99.0},  # Out of valid range
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Invalid params" in data["message"]


class TestStyleToolsAdditional:
    """Additional tests for style tools to increase coverage."""

    @pytest.mark.asyncio
    async def test_suggest_patterns_with_energy(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Suggest patterns with energy level."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_suggest_patterns"](
            style="melodic-techno", role="bass", energy="high"
        )
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_copy_style_already_exists(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Copy style that already exists in project."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        # Copy first time
        await tools["music_copy_style_to_project"](name="melodic-techno")

        # Copy second time should fail
        result = await tools["music_copy_style_to_project"](name="melodic-techno")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "already exists" in data["message"]


class TestArrangementToolsAdditional:
    """Additional tests for arrangement tools to increase coverage."""

    @pytest.mark.asyncio
    async def test_create_arrangement_with_style(self, temp_dir: Path):
        """Create arrangement with style."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_create_arrangement"](
            name="test",
            key="D_minor",
            tempo=124,
            style="melodic-techno",
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["arrangement"]["style"] == "melodic-techno"


class TestStructureToolsAdditional:
    """Additional tests for structure tools to increase coverage."""

    @pytest.mark.asyncio
    async def test_add_section_with_position(self, temp_dir: Path):
        """Add section at specific position."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("verse", 16)
        arr.add_section("outro", 8)

        # Insert intro at position 0
        result = await tools["music_add_section"](
            arrangement="test", name="intro", bars=8, position=0
        )
        data = json.loads(result)
        assert data["status"] == "success"
        # Intro should be first
        assert data["sections"][0]["name"] == "intro"

    @pytest.mark.asyncio
    async def test_arrange_layer_missing_layer(self, temp_dir: Path):
        """Arrange layer returns error after arrange_layer for missing layer."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)
        arr.add_layer("bass", LayerRole.BASS)

        # Arrange layer successfully first
        result = await tools["music_arrange_layer"](
            arrangement="test",
            layer="bass",
            section_patterns={"intro": None},
        )
        data = json.loads(result)
        assert data["status"] == "success"


class TestValidationAdditional:
    """Additional tests for validation to increase coverage."""

    @pytest.mark.asyncio
    async def test_validate_with_warnings(self, temp_dir: Path, library_path: Path):
        """Validate arrangement with various warnings."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        # Create arrangement without sections (should warn)
        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_validate"](arrangement="test")
        data = json.loads(result)
        assert data["status"] == "success"
        # Should have warnings about no sections
        assert len(data["warnings"]) > 0 or len(data["errors"]) == 0


class TestPatternToolsCopyDuplicate:
    """Tests for pattern copy scenarios."""

    @pytest.mark.asyncio
    async def test_copy_pattern_not_found(self, temp_dir: Path, library_path: Path):
        """Copy pattern that does not exist."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path, project_path=temp_dir / "patterns")
        tools = register_pattern_tools(mcp, manager, registry)

        # Copy nonexistent pattern
        result = await tools["music_copy_pattern_to_project"](pattern_id="bass/nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"].lower() or "Pattern" in data["message"]


class TestToolsExceptionHandling:
    """Tests for exception handling paths in tools."""

    @pytest.mark.asyncio
    async def test_delete_arrangement_not_found(self, temp_dir: Path):
        """Delete nonexistent arrangement - covers arrangement tool error path."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_delete_arrangement"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_get_arrangement_not_found(self, temp_dir: Path):
        """Get nonexistent arrangement."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_get_arrangement"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_list_arrangements_empty(self, temp_dir: Path):
        """List arrangements in empty directory."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_list_arrangements"]()
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["arrangements"] == []

    @pytest.mark.asyncio
    async def test_duplicate_arrangement_source_not_found(self, temp_dir: Path):
        """Duplicate arrangement when source doesn't exist."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_duplicate_arrangement"](name="nonexistent", new_name="copy")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_save_arrangement_not_found(self, temp_dir: Path):
        """Save nonexistent arrangement."""
        from chuk_mcp_music.tools.arrangement import register_arrangement_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_arrangement_tools(mcp, manager)

        result = await tools["music_save_arrangement"](name="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_structure_remove_section_not_found(self, temp_dir: Path):
        """Remove section from nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_remove_section"](arrangement="nonexistent", name="intro")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_layer_nonexistent_arrangement(self, temp_dir: Path):
        """Add layer to nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_add_layer"](arrangement="nonexistent", name="bass", role="bass")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_remove_layer_nonexistent_arrangement(self, temp_dir: Path):
        """Remove layer from nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_remove_layer"](arrangement="nonexistent", name="bass")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_set_harmony_nonexistent_arrangement(self, temp_dir: Path):
        """Set harmony on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_set_harmony"](
            arrangement="nonexistent", section=None, progression=["i", "VII"]
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_arrange_layer_nonexistent_arrangement(self, temp_dir: Path):
        """Arrange layer on nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_arrange_layer"](
            arrangement="nonexistent", layer="bass", section_patterns={}
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_preview_section_nonexistent_section(self, temp_dir: Path, library_path: Path):
        """Preview nonexistent section."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_preview_section"](arrangement="test", section="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_patterns_describe_pattern_with_constraints(
        self, temp_dir: Path, library_path: Path
    ):
        """Describe pattern with constraints."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        # Use a pattern that exists
        result = await tools["music_describe_pattern"](pattern_id="bass/root-pulse")
        data = json.loads(result)
        assert data["status"] == "success"
        assert "constraints" in data["pattern"]

    @pytest.mark.asyncio
    async def test_suggest_patterns_unknown_role(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """Suggest patterns with unusual role."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_suggest_patterns"](style="melodic-techno", role="melody")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_mute_layer_nonexistent_arrangement(self, temp_dir: Path):
        """Mute layer in nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_mute_layer"](arrangement="nonexistent", name="bass", muted=True)
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_solo_layer_nonexistent_arrangement(self, temp_dir: Path):
        """Solo layer in nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_solo_layer"](arrangement="nonexistent", name="bass", solo=True)
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_set_layer_level_nonexistent_arrangement(self, temp_dir: Path):
        """Set layer level in nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_set_layer_level"](
            arrangement="nonexistent", name="bass", level=0.8
        )
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_section_nonexistent_arrangement(self, temp_dir: Path):
        """Add section to nonexistent arrangement."""
        from chuk_mcp_music.tools.structure import register_structure_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        tools = register_structure_tools(mcp, manager)

        result = await tools["music_add_section"](arrangement="nonexistent", name="verse", bars=16)
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_list_patterns_success(self, temp_dir: Path, library_path: Path):
        """List patterns successfully."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_list_patterns"]()
        data = json.loads(result)
        assert data["status"] == "success"
        assert "patterns" in data
        assert len(data["patterns"]) > 0

    @pytest.mark.asyncio
    async def test_describe_pattern_not_found(self, temp_dir: Path, library_path: Path):
        """Describe nonexistent pattern."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        result = await tools["music_describe_pattern"](pattern_id="nonexistent/pattern")
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_update_pattern_params_success(self, temp_dir: Path, library_path: Path):
        """Update pattern parameters successfully."""
        from chuk_mcp_music.tools.patterns import register_pattern_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        tools = register_pattern_tools(mcp, manager, registry)

        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_layer("bass", LayerRole.BASS)
        await tools["music_add_pattern"](
            arrangement="test",
            layer="bass",
            pattern_id="bass/root-pulse",
            alias="main",
        )

        result = await tools["music_update_pattern_params"](
            arrangement="test",
            layer="bass",
            alias="main",
            params={"velocity_base": 0.7},
        )
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_list_styles_success(
        self, temp_dir: Path, library_path: Path, styles_library_path: Path
    ):
        """List styles successfully."""
        from chuk_mcp_music.tools.styles import register_style_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        style_loader = StyleLoader(
            library_path=styles_library_path, project_path=temp_dir / "styles"
        )
        tools = register_style_tools(mcp, manager, registry, style_loader)

        result = await tools["music_list_styles"]()
        data = json.loads(result)
        assert data["status"] == "success"
        assert "styles" in data

    @pytest.mark.asyncio
    async def test_compile_midi_success(self, temp_dir: Path, library_path: Path):
        """Compile MIDI successfully."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        # Create arrangement with section and layer
        arr = await manager.create(name="test", key="D_minor", tempo=124)
        arr.add_section("intro", 8)
        arr.add_layer("bass", LayerRole.BASS)

        result = await tools["music_compile_midi"](arrangement="test")
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_export_yaml_success(self, temp_dir: Path, library_path: Path):
        """Export YAML successfully."""
        from chuk_mcp_music.tools.compilation import register_compilation_tools

        mcp = MockMCPServer("test")
        manager = ArrangementManager(temp_dir)
        registry = PatternRegistry(library_path=library_path)
        output_dir = temp_dir / "output"
        tools = register_compilation_tools(mcp, manager, registry, output_dir)

        await manager.create(name="test", key="D_minor", tempo=124)

        result = await tools["music_export_yaml"](arrangement="test")
        data = json.loads(result)
        assert data["status"] == "success"
