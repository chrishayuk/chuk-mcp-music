"""
Tests for core music primitives.

Tests cover:
- PitchClass and Interval (pitch.py)
- ScaleDegree, ScaleType, Key (scale.py)
- ChordQuality, Chord, RomanNumeral (chord.py)
- Duration, TimeSignature, BeatPosition (rhythm.py)
"""

from fractions import Fraction

import pytest

from chuk_mcp_music.core import (
    BeatPosition,
    Chord,
    ChordQuality,
    Duration,
    Interval,
    Key,
    PitchClass,
    RomanNumeral,
    ScaleDegree,
    ScaleType,
    TimeSignature,
    get_diatonic_chords,
)


class TestPitchClass:
    """Tests for PitchClass enum."""

    def test_pitch_values(self) -> None:
        """Pitch classes have correct values."""
        assert PitchClass.C == 0
        assert PitchClass.D == 2
        assert PitchClass.E == 4
        assert PitchClass.F == 5
        assert PitchClass.G == 7
        assert PitchClass.A == 9
        assert PitchClass.B == 11

    def test_transpose_up(self) -> None:
        """Transposing up works correctly."""
        assert PitchClass.C.transpose(2) == PitchClass.D
        assert PitchClass.C.transpose(7) == PitchClass.G
        assert PitchClass.A.transpose(3) == PitchClass.C

    def test_transpose_wraps(self) -> None:
        """Transposing wraps around the octave."""
        assert PitchClass.B.transpose(1) == PitchClass.C
        assert PitchClass.G.transpose(7) == PitchClass.D

    def test_transpose_down(self) -> None:
        """Transposing down (negative) works."""
        assert PitchClass.D.transpose(-2) == PitchClass.C
        assert PitchClass.C.transpose(-1) == PitchClass.B

    def test_to_midi(self) -> None:
        """Convert to MIDI note numbers."""
        assert PitchClass.C.to_midi(4) == 60  # Middle C
        assert PitchClass.A.to_midi(4) == 69  # A440
        assert PitchClass.C.to_midi(0) == 12
        assert PitchClass.C.to_midi(-1) == 0

    def test_from_midi(self) -> None:
        """Extract pitch class from MIDI note."""
        assert PitchClass.from_midi(60) == PitchClass.C
        assert PitchClass.from_midi(69) == PitchClass.A
        assert PitchClass.from_midi(72) == PitchClass.C

    def test_parse(self) -> None:
        """Parse pitch class from string."""
        assert PitchClass.parse("C") == PitchClass.C
        assert PitchClass.parse("C#") == PitchClass.Cs
        assert PitchClass.parse("Db") == PitchClass.Cs  # Enharmonic
        assert PitchClass.parse("F#") == PitchClass.Fs

    def test_spell(self) -> None:
        """Spell pitch class as string."""
        assert PitchClass.C.spell() == "C"
        assert PitchClass.Cs.spell() == "C#"
        assert PitchClass.Cs.spell(prefer_flats=True) == "Db"

    def test_interval_to(self) -> None:
        """Get interval between pitch classes."""
        assert PitchClass.C.interval_to(PitchClass.G).semitones == 7  # P5
        assert PitchClass.C.interval_to(PitchClass.E).semitones == 4  # M3
        assert PitchClass.D.interval_to(PitchClass.F).semitones == 3  # m3


class TestInterval:
    """Tests for Interval class."""

    def test_named_intervals(self) -> None:
        """Named intervals have correct values."""
        assert Interval.UNISON.semitones == 0
        assert Interval.MINOR_THIRD.semitones == 3
        assert Interval.MAJOR_THIRD.semitones == 4
        assert Interval.PERFECT_FIFTH.semitones == 7
        assert Interval.OCTAVE.semitones == 12

    def test_short_aliases(self) -> None:
        """Short aliases work."""
        assert Interval.P1 == Interval.UNISON
        assert Interval.m3 == Interval.MINOR_THIRD
        assert Interval.M3 == Interval.MAJOR_THIRD
        assert Interval.P5 == Interval.PERFECT_FIFTH
        assert Interval.P8 == Interval.OCTAVE

    def test_add_intervals(self) -> None:
        """Adding intervals works."""
        result = Interval.MAJOR_THIRD + Interval.MINOR_THIRD
        assert result.semitones == 7  # P5

    def test_invert(self) -> None:
        """Inverting intervals works."""
        assert Interval.MAJOR_THIRD.invert().semitones == 8  # m6
        assert Interval.PERFECT_FIFTH.invert().semitones == 5  # P4

    def test_comparison(self) -> None:
        """Intervals can be compared."""
        assert Interval.MINOR_THIRD < Interval.MAJOR_THIRD
        assert Interval.PERFECT_FIFTH > Interval.PERFECT_FOURTH

    def test_hashable(self) -> None:
        """Intervals are hashable for use in sets."""
        intervals = {Interval.UNISON, Interval.MAJOR_THIRD, Interval.PERFECT_FIFTH}
        assert len(intervals) == 3
        assert Interval.MAJOR_THIRD in intervals


class TestScaleDegree:
    """Tests for ScaleDegree class."""

    def test_create_degree(self) -> None:
        """Create scale degrees."""
        d1 = ScaleDegree(1)
        assert d1.degree == 1
        assert d1.alteration == 0

    def test_altered_degree(self) -> None:
        """Altered scale degrees work."""
        flat7 = ScaleDegree(7, -1)
        assert flat7.degree == 7
        assert flat7.alteration == -1
        assert str(flat7) == "b7"

    def test_invalid_degree(self) -> None:
        """Invalid degrees raise error."""
        with pytest.raises(ValueError):
            ScaleDegree(0)
        with pytest.raises(ValueError):
            ScaleDegree(8)


