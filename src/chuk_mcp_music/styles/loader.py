"""
Style loader - discovers and loads style constraint bundles.

Styles can come from:
1. Built-in library (shipped with package)
2. Project styles (user's project/styles directory)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from chuk_mcp_music.models.style import (
    EnergyConstraints,
    EnergyMapping,
    ForbiddenElements,
    HarmonyDensity,
    KeyPreference,
    LayerHint,
    PercussionDensity,
    StructureHints,
    Style,
    StyleMetadata,
    TempoRange,
)


class StyleLoader:
    """
    Discovers and loads style definitions.

    Styles are loaded from YAML files in the library and project directories.
    Project styles override library styles with the same name.
    """

    def __init__(
        self,
        library_path: Path | None = None,
        project_path: Path | None = None,
    ):
        """
        Initialize the style loader.

        Args:
            library_path: Path to built-in style library
            project_path: Path to project styles directory
        """
        self.library_path = library_path or (Path(__file__).parent / "library")
        self.project_path = project_path
        self._cache: dict[str, Style] = {}

    def list_styles(self) -> list[StyleMetadata]:
        """
        List all available styles.

        Returns styles from both library and project, with project
        styles taking precedence.
        """
        styles: dict[str, StyleMetadata] = {}

        # Load library styles
        if self.library_path.exists():
            for path in self.library_path.glob("*.yaml"):
                style = self._load_style_file(path)
                if style:
                    styles[style.name] = StyleMetadata.from_style(style)

        # Load project styles (override library)
        if self.project_path and self.project_path.exists():
            for path in self.project_path.glob("*.yaml"):
                style = self._load_style_file(path)
                if style:
                    styles[style.name] = StyleMetadata.from_style(style)

        return list(styles.values())

    def get_style(self, name: str) -> Style | None:
        """
        Get a style by name.

        Project styles take precedence over library styles.

        Args:
            name: Style name

        Returns:
            Style if found, None otherwise
        """
        # Check cache
        if name in self._cache:
            return self._cache[name]

        # Try project first
        if self.project_path:
            project_file = self.project_path / f"{name}.yaml"
            if project_file.exists():
                style = self._load_style_file(project_file)
                if style:
                    self._cache[name] = style
                    return style

        # Fall back to library
        if self.library_path.exists():
            library_file = self.library_path / f"{name}.yaml"
            if library_file.exists():
                style = self._load_style_file(library_file)
                if style:
                    self._cache[name] = style
                    return style

        return None

    def copy_to_project(self, name: str) -> Path | None:
        """
        Copy a library style to the project for customization.

        Args:
            name: Style name

        Returns:
            Path to copied file, or None if not found
        """
        if not self.project_path:
            raise ValueError("No project path configured")

        # Find in library
        library_file = self.library_path / f"{name}.yaml"
        if not library_file.exists():
            return None

        # Create project styles directory
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Copy file
        dest_file = self.project_path / f"{name}.yaml"
        if dest_file.exists():
            raise ValueError(f"Style already exists in project: {name}")

        dest_file.write_text(library_file.read_text())

        # Invalidate cache
        self._cache.pop(name, None)

        return dest_file

    def _load_style_file(self, path: Path) -> Style | None:
        """Load a style from a YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            return self._parse_style(data)
        except Exception:
            return None

    def _parse_style(self, data: dict[str, Any]) -> Style:
        """Parse style from YAML data."""
        # Parse tokens
        tokens = data.get("tokens", {})
        tempo_data = tokens.get("tempo", {})

        tempo_range = tempo_data.get("range", [60, 200])
        tempo = TempoRange(
            min_bpm=tempo_range[0] if tempo_range else 60,
            max_bpm=tempo_range[1] if len(tempo_range) > 1 else 200,
            default_bpm=tempo_data.get("default", 120),
        )

        key_pref_str = tokens.get("key_preference", "any")
        key_preference = KeyPreference(key_pref_str)

        # Parse energy mapping
        energy_data = data.get("energy_mapping", {})
        energy_mapping = self._parse_energy_mapping(energy_data)

        # Parse layer hints
        layer_hints_data = data.get("layer_hints", {})
        layer_hints = {
            role: self._parse_layer_hint(hint_data) for role, hint_data in layer_hints_data.items()
        }

        # Parse structure hints
        structure_data = data.get("structure_hints", {})
        structure_hints = self._parse_structure_hints(structure_data)

        # Parse forbidden elements
        forbidden_data = data.get("forbidden", {})
        forbidden = ForbiddenElements(
            patterns=forbidden_data.get("patterns", []),
            progressions=forbidden_data.get("progressions", []),
        )

        return Style(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            tempo=tempo,
            key_preference=key_preference,
            time_signature=tokens.get("time_signature", "4/4"),
            energy_mapping=energy_mapping,
            layer_hints=layer_hints,
            structure_hints=structure_hints,
            forbidden=forbidden,
        )

    def _parse_energy_mapping(self, data: dict[str, Any]) -> EnergyMapping:
        """Parse energy mapping from YAML data."""

        def parse_constraints(cdata: dict[str, Any]) -> EnergyConstraints:
            layers = cdata.get("layers", [1, 5])
            return EnergyConstraints(
                layers=(layers[0], layers[1]) if len(layers) >= 2 else (1, 5),
                percussion=PercussionDensity(cdata.get("percussion", "standard")),
                harmony_density=HarmonyDensity(cdata.get("harmony_density", "moderate")),
                velocity_range=tuple(cdata.get("velocity_range", [0.5, 1.0])),
            )

        return EnergyMapping(
            lowest=parse_constraints(data.get("lowest", {})),
            low=parse_constraints(data.get("low", {})),
            medium=parse_constraints(data.get("medium", {})),
            high=parse_constraints(data.get("high", {})),
            highest=parse_constraints(data.get("highest", {})),
        )

    def _parse_layer_hint(self, data: dict[str, Any]) -> LayerHint:
        """Parse layer hint from YAML data."""
        return LayerHint(
            suggested=data.get("suggested", []),
            avoid=data.get("avoid", []),
            register=data.get("register"),
            density=data.get("density"),
        )

    def _parse_structure_hints(self, data: dict[str, Any]) -> StructureHints:
        """Parse structure hints from YAML data."""
        typical_length = data.get("typical_length_bars", [32, 128])
        intro_bars = data.get("intro_bars", [4, 16])
        outro_bars = data.get("outro_bars", [4, 16])

        return StructureHints(
            breakdown_required=data.get("breakdown_required", False),
            typical_length_bars=(
                typical_length[0] if typical_length else 32,
                typical_length[1] if len(typical_length) > 1 else 128,
            ),
            intro_bars=(
                intro_bars[0] if intro_bars else 4,
                intro_bars[1] if len(intro_bars) > 1 else 16,
            ),
            outro_bars=(
                outro_bars[0] if outro_bars else 4,
                outro_bars[1] if len(outro_bars) > 1 else 16,
            ),
            section_multiples=data.get("section_multiples", 4),
        )

    def clear_cache(self) -> None:
        """Clear the style cache."""
        self._cache.clear()
