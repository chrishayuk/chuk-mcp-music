#!/usr/bin/env python3
"""
Example: Score IR Round-Trip Workflow.

This demonstrates the intermediate representation (Score IR) and its
round-trip capabilities - the key to inspectable, diffable, modifiable
music compilation.

Usage:
    python examples/score_ir_roundtrip.py

This example shows:
1. Compiling an arrangement to Score IR (instead of directly to MIDI)
2. Inspecting the IR - understanding what notes were generated and why
3. Modifying the IR - filtering layers, adjusting velocity, transposing
4. Emitting MIDI from the modified IR

The Score IR is the "contract" between arrangement and MIDI:
    Arrangement YAML → Score IR (diffable, versioned) → MIDI

Same arrangement → same Score IR → same MIDI. Always.
"""

import json
from pathlib import Path

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.compiler import ArrangementCompiler
from chuk_mcp_music.compiler.midi import score_ir_to_midi
from chuk_mcp_music.compiler.score_ir import IRNote, ScoreIR
from chuk_mcp_music.patterns import PatternRegistry


async def main() -> None:
    """Demonstrate the Score IR round-trip workflow."""
    # Paths
    examples_dir = Path(__file__).parent
    output_dir = examples_dir / "output"
    output_dir.mkdir(exist_ok=True)

    arrangement_file = examples_dir / "demo.arrangement.yaml"
    library_path = Path(__file__).parent.parent / "src/chuk_mcp_music/patterns/library"

    print("CHUK Music Score IR Round-Trip Demo")
    print("=" * 50)
    print()

    # Initialize components
    manager = ArrangementManager(examples_dir)
    registry = PatternRegistry(library_path=library_path)
    compiler = ArrangementCompiler(registry)

    # Load the arrangement
    print("1. Loading arrangement...")
    arrangement = await manager.load(arrangement_file)
    print(f"   Name: {arrangement.name}")
    print(f"   Key: {arrangement.context.key}")
    print(f"   Tempo: {arrangement.context.tempo} BPM")
    print()

    # Step 1: Compile to Score IR (not directly to MIDI)
    print("2. Compiling to Score IR...")
    result = compiler.compile(arrangement)
    score_ir = result.score_ir

    print(f"   Schema: {score_ir.schema}")
    print(f"   Total notes: {score_ir.note_count()}")
    print(f"   Total bars: {score_ir.total_bars}")
    print()

    # Step 2: Inspect the IR
    print("3. Inspecting the IR...")
    summary = score_ir.summary()
    print(f"   Layers: {summary['layers']}")
    print(f"   Pitch range: {summary['pitch_range']}")
    print(f"   Velocity range: {summary['velocity_range']}")
    print()

    # Show note provenance - where each note came from
    print("   Sample notes with provenance:")
    for note in score_ir.notes[:5]:
        print(
            f"     pitch={note.pitch}, bar={note.bar}, beat={note.beat:.1f} "
            f"← {note.source_layer}/{note.source_pattern} in {note.source_section}"
        )
    print()

    # Step 3: Save the full IR as JSON (for diffing, golden-file testing)
    print("4. Saving Score IR as JSON...")
    ir_json_path = output_dir / "demo_score_ir.json"
    with open(ir_json_path, "w") as f:
        json.dump(score_ir.to_dict(), f, indent=2)
    print(f"   Saved to: {ir_json_path}")
    print()

    # Step 4: Emit MIDI from the original IR
    print("5. Emitting MIDI from Score IR...")
    midi_file = score_ir_to_midi(score_ir)
    midi_path = output_dir / "demo_from_ir.mid"
    midi_file.save(str(midi_path))
    print(f"   Saved to: {midi_path}")
    print()

    # Step 5: Modify the IR - extract just the bass layer
    print("6. Extracting bass layer stem...")
    bass_notes = [n for n in score_ir.notes if n.source_layer == "bass"]
    bass_ir = ScoreIR(
        schema=score_ir.schema,
        name=f"{score_ir.name}_bass_stem",
        key=score_ir.key,
        tempo=score_ir.tempo,
        time_signature=score_ir.time_signature,
        ticks_per_beat=score_ir.ticks_per_beat,
        total_ticks=score_ir.total_ticks,
        total_bars=score_ir.total_bars,
        notes=bass_notes,
        sections=score_ir.sections,
    ).canonicalize()

    bass_midi = score_ir_to_midi(bass_ir)
    bass_path = output_dir / "demo_bass_stem.mid"
    bass_midi.save(str(bass_path))
    print(f"   Bass notes: {len(bass_notes)}")
    print(f"   Saved to: {bass_path}")
    print()

    # Step 6: Modify the IR - extract drums only
    print("7. Extracting drums layer stem...")
    drum_notes = [n for n in score_ir.notes if n.source_layer == "drums"]
    drums_ir = ScoreIR(
        schema=score_ir.schema,
        name=f"{score_ir.name}_drums_stem",
        key=score_ir.key,
        tempo=score_ir.tempo,
        time_signature=score_ir.time_signature,
        ticks_per_beat=score_ir.ticks_per_beat,
        total_ticks=score_ir.total_ticks,
        total_bars=score_ir.total_bars,
        notes=drum_notes,
        sections=score_ir.sections,
    ).canonicalize()

    drums_midi = score_ir_to_midi(drums_ir)
    drums_path = output_dir / "demo_drums_stem.mid"
    drums_midi.save(str(drums_path))
    print(f"   Drum notes: {len(drum_notes)}")
    print(f"   Saved to: {drums_path}")
    print()

    # Step 7: Transpose the bass up an octave
    print("8. Transposing bass up an octave...")
    transposed_bass_notes = [
        IRNote(
            start_ticks=n.start_ticks,
            channel=n.channel,
            pitch=min(127, n.pitch + 12),  # +12 semitones = 1 octave
            duration_ticks=n.duration_ticks,
            velocity=n.velocity,
            source_layer=n.source_layer,
            source_pattern=n.source_pattern,
            source_section=n.source_section,
            bar=n.bar,
            beat=n.beat,
        )
        for n in bass_notes
    ]
    transposed_ir = ScoreIR(
        schema=score_ir.schema,
        name=f"{score_ir.name}_bass_high",
        key=score_ir.key,
        tempo=score_ir.tempo,
        time_signature=score_ir.time_signature,
        ticks_per_beat=score_ir.ticks_per_beat,
        total_ticks=score_ir.total_ticks,
        total_bars=score_ir.total_bars,
        notes=transposed_bass_notes,
        sections=score_ir.sections,
    ).canonicalize()

    transposed_midi = score_ir_to_midi(transposed_ir)
    transposed_path = output_dir / "demo_bass_high.mid"
    transposed_midi.save(str(transposed_path))
    print(
        f"   Original pitch range: {min(n.pitch for n in bass_notes)}-{max(n.pitch for n in bass_notes)}"
    )
    print(
        f"   Transposed pitch range: {min(n.pitch for n in transposed_bass_notes)}-"
        f"{max(n.pitch for n in transposed_bass_notes)}"
    )
    print(f"   Saved to: {transposed_path}")
    print()

    # Step 8: Reduce velocity (dynamics) for a softer mix
    print("9. Creating softer mix (50% velocity)...")
    soft_notes = [
        IRNote(
            start_ticks=n.start_ticks,
            channel=n.channel,
            pitch=n.pitch,
            duration_ticks=n.duration_ticks,
            velocity=max(1, int(n.velocity * 0.5)),  # 50% velocity
            source_layer=n.source_layer,
            source_pattern=n.source_pattern,
            source_section=n.source_section,
            bar=n.bar,
            beat=n.beat,
        )
        for n in score_ir.notes
    ]
    soft_ir = ScoreIR(
        schema=score_ir.schema,
        name=f"{score_ir.name}_soft",
        key=score_ir.key,
        tempo=score_ir.tempo,
        time_signature=score_ir.time_signature,
        ticks_per_beat=score_ir.ticks_per_beat,
        total_ticks=score_ir.total_ticks,
        total_bars=score_ir.total_bars,
        notes=soft_notes,
        sections=score_ir.sections,
    ).canonicalize()

    soft_midi = score_ir_to_midi(soft_ir)
    soft_path = output_dir / "demo_soft.mid"
    soft_midi.save(str(soft_path))
    print(f"   Original velocity range: {summary['velocity_range']}")
    soft_summary = soft_ir.summary()
    print(f"   Soft velocity range: {soft_summary['velocity_range']}")
    print(f"   Saved to: {soft_path}")
    print()

    # Step 9: Demonstrate diffing two IRs
    print("10. Diffing original vs. soft mix...")
    diff = score_ir.diff_summary(soft_ir)
    print(f"    Notes in both: {diff['notes_unchanged']}")
    print(f"    Tempo changed: {diff['tempo_changed']}")
    print(f"    Key changed: {diff['key_changed']}")
    print()

    print("=" * 50)
    print("Summary of generated files:")
    print(f"  - {ir_json_path.name}: Score IR as JSON (for inspection/diffing)")
    print(f"  - {midi_path.name}: Full MIDI from IR")
    print(f"  - {bass_path.name}: Bass layer only")
    print(f"  - {drums_path.name}: Drums layer only")
    print(f"  - {transposed_path.name}: Bass transposed +1 octave")
    print(f"  - {soft_path.name}: All notes at 50% velocity")
    print()
    print("The Score IR enables:")
    print("  - Inspecting what notes were generated and why")
    print("  - Extracting stems without re-rendering")
    print("  - Post-compilation modifications (transpose, velocity, filter)")
    print("  - Golden-file testing (same input → same IR → same MIDI)")
    print("  - Diffing two arrangements to see what changed")
    print()
    print("Done! Open the MIDI files in your DAW to hear them.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