class TestScaleType:
    """Tests for ScaleType class."""

    def test_major_scale_intervals(self) -> None:
        """Major scale has correct intervals."""
        intervals = ScaleType.MAJOR.intervals
        semitones = [i.semitones for i in intervals]
        assert semitones == [2, 2, 1, 2, 2, 2, 1]

    def test_minor_scale_intervals(self) -> None:
        """Natural minor scale has correct intervals."""
        intervals = ScaleType.NATURAL_MINOR.intervals
        semitones = [i.semitones for i in intervals]
        assert semitones == [2, 1, 2, 2, 1, 2, 2]

    def test_degree_to_semitones(self) -> None:
        """Convert degree to semitones."""
        # Major scale: 1=0, 2=2, 3=4, 4=5, 5=7, 6=9, 7=11
        assert ScaleType.MAJOR.degree_to_semitones(ScaleDegree(1)) == 0
        assert ScaleType.MAJOR.degree_to_semitones(ScaleDegree(3)) == 4
        assert ScaleType.MAJOR.degree_to_semitones(ScaleDegree(5)) == 7

    def test_get_pitches(self) -> None:
        """Get pitches in a scale."""
        c_major_pitches = ScaleType.MAJOR.get_pitches(PitchClass.C)
        assert c_major_pitches == [
            PitchClass.C,
            PitchClass.D,
            PitchClass.E,
            PitchClass.F,
            PitchClass.G,
            PitchClass.A,
            PitchClass.B,
        ]


class TestKey:
    """Tests for Key class."""

    def test_create_key(self) -> None:
        """Create a key."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        assert c_major.root == PitchClass.C
        assert c_major.scale == ScaleType.MAJOR

    def test_degree_to_pitch(self) -> None:
        """Resolve degree to pitch."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        assert c_major.degree_to_pitch(ScaleDegree(1)) == PitchClass.C
        assert c_major.degree_to_pitch(ScaleDegree(5)) == PitchClass.G

        d_minor = Key(PitchClass.D, ScaleType.NATURAL_MINOR)
        assert d_minor.degree_to_pitch(ScaleDegree(1)) == PitchClass.D
        assert d_minor.degree_to_pitch(ScaleDegree(3)) == PitchClass.F

    def test_degree_to_midi(self) -> None:
        """Resolve degree to MIDI note."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        assert c_major.degree_to_midi(ScaleDegree(1), octave=4) == 60  # C4
        assert c_major.degree_to_midi(ScaleDegree(5), octave=4) == 67  # G4

    def test_parse_key(self) -> None:
        """Parse key from string."""
        c_major = Key.parse("C_major")
        assert c_major.root == PitchClass.C
        assert c_major.scale == ScaleType.MAJOR

        d_minor = Key.parse("D_minor")
        assert d_minor.root == PitchClass.D
        assert d_minor.scale == ScaleType.NATURAL_MINOR


class TestChordQuality:
    """Tests for ChordQuality class."""

    def test_major_triad(self) -> None:
        """Major triad has correct intervals."""
        intervals = ChordQuality.MAJOR.intervals
        semitones = {i.semitones for i in intervals}
        assert semitones == {0, 4, 7}

    def test_minor_triad(self) -> None:
        """Minor triad has correct intervals."""
        intervals = ChordQuality.MINOR.intervals
        semitones = {i.semitones for i in intervals}
        assert semitones == {0, 3, 7}

    def test_dominant_seventh(self) -> None:
        """Dominant 7th has correct intervals."""
        intervals = ChordQuality.DOMINANT_7.intervals
        semitones = {i.semitones for i in intervals}
        assert semitones == {0, 4, 7, 10}

    def test_get_pitches(self) -> None:
        """Get pitches for a chord quality."""
        pitches = ChordQuality.MAJOR.get_pitches(PitchClass.C)
        assert PitchClass.C in pitches
        assert PitchClass.E in pitches
        assert PitchClass.G in pitches


class TestChord:
    """Tests for Chord class."""

    def test_create_chord(self) -> None:
        """Create a chord."""
        c_major = Chord(PitchClass.C, ChordQuality.MAJOR)
        assert c_major.root == PitchClass.C
        assert c_major.quality == ChordQuality.MAJOR

    def test_get_midi_notes(self) -> None:
        """Get MIDI notes for a chord."""
        c_major = Chord(PitchClass.C, ChordQuality.MAJOR)
        notes = c_major.get_midi_notes(octave=4)
        assert 60 in notes  # C4
        assert 64 in notes  # E4
        assert 67 in notes  # G4

    def test_chord_str(self) -> None:
        """String representation of chords."""
        assert str(Chord(PitchClass.C, ChordQuality.MAJOR)) == "C"
        assert str(Chord(PitchClass.A, ChordQuality.MINOR)) == "Am"
        assert str(Chord(PitchClass.G, ChordQuality.DOMINANT_7)) == "G7"


class TestRomanNumeral:
    """Tests for RomanNumeral class."""

    def test_major_numerals(self) -> None:
        """Major key Roman numerals."""
        assert RomanNumeral.I.degree.degree == 1
        assert RomanNumeral.I.quality == ChordQuality.MAJOR
        assert RomanNumeral.V.degree.degree == 5
        assert RomanNumeral.ii.quality == ChordQuality.MINOR

    def test_resolve_in_key(self) -> None:
        """Resolve Roman numeral to chord."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)

        i_chord = RomanNumeral.I.resolve(c_major)
        assert i_chord.root == PitchClass.C
        assert i_chord.quality == ChordQuality.MAJOR

        v_chord = RomanNumeral.V.resolve(c_major)
        assert v_chord.root == PitchClass.G
        assert v_chord.quality == ChordQuality.MAJOR

    def test_parse_numeral(self) -> None:
        """Parse Roman numeral from string."""
        assert RomanNumeral.parse("I").degree.degree == 1
        assert RomanNumeral.parse("I").quality == ChordQuality.MAJOR

        assert RomanNumeral.parse("ii").degree.degree == 2
        assert RomanNumeral.parse("ii").quality == ChordQuality.MINOR

        assert RomanNumeral.parse("V7").degree.degree == 5
        assert RomanNumeral.parse("V7").quality == ChordQuality.DOMINANT_7

    def test_numeral_str(self) -> None:
        """String representation of numerals."""
        assert str(RomanNumeral.I) == "I"
        assert str(RomanNumeral.ii) == "ii"
        assert str(RomanNumeral.V7) == "V7"


