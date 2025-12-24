"""
MIDI export tests - proof of life.

If these tests pass, we know the pipeline endpoint works.
"""

from pathlib import Path

from mido import MidiFile

from chuk_mcp_music.compiler.midi import (
    DRUM_CHANNEL,
    TICKS_PER_BEAT,
    MidiEvent,
    beats_to_ticks,
    create_test_midi,
    events_to_midi,
    velocity_float_to_int,
)


class TestMidiEvent:
    """Test MidiEvent dataclass."""

    def test_create_valid_event(self) -> None:
        """Can create a valid MIDI event."""
        event = MidiEvent(
            pitch=60,
            start_ticks=0,
            duration_ticks=480,
            velocity=100,
            channel=0,
        )
        assert event.pitch == 60
        assert event.start_ticks == 0
        assert event.duration_ticks == 480
        assert event.velocity == 100
        assert event.channel == 0

    def test_event_validation_pitch_range(self) -> None:
        """Pitch must be 0-127."""
        import pytest

        with pytest.raises(ValueError, match="Pitch must be 0-127"):
            MidiEvent(pitch=128, start_ticks=0, duration_ticks=480, velocity=100)

        with pytest.raises(ValueError, match="Pitch must be 0-127"):
            MidiEvent(pitch=-1, start_ticks=0, duration_ticks=480, velocity=100)

    def test_event_validation_velocity_range(self) -> None:
        """Velocity must be 0-127."""
        import pytest

        with pytest.raises(ValueError, match="Velocity must be 0-127"):
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=128)

    def test_event_validation_channel_range(self) -> None:
        """Channel must be 0-15."""
        import pytest

        with pytest.raises(ValueError, match="Channel must be 0-15"):
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=100, channel=16)


class TestEventsToMidi:
    """Test the events_to_midi function."""

    def test_empty_events(self) -> None:
        """Can create MIDI file with no events."""
        mid = events_to_midi([])
        assert len(mid.tracks) == 1
        assert mid.ticks_per_beat == TICKS_PER_BEAT

    def test_single_note(self) -> None:
        """Can create MIDI file with a single note."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=100),
        ]
        mid = events_to_midi(events)

        # Should have tempo meta message, note_on, note_off, end_of_track
        track = mid.tracks[0]

        # Find note messages
        note_messages = [msg for msg in track if msg.type in ("note_on", "note_off")]
        assert len(note_messages) == 2
        assert note_messages[0].type == "note_on"
        assert note_messages[0].note == 60
        assert note_messages[1].type == "note_off"
        assert note_messages[1].note == 60

    def test_multiple_notes_ordering(self) -> None:
        """Notes are properly ordered by time."""
        events = [
            MidiEvent(pitch=60, start_ticks=480, duration_ticks=480, velocity=100),
            MidiEvent(pitch=64, start_ticks=0, duration_ticks=480, velocity=100),
        ]
        mid = events_to_midi(events)

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
        # First note_on should be pitch 64 (starts at tick 0)
        assert note_ons[0].note == 64
        # Second note_on should be pitch 60 (starts at tick 480)
        assert note_ons[1].note == 60

    def test_tempo_setting(self) -> None:
        """Tempo is correctly set in the MIDI file."""
        mid = events_to_midi([], tempo_bpm=140)

        tempo_msgs = [msg for msg in mid.tracks[0] if msg.type == "set_tempo"]
        assert len(tempo_msgs) == 1

        # 140 BPM = 428571 microseconds per beat
        expected_tempo = int(60_000_000 / 140)
        assert tempo_msgs[0].tempo == expected_tempo


class TestCreateTestMidi:
    """Test the proof-of-life function."""

    def test_creates_valid_midi(self) -> None:
        """create_test_midi produces a valid MIDI file."""
        mid = create_test_midi()

        assert isinstance(mid, MidiFile)
        assert len(mid.tracks) >= 1
        assert mid.ticks_per_beat == TICKS_PER_BEAT

    def test_can_save_and_reload(self, temp_midi_path: Path) -> None:
        """MIDI file can be saved and reloaded."""
        mid = create_test_midi()
        mid.save(str(temp_midi_path))

        assert temp_midi_path.exists()
        assert temp_midi_path.stat().st_size > 0

        # Reload and verify
        loaded = MidiFile(str(temp_midi_path))
        assert len(loaded.tracks) == len(mid.tracks)
        assert loaded.ticks_per_beat == mid.ticks_per_beat

    def test_contains_drum_notes(self) -> None:
        """Test MIDI contains expected drum notes."""
        mid = create_test_midi()

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]

        # Should have drum notes on channel 9
        drum_notes = [msg for msg in note_ons if msg.channel == DRUM_CHANNEL]
        assert len(drum_notes) > 0

        # Should include kick (36), snare (38), hihat (42)
        pitches = {msg.note for msg in drum_notes}
        assert 36 in pitches  # Kick
        assert 38 in pitches  # Snare
        assert 42 in pitches  # Hi-hat

    def test_respects_tempo_parameter(self) -> None:
        """Tempo parameter is applied correctly."""
        mid_120 = create_test_midi(tempo_bpm=120)
        mid_140 = create_test_midi(tempo_bpm=140)

        tempo_120 = next(msg for msg in mid_120.tracks[0] if msg.type == "set_tempo")
        tempo_140 = next(msg for msg in mid_140.tracks[0] if msg.type == "set_tempo")

        # 140 BPM should have faster tempo (smaller microseconds per beat)
        assert tempo_140.tempo < tempo_120.tempo


class TestHelperFunctions:
    """Test utility functions."""

    def test_beats_to_ticks(self) -> None:
        """Beat to tick conversion works correctly."""
        assert beats_to_ticks(0) == 0
        assert beats_to_ticks(1) == TICKS_PER_BEAT
        assert beats_to_ticks(0.5) == TICKS_PER_BEAT // 2
        assert beats_to_ticks(4) == TICKS_PER_BEAT * 4

    def test_velocity_float_to_int(self) -> None:
        """Velocity conversion from float to int."""
        assert velocity_float_to_int(0.0) == 0
        assert velocity_float_to_int(1.0) == 127
        assert velocity_float_to_int(0.5) == 63

        # Clamping
        assert velocity_float_to_int(-0.5) == 0
        assert velocity_float_to_int(1.5) == 127


class TestDeterminism:
    """Verify deterministic output."""

    def test_same_events_same_output(self, temp_midi_path: Path) -> None:
        """Same events should produce identical MIDI files."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=100),
            MidiEvent(pitch=64, start_ticks=480, duration_ticks=480, velocity=90),
        ]

        mid1 = events_to_midi(events, tempo_bpm=120)
        mid2 = events_to_midi(events, tempo_bpm=120)

        # Save both and compare bytes
        path1 = temp_midi_path.parent / "test1.mid"
        path2 = temp_midi_path.parent / "test2.mid"

        mid1.save(str(path1))
        mid2.save(str(path2))

        assert path1.read_bytes() == path2.read_bytes()

    def test_create_test_midi_deterministic(self, temp_midi_path: Path) -> None:
        """create_test_midi should produce identical output each time."""
        path1 = temp_midi_path.parent / "test1.mid"
        path2 = temp_midi_path.parent / "test2.mid"

        mid1 = create_test_midi(tempo_bpm=120)
        mid2 = create_test_midi(tempo_bpm=120)

        mid1.save(str(path1))
        mid2.save(str(path2))

        assert path1.read_bytes() == path2.read_bytes()


