"""
Pitch primitives - PitchClass and Interval.

These are the foundational types for all pitch-related operations.
PitchClass represents the 12 chromatic pitches (octave-independent).
Interval represents the distance between pitches in semitones.
"""

from __future__ import annotations

from enum import IntEnum
from functools import total_ordering
from typing import ClassVar

# Display name mappings (module level to avoid IntEnum member issues)
_SHARP_NAMES: list[str] = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
]
_FLAT_NAMES: list[str] = [
    "C",
    "Db",
    "D",
    "Eb",
    "E",
    "F",
    "Gb",
    "G",
    "Ab",
    "A",
    "Bb",
    "B",
]


class PitchClass(IntEnum):
    """
    The 12 chromatic pitch classes (0-11).

    Octave-independent - C4 and C5 are both PitchClass.C.
    Enharmonic equivalents share the same value (C# == Db == 1).

    Spelling is a display concern, handled at serialization.
    Internally, we use sharp names (Cs, Ds, etc.).
    """

    C = 0
    Cs = 1  # C# / Db
    D = 2
    Ds = 3  # D# / Eb
    E = 4
    F = 5
    Fs = 6  # F# / Gb
    G = 7
    Gs = 8  # G# / Ab
    A = 9
    As = 10  # A# / Bb
    B = 11

    def transpose(self, semitones: int) -> PitchClass:
        """Transpose by a number of semitones (positive or negative)."""
        return PitchClass((self.value + semitones) % 12)

    def interval_to(self, other: PitchClass) -> Interval:
        """Get the interval from this pitch class to another (ascending)."""
        semitones = (other.value - self.value) % 12
        return Interval(semitones)

    def to_midi(self, octave: int = 4) -> int:
        """Convert to MIDI note number. C4 = 60."""
        return self.value + (octave + 1) * 12

    def spell(self, prefer_flats: bool = False) -> str:
        """Get human-readable name."""
        names = _FLAT_NAMES if prefer_flats else _SHARP_NAMES
        return names[self.value]

    @classmethod
    def from_midi(cls, midi_note: int) -> PitchClass:
        """Extract pitch class from MIDI note number."""
        return cls(midi_note % 12)

    @classmethod
    def parse(cls, name: str) -> PitchClass:
        """Parse a pitch class from a string like 'C', 'C#', 'Db'."""
        name = name.strip()

        # Try sharp names first
        if name in _SHARP_NAMES:
            return cls(_SHARP_NAMES.index(name))

        # Try flat names
        if name in _FLAT_NAMES:
            return cls(_FLAT_NAMES.index(name))

        # Try enum names (C, Cs, D, Ds, etc.)
        name_upper = name.upper()
        for member in cls:
            if member.name.upper() == name_upper:
                return member

        raise ValueError(f"Unknown pitch class: {name}")


