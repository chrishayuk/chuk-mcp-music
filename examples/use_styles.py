#!/usr/bin/env python3
"""
Example: Using the Style System.

This demonstrates how styles provide constraint bundles for music composition.
Styles narrow the solution space without forcing specific choices - they're
like design tokens for genre/mood constraints.

Usage:
    python examples/use_styles.py
"""

import tempfile
from pathlib import Path

from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.models.pattern import Pattern, PatternEvent, PatternTemplate
from chuk_mcp_music.styles import StyleLoader, StyleResolver, ViolationSeverity


def main() -> None:
    """Demonstrate the style system."""
    print("CHUK Music Style System Demo")
    print("=" * 40)
    print()

    # Load styles from the library
    library_path = Path(__file__).parent.parent / "src/chuk_mcp_music/styles/library"

    with tempfile.TemporaryDirectory() as tmp:
        loader = StyleLoader(library_path=library_path, project_path=Path(tmp))

        # List available styles
        print("Available styles:")
        for style_meta in loader.list_styles():
            tempo_range = f"{style_meta.tempo_range[0]}-{style_meta.tempo_range[1]} BPM"
            print(f"  {style_meta.name}: {style_meta.description[:50]}...")
            print(f"    Tempo: {tempo_range}, Key: {style_meta.key_preference.value}")
        print()

        # Load melodic-techno style
        style = loader.get_style("melodic-techno")
        if not style:
            print("Failed to load style")
            return

        print(f"Using style: {style.name}")
        print(f"  Description: {style.description}")
        print(f"  Tempo range: {style.tempo.min_bpm}-{style.tempo.max_bpm} BPM")
        print(f"  Key preference: {style.key_preference.value}")
        print(f"  Breakdown required: {style.structure_hints.breakdown_required}")
        print()

        # Create a resolver for this style
        resolver = StyleResolver(style)

        # Check what energy levels recommend
        print("Energy level recommendations:")
        for level in ["lowest", "low", "medium", "high", "highest"]:
            constraints = resolver.resolve_energy(level)
            print(f"  {level}:")
            print(f"    Layers: {constraints.layers[0]}-{constraints.layers[1]} active")
            print(f"    Percussion: {constraints.percussion.value}")
            print(
                f"    Velocity: {constraints.velocity_range[0]:.1f}-{constraints.velocity_range[1]:.1f}"
            )
        print()

        # Layer hints
        print("Layer hints for bass:")
        bass_hint = style.get_layer_hint(LayerRole.BASS)
        print(f"  Suggested: {bass_hint.suggested}")
        print(f"  Avoid: {bass_hint.avoid}")
        print(f"  Register: {bass_hint.pitch_register}")
        print()

        # Validate tempo
        print("Tempo validation:")
        for tempo in [100, 124, 140]:
            violations = resolver.validate_tempo(tempo)
            status = "✓" if not violations else "✗ " + violations[0].message
            print(f"  {tempo} BPM: {status}")
        print()

        # Validate structure
        print("Structure validation:")
        good_structure = {"intro": 8, "verse": 16, "breakdown": 8, "chorus": 16}
        violations = resolver.validate_structure(good_structure, has_breakdown=True)
        print(f"  With breakdown (8+16+8+16 bars): {'✓ Valid' if not violations else '✗ Issues'}")

        bad_structure = {"intro": 7, "verse": 16, "chorus": 16}
        violations = resolver.validate_structure(bad_structure, has_breakdown=False)
        warnings = [v for v in violations if v.severity == ViolationSeverity.WARNING]
        print(f"  Without breakdown (7+16+16 bars): {len(warnings)} warnings")
        for w in warnings[:2]:
            print(f"    - {w.message}")
        print()

        # Pattern validation
        print("Pattern validation:")

        # A good pattern
        good_pattern = Pattern(
            id="bass/root-pulse",
            name="root-pulse",
            description="Simple root note pulse",
            role=LayerRole.BASS,
            template=PatternTemplate(
                bars=1,
                events=[
                    PatternEvent(beat=0, duration=0.5, pitch="root", velocity=0.8),
                ],
            ),
        )
        violations = resolver.validate_pattern(good_pattern, LayerRole.BASS)
        print(f"  bass/root-pulse: {'✓ Suggested' if not violations else '✗ Issues'}")

        # A forbidden pattern
        forbidden_pattern = Pattern(
            id="drums/trap-hihat",
            name="trap-hihat",
            description="Trap-style rolling hi-hats",
            role=LayerRole.DRUMS,
            template=PatternTemplate(bars=1, events=[]),
        )
        violations = resolver.validate_pattern(forbidden_pattern, LayerRole.DRUMS)
        errors = [v for v in violations if v.severity == ViolationSeverity.ERROR]
        print(f"  drums/trap-hihat: {'✗ Forbidden' if errors else '✓ OK'}")
        if errors:
            print(f"    - {errors[0].message}")
        print()

        # Copying styles for customization
        print("Copying style to project for customization:")
        copied_path = loader.copy_to_project("ambient")
        if copied_path:
            print(f"  Copied to: {copied_path}")
            print("  You can now edit this file to customize the style!")
        print()

        print("Done! Use styles to guide AI-assisted music composition.")


if __name__ == "__main__":
    main()