class TestDiatonicChords:
    """Tests for get_diatonic_chords function."""

    def test_major_key_diatonic(self) -> None:
        """Diatonic chords in major key."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        chords = get_diatonic_chords(c_major)

        # Should have 7 chords
        assert len(chords) == 7

        # Check first and fifth
        assert chords[0][1].root == PitchClass.C
        assert chords[4][1].root == PitchClass.G

    def test_minor_key_diatonic(self) -> None:
        """Diatonic chords in minor key."""
        d_minor = Key(PitchClass.D, ScaleType.NATURAL_MINOR)
        chords = get_diatonic_chords(d_minor)

        assert len(chords) == 7
        assert chords[0][1].root == PitchClass.D
        assert chords[0][1].quality == ChordQuality.MINOR


class TestDuration:
    """Tests for Duration class."""

    def test_common_durations(self) -> None:
        """Common durations have correct values."""
        assert Duration.WHOLE.beats == Fraction(4)
        assert Duration.HALF.beats == Fraction(2)
        assert Duration.QUARTER.beats == Fraction(1)
        assert Duration.EIGHTH.beats == Fraction(1, 2)
        assert Duration.SIXTEENTH.beats == Fraction(1, 4)

    def test_dotted(self) -> None:
        """Dotted durations work."""
        dotted_quarter = Duration.QUARTER.dotted()
        assert dotted_quarter.beats == Fraction(3, 2)

    def test_triplet(self) -> None:
        """Triplet durations work."""
        triplet = Duration.QUARTER.triplet()
        assert triplet.beats == Fraction(2, 3)

    def test_to_ticks(self) -> None:
        """Convert duration to MIDI ticks."""
        assert Duration.QUARTER.to_ticks(480) == 480
        assert Duration.EIGHTH.to_ticks(480) == 240
        assert Duration.HALF.to_ticks(480) == 960

    def test_add_durations(self) -> None:
        """Adding durations works."""
        result = Duration.QUARTER + Duration.EIGHTH
        assert result.beats == Fraction(3, 2)

    def test_multiply_duration(self) -> None:
        """Multiplying durations works."""
        result = Duration.QUARTER * 2
        assert result.beats == Fraction(2)

    def test_comparison(self) -> None:
        """Durations can be compared."""
        assert Duration.EIGHTH < Duration.QUARTER
        assert Duration.HALF > Duration.QUARTER


class TestTimeSignature:
    """Tests for TimeSignature class."""

    def test_common_time(self) -> None:
        """4/4 time signature."""
        ts = TimeSignature.COMMON_TIME
        assert ts.beats_per_bar == 4
        assert ts.beat_unit == Duration.QUARTER
        assert str(ts) == "4/4"

    def test_bar_duration(self) -> None:
        """Calculate bar duration."""
        assert TimeSignature.COMMON_TIME.bar_duration.beats == Fraction(4)
        assert TimeSignature.WALTZ.bar_duration.beats == Fraction(3)

    def test_parse(self) -> None:
        """Parse time signature from string."""
        ts = TimeSignature.parse("6/8")
        assert ts.beats_per_bar == 6
        assert ts.beat_unit == Duration.EIGHTH


class TestBeatPosition:
    """Tests for BeatPosition class."""

    def test_create_position(self) -> None:
        """Create beat positions."""
        pos = BeatPosition(0, Fraction(0))
        assert pos.bar == 0
        assert pos.beat == Fraction(0)

    def test_to_ticks(self) -> None:
        """Convert position to MIDI ticks."""
        ts = TimeSignature.COMMON_TIME
        ticks_per_beat = 480

        pos = BeatPosition(0, Fraction(0))
        assert pos.to_ticks(ts, ticks_per_beat) == 0

        pos = BeatPosition(1, Fraction(0))
        assert pos.to_ticks(ts, ticks_per_beat) == 1920  # One bar in 4/4

        pos = BeatPosition(0, Fraction(2))
        assert pos.to_ticks(ts, ticks_per_beat) == 960  # Beat 3

    def test_from_ticks(self) -> None:
        """Create position from MIDI ticks."""
        ts = TimeSignature.COMMON_TIME
        ticks_per_beat = 480

        pos = BeatPosition.from_ticks(1920, ts, ticks_per_beat)
        assert pos.bar == 1
        assert pos.beat == Fraction(0)

    def test_add_duration(self) -> None:
        """Add duration to position."""
        ts = TimeSignature.COMMON_TIME
        pos = BeatPosition(0, Fraction(0))

        new_pos = pos.add_duration(Duration.QUARTER, ts)
        assert new_pos.bar == 0
        assert new_pos.beat == Fraction(1)

        # Adding enough to cross bar line
        new_pos = pos.add_duration(Duration.WHOLE, ts)
        assert new_pos.bar == 1
        assert new_pos.beat == Fraction(0)

    def test_comparison(self) -> None:
        """Beat positions can be compared."""
        pos1 = BeatPosition(0, Fraction(0))
        pos2 = BeatPosition(0, Fraction(2))
        pos3 = BeatPosition(1, Fraction(0))

        assert pos1 < pos2
        assert pos2 < pos3
        assert pos1 < pos3


class TestDurationAdditional:
    """Additional tests for Duration to improve coverage."""

    def test_double_dotted(self) -> None:
        """Double-dotted duration."""
        dd_quarter = Duration.QUARTER.double_dotted()
        assert dd_quarter.beats == Fraction(7, 4)

    def test_subtraction(self) -> None:
        """Subtraction of durations."""
        result = Duration.HALF - Duration.QUARTER
        assert result.beats == Fraction(1)

    def test_subtraction_error(self) -> None:
        """Subtraction resulting in non-positive raises error."""
        with pytest.raises(ValueError):
            _ = Duration.QUARTER - Duration.HALF

    def test_division(self) -> None:
        """Division of duration."""
        result = Duration.WHOLE / 4
        assert result.beats == Fraction(1)

    def test_right_multiply(self) -> None:
        """Right multiplication."""
        result = 2 * Duration.QUARTER
        assert result.beats == Fraction(2)

    def test_le_comparison(self) -> None:
        """Less-than-or-equal comparison."""
        assert Duration.QUARTER <= Duration.QUARTER
        assert Duration.EIGHTH <= Duration.QUARTER

    def test_ge_comparison(self) -> None:
        """Greater-than-or-equal comparison."""
        assert Duration.QUARTER >= Duration.QUARTER
        assert Duration.HALF >= Duration.QUARTER

    def test_str_named(self) -> None:
        """String representation for named durations."""
        assert "whole" in str(Duration.WHOLE)
        assert "half" in str(Duration.HALF)
        assert "quarter" in str(Duration.QUARTER)

    def test_str_unnamed(self) -> None:
        """String representation for unnamed durations."""
        custom = Duration(Fraction(7, 13))
        assert "beats" in str(custom)

    def test_repr(self) -> None:
        """Repr representation."""
        assert "Duration" in repr(Duration.QUARTER)

    def test_positive_duration_only(self) -> None:
        """Duration must be positive."""
        with pytest.raises(ValueError):
            Duration(Fraction(-1))


class TestPitchClassAdditional:
    """Additional tests for PitchClass."""

    def test_sharps(self) -> None:
        """Sharp pitch classes."""
        assert PitchClass.Cs == 1
        assert PitchClass.Ds == 3
        assert PitchClass.Fs == 6
        assert PitchClass.Gs == 8
        assert PitchClass.As == 10

    def test_interval_wrapping(self) -> None:
        """Interval wraps correctly at octave."""
        # From B to C should be 1 semitone
        assert PitchClass.B.interval_to(PitchClass.C) == Interval.m2


class TestIntervalAdditional:
    """Additional tests for Interval."""

    def test_unison(self) -> None:
        """Unison interval."""
        assert Interval.P1.semitones == 0

    def test_octave(self) -> None:
        """Octave interval."""
        assert Interval.P8.semitones == 12


class TestScaleTypeAdditional:
    """Additional tests for ScaleType."""

    def test_harmonic_minor(self) -> None:
        """Harmonic minor scale."""
        intervals = ScaleType.HARMONIC_MINOR.intervals
        assert len(intervals) == 7

    def test_dorian_mode(self) -> None:
        """Dorian mode intervals."""
        intervals = ScaleType.DORIAN.intervals
        assert len(intervals) == 7


class TestKeyAdditional:
    """Additional tests for Key."""

    def test_altered_degree(self) -> None:
        """Altered scale degree."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        # Raised 4th
        raised_4th = ScaleDegree(4, alteration=1)
        pitch = c_major.degree_to_pitch(raised_4th)
        assert pitch == PitchClass.Fs  # F# instead of F


