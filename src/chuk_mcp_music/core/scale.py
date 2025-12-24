"""
Scale primitives - ScaleDegree, ScaleType, Key.

Scales are interval patterns from a root. Keys are scale types applied to a root pitch.
Scale degrees are relative positions (1-7) within a scale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .pitch import Interval, PitchClass


@dataclass(frozen=True)
class ScaleDegree:
    """
    A scale degree with optional alteration.

    Degree is 1-7 (tonic to leading tone).
    Alteration is semitones: -1 = flat, +1 = sharp, 0 = natural.

    Examples:
        ScaleDegree(1) = tonic
        ScaleDegree(5) = dominant
        ScaleDegree(7, -1) = flat 7 (minor seventh)
        ScaleDegree(4, +1) = raised 4 (lydian)
    """

    degree: int  # 1-7
    alteration: int = 0  # -1 = flat, +1 = sharp

    def __post_init__(self) -> None:
        if not 1 <= self.degree <= 7:
            raise ValueError(f"Degree must be 1-7, got {self.degree}")

    def __str__(self) -> str:
        if self.alteration == 0:
            return str(self.degree)
        elif self.alteration > 0:
            return f"#{self.degree}" if self.alteration == 1 else f"##{self.degree}"
        else:
            return f"b{self.degree}" if self.alteration == -1 else f"bb{self.degree}"

    def __repr__(self) -> str:
        if self.alteration == 0:
            return f"ScaleDegree({self.degree})"
        return f"ScaleDegree({self.degree}, {self.alteration})"


@dataclass(frozen=True)
class ScaleType:
    """
    A scale defined by its interval pattern.

    The intervals are from one degree to the next (not cumulative).
    A major scale is: W W H W W W H (2 2 1 2 2 2 1 semitones)

    Immutable and hashable.
    """

    intervals: tuple[Interval, ...]
    name: str = ""

    # Common scale types (defined after class)
    MAJOR: ClassVar[ScaleType]
    NATURAL_MINOR: ClassVar[ScaleType]
    HARMONIC_MINOR: ClassVar[ScaleType]
    MELODIC_MINOR: ClassVar[ScaleType]
    DORIAN: ClassVar[ScaleType]
    PHRYGIAN: ClassVar[ScaleType]
    LYDIAN: ClassVar[ScaleType]
    MIXOLYDIAN: ClassVar[ScaleType]
    LOCRIAN: ClassVar[ScaleType]

    def __post_init__(self) -> None:
        # Validate that intervals sum to an octave (12 semitones)
        total = sum(i.semitones for i in self.intervals)
        if total != 12:
            raise ValueError(f"Scale intervals must sum to 12 semitones, got {total}")

    def degree_to_semitones(self, degree: ScaleDegree) -> int:
        """
        Get semitones from root to a scale degree.

        Args:
            degree: The scale degree (1-7 with optional alteration)

        Returns:
            Semitones from the root
        """
        if degree.degree == 1:
            return degree.alteration

        # Sum intervals from root to degree-1
        semitones = sum(self.intervals[i].semitones for i in range(degree.degree - 1))
        return semitones + degree.alteration

    def get_pitches(self, root: PitchClass) -> list[PitchClass]:
        """
        Get all pitch classes in this scale starting from root.

        Returns 7 pitches (the octave is not included).
        """
        pitches = [root]
        current = root
        for interval in self.intervals[:-1]:  # Don't include last (octave return)
            current = current.transpose(interval.semitones)
            pitches.append(current)
        return pitches

    def __str__(self) -> str:
        return self.name or f"ScaleType({self.intervals})"

    def __repr__(self) -> str:
        if self.name:
            return f"ScaleType.{self.name.upper().replace(' ', '_')}"
        return f"ScaleType({self.intervals!r})"


# Define scale types using interval shorthand
_M2 = Interval(2)  # Major second (whole step)
_m2 = Interval(1)  # Minor second (half step)
_A2 = Interval(3)  # Augmented second

ScaleType.MAJOR = ScaleType((_M2, _M2, _m2, _M2, _M2, _M2, _m2), "major")
ScaleType.NATURAL_MINOR = ScaleType((_M2, _m2, _M2, _M2, _m2, _M2, _M2), "natural minor")
ScaleType.HARMONIC_MINOR = ScaleType((_M2, _m2, _M2, _M2, _m2, _A2, _m2), "harmonic minor")
ScaleType.MELODIC_MINOR = ScaleType((_M2, _m2, _M2, _M2, _M2, _M2, _m2), "melodic minor")
ScaleType.DORIAN = ScaleType((_M2, _m2, _M2, _M2, _M2, _m2, _M2), "dorian")
ScaleType.PHRYGIAN = ScaleType((_m2, _M2, _M2, _M2, _m2, _M2, _M2), "phrygian")
ScaleType.LYDIAN = ScaleType((_M2, _M2, _M2, _m2, _M2, _M2, _m2), "lydian")
ScaleType.MIXOLYDIAN = ScaleType((_M2, _M2, _m2, _M2, _M2, _m2, _M2), "mixolydian")
ScaleType.LOCRIAN = ScaleType((_m2, _M2, _M2, _m2, _M2, _M2, _M2), "locrian")


@dataclass(frozen=True)
class Key:
    """
    A key is a root pitch class plus a scale type.

    This is the context for resolving scale degrees to actual pitches.

    Examples:
        Key(PitchClass.C, ScaleType.MAJOR) = C major
        Key(PitchClass.D, ScaleType.NATURAL_MINOR) = D minor
    """

    root: PitchClass
    scale: ScaleType

    def degree_to_pitch(self, degree: ScaleDegree) -> PitchClass:
        """
        Resolve a scale degree to a pitch class.

        Args:
            degree: The scale degree (1-7 with optional alteration)

        Returns:
            The resolved pitch class
        """
        semitones = self.scale.degree_to_semitones(degree)
        return self.root.transpose(semitones)

    def degree_to_midi(self, degree: ScaleDegree, octave: int = 4) -> int:
        """
        Resolve a scale degree to a MIDI note number.

        Args:
            degree: The scale degree (1-7 with optional alteration)
            octave: The octave (default 4, where C4 = 60)

        Returns:
            MIDI note number
        """
        pitch = self.degree_to_pitch(degree)
        return pitch.to_midi(octave)

    def pitch_to_degree(self, pitch: PitchClass) -> ScaleDegree | None:
        """
        Get the scale degree for a pitch class, if it's in the scale.

        Returns None if the pitch is not in the scale (would need alteration).
        """
        pitches = self.scale.get_pitches(self.root)
        for i, p in enumerate(pitches):
            if p == pitch:
                return ScaleDegree(i + 1)
        return None

    def get_pitches(self) -> list[PitchClass]:
        """Get all pitch classes in this key."""
        return self.scale.get_pitches(self.root)

    def __str__(self) -> str:
        # Use conventional naming
        scale_suffix = ""
        if self.scale == ScaleType.MAJOR:
            scale_suffix = "major"
        elif self.scale == ScaleType.NATURAL_MINOR:
            scale_suffix = "minor"
        elif self.scale == ScaleType.HARMONIC_MINOR:
            scale_suffix = "harmonic minor"
        elif self.scale == ScaleType.MELODIC_MINOR:
            scale_suffix = "melodic minor"
        else:
            scale_suffix = str(self.scale)

        return f"{self.root.spell()} {scale_suffix}"

    def __repr__(self) -> str:
        return f"Key({self.root!r}, {self.scale!r})"

    @classmethod
    def parse(cls, name: str) -> Key:
        """
        Parse a key from a string like 'C_major', 'D_minor', 'F#_dorian'.

        Args:
            name: Key name with underscore separator

        Returns:
            Parsed Key object
        """
        parts = name.split("_")
        if len(parts) < 2:
            raise ValueError(f"Invalid key format: {name}. Expected 'root_scale' like 'C_major'")

        root_str = parts[0]
        scale_str = "_".join(parts[1:]).lower()

        root = PitchClass.parse(root_str)

        scale_map = {
            "major": ScaleType.MAJOR,
            "minor": ScaleType.NATURAL_MINOR,
            "natural_minor": ScaleType.NATURAL_MINOR,
            "harmonic_minor": ScaleType.HARMONIC_MINOR,
            "melodic_minor": ScaleType.MELODIC_MINOR,
            "dorian": ScaleType.DORIAN,
            "phrygian": ScaleType.PHRYGIAN,
            "lydian": ScaleType.LYDIAN,
            "mixolydian": ScaleType.MIXOLYDIAN,
            "locrian": ScaleType.LOCRIAN,
        }

        if scale_str not in scale_map:
            raise ValueError(f"Unknown scale type: {scale_str}")

        return cls(root, scale_map[scale_str])
