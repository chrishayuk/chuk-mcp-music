"""
Rhythm primitives - Duration, TimeSignature, BeatPosition.

Time primitives for representing rhythmic values and positions.
Uses Fraction for exact subdivision representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import ClassVar


@dataclass(frozen=True)
class Duration:
    """
    A rhythmic duration expressed in beats.

    Uses Fraction for exact representation of subdivisions.
    A quarter note in 4/4 time is 1 beat (Fraction(1)).

    Immutable and hashable.
    """

    beats: Fraction

    # Common durations (defined after class)
    WHOLE: ClassVar[Duration]
    HALF: ClassVar[Duration]
    QUARTER: ClassVar[Duration]
    EIGHTH: ClassVar[Duration]
    SIXTEENTH: ClassVar[Duration]
    THIRTY_SECOND: ClassVar[Duration]

    # Dotted versions
    DOTTED_HALF: ClassVar[Duration]
    DOTTED_QUARTER: ClassVar[Duration]
    DOTTED_EIGHTH: ClassVar[Duration]

    # Triplets
    QUARTER_TRIPLET: ClassVar[Duration]
    EIGHTH_TRIPLET: ClassVar[Duration]
    SIXTEENTH_TRIPLET: ClassVar[Duration]

    def __post_init__(self) -> None:
        if self.beats <= 0:
            raise ValueError(f"Duration must be positive, got {self.beats}")

    def dotted(self) -> Duration:
        """Return a dotted version (1.5x length)."""
        return Duration(self.beats * Fraction(3, 2))

    def double_dotted(self) -> Duration:
        """Return a double-dotted version (1.75x length)."""
        return Duration(self.beats * Fraction(7, 4))

    def triplet(self) -> Duration:
        """Return a triplet version (2/3 length)."""
        return Duration(self.beats * Fraction(2, 3))

    def to_ticks(self, ticks_per_beat: int) -> int:
        """
        Convert to MIDI ticks.

        Args:
            ticks_per_beat: MIDI resolution (typically 480)

        Returns:
            Number of ticks
        """
        return int(self.beats * ticks_per_beat)

    def __add__(self, other: Duration) -> Duration:
        if not isinstance(other, Duration):
            return NotImplemented
        return Duration(self.beats + other.beats)

    def __sub__(self, other: Duration) -> Duration:
        if not isinstance(other, Duration):
            return NotImplemented
        result = self.beats - other.beats
        if result <= 0:
            raise ValueError("Duration subtraction resulted in non-positive value")
        return Duration(result)

    def __mul__(self, n: int | Fraction) -> Duration:
        if isinstance(n, (int, Fraction)):
            return Duration(self.beats * n)
        return NotImplemented

    def __rmul__(self, n: int | Fraction) -> Duration:
        return self.__mul__(n)

    def __truediv__(self, n: int) -> Duration:
        if not isinstance(n, int):
            return NotImplemented
        return Duration(self.beats / n)

    def __lt__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.beats < other.beats

    def __le__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.beats <= other.beats

    def __gt__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.beats > other.beats

    def __ge__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.beats >= other.beats

    def __str__(self) -> str:
        # Try to find a named constant
        name_map = {
            Fraction(4): "whole",
            Fraction(2): "half",
            Fraction(1): "quarter",
            Fraction(1, 2): "eighth",
            Fraction(1, 4): "sixteenth",
            Fraction(1, 8): "32nd",
            Fraction(3): "dotted half",
            Fraction(3, 2): "dotted quarter",
            Fraction(3, 4): "dotted eighth",
            Fraction(2, 3): "quarter triplet",
            Fraction(1, 3): "eighth triplet",
            Fraction(1, 6): "sixteenth triplet",
        }
        if self.beats in name_map:
            return name_map[self.beats]
        return f"{self.beats} beats"

    def __repr__(self) -> str:
        # Try to find a named constant
        for name in ["WHOLE", "HALF", "QUARTER", "EIGHTH", "SIXTEENTH", "THIRTY_SECOND"]:
            if hasattr(Duration, name):
                named = getattr(Duration, name)
                if isinstance(named, Duration) and named.beats == self.beats:
                    return f"Duration.{name}"
        return f"Duration(Fraction({self.beats.numerator}, {self.beats.denominator}))"


# Define common durations
Duration.WHOLE = Duration(Fraction(4))
Duration.HALF = Duration(Fraction(2))
Duration.QUARTER = Duration(Fraction(1))
Duration.EIGHTH = Duration(Fraction(1, 2))
Duration.SIXTEENTH = Duration(Fraction(1, 4))
Duration.THIRTY_SECOND = Duration(Fraction(1, 8))

# Dotted versions
Duration.DOTTED_HALF = Duration(Fraction(3))
Duration.DOTTED_QUARTER = Duration(Fraction(3, 2))
Duration.DOTTED_EIGHTH = Duration(Fraction(3, 4))

# Triplets
Duration.QUARTER_TRIPLET = Duration(Fraction(2, 3))
Duration.EIGHTH_TRIPLET = Duration(Fraction(1, 3))
Duration.SIXTEENTH_TRIPLET = Duration(Fraction(1, 6))


@dataclass(frozen=True)
class TimeSignature:
    """
    A time signature defining beats per bar and beat unit.

    Examples:
        TimeSignature(4, Duration.QUARTER) = 4/4
        TimeSignature(3, Duration.QUARTER) = 3/4
        TimeSignature(6, Duration.EIGHTH) = 6/8
    """

    beats_per_bar: int
    beat_unit: Duration

    # Common time signatures (defined after class)
    COMMON_TIME: ClassVar[TimeSignature]  # 4/4
    CUT_TIME: ClassVar[TimeSignature]  # 2/2
    WALTZ: ClassVar[TimeSignature]  # 3/4
    SIX_EIGHT: ClassVar[TimeSignature]  # 6/8

    def __post_init__(self) -> None:
        if self.beats_per_bar <= 0:
            raise ValueError(f"Beats per bar must be positive, got {self.beats_per_bar}")

    @property
    def bar_duration(self) -> Duration:
        """Total duration of one bar."""
        return Duration(self.beat_unit.beats * self.beats_per_bar)

    def bar_to_ticks(self, ticks_per_beat: int) -> int:
        """Get the number of ticks in one bar."""
        return self.bar_duration.to_ticks(ticks_per_beat)

    def __str__(self) -> str:
        # Convert beat unit to denominator
        denominator_map = {
            Fraction(4): 1,  # whole note
            Fraction(2): 2,  # half note
            Fraction(1): 4,  # quarter note
            Fraction(1, 2): 8,  # eighth note
            Fraction(1, 4): 16,  # sixteenth note
        }
        denominator = denominator_map.get(self.beat_unit.beats, "?")
        return f"{self.beats_per_bar}/{denominator}"

    def __repr__(self) -> str:
        return f"TimeSignature({self.beats_per_bar}, {self.beat_unit!r})"

    @classmethod
    def parse(cls, notation: str) -> TimeSignature:
        """
        Parse a time signature from notation like '4/4', '3/4', '6/8'.

        Args:
            notation: Time signature string

        Returns:
            TimeSignature object
        """
        parts = notation.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid time signature format: {notation}")

        beats_per_bar = int(parts[0])
        denominator = int(parts[1])

        # Convert denominator to beat unit
        beat_unit_map = {
            1: Duration.WHOLE,
            2: Duration.HALF,
            4: Duration.QUARTER,
            8: Duration.EIGHTH,
            16: Duration.SIXTEENTH,
        }

        if denominator not in beat_unit_map:
            raise ValueError(f"Unsupported time signature denominator: {denominator}")

        return cls(beats_per_bar, beat_unit_map[denominator])


# Define common time signatures
TimeSignature.COMMON_TIME = TimeSignature(4, Duration.QUARTER)
TimeSignature.CUT_TIME = TimeSignature(2, Duration.HALF)
TimeSignature.WALTZ = TimeSignature(3, Duration.QUARTER)
TimeSignature.SIX_EIGHT = TimeSignature(6, Duration.EIGHTH)


@dataclass(frozen=True)
class BeatPosition:
    """
    A position in musical time (bar + beat offset).

    Bar is 0-indexed (bar 0 is the first bar).
    Beat is the fractional position within the bar (0 = start of bar).

    Examples:
        BeatPosition(0, Fraction(0)) = start of first bar
        BeatPosition(0, Fraction(1)) = beat 2 of first bar (in 4/4)
        BeatPosition(1, Fraction(2, 3)) = bar 2, after 2/3 of a beat
    """

    bar: int
    beat: Fraction

    def __post_init__(self) -> None:
        if self.bar < 0:
            raise ValueError(f"Bar must be non-negative, got {self.bar}")
        if self.beat < 0:
            raise ValueError(f"Beat must be non-negative, got {self.beat}")

    def to_ticks(self, time_sig: TimeSignature, ticks_per_beat: int) -> int:
        """
        Convert to absolute tick position.

        Args:
            time_sig: Time signature for bar length calculation
            ticks_per_beat: MIDI resolution

        Returns:
            Absolute tick position
        """
        bar_ticks = time_sig.bar_to_ticks(ticks_per_beat)
        beat_ticks = int(self.beat * ticks_per_beat)
        return self.bar * bar_ticks + beat_ticks

    def to_beats(self, time_sig: TimeSignature) -> Fraction:
        """
        Convert to absolute beat position.

        Args:
            time_sig: Time signature

        Returns:
            Absolute beat number
        """
        return Fraction(self.bar * time_sig.beats_per_bar) + self.beat

    @classmethod
    def from_ticks(cls, ticks: int, time_sig: TimeSignature, ticks_per_beat: int) -> BeatPosition:
        """
        Create a BeatPosition from absolute tick position.

        Args:
            ticks: Absolute tick position
            time_sig: Time signature
            ticks_per_beat: MIDI resolution

        Returns:
            BeatPosition
        """
        bar_ticks = time_sig.bar_to_ticks(ticks_per_beat)
        bar = ticks // bar_ticks
        remaining_ticks = ticks % bar_ticks
        beat = Fraction(remaining_ticks, ticks_per_beat)
        return cls(bar, beat)

    @classmethod
    def from_beats(cls, beats: Fraction, time_sig: TimeSignature) -> BeatPosition:
        """
        Create a BeatPosition from absolute beat position.

        Args:
            beats: Absolute beat number
            time_sig: Time signature

        Returns:
            BeatPosition
        """
        bar = int(beats // time_sig.beats_per_bar)
        beat = beats % time_sig.beats_per_bar
        return cls(bar, beat)

    def add_duration(self, duration: Duration, time_sig: TimeSignature) -> BeatPosition:
        """
        Add a duration to this position.

        Args:
            duration: Duration to add
            time_sig: Time signature for bar wrapping

        Returns:
            New BeatPosition
        """
        total_beats = self.to_beats(time_sig) + duration.beats
        return BeatPosition.from_beats(total_beats, time_sig)

    def __add__(self, other: Duration) -> BeatPosition:
        # Can't add without time signature context
        # This would need to be done via add_duration
        raise TypeError("Use add_duration(duration, time_sig) to add a Duration to BeatPosition")

    def __lt__(self, other: BeatPosition) -> bool:
        if not isinstance(other, BeatPosition):
            return NotImplemented
        if self.bar != other.bar:
            return self.bar < other.bar
        return self.beat < other.beat

    def __le__(self, other: BeatPosition) -> bool:
        if not isinstance(other, BeatPosition):
            return NotImplemented
        return self < other or self == other

    def __gt__(self, other: BeatPosition) -> bool:
        if not isinstance(other, BeatPosition):
            return NotImplemented
        return other < self

    def __ge__(self, other: BeatPosition) -> bool:
        if not isinstance(other, BeatPosition):
            return NotImplemented
        return other <= self

    def __str__(self) -> str:
        if self.beat == 0:
            return f"bar {self.bar + 1}"  # Human-readable (1-indexed)
        return f"bar {self.bar + 1}, beat {float(self.beat) + 1:.2f}"

    def __repr__(self) -> str:
        if self.beat.denominator == 1:
            return f"BeatPosition({self.bar}, Fraction({int(self.beat)}))"
        return f"BeatPosition({self.bar}, Fraction({self.beat.numerator}, {self.beat.denominator}))"