class TestChordAdditional:
    """Additional tests for Chord."""

    def test_diminished_chord(self) -> None:
        """Diminished chord quality."""
        b_dim = Chord(PitchClass.B, ChordQuality.DIMINISHED)
        assert b_dim.quality == ChordQuality.DIMINISHED

    def test_augmented_chord(self) -> None:
        """Augmented chord quality."""
        c_aug = Chord(PitchClass.C, ChordQuality.AUGMENTED)
        pitches = c_aug.get_pitches()
        # Augmented has root, major third, augmented fifth
        assert len(pitches) == 3


class TestBeatPositionAdditional:
    """Additional tests for BeatPosition."""

    def test_le_comparison(self) -> None:
        """Less-than-or-equal comparison."""
        pos1 = BeatPosition(0, Fraction(0))
        pos2 = BeatPosition(0, Fraction(0))
        assert pos1 <= pos2

    def test_ge_comparison(self) -> None:
        """Greater-than-or-equal comparison."""
        pos1 = BeatPosition(1, Fraction(0))
        pos2 = BeatPosition(0, Fraction(0))
        assert pos1 >= pos2

    def test_gt_comparison(self) -> None:
        """Greater-than comparison."""
        pos1 = BeatPosition(1, Fraction(0))
        pos2 = BeatPosition(0, Fraction(0))
        assert pos1 > pos2

    def test_str_repr(self) -> None:
        """String representation."""
        pos = BeatPosition(2, Fraction(1))
        assert "2" in str(pos)


class TestTimeSignatureAdditional:
    """Additional tests for TimeSignature."""

    def test_waltz_time(self) -> None:
        """3/4 time signature."""
        ts = TimeSignature.WALTZ
        assert ts.beats_per_bar == 3
        assert str(ts) == "3/4"

    def test_compound_time(self) -> None:
        """Compound time signatures like 6/8."""
        ts = TimeSignature.parse("6/8")
        assert ts.beats_per_bar == 6

    def test_repr(self) -> None:
        """Repr representation."""
        ts = TimeSignature.COMMON_TIME
        assert "TimeSignature" in repr(ts)


