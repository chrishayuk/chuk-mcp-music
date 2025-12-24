"""
Arrangement Compiler - compiles an Arrangement to MIDI.

This is the central compilation pipeline:
    Arrangement → PatternInstances → Score IR → MIDI File

The compiler:
1. Iterates through sections
2. For each section, finds active patterns per layer
3. Compiles each pattern with the correct harmony context
4. Produces Score IR (intermediate representation)
5. Exports Score IR to MIDI

The Score IR is the stable, inspectable interface between
arrangement and MIDI. It supports diffing, golden-file testing,
and debugging.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mido import MidiFile

from chuk_mcp_music.compiler.midi import (
    TICKS_PER_BEAT,
    MidiEvent,
    events_to_midi,
)
from chuk_mcp_music.compiler.score_ir import (
    IRNote,
    IRSectionMarker,
    IRTempoEvent,
    IRTimeSignature,
    ScoreIR,
)
from chuk_mcp_music.core import Duration
from chuk_mcp_music.models.arrangement import Arrangement
from chuk_mcp_music.patterns.compiler import (
    CompileContext,
    HarmonyContext,
    PatternCompiler,
)
from chuk_mcp_music.patterns.registry import PatternRegistry

if TYPE_CHECKING:
    from chuk_mcp_music.models.pattern import Pattern


@dataclass
class CompileResult:
    """Result of compiling an arrangement."""

    midi_file: MidiFile
    score_ir: ScoreIR
    total_bars: int
    total_events: int
    layers_compiled: list[str]
    sections_compiled: list[str]


class ArrangementCompiler:
    """
    Compiles an Arrangement to a MIDI file.

    The compiler orchestrates the full pipeline from high-level
    arrangement to concrete MIDI output.
    """

    def __init__(
        self,
        pattern_registry: PatternRegistry,
        ticks_per_beat: int = TICKS_PER_BEAT,
    ):
        """
        Initialize the compiler.

        Args:
            pattern_registry: Registry for loading patterns
            ticks_per_beat: MIDI resolution
        """
        self.registry = pattern_registry
        self.ticks_per_beat = ticks_per_beat
        self.pattern_compiler = PatternCompiler(ticks_per_beat)

    def compile(self, arrangement: Arrangement) -> CompileResult:
        """
        Compile an arrangement to MIDI via Score IR.

        Args:
            arrangement: The arrangement to compile

        Returns:
            CompileResult with MIDI file, Score IR, and metadata
        """
        all_notes: list[IRNote] = []
        section_markers: list[IRSectionMarker] = []
        layers_compiled: list[str] = []
        sections_compiled: list[str] = []
        layer_info: dict[str, dict] = {}

        # Parse global context
        key = arrangement.context.get_key()
        time_sig = arrangement.context.get_time_signature()
        tempo = arrangement.context.tempo
        ticks_per_bar = self.ticks_per_beat * time_sig.beats_per_bar

        # Track current bar position
        current_bar = 0
        current_tick = 0

        # Compile each section
        for section in arrangement.sections:
            section_name = section.name
            section_bars = section.bars
            sections_compiled.append(section_name)

            section_start_tick = current_tick
            section_end_tick = current_tick + (section_bars * ticks_per_bar)

            # Add section marker
            section_markers.append(
                IRSectionMarker(
                    name=section_name,
                    start_ticks=section_start_tick,
                    end_ticks=section_end_tick,
                    bars=section_bars,
                )
            )

            # Get harmony for this section
            progression = arrangement.harmony.get_progression_for_section(section_name)

            # Compile each layer
            for layer_name, layer in arrangement.layers.items():
                if layer.muted:
                    continue

                # Check for solo mode
                if self._has_soloed_layers(arrangement) and not layer.solo:
                    continue

                # Get the pattern for this section
                pattern_ref = layer.get_pattern_for_section(section_name)
                if pattern_ref is None:
                    continue

                # Load the pattern
                pattern = self.registry.get_pattern(pattern_ref.ref)
                if pattern is None:
                    continue

                # Create harmony context
                harmony = HarmonyContext(
                    key=key,
                    progression=progression,
                    harmonic_rhythm=self._parse_harmonic_rhythm(
                        arrangement.harmony.harmonic_rhythm
                    ),
                )

                # Resolve parameters
                resolved_params = pattern.get_resolved_params(
                    variant=pattern_ref.variant,
                    overrides=pattern_ref.params,
                )

                # Create compile context
                context = CompileContext(
                    key=key,
                    tempo=tempo,
                    time_sig=time_sig,
                    harmony=harmony,
                    role=layer.role,
                    channel=layer.channel,
                    bar_offset=current_bar,
                    params=resolved_params,
                )

                # Compile to MidiEvents first
                midi_events = self._compile_layer_pattern(
                    pattern, context, section_bars, layer.level
                )

                # Convert to IR notes with source traceability
                for event in midi_events:
                    # Calculate bar and beat from ticks
                    event_bar = event.start_ticks // ticks_per_bar
                    event_beat = (event.start_ticks % ticks_per_bar) / self.ticks_per_beat

                    all_notes.append(
                        IRNote(
                            start_ticks=event.start_ticks,
                            channel=event.channel,
                            pitch=event.pitch,
                            duration_ticks=event.duration_ticks,
                            velocity=event.velocity,
                            source_layer=layer_name,
                            source_pattern=pattern_ref.ref,
                            source_section=section_name,
                            bar=event_bar,
                            beat=round(event_beat, 3),
                        )
                    )

                if layer_name not in layers_compiled:
                    layers_compiled.append(layer_name)

                # Track layer info
                if layer_name not in layer_info:
                    layer_info[layer_name] = {
                        "role": layer.role.value,
                        "channel": layer.channel,
                        "level": layer.level,
                        "muted": layer.muted,
                        "solo": layer.solo,
                    }

            current_bar += section_bars
            current_tick = section_end_tick

        # Build Score IR
        score_ir = ScoreIR(
            name=arrangement.name,
            key=arrangement.context.key,
            tempo=tempo,
            time_signature=IRTimeSignature.from_time_sig(time_sig),
            ticks_per_beat=self.ticks_per_beat,
            total_ticks=current_tick,
            total_bars=current_bar,
            notes=all_notes,
            sections=section_markers,
            tempo_events=[IRTempoEvent(ticks=0, bpm=tempo)],
            layers=layer_info,
        ).canonicalize()

        # Convert IR notes to MidiEvents for MIDI export
        midi_events = [
            MidiEvent(
                pitch=note.pitch,
                start_ticks=note.start_ticks,
                duration_ticks=note.duration_ticks,
                velocity=note.velocity,
                channel=note.channel,
            )
            for note in score_ir.notes
        ]

        # Create MIDI file
        midi_file = events_to_midi(midi_events, tempo_bpm=tempo)

        return CompileResult(
            midi_file=midi_file,
            score_ir=score_ir,
            total_bars=current_bar,
            total_events=len(score_ir.notes),
            layers_compiled=layers_compiled,
            sections_compiled=sections_compiled,
        )

    def compile_section(
        self,
        arrangement: Arrangement,
        section_name: str,
    ) -> CompileResult:
        """
        Compile a single section for preview.

        Args:
            arrangement: The arrangement
            section_name: Section to compile

        Returns:
            CompileResult with MIDI file and Score IR for the section
        """
        section = arrangement.get_section(section_name)
        if section is None:
            raise ValueError(f"Section not found: {section_name}")

        all_notes: list[IRNote] = []
        layers_compiled: list[str] = []
        layer_info: dict[str, dict] = {}

        # Parse context
        key = arrangement.context.get_key()
        time_sig = arrangement.context.get_time_signature()
        tempo = arrangement.context.tempo
        ticks_per_bar = self.ticks_per_beat * time_sig.beats_per_bar

        # Get harmony for this section
        progression = arrangement.harmony.get_progression_for_section(section_name)

        # Compile each layer
        for layer_name, layer in arrangement.layers.items():
            if layer.muted:
                continue

            if self._has_soloed_layers(arrangement) and not layer.solo:
                continue

            pattern_ref = layer.get_pattern_for_section(section_name)
            if pattern_ref is None:
                continue

            pattern = self.registry.get_pattern(pattern_ref.ref)
            if pattern is None:
                continue

            harmony = HarmonyContext(
                key=key,
                progression=progression,
                harmonic_rhythm=self._parse_harmonic_rhythm(arrangement.harmony.harmonic_rhythm),
            )

            resolved_params = pattern.get_resolved_params(
                variant=pattern_ref.variant,
                overrides=pattern_ref.params,
            )

            context = CompileContext(
                key=key,
                tempo=tempo,
                time_sig=time_sig,
                harmony=harmony,
                role=layer.role,
                channel=layer.channel,
                bar_offset=0,
                params=resolved_params,
            )

            midi_events = self._compile_layer_pattern(pattern, context, section.bars, layer.level)

            # Convert to IR notes
            for event in midi_events:
                event_bar = event.start_ticks // ticks_per_bar
                event_beat = (event.start_ticks % ticks_per_bar) / self.ticks_per_beat

                all_notes.append(
                    IRNote(
                        start_ticks=event.start_ticks,
                        channel=event.channel,
                        pitch=event.pitch,
                        duration_ticks=event.duration_ticks,
                        velocity=event.velocity,
                        source_layer=layer_name,
                        source_pattern=pattern_ref.ref,
                        source_section=section_name,
                        bar=event_bar,
                        beat=round(event_beat, 3),
                    )
                )

            layers_compiled.append(layer_name)

            if layer_name not in layer_info:
                layer_info[layer_name] = {
                    "role": layer.role.value,
                    "channel": layer.channel,
                    "level": layer.level,
                    "muted": layer.muted,
                    "solo": layer.solo,
                }

        section_ticks = section.bars * ticks_per_bar

        # Build Score IR
        score_ir = ScoreIR(
            name=f"{arrangement.name}:{section_name}",
            key=arrangement.context.key,
            tempo=tempo,
            time_signature=IRTimeSignature.from_time_sig(time_sig),
            ticks_per_beat=self.ticks_per_beat,
            total_ticks=section_ticks,
            total_bars=section.bars,
            notes=all_notes,
            sections=[
                IRSectionMarker(
                    name=section_name,
                    start_ticks=0,
                    end_ticks=section_ticks,
                    bars=section.bars,
                )
            ],
            tempo_events=[IRTempoEvent(ticks=0, bpm=tempo)],
            layers=layer_info,
        ).canonicalize()

        # Convert to MIDI events
        midi_events_final = [
            MidiEvent(
                pitch=note.pitch,
                start_ticks=note.start_ticks,
                duration_ticks=note.duration_ticks,
                velocity=note.velocity,
                channel=note.channel,
            )
            for note in score_ir.notes
        ]

        midi_file = events_to_midi(midi_events_final, tempo_bpm=tempo)

        return CompileResult(
            midi_file=midi_file,
            score_ir=score_ir,
            total_bars=section.bars,
            total_events=len(score_ir.notes),
            layers_compiled=layers_compiled,
            sections_compiled=[section_name],
        )

    def _compile_layer_pattern(
        self,
        pattern: Pattern,
        context: CompileContext,
        bars: int,
        level: float,
    ) -> list[MidiEvent]:
        """Compile a pattern for a layer, applying level adjustment."""
        events = self.pattern_compiler.compile(pattern, context, bars)

        # Apply level adjustment to velocity
        if level != 1.0:
            adjusted_events = []
            for event in events:
                adjusted_velocity = max(0, min(127, int(event.velocity * level)))
                adjusted_events.append(
                    MidiEvent(
                        pitch=event.pitch,
                        start_ticks=event.start_ticks,
                        duration_ticks=event.duration_ticks,
                        velocity=adjusted_velocity,
                        channel=event.channel,
                    )
                )
            return adjusted_events

        return events

    def _has_soloed_layers(self, arrangement: Arrangement) -> bool:
        """Check if any layer is soloed."""
        return any(layer.solo for layer in arrangement.layers.values())

    def _parse_harmonic_rhythm(self, rhythm_str: str) -> Duration:
        """Parse a harmonic rhythm string to Duration."""
        from fractions import Fraction

        rhythm_map = {
            "1bar": Duration.WHOLE,
            "2bar": Duration(Fraction(8)),  # 4 beats = 1 bar in 4/4, so 2 bars = 8 beats
            "half": Duration.HALF,
            "quarter": Duration.QUARTER,
            "2beats": Duration.HALF,
            "4beats": Duration.WHOLE,
        }
        return rhythm_map.get(rhythm_str, Duration.WHOLE)


def compile_arrangement(
    arrangement: Arrangement,
    pattern_registry: PatternRegistry,
    output_path: Path | str | None = None,
) -> CompileResult:
    """
    Convenience function to compile an arrangement.

    Args:
        arrangement: Arrangement to compile
        pattern_registry: Pattern registry
        output_path: Optional path to save MIDI file

    Returns:
        CompileResult with MIDI file
    """
    compiler = ArrangementCompiler(pattern_registry)
    result = compiler.compile(arrangement)

    if output_path:
        result.midi_file.save(str(output_path))

    return result
