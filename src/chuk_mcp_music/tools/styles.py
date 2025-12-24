"""
Style tools - MCP tools for style discovery and validation.

Tools for listing styles, getting style details, and validating
arrangements against style constraints.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.patterns import PatternRegistry
from chuk_mcp_music.styles import StyleLoader, StyleResolver

if TYPE_CHECKING:
    from chuk_mcp_server import ChukMCPServer

logger = logging.getLogger(__name__)


def register_style_tools(
    mcp: ChukMCPServer,
    manager: ArrangementManager,
    registry: PatternRegistry,
    style_loader: StyleLoader,
) -> dict[str, Any]:
    """
    Register style management tools with the MCP server.

    Args:
        mcp: The MCP server instance
        manager: The arrangement manager
        registry: The pattern registry
        style_loader: The style loader

    Returns:
        Dictionary of registered tool functions
    """
    tools: dict[str, Any] = {}

    @mcp.tool  # type: ignore[arg-type]
    async def music_list_styles() -> str:
        """
        List available styles.

        Returns all styles from the library and project with
        basic metadata.

        Returns:
            JSON string with list of style summaries

        Example:
            music_list_styles()
        """
        try:
            styles = style_loader.list_styles()

            return json.dumps(
                {
                    "status": "success",
                    "styles": [
                        {
                            "name": s.name,
                            "description": s.description,
                            "tempo_range": list(s.tempo_range),
                            "key_preference": s.key_preference.value,
                        }
                        for s in styles
                    ],
                    "count": len(styles),
                }
            )
        except Exception as e:
            logger.exception("Failed to list styles")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_list_styles"] = music_list_styles

    @mcp.tool  # type: ignore[arg-type]
    async def music_describe_style(name: str) -> str:
        """
        Get detailed information about a style.

        Returns the style's constraints, hints, and forbidden elements.

        Args:
            name: Style name

        Returns:
            JSON string with style details

        Example:
            music_describe_style(name="melodic-techno")
        """
        try:
            style = style_loader.get_style(name)
            if style is None:
                return json.dumps({"status": "error", "message": f"Style not found: {name}"})

            return json.dumps(
                {
                    "status": "success",
                    "style": {
                        "name": style.name,
                        "description": style.description,
                        "tempo": {
                            "min": style.tempo.min_bpm,
                            "max": style.tempo.max_bpm,
                            "default": style.tempo.default_bpm,
                        },
                        "key_preference": style.key_preference.value,
                        "time_signature": style.time_signature,
                        "energy_levels": {
                            "lowest": {
                                "layers": list(style.energy_mapping.lowest.layers),
                                "percussion": style.energy_mapping.lowest.percussion.value,
                            },
                            "low": {
                                "layers": list(style.energy_mapping.low.layers),
                                "percussion": style.energy_mapping.low.percussion.value,
                            },
                            "medium": {
                                "layers": list(style.energy_mapping.medium.layers),
                                "percussion": style.energy_mapping.medium.percussion.value,
                            },
                            "high": {
                                "layers": list(style.energy_mapping.high.layers),
                                "percussion": style.energy_mapping.high.percussion.value,
                            },
                            "highest": {
                                "layers": list(style.energy_mapping.highest.layers),
                                "percussion": style.energy_mapping.highest.percussion.value,
                            },
                        },
                        "layer_hints": {
                            role: {
                                "suggested": hint.suggested,
                                "avoid": hint.avoid,
                                "register": hint.pitch_register,
                            }
                            for role, hint in style.layer_hints.items()
                        },
                        "structure": {
                            "breakdown_required": style.structure_hints.breakdown_required,
                            "typical_bars": list(style.structure_hints.typical_length_bars),
                            "section_multiples": style.structure_hints.section_multiples,
                        },
                        "forbidden": {
                            "patterns": style.forbidden.patterns,
                            "progressions": style.forbidden.progressions,
                        },
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to describe style")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_describe_style"] = music_describe_style

    @mcp.tool  # type: ignore[arg-type]
    async def music_suggest_patterns(
        style: str,
        role: str,
        energy: str | None = None,
    ) -> str:
        """
        Get style-appropriate pattern suggestions for a role.

        Returns patterns ranked by how well they fit the style
        and energy level.

        Args:
            style: Style name
            role: Layer role ('drums', 'bass', 'harmony', 'melody', 'fx')
            energy: Optional energy level ('lowest', 'low', 'medium', 'high', 'highest')

        Returns:
            JSON string with ranked pattern suggestions

        Example:
            music_suggest_patterns(style="melodic-techno", role="bass", energy="medium")
        """
        try:
            style_obj = style_loader.get_style(style)
            if style_obj is None:
                return json.dumps({"status": "error", "message": f"Style not found: {style}"})

            role_enum = LayerRole(role)
            resolver = StyleResolver(style_obj)

            # Get all patterns for this role
            patterns = registry.list_patterns(role=role_enum)
            pattern_objs = [
                p
                for pid in [f"{role}/{pat.name}" for pat in patterns]
                if (p := registry.get_pattern(pid)) is not None
            ]

            # Actually load the patterns
            pattern_objs = []
            for pat_meta in patterns:
                pattern = registry.get_pattern(f"{role}/{pat_meta.name}")
                if pattern:
                    pattern_objs.append(pattern)

            suggestions = resolver.suggest_patterns(
                pattern_objs,
                role_enum,
                energy,
            )

            return json.dumps(
                {
                    "status": "success",
                    "suggestions": [
                        {
                            "pattern_id": s.pattern_id,
                            "score": s.score,
                            "reason": s.reason,
                        }
                        for s in suggestions
                    ],
                }
            )
        except Exception as e:
            logger.exception("Failed to suggest patterns")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_suggest_patterns"] = music_suggest_patterns

    @mcp.tool  # type: ignore[arg-type]
    async def music_validate_style(
        arrangement: str,
        style: str,
    ) -> str:
        """
        Validate an arrangement against a style's constraints.

        Checks tempo, patterns, and structure against style rules.
        Returns warnings and errors.

        Args:
            arrangement: Arrangement name
            style: Style name

        Returns:
            JSON string with validation results

        Example:
            music_validate_style(arrangement="my-track", style="melodic-techno")
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            style_obj = style_loader.get_style(style)
            if style_obj is None:
                return json.dumps({"status": "error", "message": f"Style not found: {style}"})

            resolver = StyleResolver(style_obj)
            all_violations = []

            # Validate tempo
            tempo_violations = resolver.validate_tempo(arr.context.tempo)
            all_violations.extend(tempo_violations)

            # Validate structure
            section_bars = {s.name: s.bars for s in arr.sections}
            has_breakdown = any(s.name == "breakdown" for s in arr.sections)
            structure_violations = resolver.validate_structure(section_bars, has_breakdown)
            all_violations.extend(structure_violations)

            # Validate patterns in each layer
            for _layer_name, layer in arr.layers.items():
                for _pattern_alias, pattern_ref in layer.patterns.items():
                    pattern = registry.get_pattern(pattern_ref.ref)
                    if pattern:
                        pattern_violations = resolver.validate_pattern(pattern, layer.role)
                        all_violations.extend(pattern_violations)

            # Separate errors and warnings
            errors = [v for v in all_violations if v.severity.value == "error"]
            warnings = [v for v in all_violations if v.severity.value == "warning"]

            return json.dumps(
                {
                    "status": "success",
                    "valid": len(errors) == 0,
                    "errors": [{"message": v.message, "element": v.element} for v in errors],
                    "warnings": [{"message": v.message, "element": v.element} for v in warnings],
                }
            )
        except Exception as e:
            logger.exception("Failed to validate style")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_validate_style"] = music_validate_style

    @mcp.tool  # type: ignore[arg-type]
    async def music_apply_style(
        arrangement: str,
        style: str,
    ) -> str:
        """
        Apply a style to an arrangement.

        Updates the arrangement's style reference and optionally
        adjusts tempo to fit within the style's range.

        Args:
            arrangement: Arrangement name
            style: Style name

        Returns:
            JSON string with updated arrangement

        Example:
            music_apply_style(arrangement="my-track", style="melodic-techno")
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            style_obj = style_loader.get_style(style)
            if style_obj is None:
                return json.dumps({"status": "error", "message": f"Style not found: {style}"})

            # Update style reference
            arr.context.style = style

            # Adjust tempo if out of range
            tempo_adjusted = False
            if not style_obj.validate_tempo(arr.context.tempo):
                arr.context.tempo = style_obj.tempo.default_bpm
                tempo_adjusted = True

            return json.dumps(
                {
                    "status": "success",
                    "arrangement": arrangement,
                    "style": style,
                    "tempo_adjusted": tempo_adjusted,
                    "tempo": arr.context.tempo,
                }
            )
        except Exception as e:
            logger.exception("Failed to apply style")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_apply_style"] = music_apply_style

    @mcp.tool  # type: ignore[arg-type]
    async def music_copy_style_to_project(name: str) -> str:
        """
        Copy a library style to the project for customization.

        Args:
            name: Style name

        Returns:
            JSON string with path to copied style

        Example:
            music_copy_style_to_project(name="melodic-techno")
        """
        try:
            path = style_loader.copy_to_project(name)
            if path is None:
                return json.dumps({"status": "error", "message": f"Style not found: {name}"})

            return json.dumps(
                {
                    "status": "success",
                    "message": "Style copied to project",
                    "path": str(path),
                    "hint": "You can now customize this style by editing the YAML file",
                }
            )
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)})
        except Exception as e:
            logger.exception("Failed to copy style")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_copy_style_to_project"] = music_copy_style_to_project

    return tools
