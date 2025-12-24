"""
Structure tools - MCP tools for sections and structure management.

Tools for managing sections, structure, and layer arrangement.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.models.arrangement import EnergyLevel

if TYPE_CHECKING:
    from chuk_mcp_server import ChukMCPServer

logger = logging.getLogger(__name__)


def register_structure_tools(
    mcp: ChukMCPServer,
    manager: ArrangementManager,
) -> dict[str, Any]:
    """
    Register structure management tools with the MCP server.

    Args:
        mcp: The MCP server instance
        manager: The arrangement manager

    Returns:
        Dictionary of registered tool functions
    """
    tools: dict[str, Any] = {}

    @mcp.tool  # type: ignore[arg-type]
    async def music_add_section(
        arrangement: str,
        name: str,
        bars: int,
        energy: str | None = None,
        position: int | None = None,
    ) -> str:
        """
        Add a section to an arrangement.

        Sections define the song structure (intro, verse, chorus, etc.)
        and can have associated energy levels.

        Args:
            arrangement: Arrangement name
            name: Section name (e.g., 'intro', 'verse', 'chorus', 'breakdown')
            bars: Number of bars for this section
            energy: Optional energy level ('lowest', 'low', 'medium', 'high', 'highest')
            position: Optional position to insert (default: append at end)

        Returns:
            JSON string with updated arrangement sections

        Example:
            music_add_section(
                arrangement="my-track",
                name="verse",
                bars=16,
                energy="medium"
            )
        """
        try:
            arr = await manager.add_section(
                name=arrangement,
                section_name=name,
                bars=bars,
                energy=energy,
                position=position,
            )

            return json.dumps(
                {
                    "status": "success",
                    "sections": [
                        {
                            "name": s.name,
                            "bars": s.bars,
                            "energy": s.energy.value if s.energy else None,
                        }
                        for s in arr.sections
                    ],
                    "total_bars": arr.total_bars(),
                }
            )
        except Exception as e:
            logger.exception("Failed to add section")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_add_section"] = music_add_section

    @mcp.tool  # type: ignore[arg-type]
    async def music_remove_section(arrangement: str, name: str) -> str:
        """
        Remove a section from an arrangement.

        Args:
            arrangement: Arrangement name
            name: Section name to remove

        Returns:
            JSON string with updated arrangement sections

        Example:
            music_remove_section(arrangement="my-track", name="breakdown")
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            removed = arr.remove_section(name)
            if not removed:
                return json.dumps({"status": "error", "message": f"Section not found: {name}"})

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Removed section: {name}",
                    "sections": [s.name for s in arr.sections],
                    "total_bars": arr.total_bars(),
                }
            )
        except Exception as e:
            logger.exception("Failed to remove section")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_remove_section"] = music_remove_section

    @mcp.tool  # type: ignore[arg-type]
    async def music_reorder_sections(arrangement: str, order: list[str]) -> str:
        """
        Reorder sections in an arrangement.

        Args:
            arrangement: Arrangement name
            order: New section order as list of section names

        Returns:
            JSON string with updated section order

        Example:
            music_reorder_sections(
                arrangement="my-track",
                order=["intro", "chorus", "verse", "outro"]
            )
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            # Validate all section names exist
            section_names = {s.name for s in arr.sections}
            for name in order:
                if name not in section_names:
                    return json.dumps({"status": "error", "message": f"Section not found: {name}"})

            # Reorder by rebuilding the list
            section_map = {s.name: s for s in arr.sections}
            arr.sections = [section_map[name] for name in order]

            return json.dumps(
                {
                    "status": "success",
                    "sections": [s.name for s in arr.sections],
                    "total_bars": arr.total_bars(),
                }
            )
        except Exception as e:
            logger.exception("Failed to reorder sections")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_reorder_sections"] = music_reorder_sections

    @mcp.tool  # type: ignore[arg-type]
    async def music_set_section_energy(
        arrangement: str,
        section: str,
        energy: str,
    ) -> str:
        """
        Set the energy level for a section.

        Energy levels are semantic tokens that help the system
        make appropriate pattern and dynamics choices.

        Args:
            arrangement: Arrangement name
            section: Section name
            energy: Energy level ('lowest', 'low', 'medium', 'high', 'highest')

        Returns:
            JSON string with updated section

        Example:
            music_set_section_energy(
                arrangement="my-track",
                section="chorus",
                energy="high"
            )
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            section_obj = arr.get_section(section)
            if section_obj is None:
                return json.dumps({"status": "error", "message": f"Section not found: {section}"})

            # Sections are frozen, so we need to replace
            for i, s in enumerate(arr.sections):
                if s.name == section:
                    from chuk_mcp_music.models.arrangement import Section

                    arr.sections[i] = Section(
                        name=s.name,
                        bars=s.bars,
                        energy=EnergyLevel(energy),
                    )
                    break

            return json.dumps(
                {
                    "status": "success",
                    "section": {
                        "name": section,
                        "energy": energy,
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to set section energy")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_set_section_energy"] = music_set_section_energy

    @mcp.tool  # type: ignore[arg-type]
    async def music_add_layer(
        arrangement: str,
        name: str,
        role: str,
        channel: int | None = None,
    ) -> str:
        """
        Add a layer to an arrangement.

        Layers represent different instrument tracks (drums, bass, harmony, etc.)
        Each layer can have patterns assigned to different sections.

        Args:
            arrangement: Arrangement name
            name: Layer name (e.g., 'drums', 'bass', 'lead')
            role: Layer role ('sub', 'bass', 'drums', 'harmony', 'melody', 'fx', 'vocal')
            channel: Optional MIDI channel (0-15, 9 for drums). Auto-assigned if omitted.

        Returns:
            JSON string with updated layers

        Example:
            music_add_layer(
                arrangement="my-track",
                name="drums",
                role="drums"
            )
        """
        try:
            arr = await manager.add_layer(
                name=arrangement,
                layer_name=name,
                role=role,
                channel=channel,
            )

            return json.dumps(
                {
                    "status": "success",
                    "layers": [
                        {
                            "name": lname,
                            "role": layer.role.value,
                            "channel": layer.channel,
                        }
                        for lname, layer in arr.layers.items()
                    ],
                }
            )
        except Exception as e:
            logger.exception("Failed to add layer")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_add_layer"] = music_add_layer

    @mcp.tool  # type: ignore[arg-type]
    async def music_remove_layer(arrangement: str, name: str) -> str:
        """
        Remove a layer from an arrangement.

        Args:
            arrangement: Arrangement name
            name: Layer name to remove

        Returns:
            JSON string with updated layers

        Example:
            music_remove_layer(arrangement="my-track", name="drums")
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            removed = arr.remove_layer(name)
            if not removed:
                return json.dumps({"status": "error", "message": f"Layer not found: {name}"})

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Removed layer: {name}",
                    "layers": list(arr.layers.keys()),
                }
            )
        except Exception as e:
            logger.exception("Failed to remove layer")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_remove_layer"] = music_remove_layer

    @mcp.tool  # type: ignore[arg-type]
    async def music_arrange_layer(
        arrangement: str,
        layer: str,
        section_patterns: dict[str, str | None],
    ) -> str:
        """
        Set which patterns play in which sections for a layer.

        This is the core arrangement operation - assigning patterns to sections.
        Use null to indicate silence in a section.

        Args:
            arrangement: Arrangement name
            layer: Layer name
            section_patterns: Mapping of section name to pattern alias (or null for silence)

        Returns:
            JSON string with updated layer arrangement

        Example:
            music_arrange_layer(
                arrangement="my-track",
                layer="drums",
                section_patterns={
                    "intro": null,
                    "verse": "main",
                    "chorus": "main",
                    "outro": "sparse"
                }
            )
        """
        try:
            arr = await manager.arrange_layer(
                name=arrangement,
                layer_name=layer,
                section_patterns=section_patterns,
            )

            layer_obj = arr.get_layer(layer)
            if layer_obj is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {layer}"})

            return json.dumps(
                {
                    "status": "success",
                    "layer": layer,
                    "arrangement": layer_obj.arrangement,
                }
            )
        except Exception as e:
            logger.exception("Failed to arrange layer")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_arrange_layer"] = music_arrange_layer

    @mcp.tool  # type: ignore[arg-type]
    async def music_mute_layer(arrangement: str, name: str, muted: bool = True) -> str:
        """
        Mute or unmute a layer.

        Muted layers are excluded from compilation.

        Args:
            arrangement: Arrangement name
            name: Layer name
            muted: True to mute, False to unmute

        Returns:
            JSON string with layer status

        Example:
            music_mute_layer(arrangement="my-track", name="drums", muted=True)
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            layer = arr.get_layer(name)
            if layer is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {name}"})

            layer.muted = muted

            return json.dumps(
                {
                    "status": "success",
                    "layer": name,
                    "muted": layer.muted,
                }
            )
        except Exception as e:
            logger.exception("Failed to mute layer")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_mute_layer"] = music_mute_layer

    @mcp.tool  # type: ignore[arg-type]
    async def music_solo_layer(arrangement: str, name: str, solo: bool = True) -> str:
        """
        Solo or unsolo a layer.

        When any layer is soloed, only soloed layers are included in compilation.

        Args:
            arrangement: Arrangement name
            name: Layer name
            solo: True to solo, False to unsolo

        Returns:
            JSON string with layer status

        Example:
            music_solo_layer(arrangement="my-track", name="bass", solo=True)
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            layer = arr.get_layer(name)
            if layer is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {name}"})

            layer.solo = solo

            return json.dumps(
                {
                    "status": "success",
                    "layer": name,
                    "solo": layer.solo,
                }
            )
        except Exception as e:
            logger.exception("Failed to solo layer")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_solo_layer"] = music_solo_layer

    @mcp.tool  # type: ignore[arg-type]
    async def music_set_layer_level(arrangement: str, name: str, level: float) -> str:
        """
        Set the volume level for a layer.

        Adjusts the velocity of all events in the layer.

        Args:
            arrangement: Arrangement name
            name: Layer name
            level: Volume level (0.0 to 2.0, where 1.0 is normal)

        Returns:
            JSON string with layer status

        Example:
            music_set_layer_level(arrangement="my-track", name="harmony", level=0.7)
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            layer = arr.get_layer(name)
            if layer is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {name}"})

            layer.level = max(0.0, min(2.0, level))

            return json.dumps(
                {
                    "status": "success",
                    "layer": name,
                    "level": layer.level,
                }
            )
        except Exception as e:
            logger.exception("Failed to set layer level")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_set_layer_level"] = music_set_layer_level

    @mcp.tool  # type: ignore[arg-type]
    async def music_set_harmony(
        arrangement: str,
        section: str | None,
        progression: list[str],
        harmonic_rhythm: str = "1bar",
    ) -> str:
        """
        Set the chord progression for a section or default.

        Progressions are specified as Roman numerals (I, ii, iii, IV, V, vi, vii).
        Use lowercase for minor chords, uppercase for major.

        Args:
            arrangement: Arrangement name
            section: Section name, or null for default progression
            progression: Chord progression as Roman numerals (e.g., ['i', 'VI', 'III', 'VII'])
            harmonic_rhythm: How often chords change ('1bar', '2bar', 'half', 'quarter')

        Returns:
            JSON string with updated harmony

        Example:
            music_set_harmony(
                arrangement="my-track",
                section="chorus",
                progression=["i", "VII", "VI", "VII"],
                harmonic_rhythm="1bar"
            )
        """
        try:
            await manager.set_harmony(
                name=arrangement,
                section_name=section,
                progression=progression,
                harmonic_rhythm=harmonic_rhythm,
            )

            return json.dumps(
                {
                    "status": "success",
                    "section": section or "default",
                    "progression": progression,
                    "harmonic_rhythm": harmonic_rhythm,
                }
            )
        except Exception as e:
            logger.exception("Failed to set harmony")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_set_harmony"] = music_set_harmony

    return tools