@total_ordering
class Interval:
    """
    Distance between pitches in semitones.

    This is the fundamental building block - scales are interval patterns,
    chords are interval stacks, melodies are interval sequences.

    Immutable and hashable.
    """

    __slots__ = ("_semitones",)
    _semitones: int

    # Named intervals (class constants)
    UNISON: ClassVar[Interval]
    MINOR_SECOND: ClassVar[Interval]
    MAJOR_SECOND: ClassVar[Interval]
    MINOR_THIRD: ClassVar[Interval]
    MAJOR_THIRD: ClassVar[Interval]
    PERFECT_FOURTH: ClassVar[Interval]
    TRITONE: ClassVar[Interval]
    PERFECT_FIFTH: ClassVar[Interval]
    MINOR_SIXTH: ClassVar[Interval]
    MAJOR_SIXTH: ClassVar[Interval]
    MINOR_SEVENTH: ClassVar[Interval]
    MAJOR_SEVENTH: ClassVar[Interval]
    OCTAVE: ClassVar[Interval]

    # Short aliases
    P1: ClassVar[Interval]
    m2: ClassVar[Interval]
    M2: ClassVar[Interval]
    m3: ClassVar[Interval]
    M3: ClassVar[Interval]
    P4: ClassVar[Interval]
    TT: ClassVar[Interval]
    P5: ClassVar[Interval]
    m6: ClassVar[Interval]
    M6: ClassVar[Interval]
    m7: ClassVar[Interval]
    M7: ClassVar[Interval]
    P8: ClassVar[Interval]

    def __init__(self, semitones: int) -> None:
        """Create an interval with the given number of semitones."""
        object.__setattr__(self, "_semitones", semitones)

    @property
    def semitones(self) -> int:
        """Number of semitones in this interval."""
        return self._semitones

    def invert(self) -> Interval:
        """
        Invert the interval within an octave.

        M3 (4) -> m6 (8)
        P5 (7) -> P4 (5)
        """
        return Interval(12 - (self._semitones % 12))

    def __add__(self, other: Interval) -> Interval:
        """Add two intervals."""
        if not isinstance(other, Interval):
            return NotImplemented
        return Interval(self._semitones + other._semitones)

    def __sub__(self, other: Interval) -> Interval:
        """Subtract an interval from another."""
        if not isinstance(other, Interval):
            return NotImplemented
        return Interval(self._semitones - other._semitones)

    def __neg__(self) -> Interval:
        """Negate the interval (descending instead of ascending)."""
        return Interval(-self._semitones)

    def __mul__(self, n: int) -> Interval:
        """Multiply an interval (e.g., two octaves)."""
        if not isinstance(n, int):
            return NotImplemented
        return Interval(self._semitones * n)

    def __rmul__(self, n: int) -> Interval:
        """Right multiply."""
        return self.__mul__(n)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return bool(self._semitones == other._semitones)

    def __lt__(self, other: Interval) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return bool(self._semitones < other._semitones)

    def __hash__(self) -> int:
        return hash(self._semitones)

    def __repr__(self) -> str:
        # Try to find a named constant
        for name in [
            "UNISON",
            "MINOR_SECOND",
            "MAJOR_SECOND",
            "MINOR_THIRD",
            "MAJOR_THIRD",
            "PERFECT_FOURTH",
            "TRITONE",
            "PERFECT_FIFTH",
            "MINOR_SIXTH",
            "MAJOR_SIXTH",
            "MINOR_SEVENTH",
            "MAJOR_SEVENTH",
            "OCTAVE",
        ]:
            if hasattr(Interval, name):
                named = getattr(Interval, name)
                if isinstance(named, Interval) and named._semitones == self._semitones:
                    return f"Interval.{name}"
        return f"Interval({self._semitones})"

    def __str__(self) -> str:
        """Human-readable interval name."""
        names = {
            0: "P1",
            1: "m2",
            2: "M2",
            3: "m3",
            4: "M3",
            5: "P4",
            6: "TT",
            7: "P5",
            8: "m6",
            9: "M6",
            10: "m7",
            11: "M7",
            12: "P8",
        }
        mod = self._semitones % 12
        octaves = self._semitones // 12
        base = names.get(mod, f"{mod}st")
        if octaves == 0:
            return base
        elif octaves == 1 and mod == 0:
            return "P8"
        else:
            return f"{base}+{octaves}oct" if octaves > 0 else f"{base}{octaves}oct"


# Initialize class constants after class is defined
Interval.UNISON = Interval(0)
Interval.MINOR_SECOND = Interval(1)
Interval.MAJOR_SECOND = Interval(2)
Interval.MINOR_THIRD = Interval(3)
Interval.MAJOR_THIRD = Interval(4)
Interval.PERFECT_FOURTH = Interval(5)
Interval.TRITONE = Interval(6)
Interval.PERFECT_FIFTH = Interval(7)
Interval.MINOR_SIXTH = Interval(8)
Interval.MAJOR_SIXTH = Interval(9)
Interval.MINOR_SEVENTH = Interval(10)
Interval.MAJOR_SEVENTH = Interval(11)
Interval.OCTAVE = Interval(12)

# Short aliases
Interval.P1 = Interval.UNISON
Interval.m2 = Interval.MINOR_SECOND
Interval.M2 = Interval.MAJOR_SECOND
Interval.m3 = Interval.MINOR_THIRD
Interval.M3 = Interval.MAJOR_THIRD
Interval.P4 = Interval.PERFECT_FOURTH
Interval.TT = Interval.TRITONE
Interval.P5 = Interval.PERFECT_FIFTH
Interval.m6 = Interval.MINOR_SIXTH
Interval.M6 = Interval.MAJOR_SIXTH
Interval.m7 = Interval.MINOR_SEVENTH
Interval.M7 = Interval.MAJOR_SEVENTH
Interval.P8 = Interval.OCTAVE
