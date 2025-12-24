"""
MCP tool implementations.

Tools are organized by domain:
- arrangement - Arrangement lifecycle
- structure - Sections, layer arrangement, harmony
- patterns - Pattern discovery and assignment
- styles - Style discovery and validation
- compilation - MIDI export tools
"""

from chuk_mcp_music.tools.arrangement import register_arrangement_tools
from chuk_mcp_music.tools.compilation import register_compilation_tools
from chuk_mcp_music.tools.patterns import register_pattern_tools
from chuk_mcp_music.tools.structure import register_structure_tools
from chuk_mcp_music.tools.styles import register_style_tools

__all__ = [
    "register_arrangement_tools",
    "register_compilation_tools",
    "register_pattern_tools",
    "register_structure_tools",
    "register_style_tools",
]
