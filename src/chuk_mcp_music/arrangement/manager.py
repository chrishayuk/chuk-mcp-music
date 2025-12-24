"""
Arrangement Manager - handles arrangement lifecycle.

Provides async operations for creating, loading, saving, and managing arrangements.
Integrates with the artifact store for persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from chuk_mcp_music.models.arrangement import (
    Arrangement,
    ArrangementContext,
    EnergyLevel,
    LayerRole,
    PatternRef,
)


class ArrangementMetadata:
    """Lightweight metadata for listing arrangements."""

    def __init__(
        self,
        name: str,
        path: Path,
        key: str,
        tempo: int,
        total_bars: int,
        layer_count: int,
        modified: datetime,
    ):
        self.name = name
        self.path = path
        self.key = key
        self.tempo = tempo
        self.total_bars = total_bars
        self.layer_count = layer_count
        self.modified = modified

    def __repr__(self) -> str:
        return f"ArrangementMetadata({self.name!r}, {self.key}, {self.tempo}bpm)"


class ArrangementManager:
    """
    Manages arrangement lifecycle with file persistence.

    Provides methods to create, load, save, and list arrangements.
    All I/O operations are async-ready.
    """

    def __init__(self, arrangements_dir: Path):
        """
        Initialize the manager.

        Args:
            arrangements_dir: Directory for storing arrangement files
        """
        self.arrangements_dir = arrangements_dir
        self._cache: dict[str, Arrangement] = {}

    async def create(
        self,
        name: str,
        key: str,
        tempo: int,
        time_signature: str = "4/4",
        style: str | None = None,
    ) -> Arrangement:
        """
        Create a new arrangement.

        Args:
            name: Arrangement name
            key: Key (e.g., 'C_major', 'D_minor')
            tempo: Tempo in BPM
            time_signature: Time signature (default: '4/4')
            style: Optional style constraint bundle

        Returns:
            The created Arrangement
        """
        context = ArrangementContext(
            key=key,
            tempo=tempo,
            time_signature=time_signature,
            style=style,
        )

        arrangement = Arrangement(
            name=name,
            context=context,
        )

        self._cache[name] = arrangement
        return arrangement

    async def get(self, name: str) -> Arrangement | None:
        """
        Get an arrangement by name.

        Checks cache first, then loads from file if not cached.

        Args:
            name: Arrangement name

        Returns:
            The Arrangement or None if not found
        """
        # Check cache
        if name in self._cache:
            return self._cache[name]

        # Try to load from file
        path = self._get_path(name)
        if path.exists():
            arrangement = await self.load(path)
            self._cache[name] = arrangement
            return arrangement

        return None

    async def save(self, arrangement: Arrangement) -> Path:
        """
        Save an arrangement to disk.

        Args:
            arrangement: The arrangement to save

        Returns:
            Path to the saved file
        """
        # Ensure directory exists
        self.arrangements_dir.mkdir(parents=True, exist_ok=True)

        # Update modification time
        arrangement.modified = datetime.now(UTC)

        # Convert to YAML
        yaml_dict = arrangement.to_yaml_dict()
        path = self._get_path(arrangement.name)

        with open(path, "w") as f:
            yaml.safe_dump(yaml_dict, f, default_flow_style=False, sort_keys=False)

        # Update cache
        self._cache[arrangement.name] = arrangement

        return path

    async def load(self, path: Path) -> Arrangement:
        """
        Load an arrangement from a file.

        Args:
            path: Path to the arrangement file

        Returns:
            The loaded Arrangement
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        arrangement = Arrangement.from_yaml_dict(data)
        self._cache[arrangement.name] = arrangement
        return arrangement

    async def list_arrangements(self) -> list[ArrangementMetadata]:
        """
        List all arrangements in the directory.

        Returns:
            List of arrangement metadata
        """
        if not self.arrangements_dir.exists():
            return []

        result = []
        for path in self.arrangements_dir.glob("*.arrangement.yaml"):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)

                sections = data.get("sections", [])
                total_bars = sum(s.get("bars", 0) for s in sections)

                result.append(
                    ArrangementMetadata(
                        name=data.get("name", path.stem),
                        path=path,
                        key=data.get("context", {}).get("key", "C_major"),
                        tempo=data.get("context", {}).get("tempo", 120),
                        total_bars=total_bars,
                        layer_count=len(data.get("layers", {})),
                        modified=datetime.fromtimestamp(path.stat().st_mtime),
                    )
                )
            except Exception:
                # Skip files that can't be parsed
                continue

        return sorted(result, key=lambda m: m.modified, reverse=True)

    async def delete(self, name: str) -> bool:
        """
        Delete an arrangement.

        Args:
            name: Arrangement name

        Returns:
            True if deleted, False if not found
        """
        path = self._get_path(name)

        if path.exists():
            path.unlink()
            self._cache.pop(name, None)
            return True

        return False

    async def duplicate(self, name: str, new_name: str) -> Arrangement:
        """
        Duplicate an arrangement with a new name.

        Args:
            name: Original arrangement name
            new_name: New arrangement name

        Returns:
            The duplicated Arrangement
        """
        original = await self.get(name)
        if original is None:
            raise ValueError(f"Arrangement not found: {name}")

        # Create a copy with new name
        new_arrangement = Arrangement(
            name=new_name,
            context=original.context,
            harmony=original.harmony,
            sections=list(original.sections),
            layers=dict(original.layers),
        )

        self._cache[new_name] = new_arrangement
        return new_arrangement

    def _get_path(self, name: str) -> Path:
        """Get the file path for an arrangement."""
        # Sanitize name for filename
        safe_name = name.replace(" ", "_").replace("/", "_")
        return self.arrangements_dir / f"{safe_name}.arrangement.yaml"

    # Convenience methods for arrangement operations

    async def add_section(
        self,
        name: str,
        section_name: str,
        bars: int,
        energy: str | None = None,
        position: int | None = None,
    ) -> Arrangement:
        """
        Add a section to an arrangement.

        Args:
            name: Arrangement name
            section_name: Section name
            bars: Number of bars
            energy: Optional energy level
            position: Optional position

        Returns:
            The updated Arrangement
        """
        arrangement = await self.get(name)
        if arrangement is None:
            raise ValueError(f"Arrangement not found: {name}")

        energy_level = EnergyLevel(energy) if energy else None
        arrangement.add_section(section_name, bars, energy_level, position)
        return arrangement

    async def add_layer(
        self,
        name: str,
        layer_name: str,
        role: str,
        channel: int | None = None,
    ) -> Arrangement:
        """
        Add a layer to an arrangement.

        Args:
            name: Arrangement name
            layer_name: Layer name
            role: Layer role
            channel: Optional MIDI channel

        Returns:
            The updated Arrangement
        """
        arrangement = await self.get(name)
        if arrangement is None:
            raise ValueError(f"Arrangement not found: {name}")

        arrangement.add_layer(layer_name, LayerRole(role), channel)
        return arrangement

    async def assign_pattern(
        self,
        name: str,
        layer_name: str,
        pattern_alias: str,
        pattern_ref: str,
        variant: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Arrangement:
        """
        Assign a pattern to a layer.

        Args:
            name: Arrangement name
            layer_name: Layer name
            pattern_alias: Alias for this pattern in the layer
            pattern_ref: Pattern reference (e.g., 'bass/root-pulse')
            variant: Optional variant name
            params: Optional parameter overrides

        Returns:
            The updated Arrangement
        """
        arrangement = await self.get(name)
        if arrangement is None:
            raise ValueError(f"Arrangement not found: {name}")

        layer = arrangement.get_layer(layer_name)
        if layer is None:
            raise ValueError(f"Layer not found: {layer_name}")

        layer.patterns[pattern_alias] = PatternRef(
            ref=pattern_ref,
            variant=variant,
            params=params or {},
        )
        arrangement.modified = datetime.now(UTC)
        return arrangement

    async def arrange_layer(
        self,
        name: str,
        layer_name: str,
        section_patterns: dict[str, str | None],
    ) -> Arrangement:
        """
        Set what patterns play in which sections for a layer.

        Args:
            name: Arrangement name
            layer_name: Layer name
            section_patterns: Mapping of section name to pattern alias (or None)

        Returns:
            The updated Arrangement
        """
        arrangement = await self.get(name)
        if arrangement is None:
            raise ValueError(f"Arrangement not found: {name}")

        layer = arrangement.get_layer(layer_name)
        if layer is None:
            raise ValueError(f"Layer not found: {layer_name}")

        layer.arrangement.update(section_patterns)
        arrangement.modified = datetime.now(UTC)
        return arrangement

    async def set_harmony(
        self,
        name: str,
        section_name: str | None,
        progression: list[str],
        harmonic_rhythm: str = "1bar",
    ) -> Arrangement:
        """
        Set harmony for a section or default.

        Args:
            name: Arrangement name
            section_name: Section name (None for default)
            progression: Chord progression as Roman numerals
            harmonic_rhythm: Harmonic rhythm

        Returns:
            The updated Arrangement
        """
        from chuk_mcp_music.models.arrangement import HarmonyProgression

        arrangement = await self.get(name)
        if arrangement is None:
            raise ValueError(f"Arrangement not found: {name}")

        if section_name is None:
            arrangement.harmony.default_progression = progression
            arrangement.harmony.harmonic_rhythm = harmonic_rhythm
        else:
            arrangement.harmony.sections[section_name] = HarmonyProgression(
                progression=progression,
                harmonic_rhythm=harmonic_rhythm,
            )

        arrangement.modified = datetime.now(UTC)
        return arrangement
