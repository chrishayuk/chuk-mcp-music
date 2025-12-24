"""
Arrangement management - the producer mental model.

This module provides:
- ArrangementManager: Lifecycle management for arrangements
- ArrangementValidator: Structure and constraint validation
"""

from chuk_mcp_music.arrangement.manager import ArrangementManager, ArrangementMetadata
from chuk_mcp_music.arrangement.validator import (
    ArrangementValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_arrangement,
)

__all__ = [
    "ArrangementManager",
    "ArrangementMetadata",
    "ArrangementValidator",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "validate_arrangement",
]
