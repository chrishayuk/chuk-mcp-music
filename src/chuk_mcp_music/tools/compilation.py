"""
Compilation tools - MCP tools for MIDI export.

Tools for compiling arrangements to MIDI files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.compiler import ArrangementCompiler
from chuk_mcp_music.patterns import PatternRegistry

if TYPE_CHECKING:
    from chuk_mcp_server import ChukMCPServer

logger = logging.getLogger(__name__)


def register_compilation_tools(
    mcp: ChukMCPServer,
    manager: ArrangementManager,
    registry: PatternRegistry,
    output_dir: Path,
) -> dict[str, Any]:
    """
    Register compilation/export tools with the MCP server.

    Args:
        mcp: The MCP server instance
        manager: The arrangement manager
        registry: The pattern registry
        output_dir: Directory for output files

    Returns:
        Dictionary of registered tool functions
    """
    tools: dict[str, Any] = {}
    compiler = ArrangementCompiler(registry)

    @mcp.tool  # type: ignore[arg-type]
    async def music_compile_midi(
        arrangement: str,
        output_name: str | None = None,
    ) -> str:
        """
        Compile an arrangement to a MIDI file.

        Generates a complete MIDI file from the arrangement,
        ready to open in any DAW.

        Args:
            arrangement: Arrangement name
            output_name: Optional output filename (without .mid extension)

        Returns:
            JSON string with compilation result and file path

        Example:
            music_compile_midi(arrangement="my-track")
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            # Compile
            result = compiler.compile(arr)

            # Determine output path
            filename = f"{output_name or arrangement}.mid"
            output_path = output_dir / filename
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save
            result.midi_file.save(str(output_path))

            return json.dumps(
                {
                    "status": "success",
                    "path": str(output_path),
                    "compilation": {
                        "total_bars": result.total_bars,
                        "total_events": result.total_events,
                        "layers": result.layers_compiled,
                        "sections": result.sections_compiled,
                    },
                    "message": f"Compiled {result.total_bars} bars, {result.total_events} events",
                }
            )
        except Exception as e:
            logger.exception("Failed to compile MIDI")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_compile_midi"] = music_compile_midi

    @mcp.tool  # type: ignore[arg-type]
    async def music_preview_section(
        arrangement: str,
        section: str,
        output_name: str | None = None,
    ) -> str:
        """
        Compile a single section for preview.

        Generates a MIDI file for just one section, useful for
        quick iteration and testing.

        Args:
            arrangement: Arrangement name
            section: Section name to preview
            output_name: Optional output filename (without .mid extension)

        Returns:
            JSON string with compilation result and file path

        Example:
            music_preview_section(arrangement="my-track", section="chorus")
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            # Compile section
            result = compiler.compile_section(arr, section)

            # Determine output path
            filename = f"{output_name or f'{arrangement}_{section}'}.mid"
            output_path = output_dir / filename
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save
            result.midi_file.save(str(output_path))

            return json.dumps(
                {
                    "status": "success",
                    "path": str(output_path),
                    "section": section,
                    "compilation": {
                        "bars": result.total_bars,
                        "events": result.total_events,
                        "layers": result.layers_compiled,
                    },
                }
            )
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)})
        except Exception as e:
            logger.exception("Failed to preview section")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_preview_section"] = music_preview_section

    @mcp.tool  # type: ignore[arg-type]
    async def music_export_yaml(arrangement: str) -> str:
        """
        Export arrangement as YAML.

        Returns the arrangement in its canonical YAML format,
        suitable for version control or manual editing.

        Args:
            arrangement: Arrangement name

        Returns:
            JSON string containing the YAML content

        Example:
            music_export_yaml(arrangement="my-track")
        """
        try:
            import yaml

            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            yaml_dict = arr.to_yaml_dict()
            yaml_content = yaml.safe_dump(yaml_dict, default_flow_style=False, sort_keys=False)

            return json.dumps(
                {
                    "status": "success",
                    "yaml": yaml_content,
                }
            )
        except Exception as e:
            logger.exception("Failed to export YAML")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_export_yaml"] = music_export_yaml

    @mcp.tool  # type: ignore[arg-type]
    async def music_validate(arrangement: str) -> str:
        """
        Validate an arrangement's structure and constraints.

        Checks for issues like:
        - Invalid pattern references
        - Missing sections in layer arrangements
        - Channel conflicts
        - Style constraint violations

        Args:
            arrangement: Arrangement name

        Returns:
            JSON string with validation results

        Example:
            music_validate(arrangement="my-track")
        """
        try:
            from chuk_mcp_music.arrangement.validator import validate_arrangement

            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            result = validate_arrangement(arr)

            return json.dumps(
                {
                    "status": "success",
                    "valid": result.is_valid,
                    "errors": [
                        {"message": e.message, "severity": e.severity.value} for e in result.errors
                    ],
                    "warnings": [
                        {"message": w.message, "severity": w.severity.value}
                        for w in result.warnings
                    ],
                }
            )
        except Exception as e:
            logger.exception("Failed to validate arrangement")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_validate"] = music_validate

    @mcp.tool  # type: ignore[arg-type]
    async def music_compile_to_ir(
        arrangement: str,
        section: str | None = None,
        include_notes: bool = True,
    ) -> str:
        """
        Compile an arrangement to Score IR for inspection.

        Returns the intermediate representation before MIDI encoding.
        Useful for debugging, diffing, and understanding compilation.

        The Score IR is versioned (score_ir/v1) and canonicalized for
        deterministic output - the same arrangement always produces
        the same IR, making it ideal for golden-file testing.

        Args:
            arrangement: Arrangement name
            section: Optional section name (compile only that section)
            include_notes: Whether to include individual notes (default True)

        Returns:
            JSON string with Score IR

        Example:
            music_compile_to_ir(arrangement="my-track")
            music_compile_to_ir(arrangement="my-track", section="chorus")
            music_compile_to_ir(arrangement="my-track", include_notes=False)
        """
        try:
            arr = await manager.get(arrangement)
            if arr is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            # Compile to get Score IR
            result = compiler.compile_section(arr, section) if section else compiler.compile(arr)

            # Get the Score IR
            score_ir = result.score_ir

            # Build response
            ir_dict = score_ir.to_dict()

            # Optionally exclude notes for summary view
            if not include_notes:
                ir_dict["notes"] = []
                ir_dict["note_count"] = score_ir.note_count()

            return json.dumps(
                {
                    "status": "success",
                    "score_ir": ir_dict,
                    "summary": score_ir.summary(),
                }
            )
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)})
        except Exception as e:
            logger.exception("Failed to compile to IR")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_compile_to_ir"] = music_compile_to_ir

    @mcp.tool  # type: ignore[arg-type]
    async def music_diff_ir(
        arrangement: str,
        other_arrangement: str,
    ) -> str:
        """
        Compare the Score IR of two arrangements.

        Returns a summary of differences between two compiled arrangements.
        Useful for understanding what changed between versions.

        Args:
            arrangement: First arrangement name
            other_arrangement: Second arrangement name

        Returns:
            JSON string with diff summary

        Example:
            music_diff_ir(arrangement="track-v1", other_arrangement="track-v2")
        """
        try:
            arr1 = await manager.get(arrangement)
            if arr1 is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {arrangement}"}
                )

            arr2 = await manager.get(other_arrangement)
            if arr2 is None:
                return json.dumps(
                    {"status": "error", "message": f"Arrangement not found: {other_arrangement}"}
                )

            # Compile both
            result1 = compiler.compile(arr1)
            result2 = compiler.compile(arr2)

            # Get diff summary
            diff = result1.score_ir.diff_summary(result2.score_ir)

            return json.dumps(
                {
                    "status": "success",
                    "arrangement_a": arrangement,
                    "arrangement_b": other_arrangement,
                    "diff": diff,
                }
            )
        except Exception as e:
            logger.exception("Failed to diff arrangements")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_diff_ir"] = music_diff_ir

    return tools