class TestMidiEdgeCases:
    """Additional tests for MIDI edge cases."""

    def test_overlapping_notes(self) -> None:
        """Handle overlapping notes correctly."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=960, velocity=100),
            MidiEvent(
                pitch=60, start_ticks=480, duration_ticks=960, velocity=80
            ),  # Same pitch, overlap
        ]
        mid = events_to_midi(events)

        # Should have 4 messages (2 on, 2 off)
        note_messages = [msg for msg in mid.tracks[0] if msg.type in ("note_on", "note_off")]
        assert len(note_messages) == 4

    def test_very_short_notes(self) -> None:
        """Handle very short notes."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=1, velocity=100),
        ]
        mid = events_to_midi(events)

        note_messages = [msg for msg in mid.tracks[0] if msg.type in ("note_on", "note_off")]
        assert len(note_messages) == 2

    def test_multiple_channels(self) -> None:
        """Handle notes on multiple channels."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=100, channel=0),
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=100, channel=1),
            MidiEvent(pitch=36, start_ticks=0, duration_ticks=480, velocity=100, channel=9),
        ]
        mid = events_to_midi(events)

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
        channels = {msg.channel for msg in note_ons}
        assert channels == {0, 1, 9}

    def test_zero_velocity_note(self) -> None:
        """Zero velocity notes are valid."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=0),
        ]
        mid = events_to_midi(events)

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
        assert note_ons[0].velocity == 0

    def test_notes_with_large_gaps(self) -> None:
        """Handle notes with large time gaps."""
        events = [
            MidiEvent(pitch=60, start_ticks=0, duration_ticks=480, velocity=100),
            MidiEvent(
                pitch=64, start_ticks=96000, duration_ticks=480, velocity=100
            ),  # 200 beats later
        ]
        mid = events_to_midi(events)

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
        assert len(note_ons) == 2

    def test_all_128_pitches(self) -> None:
        """All 128 pitches can be used."""
        events = [
            MidiEvent(pitch=i, start_ticks=i * 480, duration_ticks=480, velocity=100)
            for i in range(128)
        ]
        mid = events_to_midi(events)

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
        pitches = {msg.note for msg in note_ons}
        assert pitches == set(range(128))

    def test_all_16_channels(self) -> None:
        """All 16 channels can be used."""
        events = [
            MidiEvent(pitch=60, start_ticks=i * 480, duration_ticks=480, velocity=100, channel=i)
            for i in range(16)
        ]
        mid = events_to_midi(events)

        note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
        channels = {msg.channel for msg in note_ons}
        assert channels == set(range(16))
