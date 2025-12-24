"""
MIDI export - the end of the pipeline.

This module handles conversion from EventList to MIDI files using mido.
All operations are deterministic: same input → same output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mido import Message, MetaMessage, MidiFile, MidiTrack

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chuk_mcp_music.compiler.score_ir import ScoreIR


# Standard ticks per beat (quarter note) - industry standard
TICKS_PER_BEAT = 480

# GM Drum channel (0-indexed, so 9 = channel 10)
DRUM_CHANNEL = 9


@dataclass(frozen=True)
class MidiEvent:
    """
    A single MIDI note event.

    This is the lowest-level representation before writing to MIDI.
    All times are in ticks (absolute from start of track).
    """

    pitch: int  # MIDI note number (0-127)
    start_ticks: int  # Absolute start time in ticks
    duration_ticks: int  # Duration in ticks
    velocity: int  # 0-127
    channel: int = 0  # 0-15 (9 = drums)

    def __post_init__(self) -> None:
        """Validate MIDI ranges."""
        if not 0 <= self.pitch <= 127:
            raise ValueError(f"Pitch must be 0-127, got {self.pitch}")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"Velocity must be 0-127, got {self.velocity}")
        if not 0 <= self.channel <= 15:
            raise ValueError(f"Channel must be 0-15, got {self.channel}")
        if self.start_ticks < 0:
            raise ValueError(f"Start ticks must be >= 0, got {self.start_ticks}")
        if self.duration_ticks < 0:
            raise ValueError(f"Duration ticks must be >= 0, got {self.duration_ticks}")


def events_to_midi(
    events: Sequence[MidiEvent],
    tempo_bpm: int = 120,
    ticks_per_beat: int = TICKS_PER_BEAT,
) -> MidiFile:
    """
    Convert a sequence of MidiEvents to a MidiFile.

    Args:
        events: Sequence of MidiEvent objects
        tempo_bpm: Tempo in beats per minute
        ticks_per_beat: Resolution (default 480)

    Returns:
        A mido MidiFile ready to be saved

    This function is deterministic: same events → same MIDI file.
    """
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo (microseconds per beat)
    tempo_us = int(60_000_000 / tempo_bpm)
    track.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))

    # Convert events to note_on/note_off messages
    # We need to sort by time and convert to delta times
    messages: list[tuple[int, Message]] = []

    for event in events:
        # Note on
        messages.append(
            (
                event.start_ticks,
                Message(
                    "note_on",
                    channel=event.channel,
                    note=event.pitch,
                    velocity=event.velocity,
                    time=0,  # Will be converted to delta
                ),
            )
        )
        # Note off
        messages.append(
            (
                event.start_ticks + event.duration_ticks,
                Message(
                    "note_off",
                    channel=event.channel,
                    note=event.pitch,
                    velocity=0,
                    time=0,  # Will be converted to delta
                ),
            )
        )

    # Sort by absolute time, then by message type (note_off before note_on at same time)
    # This ensures clean note transitions
    messages.sort(key=lambda x: (x[0], x[1].type != "note_off"))

    # Convert to delta times
    current_time = 0
    for abs_time, msg in messages:
        delta = abs_time - current_time
        msg.time = delta
        track.append(msg)
        current_time = abs_time

    # End of track
    track.append(MetaMessage("end_of_track", time=0))

    return mid


def create_test_midi(tempo_bpm: int = 120) -> MidiFile:
    """
    Create a minimal test MIDI file.

    This is the proof-of-life function. If this works,
    we know MIDI export is viable.

    Creates 4 bars of a simple four-on-floor drum pattern.
    """
    events: list[MidiEvent] = []
    ticks_per_beat = TICKS_PER_BEAT
    ticks_per_bar = ticks_per_beat * 4  # 4/4 time

    # 4 bars of drums
    for bar in range(4):
        bar_start = bar * ticks_per_bar

        # Kick on beats 1, 2, 3, 4
        for beat in range(4):
            events.append(
                MidiEvent(
                    pitch=36,  # Kick drum (GM)
                    start_ticks=bar_start + beat * ticks_per_beat,
                    duration_ticks=ticks_per_beat // 2,
                    velocity=100,
                    channel=DRUM_CHANNEL,
                )
            )

        # Snare on beats 2 and 4
        for beat in [1, 3]:  # 0-indexed
            events.append(
                MidiEvent(
                    pitch=38,  # Snare drum (GM)
                    start_ticks=bar_start + beat * ticks_per_beat,
                    duration_ticks=ticks_per_beat // 2,
                    velocity=90,
                    channel=DRUM_CHANNEL,
                )
            )

        # Closed hi-hat on every eighth note
        for eighth in range(8):
            events.append(
                MidiEvent(
                    pitch=42,  # Closed hi-hat (GM)
                    start_ticks=bar_start + eighth * (ticks_per_beat // 2),
                    duration_ticks=ticks_per_beat // 4,
                    velocity=70 if eighth % 2 == 0 else 50,  # Accent on beats
                    channel=DRUM_CHANNEL,
                )
            )

    return events_to_midi(events, tempo_bpm=tempo_bpm)


def score_ir_to_midi(score_ir: ScoreIR) -> MidiFile:
    """
    Convert a Score IR directly to a MidiFile.

    This enables the round-trip workflow:
    1. Compile arrangement to IR
    2. Modify IR (filter notes, adjust velocities, etc.)
    3. Emit MIDI from modified IR

    Args:
        score_ir: A ScoreIR object (can be loaded from JSON)

    Returns:
        A mido MidiFile ready to be saved

    Example:
        ir = ScoreIR.from_json(json_str)
        # Filter out drums
        ir.notes = [n for n in ir.notes if n.source_layer != "drums"]
        midi = score_ir_to_midi(ir)
        midi.save("no_drums.mid")
    """
    # Convert IR notes to MidiEvents
    events = [
        MidiEvent(
            pitch=note.pitch,
            start_ticks=note.start_ticks,
            duration_ticks=note.duration_ticks,
            velocity=note.velocity,
            channel=note.channel,
        )
        for note in score_ir.notes
    ]

    return events_to_midi(
        events,
        tempo_bpm=score_ir.tempo,
        ticks_per_beat=score_ir.ticks_per_beat,
    )


def beats_to_ticks(beats: float, ticks_per_beat: int = TICKS_PER_BEAT) -> int:
    """Convert a beat position to ticks."""
    return int(beats * ticks_per_beat)


def velocity_float_to_int(velocity: float) -> int:
    """Convert velocity from 0.0-1.0 range to 0-127."""
    return max(0, min(127, int(velocity * 127)))


if __name__ == "__main__":
    # Quick manual test
    mid = create_test_midi()
    mid.save("test_output.mid")
    print("Created test_output.mid - open in a DAW to verify")
    print(f"  Tracks: {len(mid.tracks)}")
    print(f"  Ticks per beat: {mid.ticks_per_beat}")
