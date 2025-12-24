"""
Pattern Compiler - compiles patterns to MIDI events.

The compiler resolves symbolic references (chord.root, scale.3)
to actual MIDI pitches using the harmony and key context.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from chuk_mcp_music.compiler.midi import TICKS_PER_BEAT, MidiEvent
from chuk_mcp_music.core import (
    BeatPosition,
    Duration,
    Key,
    RomanNumeral,
    ScaleDegree,
    TimeSignature,
)
from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.models.pattern import Pattern, PatternEvent

# Default register ranges for each layer role (MIDI note numbers)
DEFAULT_REGISTERS: dict[LayerRole, tuple[int, int]] = {
    LayerRole.SUB: (24, 36),  # C1-C2
    LayerRole.BASS: (36, 52),  # C2-E3
    LayerRole.DRUMS: (36, 84),  # GM drum map
    LayerRole.HARMONY: (48, 72),  # C3-C5
    LayerRole.MELODY: (60, 84),  # C4-C6
    LayerRole.FX: (36, 96),  # Wide range
    LayerRole.VOCAL: (48, 84),  # C3-C6
}


@dataclass
class HarmonyContext:
    """
    Provides chord information at any point in time.

    The harmony context knows what chord is active at each beat
    and can resolve symbolic references.
    """

    key: Key
    progression: list[str]  # Roman numerals as strings
    harmonic_rhythm: Duration  # How often chords change

    def chord_at(self, position: BeatPosition, time_sig: TimeSignature) -> RomanNumeral:
        """
        Get the chord active at a given position.

        Args:
            position: Beat position
            time_sig: Time signature

        Returns:
            The active Roman numeral
        """
        if not self.progression:
            return RomanNumeral.I  # Default to tonic

        # Calculate which chord in the progression
        total_beats = position.to_beats(time_sig)
        chord_beats = self.harmonic_rhythm.beats

        chord_index = int(total_beats // chord_beats) % len(self.progression)
        return RomanNumeral.parse(self.progression[chord_index])

    def resolve_degree(
        self,
        degree_str: str,
        position: BeatPosition,
        time_sig: TimeSignature,
        role: LayerRole,
        octave_shift: int = 0,
    ) -> int:
        """
        Resolve a symbolic degree to a MIDI pitch.

        Degree formats:
        - chord.root, chord.third, chord.fifth, chord.seventh
        - scale.1, scale.2, ..., scale.7
        - Numeric: just a scale degree number

        Args:
            degree_str: Symbolic degree reference
            position: Current position
            time_sig: Time signature
            role: Layer role (for register)
            octave_shift: Additional octave shift

        Returns:
            MIDI note number
        """
        register = DEFAULT_REGISTERS.get(role, (48, 72))
        base_octave = self._octave_for_register(register)

        if degree_str.startswith("chord."):
            # Chord tone reference
            chord_tone = degree_str.split(".")[1]
            chord = self.chord_at(position, time_sig)
            resolved_chord = chord.resolve(self.key)

            if chord_tone == "root":
                pitch = resolved_chord.root
            elif chord_tone == "third":
                third = resolved_chord.quality.third
                if third:
                    pitch = resolved_chord.root.transpose(third.semitones)
                else:
                    pitch = resolved_chord.root
            elif chord_tone == "fifth":
                fifth = resolved_chord.quality.fifth
                if fifth:
                    pitch = resolved_chord.root.transpose(fifth.semitones)
                else:
                    pitch = resolved_chord.root.transpose(7)  # Perfect fifth
            elif chord_tone == "seventh":
                seventh = resolved_chord.quality.seventh
                if seventh:
                    pitch = resolved_chord.root.transpose(seventh.semitones)
                else:
                    pitch = resolved_chord.root.transpose(10)  # Minor seventh
            else:
                pitch = resolved_chord.root

            midi_note = pitch.to_midi(base_octave + octave_shift)

        elif degree_str.startswith("scale."):
            # Scale degree reference
            degree_num = int(degree_str.split(".")[1])
            degree = ScaleDegree(degree_num)
            pitch = self.key.degree_to_pitch(degree)
            midi_note = pitch.to_midi(base_octave + octave_shift)

        else:
            # Try parsing as a number (scale degree)
            try:
                degree_num = int(degree_str)
                degree = ScaleDegree(min(7, max(1, degree_num)))
                pitch = self.key.degree_to_pitch(degree)
                midi_note = pitch.to_midi(base_octave + octave_shift)
            except ValueError:
                # Unknown format, default to root
                midi_note = self.key.root.to_midi(base_octave + octave_shift)

        # Ensure within register
        return self._clamp_to_register(midi_note, register)

    def _octave_for_register(self, register: tuple[int, int]) -> int:
        """Get the base octave for a register."""
        mid_note = (register[0] + register[1]) // 2
        return (mid_note // 12) - 1  # MIDI octave convention

    def _clamp_to_register(self, midi_note: int, register: tuple[int, int]) -> int:
        """Clamp a note to the register range, shifting octaves if needed."""
        low, high = register

        while midi_note < low:
            midi_note += 12
        while midi_note > high:
            midi_note -= 12

        return max(low, min(high, midi_note))


@dataclass
class CompileContext:
    """
    Context for compiling a pattern.

    Contains all the information needed to compile a pattern to events.
    """

    key: Key
    tempo: int
    time_sig: TimeSignature
    harmony: HarmonyContext
    role: LayerRole
    channel: int
    bar_offset: int = 0  # Starting bar for this pattern

    # Resolved parameters
    params: dict[str, Any] | None = None


class PatternCompiler:
    """
    Compiles patterns to MIDI events.

    The compiler takes a pattern and context, resolves all symbolic
    references, and produces concrete MIDI events.
    """

    def __init__(self, ticks_per_beat: int = TICKS_PER_BEAT):
        """
        Initialize the compiler.

        Args:
            ticks_per_beat: MIDI resolution
        """
        self.ticks_per_beat = ticks_per_beat

    def compile(
        self,
        pattern: Pattern,
        context: CompileContext,
        bars: int = 1,
    ) -> list[MidiEvent]:
        """
        Compile a pattern to MIDI events.

        Args:
            pattern: The pattern to compile
            context: Compilation context
            bars: Number of bars to generate

        Returns:
            List of MIDI events
        """
        events: list[MidiEvent] = []

        # Get resolved parameters
        params = context.params or pattern.get_resolved_params()

        # Calculate pattern length in bars
        pattern_bars = pattern.template.bars

        # Generate events for each repetition
        current_bar = 0
        while current_bar < bars:
            # Compile one iteration of the pattern
            pattern_events = self._compile_iteration(
                pattern,
                context,
                params,
                current_bar + context.bar_offset,
            )
            events.extend(pattern_events)

            current_bar += pattern_bars

            # Stop if pattern doesn't loop
            if not pattern.template.loop:
                break

        return events

    def _compile_iteration(
        self,
        pattern: Pattern,
        context: CompileContext,
        params: dict[str, Any],
        bar_offset: int,
    ) -> list[MidiEvent]:
        """Compile one iteration of a pattern."""
        events: list[MidiEvent] = []
        ticks_per_bar = context.time_sig.bar_to_ticks(self.ticks_per_beat)

        for event in pattern.template.events:
            midi_event = self._compile_event(
                event,
                pattern,
                context,
                params,
                bar_offset,
                ticks_per_bar,
            )
            if midi_event:
                events.append(midi_event)

        return events

    def _compile_event(
        self,
        event: PatternEvent,
        pattern: Pattern,
        context: CompileContext,
        params: dict[str, Any],
        bar_offset: int,
        ticks_per_bar: int,
    ) -> MidiEvent | None:
        """Compile a single pattern event to MIDI."""
        # Calculate position
        beat_position = BeatPosition(bar_offset, Fraction(event.beat))
        start_ticks = beat_position.to_ticks(context.time_sig, self.ticks_per_beat)

        # Resolve duration
        duration_ticks = self._resolve_duration(event.duration, params)

        # Resolve pitch
        if pattern.pitched and event.degree:
            # Pitched pattern with symbolic degree
            pitch = context.harmony.resolve_degree(
                event.degree,
                beat_position,
                context.time_sig,
                context.role,
                event.octave_shift,
            )
        elif event.note is not None:
            # Absolute MIDI note (drums)
            pitch = event.note
        else:
            # No pitch specified
            return None

        # Resolve velocity
        velocity = self._resolve_velocity(event.velocity, params)

        return MidiEvent(
            pitch=pitch,
            start_ticks=start_ticks,
            duration_ticks=duration_ticks,
            velocity=velocity,
            channel=context.channel,
        )

    def _resolve_duration(
        self,
        duration: str | float,
        params: dict[str, Any],
    ) -> int:
        """Resolve a duration to ticks."""
        if isinstance(duration, (int, float)):
            # Direct beat value
            return int(duration * self.ticks_per_beat)

        # String value - could be a parameter reference or named duration
        if duration.startswith("$"):
            # Parameter reference
            param_name = duration[1:]
            duration = params.get(param_name, "quarter")

        # Named duration
        duration_map = {
            "whole": Duration.WHOLE,
            "half": Duration.HALF,
            "quarter": Duration.QUARTER,
            "eighth": Duration.EIGHTH,
            "sixteenth": Duration.SIXTEENTH,
        }

        if duration in duration_map:
            return duration_map[duration].to_ticks(self.ticks_per_beat)

        # Try parsing as float
        try:
            return int(float(duration) * self.ticks_per_beat)
        except ValueError:
            return self.ticks_per_beat  # Default to quarter note

    def _resolve_velocity(
        self,
        velocity: float | str,
        params: dict[str, Any],
    ) -> int:
        """Resolve velocity to MIDI value (0-127)."""
        if isinstance(velocity, str) and velocity.startswith("$"):
            # Parameter reference
            param_name = velocity[1:]
            velocity = params.get(param_name, 0.8)

        # Convert float (0-1) to MIDI (0-127)
        if isinstance(velocity, (int, float)):
            return max(0, min(127, int(float(velocity) * 127)))

        return 100  # Default velocity


def compile_pattern(
    pattern: Pattern,
    key: Key,
    tempo: int,
    time_sig: TimeSignature,
    progression: list[str],
    role: LayerRole,
    channel: int,
    bars: int = 1,
    bar_offset: int = 0,
    variant: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[MidiEvent]:
    """
    Convenience function to compile a pattern.

    Args:
        pattern: Pattern to compile
        key: Musical key
        tempo: Tempo in BPM
        time_sig: Time signature
        progression: Chord progression (Roman numerals)
        role: Layer role
        channel: MIDI channel
        bars: Number of bars to generate
        bar_offset: Starting bar
        variant: Optional variant name
        params: Optional parameter overrides

    Returns:
        List of MIDI events
    """
    harmony = HarmonyContext(
        key=key,
        progression=progression,
        harmonic_rhythm=Duration.WHOLE,  # One chord per bar
    )

    resolved_params = pattern.get_resolved_params(variant, params)

    context = CompileContext(
        key=key,
        tempo=tempo,
        time_sig=time_sig,
        harmony=harmony,
        role=role,
        channel=channel,
        bar_offset=bar_offset,
        params=resolved_params,
    )

    compiler = PatternCompiler()
    return compiler.compile(pattern, context, bars)
