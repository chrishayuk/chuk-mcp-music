"""
Core music primitives - the Radix layer.

These are the mathematical invariants that everything else composes on:
- PitchClass: The 12 chromatic pitch classes (0-11)
- Interval: Distance between pitches in semitones
- ScaleDegree: Position in a scale (1-7)
- ScaleType: Interval pattern defining a scale
- Key: Root + scale type, resolves degrees to pitches
- ChordQuality: Interval stacks defining chord types
- Chord: Concrete chord with root and quality
- RomanNumeral: Key-independent chord references
- Duration: Note lengths as fractions
- TimeSignature: Beats per bar and beat unit
- BeatPosition: Position in musical time (bar + beat)
"""

from chuk_mcp_music.core.chord import Chord, ChordQuality, RomanNumeral, get_diatonic_chords
from chuk_mcp_music.core.pitch import Interval, PitchClass
from chuk_mcp_music.core.rhythm import BeatPosition, Duration, TimeSignature
from chuk_mcp_music.core.scale import Key, ScaleDegree, ScaleType

__all__ = [
    # Pitch
    "PitchClass",
    "Interval",
    # Scale
    "ScaleDegree",
    "ScaleType",
    "Key",
    # Chord
    "ChordQuality",
    "Chord",
    "RomanNumeral",
    "get_diatonic_chords",
    # Rhythm
    "Duration",
    "TimeSignature",
    "BeatPosition",
]
