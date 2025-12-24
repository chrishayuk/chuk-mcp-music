"""
Chord primitives - ChordQuality, RomanNumeral, Chord.

Chords are stacks of intervals. Chord qualities define the interval pattern.
Roman numerals are key-independent chord references (the design token).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .pitch import Interval, PitchClass
from .scale import Key, ScaleDegree, ScaleType


@dataclass(frozen=True)
class ChordQuality:
    """
    A chord quality defined by its intervals from the root.

    Intervals are measured from the root, not stacked.
    For example, a major triad is root + M3 + P5 (0, 4, 7 semitones).

    Immutable and hashable.
    """

    intervals: frozenset[Interval]
    name: str = ""

    # Common chord qualities (defined after class)
    MAJOR: ClassVar[ChordQuality]
    MINOR: ClassVar[ChordQuality]
    DIMINISHED: ClassVar[ChordQuality]
    AUGMENTED: ClassVar[ChordQuality]
    MAJOR_7: ClassVar[ChordQuality]
    MINOR_7: ClassVar[ChordQuality]
    DOMINANT_7: ClassVar[ChordQuality]
    DIMINISHED_7: ClassVar[ChordQuality]
    HALF_DIMINISHED_7: ClassVar[ChordQuality]
    SUS2: ClassVar[ChordQuality]
    SUS4: ClassVar[ChordQuality]

    def get_pitches(self, root: PitchClass) -> list[PitchClass]:
        """
        Get all pitch classes in this chord.

        Args:
            root: The root pitch class

        Returns:
            List of pitch classes, sorted by interval
        """
        sorted_intervals = sorted(self.intervals, key=lambda i: i.semitones)
        return [root.transpose(interval.semitones) for interval in sorted_intervals]

    def get_midi_notes(self, root_midi: int) -> list[int]:
        """
        Get MIDI note numbers for this chord.

        Args:
            root_midi: MIDI note number for the root

        Returns:
            List of MIDI note numbers, sorted ascending
        """
        sorted_intervals = sorted(self.intervals, key=lambda i: i.semitones)
        return [root_midi + interval.semitones for interval in sorted_intervals]

    @property
    def root(self) -> Interval:
        """The root interval (always unison)."""
        return Interval.UNISON

    @property
    def third(self) -> Interval | None:
        """The third of the chord (if present)."""
        for interval in self.intervals:
            if interval.semitones in (3, 4):  # minor or major third
                return interval
        return None

    @property
    def fifth(self) -> Interval | None:
        """The fifth of the chord (if present)."""
        for interval in self.intervals:
            if interval.semitones in (6, 7, 8):  # dim, perfect, or aug fifth
                return interval
        return None

    @property
    def seventh(self) -> Interval | None:
        """The seventh of the chord (if present)."""
        for interval in self.intervals:
            if interval.semitones in (9, 10, 11):  # dim7, m7, M7
                return interval
        return None

    def __str__(self) -> str:
        return self.name or f"ChordQuality({self.intervals})"

    def __repr__(self) -> str:
        if self.name:
            return f"ChordQuality.{self.name.upper().replace(' ', '_')}"
        return f"ChordQuality({self.intervals!r})"


# Define chord qualities
ChordQuality.MAJOR = ChordQuality(
    frozenset({Interval.UNISON, Interval.MAJOR_THIRD, Interval.PERFECT_FIFTH}), "major"
)
ChordQuality.MINOR = ChordQuality(
    frozenset({Interval.UNISON, Interval.MINOR_THIRD, Interval.PERFECT_FIFTH}), "minor"
)
ChordQuality.DIMINISHED = ChordQuality(
    frozenset({Interval.UNISON, Interval.MINOR_THIRD, Interval.TRITONE}), "diminished"
)
ChordQuality.AUGMENTED = ChordQuality(
    frozenset({Interval.UNISON, Interval.MAJOR_THIRD, Interval.MINOR_SIXTH}), "augmented"
)
ChordQuality.MAJOR_7 = ChordQuality(
    frozenset(
        {Interval.UNISON, Interval.MAJOR_THIRD, Interval.PERFECT_FIFTH, Interval.MAJOR_SEVENTH}
    ),
    "major 7",
)
ChordQuality.MINOR_7 = ChordQuality(
    frozenset(
        {Interval.UNISON, Interval.MINOR_THIRD, Interval.PERFECT_FIFTH, Interval.MINOR_SEVENTH}
    ),
    "minor 7",
)
ChordQuality.DOMINANT_7 = ChordQuality(
    frozenset(
        {Interval.UNISON, Interval.MAJOR_THIRD, Interval.PERFECT_FIFTH, Interval.MINOR_SEVENTH}
    ),
    "dominant 7",
)
ChordQuality.DIMINISHED_7 = ChordQuality(
    frozenset({Interval.UNISON, Interval.MINOR_THIRD, Interval.TRITONE, Interval.MAJOR_SIXTH}),
    "diminished 7",
)
ChordQuality.HALF_DIMINISHED_7 = ChordQuality(
    frozenset({Interval.UNISON, Interval.MINOR_THIRD, Interval.TRITONE, Interval.MINOR_SEVENTH}),
    "half-diminished 7",
)
ChordQuality.SUS2 = ChordQuality(
    frozenset({Interval.UNISON, Interval.MAJOR_SECOND, Interval.PERFECT_FIFTH}), "sus2"
)
ChordQuality.SUS4 = ChordQuality(
    frozenset({Interval.UNISON, Interval.PERFECT_FOURTH, Interval.PERFECT_FIFTH}), "sus4"
)


@dataclass(frozen=True)
class Chord:
    """
    A concrete chord with a root pitch and quality.

    This is the resolved form - an actual chord that can be played.
    """

    root: PitchClass
    quality: ChordQuality
    bass: PitchClass | None = None  # For slash chords

    def get_pitches(self) -> list[PitchClass]:
        """Get all pitch classes in this chord."""
        return self.quality.get_pitches(self.root)

    def get_midi_notes(self, octave: int = 4) -> list[int]:
        """
        Get MIDI note numbers for this chord.

        Args:
            octave: Octave for the root (default 4)

        Returns:
            List of MIDI note numbers
        """
        root_midi = self.root.to_midi(octave)
        return self.quality.get_midi_notes(root_midi)

    def __str__(self) -> str:
        quality_suffix = ""
        if self.quality == ChordQuality.MAJOR:
            quality_suffix = ""
        elif self.quality == ChordQuality.MINOR:
            quality_suffix = "m"
        elif self.quality == ChordQuality.DIMINISHED:
            quality_suffix = "dim"
        elif self.quality == ChordQuality.AUGMENTED:
            quality_suffix = "aug"
        elif self.quality == ChordQuality.MAJOR_7:
            quality_suffix = "maj7"
        elif self.quality == ChordQuality.MINOR_7:
            quality_suffix = "m7"
        elif self.quality == ChordQuality.DOMINANT_7:
            quality_suffix = "7"
        elif self.quality == ChordQuality.DIMINISHED_7:
            quality_suffix = "dim7"
        elif self.quality == ChordQuality.HALF_DIMINISHED_7:
            quality_suffix = "m7b5"
        elif self.quality == ChordQuality.SUS2:
            quality_suffix = "sus2"
        elif self.quality == ChordQuality.SUS4:
            quality_suffix = "sus4"
        else:
            quality_suffix = str(self.quality)

        result = f"{self.root.spell()}{quality_suffix}"
        if self.bass and self.bass != self.root:
            result += f"/{self.bass.spell()}"
        return result


@dataclass(frozen=True)
class RomanNumeral:
    """
    A key-independent chord reference - the design token.

    Roman numerals represent chords relative to a key:
    - I, ii, iii, IV, V, vi, vii° in major
    - i, ii°, III, iv, v, VI, VII in minor

    This is how producers and theorists think about harmony.
    """

    degree: ScaleDegree
    quality: ChordQuality
    inversion: int = 0  # 0 = root, 1 = first, 2 = second, 3 = third (for 7ths)

    # Common Roman numerals (defined after class)
    # Major key
    I: ClassVar[RomanNumeral]  # noqa: E741
    ii: ClassVar[RomanNumeral]
    iii: ClassVar[RomanNumeral]
    IV: ClassVar[RomanNumeral]
    V: ClassVar[RomanNumeral]
    vi: ClassVar[RomanNumeral]
    vii_dim: ClassVar[RomanNumeral]
    V7: ClassVar[RomanNumeral]

    # Minor key
    i: ClassVar[RomanNumeral]
    ii_dim: ClassVar[RomanNumeral]
    III: ClassVar[RomanNumeral]
    iv: ClassVar[RomanNumeral]
    v: ClassVar[RomanNumeral]
    VI: ClassVar[RomanNumeral]
    VII: ClassVar[RomanNumeral]

    def resolve(self, key: Key) -> Chord:
        """
        Resolve this Roman numeral to a concrete chord in a key.

        Args:
            key: The key context

        Returns:
            A concrete Chord
        """
        root = key.degree_to_pitch(self.degree)

        # Handle inversions by setting bass note
        bass = None
        if self.inversion > 0:
            # Get the chord tones and select bass
            pitches = self.quality.get_pitches(root)
            if self.inversion < len(pitches):
                bass = pitches[self.inversion]

        return Chord(root, self.quality, bass)

    def __str__(self) -> str:
        # Build Roman numeral string
        numeral_map = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}
        base = numeral_map.get(self.degree.degree, str(self.degree.degree))

        # Alterations
        if self.degree.alteration < 0:
            base = "b" * abs(self.degree.alteration) + base
        elif self.degree.alteration > 0:
            base = "#" * self.degree.alteration + base

        # Case indicates quality
        if self.quality in (ChordQuality.MINOR, ChordQuality.DIMINISHED, ChordQuality.MINOR_7):
            base = base.lower()

        # Quality suffix
        if self.quality == ChordQuality.DIMINISHED:
            base += "°"
        elif self.quality == ChordQuality.AUGMENTED:
            base += "+"
        elif self.quality == ChordQuality.DOMINANT_7:
            base += "7"
        elif self.quality == ChordQuality.MAJOR_7:
            base += "Δ7"
        elif self.quality == ChordQuality.MINOR_7:
            base += "7"
        elif self.quality == ChordQuality.HALF_DIMINISHED_7:
            base += "ø7"
        elif self.quality == ChordQuality.DIMINISHED_7:
            base += "°7"

        # Inversion
        if self.inversion == 1:
            base += "6"
        elif self.inversion == 2:
            base += "64"
        elif self.inversion == 3:
            base += "42"

        return base

    @classmethod
    def parse(cls, symbol: str) -> RomanNumeral:
        """
        Parse a Roman numeral from a string like 'I', 'ii', 'V7', 'bVII'.

        This is a simplified parser for common cases.
        """
        symbol = symbol.strip()

        # Handle alterations
        alteration = 0
        while symbol.startswith("b"):
            alteration -= 1
            symbol = symbol[1:]
        while symbol.startswith("#"):
            alteration += 1
            symbol = symbol[1:]

        # Extract numeral and suffix
        numeral_chars = ""
        suffix = ""
        for i, char in enumerate(symbol):
            if char.upper() in "IV":
                numeral_chars += char
            else:
                suffix = symbol[i:]
                break
        else:
            numeral_chars = symbol
            suffix = ""

        # Parse numeral to degree
        numeral_upper = numeral_chars.upper()
        degree_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
        if numeral_upper not in degree_map:
            raise ValueError(f"Unknown Roman numeral: {numeral_chars}")

        degree = ScaleDegree(degree_map[numeral_upper], alteration)

        # Determine quality from case and suffix
        is_minor = numeral_chars.islower()

        if "°" in suffix or "dim" in suffix:
            quality = ChordQuality.DIMINISHED
        elif "+" in suffix or "aug" in suffix:
            quality = ChordQuality.AUGMENTED
        elif "7" in suffix:
            if "Δ" in suffix or "maj" in suffix:
                quality = ChordQuality.MAJOR_7
            elif "ø" in suffix:
                quality = ChordQuality.HALF_DIMINISHED_7
            elif is_minor:
                quality = ChordQuality.MINOR_7
            else:
                quality = ChordQuality.DOMINANT_7
        elif is_minor:
            quality = ChordQuality.MINOR
        else:
            quality = ChordQuality.MAJOR

        return cls(degree, quality)


# Define common Roman numerals

# Major key diatonic chords
RomanNumeral.I = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR)
RomanNumeral.ii = RomanNumeral(ScaleDegree(2), ChordQuality.MINOR)
RomanNumeral.iii = RomanNumeral(ScaleDegree(3), ChordQuality.MINOR)
RomanNumeral.IV = RomanNumeral(ScaleDegree(4), ChordQuality.MAJOR)
RomanNumeral.V = RomanNumeral(ScaleDegree(5), ChordQuality.MAJOR)
RomanNumeral.vi = RomanNumeral(ScaleDegree(6), ChordQuality.MINOR)
RomanNumeral.vii_dim = RomanNumeral(ScaleDegree(7), ChordQuality.DIMINISHED)
RomanNumeral.V7 = RomanNumeral(ScaleDegree(5), ChordQuality.DOMINANT_7)

# Minor key diatonic chords
RomanNumeral.i = RomanNumeral(ScaleDegree(1), ChordQuality.MINOR)
RomanNumeral.ii_dim = RomanNumeral(ScaleDegree(2), ChordQuality.DIMINISHED)
RomanNumeral.III = RomanNumeral(ScaleDegree(3), ChordQuality.MAJOR)
RomanNumeral.iv = RomanNumeral(ScaleDegree(4), ChordQuality.MINOR)
RomanNumeral.v = RomanNumeral(ScaleDegree(5), ChordQuality.MINOR)
RomanNumeral.VI = RomanNumeral(ScaleDegree(6), ChordQuality.MAJOR)
RomanNumeral.VII = RomanNumeral(ScaleDegree(7), ChordQuality.MAJOR)


def get_diatonic_chords(key: Key) -> list[tuple[str, Chord]]:
    """
    Get all diatonic chords for a key.

    Args:
        key: The key

    Returns:
        List of (roman numeral string, chord) tuples
    """
    if key.scale == ScaleType.MAJOR:
        numerals = [
            RomanNumeral.I,
            RomanNumeral.ii,
            RomanNumeral.iii,
            RomanNumeral.IV,
            RomanNumeral.V,
            RomanNumeral.vi,
            RomanNumeral.vii_dim,
        ]
    elif key.scale == ScaleType.NATURAL_MINOR:
        numerals = [
            RomanNumeral.i,
            RomanNumeral.ii_dim,
            RomanNumeral.III,
            RomanNumeral.iv,
            RomanNumeral.v,
            RomanNumeral.VI,
            RomanNumeral.VII,
        ]
    else:
        # For other scales, derive from scale degrees
        # This is simplified - proper implementation would analyze each degree
        numerals = [RomanNumeral(ScaleDegree(i + 1), ChordQuality.MAJOR) for i in range(7)]

    return [(str(numeral), numeral.resolve(key)) for numeral in numerals]
