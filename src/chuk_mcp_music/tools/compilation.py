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

    @mcp.tool  # type: ignore[arg-type]
    async def music_emit_midi_from_ir(
        ir_json: str,
        output_name: str,
    ) -> str:
        """
        Emit a MIDI file directly from Score IR JSON.

        This enables the round-trip workflow:
        1. Compile arrangement to IR (music_compile_to_ir)
        2. Modify the IR (filter notes, adjust velocities, etc.)
        3. Emit MIDI from the modified IR (this tool)

        Args:
            ir_json: Score IR as JSON string (from music_compile_to_ir)
            output_name: Output filename (without .mid extension)

        Returns:
            JSON string with output file path

        Example:
            # Get IR, modify it externally, then emit
            ir = music_compile_to_ir(arrangement="my-track")
            # ... modify ir["score_ir"] ...
            music_emit_midi_from_ir(ir_json=modified_ir, output_name="modified")
        """
        try:
            from chuk_mcp_music.compiler.midi import score_ir_to_midi
            from chuk_mcp_music.compiler.score_ir import ScoreIR

            # Parse the IR
            score_ir = ScoreIR.from_json(ir_json)

            # Convert to MIDI
            midi_file = score_ir_to_midi(score_ir)

            # Save
            filename = f"{output_name}.mid"
            output_path = output_dir / filename
            output_dir.mkdir(parents=True, exist_ok=True)
            midi_file.save(str(output_path))

            return json.dumps(
                {
                    "status": "success",
                    "path": str(output_path),
                    "summary": score_ir.summary(),
                    "message": f"Emitted {score_ir.note_count()} notes to {filename}",
                }
            )
        except Exception as e:
            logger.exception("Failed to emit MIDI from IR")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_emit_midi_from_ir"] = music_emit_midi_from_ir

    @mcp.tool  # type: ignore[arg-type]
    async def music_modify_ir(
        ir_json: str,
        filter_layers: list[str] | None = None,
        exclude_layers: list[str] | None = None,
        filter_sections: list[str] | None = None,
        exclude_sections: list[str] | None = None,
        velocity_scale: float | None = None,
        transpose: int | None = None,
    ) -> str:
        """
        Filter and transform a Score IR.

        Modify an IR before emitting to MIDI. Useful for:
        - Extracting specific layers (stems)
        - Removing unwanted sections
        - Adjusting velocity (dynamics)
        - Transposing pitch

        Args:
            ir_json: Score IR as JSON string
            filter_layers: Keep only these layers (by name)
            exclude_layers: Remove these layers (by name)
            filter_sections: Keep only these sections (by name)
            exclude_sections: Remove these sections (by name)
            velocity_scale: Multiply all velocities by this factor (0.0-2.0)
            transpose: Transpose all pitches by this many semitones

        Returns:
            JSON string with modified Score IR

        Example:
            # Extract just the bass layer
            music_modify_ir(ir_json=ir, filter_layers=["bass"])

            # Remove drums and reduce velocity
            music_modify_ir(ir_json=ir, exclude_layers=["drums"], velocity_scale=0.8)

            # Transpose up an octave
            music_modify_ir(ir_json=ir, transpose=12)
        """
        try:
            from chuk_mcp_music.compiler.score_ir import IRNote, ScoreIR

            # Parse the IR
            score_ir = ScoreIR.from_json(ir_json)
            notes = list(score_ir.notes)

            # Filter by layers
            if filter_layers:
                notes = [n for n in notes if n.source_layer in filter_layers]
            if exclude_layers:
                notes = [n for n in notes if n.source_layer not in exclude_layers]

            # Filter by sections
            if filter_sections:
                notes = [n for n in notes if n.source_section in filter_sections]
            if exclude_sections:
                notes = [n for n in notes if n.source_section not in exclude_sections]

            # Transform velocity
            if velocity_scale is not None:
                scale = max(0.0, min(2.0, velocity_scale))
                notes = [
                    IRNote(
                        start_ticks=n.start_ticks,
                        channel=n.channel,
                        pitch=n.pitch,
                        duration_ticks=n.duration_ticks,
                        velocity=max(0, min(127, int(n.velocity * scale))),
                        source_layer=n.source_layer,
                        source_pattern=n.source_pattern,
                        source_section=n.source_section,
                        bar=n.bar,
                        beat=n.beat,
                    )
                    for n in notes
                ]

            # Transform pitch
            if transpose is not None:
                notes = [
                    IRNote(
                        start_ticks=n.start_ticks,
                        channel=n.channel,
                        pitch=max(0, min(127, n.pitch + transpose)),
                        duration_ticks=n.duration_ticks,
                        velocity=n.velocity,
                        source_layer=n.source_layer,
                        source_pattern=n.source_pattern,
                        source_section=n.source_section,
                        bar=n.bar,
                        beat=n.beat,
                    )
                    for n in notes
                ]

            # Build modified IR
            modified_ir = ScoreIR(
                schema=score_ir.schema,
                name=score_ir.name + "_modified",
                key=score_ir.key,
                tempo=score_ir.tempo,
                time_signature=score_ir.time_signature,
                ticks_per_beat=score_ir.ticks_per_beat,
                total_ticks=score_ir.total_ticks,
                total_bars=score_ir.total_bars,
                notes=notes,
                sections=score_ir.sections,
                tempo_events=score_ir.tempo_events,
                layers=score_ir.layers,
            ).canonicalize()

            return json.dumps(
                {
                    "status": "success",
                    "score_ir": modified_ir.to_dict(),
                    "summary": modified_ir.summary(),
                    "modifications": {
                        "filter_layers": filter_layers,
                        "exclude_layers": exclude_layers,
                        "filter_sections": filter_sections,
                        "exclude_sections": exclude_sections,
                        "velocity_scale": velocity_scale,
                        "transpose": transpose,
                    },
                }
            )
        except Exception as e:
            logger.exception("Failed to modify IR")
            return json.dumps({"status": "error", "message": str(e)})

    tools["music_modify_ir"] = music_modify_ir

    return tools
