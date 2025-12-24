"""
Arrangement tools - MCP tools for arrangement lifecycle.

Tools for creating, managing, and querying arrangements.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from chuk_mcp_music.arrangement import ArrangementManager

if TYPE_CHECKING:
    from chuk_mcp_server import ChukMCPServer

logger = logging.getLogger(__name__)


def register_arrangement_tools(
    mcp: ChukMCPServer,
    manager: ArrangementManager,
) -> dict[str, Any]:
    """
    Register arrangement lifecycle tools with the MCP server.

    Args:
        mcp: The MCP server instance
        manager: The arrangement manager

    Returns:
        Dictionary of registered tool functions
    """
    tools: dict[str, Any] = {}

    @mcp.tool  # type: ignore[arg-type]
    async def music_create_arrangement(
        name: str,
        key: str,
        tempo: int,
        time_signature: str = "4/4",
        style: str | None = None,
    ) -> str:
        """
        Create a new music arrangement.

        Creates a new arrangement with the specified key, tempo, and optional style.
        The arrangement is set as the current active arrangement.

        Args:
            name: Unique name for the arrangement
            key: Musical key (e.g., 'C_major', 'D_minor', 'F_major')
            tempo: Tempo in BPM (40-300)
            time_signature: Time signature (default: '4/4')
            style: Optional style constraint bundle (e.g., 'melodic-techno', 'ambient')

        Returns:
            JSON string with arrangement details

        Example:
            music_create_arrangement(
                name="my-track",
                key="D_minor",
                tempo=124,
                style="melodic-techno"
            )
        """
        try:
            arrangement = await manager.create(
                name=name,
                key=key,
                tempo=tempo,
                time_signature=time_signature,
                style=style,
            )

            return json.dumps(
                {
                    "status": "success",
                    "arrangement": {
                        "name": arrangement.name,
                        "key": arrangement.context.key,
                        "tempo": arrangement.context.tempo,
                        "time_signature": arrangement.context.time_signature,
                        "style": arrangement.context.style,
                        "total_bars": arrangement.total_bars(),
                        "sections": len(arrangement.sections),
                        "layers": len(arrangement.layers),
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to create arrangement")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_create_arrangement"] = music_create_arrangement

    @mcp.tool  # type: ignore[arg-type]
    async def music_get_arrangement(name: str) -> str:
        """
        Get arrangement details.

        Retrieves the full details of an arrangement including
        structure, layers, and harmony configuration.

        Args:
            name: Arrangement name

        Returns:
            JSON string with arrangement details

        Example:
            music_get_arrangement(name="my-track")
        """
        try:
            arrangement = await manager.get(name)
            if arrangement is None:
                return json.dumps({"status": "error", "message": f"Arrangement not found: {name}"})

            return json.dumps(
                {
                    "status": "success",
                    "arrangement": arrangement.to_yaml_dict(),
                }
            )
        except Exception as e:
            logger.exception("Failed to get arrangement")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_get_arrangement"] = music_get_arrangement

    @mcp.tool  # type: ignore[arg-type]
    async def music_list_arrangements() -> str:
        """
        List all saved arrangements.

        Returns a list of all arrangements in the project with basic metadata.

        Returns:
            JSON string with list of arrangement summaries

        Example:
            music_list_arrangements()
        """
        try:
            arrangements = await manager.list_arrangements()

            return json.dumps(
                {
                    "status": "success",
                    "arrangements": [
                        {
                            "name": arr.name,
                            "key": arr.key,
                            "tempo": arr.tempo,
                            "total_bars": arr.total_bars,
                            "layers": arr.layer_count,
                            "modified": arr.modified.isoformat(),
                        }
                        for arr in arrangements
                    ],
                }
            )
        except Exception as e:
            logger.exception("Failed to list arrangements")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_list_arrangements"] = music_list_arrangements

    @mcp.tool  # type: ignore[arg-type]
    async def music_save_arrangement(name: str) -> str:
        """
        Save an arrangement to disk.

        Persists the arrangement to a YAML file that can be
        edited manually or version controlled.

        Args:
            name: Arrangement name

        Returns:
            JSON string with save result

        Example:
            music_save_arrangement(name="my-track")
        """
        try:
            arrangement = await manager.get(name)
            if arrangement is None:
                return json.dumps({"status": "error", "message": f"Arrangement not found: {name}"})

            path = await manager.save(arrangement)

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Arrangement saved to {path}",
                    "path": str(path),
                }
            )
        except Exception as e:
            logger.exception("Failed to save arrangement")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_save_arrangement"] = music_save_arrangement

    @mcp.tool  # type: ignore[arg-type]
    async def music_delete_arrangement(name: str) -> str:
        """
        Delete an arrangement.

        Removes the arrangement from memory and disk.

        Args:
            name: Arrangement name

        Returns:
            JSON string with delete result

        Example:
            music_delete_arrangement(name="my-track")
        """
        try:
            deleted = await manager.delete(name)

            if deleted:
                return json.dumps(
                    {
                        "status": "success",
                        "message": f"Arrangement '{name}' deleted",
                    }
                )
            else:
                return json.dumps({"status": "error", "message": f"Arrangement not found: {name}"})
        except Exception as e:
            logger.exception("Failed to delete arrangement")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_delete_arrangement"] = music_delete_arrangement

    @mcp.tool  # type: ignore[arg-type]
    async def music_duplicate_arrangement(name: str, new_name: str) -> str:
        """
        Duplicate an arrangement with a new name.

        Creates a copy of an existing arrangement for variation or experimentation.

        Args:
            name: Original arrangement name
            new_name: Name for the duplicate

        Returns:
            JSON string with the new arrangement details

        Example:
            music_duplicate_arrangement(name="my-track", new_name="my-track-v2")
        """
        try:
            new_arrangement = await manager.duplicate(name, new_name)

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Created duplicate: {new_name}",
                    "arrangement": {
                        "name": new_arrangement.name,
                        "key": new_arrangement.context.key,
                        "tempo": new_arrangement.context.tempo,
                        "total_bars": new_arrangement.total_bars(),
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to duplicate arrangement")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_duplicate_arrangement"] = music_duplicate_arrangement

    return tools
