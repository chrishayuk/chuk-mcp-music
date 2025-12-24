"""
Style system - constraint bundles that narrow the solution space.

Styles don't force specific choices, they narrow what's appropriate.
They're like design tokens for genre/mood constraints.
"""

from chuk_mcp_music.styles.loader import StyleLoader
from chuk_mcp_music.styles.resolver import (
    PatternSuggestion,
    StyleResolver,
    StyleViolation,
    ViolationSeverity,
)

__all__ = [
    "PatternSuggestion",
    "StyleLoader",
    "StyleResolver",
    "StyleViolation",
    "ViolationSeverity",
]
