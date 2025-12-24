"""
Pattern system - the shadcn layer.

Patterns are copyable, ownable, modifiable templates.
They define musical building blocks with parameters and variants.
"""

from chuk_mcp_music.patterns.compiler import (
    CompileContext,
    HarmonyContext,
    PatternCompiler,
    compile_pattern,
)
from chuk_mcp_music.patterns.registry import PatternRegistry

__all__ = [
    "CompileContext",
    "HarmonyContext",
    "PatternCompiler",
    "PatternRegistry",
    "compile_pattern",
]
