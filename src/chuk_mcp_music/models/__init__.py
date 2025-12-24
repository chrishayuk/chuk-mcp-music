"""
Pydantic models for the music system.

This module provides:
- Arrangement: Complete composition model
- Layer: Track/stem in the composition
- Section: Structural segment
- PatternRef: Reference to a pattern with params
- Harmony: Chord progression configuration
"""

from chuk_mcp_music.models.arrangement import (
    Arrangement,
    ArrangementContext,
    EnergyLevel,
    Harmony,
    HarmonyProgression,
    Layer,
    LayerRole,
    PatternRef,
    Section,
)

__all__ = [
    "Arrangement",
    "ArrangementContext",
    "EnergyLevel",
    "Harmony",
    "HarmonyProgression",
    "Layer",
    "LayerRole",
    "PatternRef",
    "Section",
]