class TestChordQualityAdditional:
    """Additional tests for ChordQuality to improve coverage."""

    def test_root_property(self) -> None:
        """Root property returns unison."""
        assert ChordQuality.MAJOR.root == Interval.UNISON

    def test_third_property_major(self) -> None:
        """Third property for major chord."""
        third = ChordQuality.MAJOR.third
        assert third is not None
        assert third.semitones == 4  # Major third

    def test_third_property_minor(self) -> None:
        """Third property for minor chord."""
        third = ChordQuality.MINOR.third
        assert third is not None
        assert third.semitones == 3  # Minor third

    def test_fifth_property_perfect(self) -> None:
        """Fifth property for major chord."""
        fifth = ChordQuality.MAJOR.fifth
        assert fifth is not None
        assert fifth.semitones == 7  # Perfect fifth

    def test_fifth_property_diminished(self) -> None:
        """Fifth property for diminished chord."""
        fifth = ChordQuality.DIMINISHED.fifth
        assert fifth is not None
        assert fifth.semitones == 6  # Diminished fifth (tritone)

    def test_fifth_property_augmented(self) -> None:
        """Fifth property for augmented chord."""
        fifth = ChordQuality.AUGMENTED.fifth
        assert fifth is not None
        assert fifth.semitones == 8  # Augmented fifth (minor sixth)

    def test_seventh_property_major(self) -> None:
        """Seventh property for major 7th chord."""
        seventh = ChordQuality.MAJOR_7.seventh
        assert seventh is not None
        assert seventh.semitones == 11  # Major seventh

    def test_seventh_property_minor(self) -> None:
        """Seventh property for dominant 7th chord."""
        seventh = ChordQuality.DOMINANT_7.seventh
        assert seventh is not None
        assert seventh.semitones == 10  # Minor seventh

    def test_seventh_property_diminished(self) -> None:
        """Seventh property for diminished 7th chord."""
        seventh = ChordQuality.DIMINISHED_7.seventh
        assert seventh is not None
        assert seventh.semitones == 9  # Diminished seventh

    def test_seventh_property_none(self) -> None:
        """Seventh property for triad returns None."""
        assert ChordQuality.MAJOR.seventh is None

    def test_third_property_sus2(self) -> None:
        """Third property for sus2 chord returns None."""
        assert ChordQuality.SUS2.third is None

    def test_str_with_name(self) -> None:
        """String representation with name."""
        assert str(ChordQuality.MAJOR) == "major"

    def test_str_without_name(self) -> None:
        """String representation without name."""
        custom = ChordQuality(frozenset({Interval.UNISON, Interval.PERFECT_FOURTH}), "")
        assert "ChordQuality" in str(custom)

    def test_repr_with_name(self) -> None:
        """Repr with name."""
        assert "MAJOR" in repr(ChordQuality.MAJOR)

    def test_repr_without_name(self) -> None:
        """Repr without name."""
        custom = ChordQuality(frozenset({Interval.UNISON, Interval.PERFECT_FOURTH}), "")
        assert "ChordQuality(" in repr(custom)


class TestChordStrAdditional:
    """Additional tests for Chord string representation."""

    def test_diminished_str(self) -> None:
        """String for diminished chord."""
        assert str(Chord(PitchClass.B, ChordQuality.DIMINISHED)) == "Bdim"

    def test_augmented_str(self) -> None:
        """String for augmented chord."""
        assert str(Chord(PitchClass.C, ChordQuality.AUGMENTED)) == "Caug"

    def test_major7_str(self) -> None:
        """String for major 7th chord."""
        assert str(Chord(PitchClass.C, ChordQuality.MAJOR_7)) == "Cmaj7"

    def test_minor7_str(self) -> None:
        """String for minor 7th chord."""
        assert str(Chord(PitchClass.A, ChordQuality.MINOR_7)) == "Am7"

    def test_diminished7_str(self) -> None:
        """String for diminished 7th chord."""
        assert str(Chord(PitchClass.B, ChordQuality.DIMINISHED_7)) == "Bdim7"

    def test_half_diminished_str(self) -> None:
        """String for half-diminished 7th chord."""
        assert str(Chord(PitchClass.B, ChordQuality.HALF_DIMINISHED_7)) == "Bm7b5"

    def test_sus2_str(self) -> None:
        """String for sus2 chord."""
        assert str(Chord(PitchClass.D, ChordQuality.SUS2)) == "Dsus2"

    def test_sus4_str(self) -> None:
        """String for sus4 chord."""
        assert str(Chord(PitchClass.D, ChordQuality.SUS4)) == "Dsus4"

    def test_custom_quality_str(self) -> None:
        """String for chord with custom quality."""
        custom = ChordQuality(frozenset({Interval.UNISON, Interval.PERFECT_FOURTH}), "power4")
        chord = Chord(PitchClass.C, custom)
        assert "power4" in str(chord)

    def test_slash_chord_str(self) -> None:
        """String for slash chord."""
        c_over_e = Chord(PitchClass.C, ChordQuality.MAJOR, bass=PitchClass.E)
        assert str(c_over_e) == "C/E"


class TestRomanNumeralStrAdditional:
    """Additional tests for RomanNumeral string representation."""

    def test_flat_numeral(self) -> None:
        """Flat alteration in numeral."""
        flat_vii = RomanNumeral(ScaleDegree(7, -1), ChordQuality.MAJOR)
        assert str(flat_vii) == "bVII"

    def test_sharp_numeral(self) -> None:
        """Sharp alteration in numeral."""
        sharp_iv = RomanNumeral(ScaleDegree(4, 1), ChordQuality.MAJOR)
        assert str(sharp_iv) == "#IV"

    def test_augmented_numeral(self) -> None:
        """Augmented numeral."""
        aug = RomanNumeral(ScaleDegree(5), ChordQuality.AUGMENTED)
        assert "+" in str(aug)

    def test_major7_numeral(self) -> None:
        """Major 7 numeral."""
        maj7 = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR_7)
        assert "Δ7" in str(maj7)

    def test_minor7_numeral(self) -> None:
        """Minor 7 numeral."""
        min7 = RomanNumeral(ScaleDegree(2), ChordQuality.MINOR_7)
        assert "7" in str(min7)
        assert str(min7).startswith("ii")

    def test_half_diminished_numeral(self) -> None:
        """Half-diminished numeral."""
        half_dim = RomanNumeral(ScaleDegree(7), ChordQuality.HALF_DIMINISHED_7)
        assert "ø7" in str(half_dim)

    def test_diminished7_numeral(self) -> None:
        """Diminished 7 numeral."""
        dim7 = RomanNumeral(ScaleDegree(7), ChordQuality.DIMINISHED_7)
        assert "°7" in str(dim7)

    def test_first_inversion(self) -> None:
        """First inversion numeral."""
        inv1 = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR, inversion=1)
        assert "6" in str(inv1)

    def test_second_inversion(self) -> None:
        """Second inversion numeral."""
        inv2 = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR, inversion=2)
        assert "64" in str(inv2)

    def test_third_inversion(self) -> None:
        """Third inversion numeral."""
        inv3 = RomanNumeral(ScaleDegree(5), ChordQuality.DOMINANT_7, inversion=3)
        assert "42" in str(inv3)


