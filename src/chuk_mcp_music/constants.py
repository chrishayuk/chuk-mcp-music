"""
Constants and enums for the music system.

No magic strings - use enums and Literal types for constrained values.
"""

from enum import Enum, IntEnum
from typing import Literal


class LayerRole(str, Enum):
    """
    Frequency/function hierarchy for layers.

    This is how producers think about arrangement.
    """

    SUB = "sub"  # Sub bass (20-60 Hz)
    BASS = "bass"  # Bass (60-250 Hz)
    DRUMS = "drums"  # Rhythm section
    HARMONY = "harmony"  # Chords, pads
    MELODY = "melody"  # Lead lines
    FX = "fx"  # Risers, impacts, ear candy
    VOCAL = "vocal"  # Voice


class GMDrumNote(IntEnum):
    """General MIDI drum note numbers."""

    KICK = 36
    KICK_2 = 35
    SNARE = 38
    SNARE_2 = 40
    CLAP = 39
    CLOSED_HIHAT = 42
    OPEN_HIHAT = 46
    PEDAL_HIHAT = 44
    RIDE = 51
    CRASH = 49
    TOM_LOW = 41
    TOM_MID = 47
    TOM_HIGH = 50


# Default MIDI channel assignments by role
DEFAULT_CHANNEL_MAP: dict[LayerRole, int] = {
    LayerRole.SUB: 0,
    LayerRole.BASS: 1,
    LayerRole.DRUMS: 9,  # GM drums
    LayerRole.HARMONY: 2,
    LayerRole.MELODY: 3,
    LayerRole.FX: 4,
    LayerRole.VOCAL: 5,
}

# Default MIDI register (octave range) by role
DEFAULT_REGISTER_MAP: dict[LayerRole, tuple[int, int]] = {
    LayerRole.SUB: (24, 36),  # C1-C2
    LayerRole.BASS: (36, 52),  # C2-E3
    LayerRole.DRUMS: (36, 84),  # GM drum range
    LayerRole.HARMONY: (48, 72),  # C3-C5
    LayerRole.MELODY: (60, 84),  # C4-C6
    LayerRole.FX: (0, 127),  # Unconstrained
    LayerRole.VOCAL: (48, 84),  # C3-C6
}

# Schema versions - frozen for v1
SchemaVersion = Literal[
    "project/v1",
    "arrangement/v1",
    "pattern/v1",
    "instance/v1",
    "events/v1",
    "harmony/v1",
    "style/v1",
    "operation/v1",
    "pattern-test/v1",
]

# Energy levels (semantic tokens)
EnergyLevel = Literal["minimal", "low", "medium", "high", "peak"]

# Density levels
DensityLevel = Literal["sparse", "moderate", "dense", "very_dense"]


class ErrorMessages:
    """Standardized error messages."""

    NO_ARRANGEMENT = "No arrangement found. Create one first."
    ARRANGEMENT_NOT_FOUND = "Arrangement '{name}' not found."
    PATTERN_NOT_FOUND = "Pattern '{pattern_id}' not found."
    LAYER_NOT_FOUND = "Layer '{layer}' not found in arrangement."
    SECTION_NOT_FOUND = "Section '{section}' not found in arrangement."
    INVALID_KEY = "Invalid key: '{key}'. Expected format like 'C_major' or 'D_minor'."
    INVALID_TEMPO = "Invalid tempo: {tempo}. Must be between 40 and 240 BPM."


class SuccessMessages:
    """Standardized success messages."""

    ARRANGEMENT_CREATED = "Created arrangement '{name}'."
    ARRANGEMENT_COMPILED = "Compiled arrangement '{name}' to {path}."
    PATTERN_ADDED = "Added pattern '{pattern_id}' to layer '{layer}'."
    SECTION_ADDED = "Added section '{section}' ({bars} bars)."
