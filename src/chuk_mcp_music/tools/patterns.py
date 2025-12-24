"""
Pattern tools - MCP tools for pattern discovery and assignment.

Tools for listing, describing, and assigning patterns to layers.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.models.arrangement import LayerRole, PatternRef
from chuk_mcp_music.patterns import PatternRegistry

if TYPE_CHECKING:
    from chuk_mcp_server import ChukMCPServer

logger = logging.getLogger(__name__)


def register_pattern_tools(
    mcp: ChukMCPServer,
    manager: ArrangementManager,
    registry: PatternRegistry,
) -> dict[str, Any]:
    """
    Register pattern management tools with the MCP server.

    Args:
        mcp: The MCP server instance
        manager: The arrangement manager
        registry: The pattern registry

    Returns:
        Dictionary of registered tool functions
    """
    tools: dict[str, Any] = {}

    @mcp.tool  # type: ignore[arg-type]
    async def music_list_patterns(
        role: str | None = None,
        style: str | None = None,
    ) -> str:
        """
        List available patterns.

        Returns patterns from the library, optionally filtered by role or style.

        Args:
            role: Optional filter by layer role ('drums', 'bass', 'harmony', 'melody', 'fx')
            style: Optional filter by compatible style

        Returns:
            JSON string with list of pattern summaries

        Example:
            music_list_patterns(role="bass")
        """
        try:
            role_enum = LayerRole(role) if role else None
            patterns = registry.list_patterns(role=role_enum, style=style)

            return json.dumps(
                {
                    "status": "success",
                    "patterns": [
                        {
                            "id": f"{p.role.value}/{p.name}",
                            "name": p.name,
                            "role": p.role.value,
                            "description": p.description,
                            "pitched": p.pitched,
                            "variants": p.variants,
                        }
                        for p in patterns
                    ],
                    "count": len(patterns),
                }
            )
        except Exception as e:
            logger.exception("Failed to list patterns")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_list_patterns"] = music_list_patterns

    @mcp.tool  # type: ignore[arg-type]
    async def music_describe_pattern(pattern_id: str) -> str:
        """
        Get detailed information about a pattern.

        Returns the pattern's parameters, variants, and template structure.

        Args:
            pattern_id: Pattern identifier (e.g., 'bass/root-pulse', 'drums/four-on-floor')

        Returns:
            JSON string with pattern details

        Example:
            music_describe_pattern(pattern_id="bass/root-pulse")
        """
        try:
            pattern = registry.get_pattern(pattern_id)
            if pattern is None:
                return json.dumps(
                    {"status": "error", "message": f"Pattern not found: {pattern_id}"}
                )

            return json.dumps(
                {
                    "status": "success",
                    "pattern": {
                        "id": pattern_id,
                        "name": pattern.name,
                        "role": pattern.role.value,
                        "description": pattern.description,
                        "version": pattern.version,
                        "pitched": pattern.pitched,
                        "parameters": {
                            name: {
                                "type": param.param_type.value,
                                "description": param.description,
                                "values": param.values,
                                "range": list(param.range) if param.range else None,
                                "default": param.default,
                            }
                            for name, param in pattern.parameters.items()
                        },
                        "variants": {
                            name: {
                                "description": variant.description,
                                "params": variant.params,
                            }
                            for name, variant in pattern.variants.items()
                        },
                        "template": {
                            "bars": pattern.template.bars,
                            "loop": pattern.template.loop,
                            "event_count": len(pattern.template.events),
                        },
                        "constraints": {
                            "requires_harmony": pattern.constraints.requires_harmony
                            if pattern.constraints
                            else True,
                            "compatible_styles": pattern.constraints.compatible_styles
                            if pattern.constraints
                            else None,
                        },
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to describe pattern")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_describe_pattern"] = music_describe_pattern

    @mcp.tool  # type: ignore[arg-type]
    async def music_add_pattern(
        arrangement: str,
        layer: str,
        pattern_id: str,
        alias: str | None = None,
        variant: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a pattern to a layer.

        Makes a pattern available for use in a layer. The pattern can then
        be assigned to sections using music_arrange_layer.

        Args:
            arrangement: Arrangement name
            layer: Layer name
            pattern_id: Pattern identifier (e.g., 'bass/root-pulse')
            alias: Optional alias for this pattern in the layer (defaults to pattern name)
            variant: Optional variant name to apply
            params: Optional parameter overrides

        Returns:
            JSON string with updated layer patterns

        Example:
            music_add_pattern(
                arrangement="my-track",
                layer="bass",
                pattern_id="bass/root-pulse",
                alias="main",
                variant="driving"
            )
        """
        try:
            # Verify pattern exists
            pattern = registry.get_pattern(pattern_id)
            if pattern is None:
                return json.dumps(
                    {"status": "error", "message": f"Pattern not found: {pattern_id}"}
                )

            # Get the arrangement
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            layer_obj = arr.get_layer(layer)
            if layer_obj is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {layer}"})

            # Determine alias
            pattern_alias = alias or pattern.name

            # Validate variant if specified
            if variant and pattern.variants and variant not in pattern.variants:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Unknown variant: {variant}. Available: {list(pattern.variants.keys())}",
                    }
                )

            # Validate params if specified
            if params:
                errors = pattern.validate_params(params)
                if errors:
                    return json.dumps({"status": "error", "message": f"Invalid params: {errors}"})

            # Add to layer
            layer_obj.patterns[pattern_alias] = PatternRef(
                ref=pattern_id,
                variant=variant,
                params=params or {},
            )

            return json.dumps(
                {
                    "status": "success",
                    "layer": layer,
                    "pattern_alias": pattern_alias,
                    "patterns": {
                        alias: {"ref": p.ref, "variant": p.variant}
                        for alias, p in layer_obj.patterns.items()
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to add pattern")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_add_pattern"] = music_add_pattern

    @mcp.tool  # type: ignore[arg-type]
    async def music_remove_pattern(
        arrangement: str,
        layer: str,
        alias: str,
    ) -> str:
        """
        Remove a pattern from a layer.

        Args:
            arrangement: Arrangement name
            layer: Layer name
            alias: Pattern alias to remove

        Returns:
            JSON string with updated layer patterns

        Example:
            music_remove_pattern(
                arrangement="my-track",
                layer="bass",
                alias="main"
            )
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            layer_obj = arr.get_layer(layer)
            if layer_obj is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {layer}"})

            if alias not in layer_obj.patterns:
                return json.dumps(
                    {"status": "error", "message": f"Pattern alias not found: {alias}"}
                )

            # Remove from patterns
            del layer_obj.patterns[alias]

            # Remove from arrangement references
            for section, pattern_alias in list(layer_obj.arrangement.items()):
                if pattern_alias == alias:
                    layer_obj.arrangement[section] = None

            return json.dumps(
                {
                    "status": "success",
                    "layer": layer,
                    "removed": alias,
                    "patterns": list(layer_obj.patterns.keys()),
                }
            )
        except Exception as e:
            logger.exception("Failed to remove pattern")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_remove_pattern"] = music_remove_pattern

    @mcp.tool  # type: ignore[arg-type]
    async def music_update_pattern_params(
        arrangement: str,
        layer: str,
        alias: str,
        variant: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Update pattern parameters or variant.

        Args:
            arrangement: Arrangement name
            layer: Layer name
            alias: Pattern alias
            variant: New variant to apply (or null to remove)
            params: New parameter overrides (merged with existing)

        Returns:
            JSON string with updated pattern

        Example:
            music_update_pattern_params(
                arrangement="my-track",
                layer="bass",
                alias="main",
                variant="dark",
                params={"velocity_base": 0.7}
            )
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            layer_obj = arr.get_layer(layer)
            if layer_obj is None:
                return json.dumps({"status": "error", "message": f"Layer not found: {layer}"})

            if alias not in layer_obj.patterns:
                return json.dumps(
                    {"status": "error", "message": f"Pattern alias not found: {alias}"}
                )

            pattern_ref = layer_obj.patterns[alias]

            # Merge params
            new_params = dict(pattern_ref.params)
            if params:
                new_params.update(params)

            # Create new PatternRef (frozen model)
            layer_obj.patterns[alias] = PatternRef(
                ref=pattern_ref.ref,
                variant=variant if variant is not None else pattern_ref.variant,
                params=new_params,
            )

            return json.dumps(
                {
                    "status": "success",
                    "layer": layer,
                    "pattern": {
                        "alias": alias,
                        "ref": layer_obj.patterns[alias].ref,
                        "variant": layer_obj.patterns[alias].variant,
                        "params": layer_obj.patterns[alias].params,
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to update pattern params")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_update_pattern_params"] = music_update_pattern_params

    @mcp.tool  # type: ignore[arg-type]
    async def music_copy_pattern_to_project(pattern_id: str) -> str:
        """
        Copy a library pattern to the project for customization.

        This is the "shadcn add" moment - the pattern becomes yours to modify.

        Args:
            pattern_id: Pattern identifier (e.g., 'bass/root-pulse')

        Returns:
            JSON string with path to copied pattern

        Example:
            music_copy_pattern_to_project(pattern_id="drums/four-on-floor")
        """
        try:
            path = registry.copy_to_project(pattern_id)
            if path is None:
                return json.dumps(
                    {"status": "error", "message": f"Pattern not found: {pattern_id}"}
                )

            return json.dumps(
                {
                    "status": "success",
                    "message": "Pattern copied to project",
                    "path": str(path),
                    "hint": "You can now customize this pattern by editing the YAML file",
                }
            )
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)})
        except Exception as e:
            logger.exception("Failed to copy pattern")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_copy_pattern_to_project"] = music_copy_pattern_to_project

    return tools