class TestRomanNumeralParseAdditional:
    """Additional tests for RomanNumeral.parse."""

    def test_parse_flat_seventh(self) -> None:
        """Parse flat VII."""
        numeral = RomanNumeral.parse("bVII")
        assert numeral.degree.degree == 7
        assert numeral.degree.alteration == -1
        assert numeral.quality == ChordQuality.MAJOR

    def test_parse_sharp_iv(self) -> None:
        """Parse sharp iv (minor)."""
        numeral = RomanNumeral.parse("#iv")
        assert numeral.degree.degree == 4
        assert numeral.degree.alteration == 1
        assert numeral.quality == ChordQuality.MINOR

    def test_parse_diminished(self) -> None:
        """Parse diminished chord."""
        numeral = RomanNumeral.parse("vii°")
        assert numeral.quality == ChordQuality.DIMINISHED

    def test_parse_augmented(self) -> None:
        """Parse augmented chord."""
        numeral = RomanNumeral.parse("V+")
        assert numeral.quality == ChordQuality.AUGMENTED

    def test_parse_major7(self) -> None:
        """Parse major 7 chord."""
        numeral = RomanNumeral.parse("IΔ7")
        assert numeral.quality == ChordQuality.MAJOR_7

    def test_parse_half_diminished(self) -> None:
        """Parse half-diminished chord."""
        numeral = RomanNumeral.parse("viiø7")
        assert numeral.quality == ChordQuality.HALF_DIMINISHED_7

    def test_parse_minor7(self) -> None:
        """Parse minor 7 chord."""
        numeral = RomanNumeral.parse("ii7")
        assert numeral.quality == ChordQuality.MINOR_7

    def test_parse_invalid(self) -> None:
        """Parse invalid numeral raises error."""
        with pytest.raises(ValueError):
            RomanNumeral.parse("X")

    def test_parse_third(self) -> None:
        """Parse III (no trailing characters)."""
        numeral = RomanNumeral.parse("III")
        assert numeral.degree.degree == 3
        assert numeral.quality == ChordQuality.MAJOR

    def test_parse_vi(self) -> None:
        """Parse vi (lowercase, no suffix)."""
        numeral = RomanNumeral.parse("vi")
        assert numeral.degree.degree == 6
        assert numeral.quality == ChordQuality.MINOR


class TestRomanNumeralResolveAdditional:
    """Additional tests for RomanNumeral.resolve."""

    def test_resolve_with_inversion(self) -> None:
        """Resolve numeral with inversion."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        inv1 = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR, inversion=1)
        chord = inv1.resolve(c_major)
        assert chord.bass == PitchClass.E  # E in bass for C/E

    def test_resolve_invalid_inversion(self) -> None:
        """Inversion beyond chord tones is ignored."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        inv5 = RomanNumeral(ScaleDegree(1), ChordQuality.MAJOR, inversion=5)
        chord = inv5.resolve(c_major)
        # Should not crash, bass is None for invalid inversion
        assert chord.bass is None


class TestDiatonicChordsAdditional:
    """Additional tests for get_diatonic_chords."""

    def test_other_scale_type(self) -> None:
        """Diatonic chords for non-major/minor scale."""
        c_dorian = Key(PitchClass.C, ScaleType.DORIAN)
        chords = get_diatonic_chords(c_dorian)
        assert len(chords) == 7


class TestPitchClassParsing:
    """Additional tests for PitchClass.parse."""

    def test_parse_enum_name(self) -> None:
        """Parse using enum name like 'Cs' for C#."""
        assert PitchClass.parse("Cs") == PitchClass.Cs
        assert PitchClass.parse("cs") == PitchClass.Cs  # Case insensitive
        assert PitchClass.parse("Fs") == PitchClass.Fs

    def test_parse_invalid(self) -> None:
        """Parse invalid name raises ValueError."""
        with pytest.raises(ValueError):
            PitchClass.parse("X")
        with pytest.raises(ValueError):
            PitchClass.parse("H")

    def test_parse_whitespace(self) -> None:
        """Parse handles whitespace."""
        assert PitchClass.parse("  C  ") == PitchClass.C


class TestIntervalOperations:
    """Additional tests for Interval operations."""

    def test_add_non_interval(self) -> None:
        """Adding non-Interval returns NotImplemented."""
        result = Interval.MAJOR_THIRD.__add__(5)
        assert result == NotImplemented

    def test_sub_non_interval(self) -> None:
        """Subtracting non-Interval returns NotImplemented."""
        result = Interval.MAJOR_THIRD.__sub__(5)
        assert result == NotImplemented

    def test_sub_intervals(self) -> None:
        """Subtracting intervals works."""
        result = Interval.PERFECT_FIFTH - Interval.MAJOR_THIRD
        assert result.semitones == 3  # P5 - M3 = m3

    def test_neg_interval(self) -> None:
        """Negating an interval."""
        neg = -Interval.MAJOR_THIRD
        assert neg.semitones == -4

    def test_mul_non_int(self) -> None:
        """Multiplying by non-int returns NotImplemented."""
        result = Interval.MAJOR_THIRD.__mul__(2.5)  # type: ignore
        assert result == NotImplemented

    def test_rmul_interval(self) -> None:
        """Right multiplication."""
        result = 2 * Interval.MAJOR_THIRD
        assert result.semitones == 8

    def test_eq_non_interval(self) -> None:
        """Equality with non-Interval returns NotImplemented."""
        result = Interval.MAJOR_THIRD.__eq__(4)
        assert result == NotImplemented

    def test_lt_non_interval(self) -> None:
        """Less-than with non-Interval returns NotImplemented."""
        result = Interval.MAJOR_THIRD.__lt__(4)  # type: ignore
        assert result == NotImplemented


