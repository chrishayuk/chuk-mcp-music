#!/usr/bin/env python3
"""
Example: Compile an arrangement YAML to MIDI.

This demonstrates the full pipeline from arrangement definition to playable MIDI.

Usage:
    python examples/compile_arrangement.py
    # Creates: examples/output/demo.mid

This is the "Hello World" for chuk-mcp-music - proving that:
1. YAML arrangement can be loaded
2. Patterns are resolved and compiled
3. Harmony context drives note generation
4. Output is a valid, playable MIDI file
"""

from pathlib import Path

from chuk_mcp_music.arrangement import ArrangementManager
from chuk_mcp_music.compiler import ArrangementCompiler
from chuk_mcp_music.patterns import PatternRegistry


async def main() -> None:
    """Compile the demo arrangement to MIDI."""
    # Paths
    examples_dir = Path(__file__).parent
    output_dir = examples_dir / "output"
    output_dir.mkdir(exist_ok=True)

    arrangement_file = examples_dir / "demo.arrangement.yaml"
    library_path = Path(__file__).parent.parent / "src/chuk_mcp_music/patterns/library"

    print("CHUK Music Arrangement Compiler")
    print("=" * 40)
    print(f"Arrangement: {arrangement_file.name}")
    print(f"Pattern library: {library_path}")
    print()

    # Initialize components
    manager = ArrangementManager(examples_dir)
    registry = PatternRegistry(library_path=library_path)

    # Load the arrangement
    print("Loading arrangement...")
    arrangement = await manager.load(arrangement_file)
    print(f"  Name: {arrangement.name}")
    print(f"  Key: {arrangement.context.key}")
    print(f"  Tempo: {arrangement.context.tempo} BPM")
    print(f"  Sections: {len(arrangement.sections)}")
    print(f"  Layers: {len(arrangement.layers)}")
    print(f"  Total bars: {arrangement.total_bars()}")
    print()

    # Show structure
    print("Structure:")
    for section in arrangement.sections:
        energy = section.energy.value if section.energy else "unset"
        print(f"  {section.name}: {section.bars} bars (energy: {energy})")
    print()

    # Show layers
    print("Layers:")
    for name, layer in arrangement.layers.items():
        patterns = list(layer.patterns.keys())
        print(f"  {name} ({layer.role.value}): patterns={patterns}")
    print()

    # Compile to MIDI
    print("Compiling to MIDI...")
    compiler = ArrangementCompiler(registry)
    result = compiler.compile(arrangement)

    output_path = output_dir / "demo.mid"
    result.midi_file.save(str(output_path))

    print(f"  Total events: {result.total_events}")
    print(f"  Total bars: {result.total_bars}")
    print(f"  Layers compiled: {result.layers_compiled}")
    print(f"  Sections compiled: {result.sections_compiled}")
    print()
    print(f"Output: {output_path}")
    print()

    # Also compile individual sections for preview
    print("Compiling section previews...")
    for section in arrangement.sections[:3]:  # First 3 sections as demo
        section_result = compiler.compile_section(arrangement, section.name)
        section_path = output_dir / f"demo_{section.name}.mid"
        section_result.midi_file.save(str(section_path))
        print(f"  {section.name}: {section_result.total_events} events -> {section_path.name}")

    print()
    print("Done! Open the MIDI files in your DAW to hear them.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
