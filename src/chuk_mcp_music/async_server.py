#!/usr/bin/env python3
"""
Async Music MCP Server using chuk-mcp-server

This server provides MCP tools for creating and managing music arrangements.
It uses a pattern-based composition system inspired by shadcn/ui - you own
your patterns and can customize them.

The server provides tools for:
- Creating and managing arrangements (key, tempo, structure)
- Adding and arranging patterns across layers and sections
- Style-based constraints and pattern suggestions
- Compiling arrangements to MIDI files
- Pattern discovery and customization
"""

import logging
from pathlib import Path

from chuk_mcp_server import ChukMCPServer

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.patterns import PatternRegistry
from chuk_mcp_music.styles import StyleLoader
from chuk_mcp_music.tools import (
    register_arrangement_tools,
    register_compilation_tools,
    register_pattern_tools,
    register_structure_tools,
    register_style_tools,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp = ChukMCPServer("chuk-mcp-music")

# Paths - use standard project structure
BASE_PATH = Path.cwd()
ARRANGEMENTS_DIR = BASE_PATH / "arrangements"
PATTERNS_DIR = BASE_PATH / "patterns"
STYLES_DIR = BASE_PATH / "styles"
OUTPUT_DIR = BASE_PATH / "output"
LIBRARY_PATH = Path(__file__).parent / "patterns" / "library"
STYLES_LIBRARY_PATH = Path(__file__).parent / "styles" / "library"

# Create managers
arrangement_manager = ArrangementManager(ARRANGEMENTS_DIR)
pattern_registry = PatternRegistry(
    library_path=LIBRARY_PATH,
    project_path=PATTERNS_DIR,
)
style_loader = StyleLoader(
    library_path=STYLES_LIBRARY_PATH,
    project_path=STYLES_DIR,
)

# Register all tools
arrangement_tools = register_arrangement_tools(mcp, arrangement_manager)
structure_tools = register_structure_tools(mcp, arrangement_manager)
pattern_tools = register_pattern_tools(mcp, arrangement_manager, pattern_registry)
style_tools = register_style_tools(mcp, arrangement_manager, pattern_registry, style_loader)
compilation_tools = register_compilation_tools(
    mcp, arrangement_manager, pattern_registry, OUTPUT_DIR
)

# Export tool functions for direct access
music_create_arrangement = arrangement_tools["music_create_arrangement"]
music_get_arrangement = arrangement_tools["music_get_arrangement"]
music_list_arrangements = arrangement_tools["music_list_arrangements"]
music_save_arrangement = arrangement_tools["music_save_arrangement"]
music_delete_arrangement = arrangement_tools["music_delete_arrangement"]
music_duplicate_arrangement = arrangement_tools["music_duplicate_arrangement"]

music_add_section = structure_tools["music_add_section"]
music_remove_section = structure_tools["music_remove_section"]
music_reorder_sections = structure_tools["music_reorder_sections"]
music_set_section_energy = structure_tools["music_set_section_energy"]
music_add_layer = structure_tools["music_add_layer"]
music_remove_layer = structure_tools["music_remove_layer"]
music_arrange_layer = structure_tools["music_arrange_layer"]
music_mute_layer = structure_tools["music_mute_layer"]
music_solo_layer = structure_tools["music_solo_layer"]
music_set_layer_level = structure_tools["music_set_layer_level"]
music_set_harmony = structure_tools["music_set_harmony"]

music_list_patterns = pattern_tools["music_list_patterns"]
music_describe_pattern = pattern_tools["music_describe_pattern"]
music_add_pattern = pattern_tools["music_add_pattern"]
music_remove_pattern = pattern_tools["music_remove_pattern"]
music_update_pattern_params = pattern_tools["music_update_pattern_params"]
music_copy_pattern_to_project = pattern_tools["music_copy_pattern_to_project"]

music_compile_midi = compilation_tools["music_compile_midi"]
music_preview_section = compilation_tools["music_preview_section"]
music_export_yaml = compilation_tools["music_export_yaml"]
music_validate = compilation_tools["music_validate"]

music_list_styles = style_tools["music_list_styles"]
music_describe_style = style_tools["music_describe_style"]
music_suggest_patterns = style_tools["music_suggest_patterns"]
music_validate_style = style_tools["music_validate_style"]
music_apply_style = style_tools["music_apply_style"]
music_copy_style_to_project = style_tools["music_copy_style_to_project"]

logger.info("CHUK Music MCP Server initialized")
logger.info(f"  Library path: {LIBRARY_PATH}")
logger.info(f"  Arrangements dir: {ARRANGEMENTS_DIR}")
logger.info(f"  Output dir: {OUTPUT_DIR}")