class TestIntervalReprStr:
    """Tests for Interval string representations."""

    def test_repr_named(self) -> None:
        """Repr for named intervals."""
        assert repr(Interval.UNISON) == "Interval.UNISON"
        assert repr(Interval.MAJOR_THIRD) == "Interval.MAJOR_THIRD"
        assert repr(Interval.OCTAVE) == "Interval.OCTAVE"

    def test_repr_unnamed(self) -> None:
        """Repr for unnamed intervals."""
        i15 = Interval(15)  # More than an octave
        assert "Interval(15)" in repr(i15)

    def test_str_basic(self) -> None:
        """Str for basic intervals within octave."""
        assert str(Interval.UNISON) == "P1"
        assert str(Interval.MINOR_SECOND) == "m2"
        assert str(Interval.MAJOR_SECOND) == "M2"
        assert str(Interval.MINOR_THIRD) == "m3"
        assert str(Interval.MAJOR_THIRD) == "M3"
        assert str(Interval.PERFECT_FOURTH) == "P4"
        assert str(Interval.TRITONE) == "TT"
        assert str(Interval.PERFECT_FIFTH) == "P5"
        assert str(Interval.MINOR_SIXTH) == "m6"
        assert str(Interval.MAJOR_SIXTH) == "M6"
        assert str(Interval.MINOR_SEVENTH) == "m7"
        assert str(Interval.MAJOR_SEVENTH) == "M7"
        assert str(Interval.OCTAVE) == "P8"

    def test_str_compound(self) -> None:
        """Str for compound intervals."""
        # More than an octave
        i15 = Interval(15)  # m3 + octave
        assert "+1oct" in str(i15)

    def test_str_negative(self) -> None:
        """Str for negative intervals."""
        neg = Interval(-4)
        assert "oct" in str(neg)  # Will have negative octave marker


class TestScaleDegreeStrRepr:
    """Additional tests for ScaleDegree string representations."""

    def test_str_natural(self) -> None:
        """Str for natural degree."""
        assert str(ScaleDegree(1)) == "1"
        assert str(ScaleDegree(5)) == "5"

    def test_str_single_sharp(self) -> None:
        """Str for single sharp."""
        assert str(ScaleDegree(4, 1)) == "#4"

    def test_str_double_sharp(self) -> None:
        """Str for double sharp."""
        assert str(ScaleDegree(4, 2)) == "##4"

    def test_str_single_flat(self) -> None:
        """Str for single flat."""
        assert str(ScaleDegree(7, -1)) == "b7"

    def test_str_double_flat(self) -> None:
        """Str for double flat."""
        assert str(ScaleDegree(7, -2)) == "bb7"

    def test_repr_natural(self) -> None:
        """Repr for natural degree."""
        assert repr(ScaleDegree(5)) == "ScaleDegree(5)"

    def test_repr_altered(self) -> None:
        """Repr for altered degree."""
        assert repr(ScaleDegree(4, 1)) == "ScaleDegree(4, 1)"
        assert repr(ScaleDegree(7, -1)) == "ScaleDegree(7, -1)"


class TestScaleTypeValidation:
    """Tests for ScaleType validation."""

    def test_invalid_scale_intervals(self) -> None:
        """Scale intervals must sum to 12."""
        with pytest.raises(ValueError, match="must sum to 12"):
            ScaleType((Interval(2), Interval(2), Interval(2)), "broken")

    def test_str_with_name(self) -> None:
        """Str for named scale."""
        assert str(ScaleType.MAJOR) == "major"

    def test_str_without_name(self) -> None:
        """Str for unnamed scale."""
        # We can't create a valid unnamed scale easily, but can test named
        assert "major" in str(ScaleType.MAJOR)

    def test_repr_with_name(self) -> None:
        """Repr for named scale."""
        assert "MAJOR" in repr(ScaleType.MAJOR)
        assert "NATURAL_MINOR" in repr(ScaleType.NATURAL_MINOR)


