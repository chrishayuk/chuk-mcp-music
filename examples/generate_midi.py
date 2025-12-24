#!/usr/bin/env python3
"""
Example: Generate a simple MIDI file.

This demonstrates the MIDI export pipeline - the endpoint of the system.
Run this script to create a playable MIDI file you can open in any DAW.

Usage:
    python examples/generate_midi.py
    # Creates: examples/output/four_on_floor.mid
"""

from pathlib import Path

from chuk_mcp_music.compiler.midi import (
    DRUM_CHANNEL,
    TICKS_PER_BEAT,
    MidiEvent,
    create_test_midi,
    events_to_midi,
)


def main() -> None:
    """Generate example MIDI files."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Example 1: Simple four-on-floor drum pattern (4 bars)
    print("Generating four_on_floor.mid...")
    mid = create_test_midi(tempo_bpm=124)
    mid.save(str(output_dir / "four_on_floor.mid"))
    print(f"  Created: {output_dir / 'four_on_floor.mid'}")

    # Example 2: Custom pattern - simple bassline
    print("\nGenerating simple_bassline.mid...")
    bassline = create_simple_bassline()
    bassline.save(str(output_dir / "simple_bassline.mid"))
    print(f"  Created: {output_dir / 'simple_bassline.mid'}")

    # Example 3: Combined drums + bass
    print("\nGenerating drums_and_bass.mid...")
    combined = create_drums_and_bass()
    combined.save(str(output_dir / "drums_and_bass.mid"))
    print(f"  Created: {output_dir / 'drums_and_bass.mid'}")

    print("\nDone! Open the MIDI files in your DAW to hear them.")


def create_simple_bassline():
    """
    Create a simple bassline following a i-VI-III-VII progression in D minor.

    This demonstrates:
    - Creating MidiEvents manually
    - Using different pitches for chord roots
    - Setting velocity for dynamics
    """
    events: list[MidiEvent] = []
    ticks_per_bar = TICKS_PER_BEAT * 4  # 4/4 time

    # D minor progression: Dm - Bb - F - C
    # MIDI notes: D2=38, Bb1=34, F2=41, C2=36
    progression = [38, 34, 41, 36]  # Root notes for i, VI, III, VII

    # 4 bars, one chord per bar
    for bar, root_note in enumerate(progression):
        bar_start = bar * ticks_per_bar

        # Quarter note pulse on the root
        for beat in range(4):
            events.append(
                MidiEvent(
                    pitch=root_note,
                    start_ticks=bar_start + beat * TICKS_PER_BEAT,
                    duration_ticks=TICKS_PER_BEAT - 20,  # Slightly shorter for separation
                    velocity=100 if beat == 0 else 80,  # Accent on downbeat
                    channel=0,  # Bass channel
                )
            )

    return events_to_midi(events, tempo_bpm=124)


def create_drums_and_bass():
    """
    Create a combined drums and bass pattern.

    This demonstrates:
    - Multiple channels (drums on 9, bass on 0)
    - Layered patterns
    - 8 bars of music
    """
    events: list[MidiEvent] = []
    ticks_per_bar = TICKS_PER_BEAT * 4

    # D minor progression repeated twice: Dm - Bb - F - C - Dm - Bb - F - C
    progression = [38, 34, 41, 36, 38, 34, 41, 36]

    for bar in range(8):
        bar_start = bar * ticks_per_bar
        root_note = progression[bar]

        # DRUMS (channel 9)
        # Kick on 1 and 3
        for beat in [0, 2]:
            events.append(
                MidiEvent(
                    pitch=36,  # Kick
                    start_ticks=bar_start + beat * TICKS_PER_BEAT,
                    duration_ticks=TICKS_PER_BEAT // 2,
                    velocity=100,
                    channel=DRUM_CHANNEL,
                )
            )

        # Snare on 2 and 4
        for beat in [1, 3]:
            events.append(
                MidiEvent(
                    pitch=38,  # Snare
                    start_ticks=bar_start + beat * TICKS_PER_BEAT,
                    duration_ticks=TICKS_PER_BEAT // 2,
                    velocity=90,
                    channel=DRUM_CHANNEL,
                )
            )

        # Hi-hat on every eighth
        for eighth in range(8):
            events.append(
                MidiEvent(
                    pitch=42,  # Closed hi-hat
                    start_ticks=bar_start + eighth * (TICKS_PER_BEAT // 2),
                    duration_ticks=TICKS_PER_BEAT // 4,
                    velocity=60 if eighth % 2 == 0 else 40,
                    channel=DRUM_CHANNEL,
                )
            )

        # BASS (channel 0)
        # Eighth note pulse
        for eighth in range(8):
            events.append(
                MidiEvent(
                    pitch=root_note,
                    start_ticks=bar_start + eighth * (TICKS_PER_BEAT // 2),
                    duration_ticks=(TICKS_PER_BEAT // 2) - 10,
                    velocity=90 if eighth % 2 == 0 else 70,
                    channel=0,
                )
            )

    return events_to_midi(events, tempo_bpm=124)


if __name__ == "__main__":
    main()