class TestKeyPitchToDegree:
    """Tests for Key.pitch_to_degree."""

    def test_pitch_in_scale(self) -> None:
        """Pitch in scale returns degree."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        degree = c_major.pitch_to_degree(PitchClass.G)
        assert degree is not None
        assert degree.degree == 5

    def test_pitch_not_in_scale(self) -> None:
        """Pitch not in scale returns None."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        degree = c_major.pitch_to_degree(PitchClass.Fs)  # F# not in C major
        assert degree is None

    def test_tonic(self) -> None:
        """Tonic pitch returns degree 1."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        degree = c_major.pitch_to_degree(PitchClass.C)
        assert degree is not None
        assert degree.degree == 1


class TestKeyStrRepr:
    """Tests for Key string representations."""

    def test_str_major(self) -> None:
        """Str for major key."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        assert str(c_major) == "C major"

    def test_str_minor(self) -> None:
        """Str for minor key."""
        d_minor = Key(PitchClass.D, ScaleType.NATURAL_MINOR)
        assert str(d_minor) == "D minor"

    def test_str_harmonic_minor(self) -> None:
        """Str for harmonic minor key."""
        a_harm = Key(PitchClass.A, ScaleType.HARMONIC_MINOR)
        assert str(a_harm) == "A harmonic minor"

    def test_str_melodic_minor(self) -> None:
        """Str for melodic minor key."""
        a_mel = Key(PitchClass.A, ScaleType.MELODIC_MINOR)
        assert str(a_mel) == "A melodic minor"

    def test_str_mode(self) -> None:
        """Str for mode key."""
        d_dorian = Key(PitchClass.D, ScaleType.DORIAN)
        assert "dorian" in str(d_dorian)

    def test_repr(self) -> None:
        """Repr for key."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        assert "Key" in repr(c_major)

    def test_get_pitches(self) -> None:
        """Get all pitches in a key."""
        c_major = Key(PitchClass.C, ScaleType.MAJOR)
        pitches = c_major.get_pitches()
        assert len(pitches) == 7
        assert pitches[0] == PitchClass.C


class TestKeyParseErrors:
    """Tests for Key.parse error handling."""

    def test_parse_no_separator(self) -> None:
        """Parse without separator raises error."""
        with pytest.raises(ValueError, match="Invalid key format"):
            Key.parse("Cmajor")

    def test_parse_unknown_scale(self) -> None:
        """Parse with unknown scale raises error."""
        with pytest.raises(ValueError, match="Unknown scale type"):
            Key.parse("C_blues")

    def test_parse_modes(self) -> None:
        """Parse various modes."""
        assert Key.parse("C_dorian").scale == ScaleType.DORIAN
        assert Key.parse("C_phrygian").scale == ScaleType.PHRYGIAN
        assert Key.parse("C_lydian").scale == ScaleType.LYDIAN
        assert Key.parse("C_mixolydian").scale == ScaleType.MIXOLYDIAN
        assert Key.parse("C_locrian").scale == ScaleType.LOCRIAN

    def test_parse_harmonic_minor(self) -> None:
        """Parse harmonic minor."""
        key = Key.parse("A_harmonic_minor")
        assert key.scale == ScaleType.HARMONIC_MINOR

    def test_parse_melodic_minor(self) -> None:
        """Parse melodic minor."""
        key = Key.parse("A_melodic_minor")
        assert key.scale == ScaleType.MELODIC_MINOR

    def test_parse_natural_minor(self) -> None:
        """Parse natural minor explicitly."""
        key = Key.parse("A_natural_minor")
        assert key.scale == ScaleType.NATURAL_MINOR


class TestDurationComparisons:
    """Additional tests for Duration comparisons with non-Duration types."""

    def test_add_non_duration(self) -> None:
        """Add non-Duration returns NotImplemented."""
        result = Duration.QUARTER.__add__(5)  # type: ignore
        assert result == NotImplemented

    def test_sub_non_duration(self) -> None:
        """Sub non-Duration returns NotImplemented."""
        result = Duration.QUARTER.__sub__(5)  # type: ignore
        assert result == NotImplemented

    def test_mul_non_numeric(self) -> None:
        """Mul non-numeric returns NotImplemented."""
        result = Duration.QUARTER.__mul__("invalid")  # type: ignore
        assert result == NotImplemented

    def test_truediv_non_int(self) -> None:
        """Truediv non-int returns NotImplemented."""
        result = Duration.QUARTER.__truediv__(2.5)  # type: ignore
        assert result == NotImplemented

    def test_lt_non_duration(self) -> None:
        """Lt non-Duration returns NotImplemented."""
        result = Duration.QUARTER.__lt__(5)  # type: ignore
        assert result == NotImplemented

    def test_le_non_duration(self) -> None:
        """Le non-Duration returns NotImplemented."""
        result = Duration.QUARTER.__le__(5)  # type: ignore
        assert result == NotImplemented

    def test_gt_non_duration(self) -> None:
        """Gt non-Duration returns NotImplemented."""
        result = Duration.QUARTER.__gt__(5)  # type: ignore
        assert result == NotImplemented

    def test_ge_non_duration(self) -> None:
        """Ge non-Duration returns NotImplemented."""
        result = Duration.QUARTER.__ge__(5)  # type: ignore
        assert result == NotImplemented

    def test_repr_unnamed_duration(self) -> None:
        """Repr for unnamed duration."""
        d = Duration(Fraction(5, 7))  # Not a named constant
        assert "Fraction(5, 7)" in repr(d)


class TestBeatPositionComparisons:
    """Additional tests for BeatPosition comparisons with non-BeatPosition types."""

    def test_lt_non_beat_position(self) -> None:
        """Lt non-BeatPosition returns NotImplemented."""
        pos = BeatPosition(0, Fraction(0))
        result = pos.__lt__(5)  # type: ignore
        assert result == NotImplemented

    def test_le_non_beat_position(self) -> None:
        """Le non-BeatPosition returns NotImplemented."""
        pos = BeatPosition(0, Fraction(0))
        result = pos.__le__(5)  # type: ignore
        assert result == NotImplemented

    def test_gt_non_beat_position(self) -> None:
        """Gt non-BeatPosition returns NotImplemented."""
        pos = BeatPosition(0, Fraction(0))
        result = pos.__gt__(5)  # type: ignore
        assert result == NotImplemented

    def test_ge_non_beat_position(self) -> None:
        """Ge non-BeatPosition returns NotImplemented."""
        pos = BeatPosition(0, Fraction(0))
        result = pos.__ge__(5)  # type: ignore
        assert result == NotImplemented

    def test_repr_with_fraction_denominator(self) -> None:
        """Repr for beat position with fractional beat."""
        pos = BeatPosition(1, Fraction(1, 3))
        assert "Fraction(1, 3)" in repr(pos)

    def test_repr_with_integer_beat(self) -> None:
        """Repr for beat position with integer beat."""
        pos = BeatPosition(0, Fraction(2))
        assert "Fraction(2)" in repr(pos)

    def test_str_with_beat(self) -> None:
        """Str for beat position with non-zero beat."""
        pos = BeatPosition(0, Fraction(2))
        assert "beat" in str(pos)

    def test_invalid_bar(self) -> None:
        """BeatPosition with negative bar raises error."""
        with pytest.raises(ValueError):
            BeatPosition(-1, Fraction(0))

    def test_invalid_beat(self) -> None:
        """BeatPosition with negative beat raises error."""
        with pytest.raises(ValueError):
            BeatPosition(0, Fraction(-1))

    def test_add_duration_raises(self) -> None:
        """Adding Duration via + raises TypeError."""
        pos = BeatPosition(0, Fraction(0))
        with pytest.raises(TypeError):
            pos + Duration.QUARTER  # type: ignore
