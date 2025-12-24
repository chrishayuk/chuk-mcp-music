"""
Pattern Registry - discovers and loads patterns.

The registry provides access to both the built-in library patterns
and user-owned patterns in a project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from chuk_mcp_music.models.arrangement import LayerRole
from chuk_mcp_music.models.pattern import (
    Pattern,
    PatternConstraints,
    PatternEvent,
    PatternMetadata,
    PatternParameter,
    PatternTemplate,
    PatternVariant,
)


class PatternRegistry:
    """
    Discovers and loads patterns from library and project.

    The registry maintains a cache of loaded patterns and provides
    filtering by role and style.
    """

    def __init__(
        self,
        library_path: Path | None = None,
        project_path: Path | None = None,
    ):
        """
        Initialize the registry.

        Args:
            library_path: Path to built-in pattern library
            project_path: Path to project patterns (user-owned)
        """
        self.library_path = library_path
        self.project_path = project_path
        self._cache: dict[str, Pattern] = {}
        self._metadata_cache: dict[str, PatternMetadata] = {}

    def list_patterns(
        self,
        role: LayerRole | None = None,
        style: str | None = None,
    ) -> list[PatternMetadata]:
        """
        List available patterns with optional filtering.

        Args:
            role: Filter by layer role
            style: Filter by compatible style

        Returns:
            List of pattern metadata
        """
        self._ensure_metadata_loaded()

        result = list(self._metadata_cache.values())

        # Filter by role
        if role:
            result = [m for m in result if m.role == role]

        # Filter by style (would need to load full pattern to check)
        # For now, skip style filtering at metadata level

        return sorted(result, key=lambda m: m.name)

    def get_pattern(self, pattern_id: str) -> Pattern | None:
        """
        Get a pattern by ID.

        Pattern ID is in format: role/name (e.g., 'bass/root-pulse')

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern or None if not found
        """
        # Check cache
        if pattern_id in self._cache:
            return self._cache[pattern_id]

        # Try to load
        pattern = self._load_pattern(pattern_id)
        if pattern:
            self._cache[pattern_id] = pattern

        return pattern

    def get_pattern_metadata(self, pattern_id: str) -> PatternMetadata | None:
        """
        Get metadata for a pattern.

        Args:
            pattern_id: Pattern identifier

        Returns:
            PatternMetadata or None if not found
        """
        self._ensure_metadata_loaded()
        return self._metadata_cache.get(pattern_id)

    def copy_to_project(self, pattern_id: str) -> Path | None:
        """
        Copy a library pattern to the project (the shadcn 'add' moment).

        Args:
            pattern_id: Pattern identifier

        Returns:
            Path to copied pattern, or None if source not found
        """
        if not self.project_path:
            raise ValueError("No project path configured")

        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return None

        # Determine target path
        role_dir = self.project_path / pattern.role.value
        role_dir.mkdir(parents=True, exist_ok=True)

        target_path = role_dir / f"{pattern.name}.yaml"

        # Write pattern to project
        yaml_dict = self._pattern_to_yaml_dict(pattern)
        with open(target_path, "w") as f:
            yaml.safe_dump(yaml_dict, f, default_flow_style=False, sort_keys=False)

        # Clear caches so project pattern takes precedence
        self._cache.pop(pattern_id, None)
        self._metadata_cache.clear()

        return target_path

    def register_pattern(self, pattern: Pattern, pattern_id: str | None = None) -> str:
        """
        Register a pattern programmatically.

        Useful for testing or dynamic pattern creation.

        Args:
            pattern: Pattern to register
            pattern_id: Optional ID (defaults to role/name)

        Returns:
            The pattern ID
        """
        if pattern_id is None:
            pattern_id = f"{pattern.role.value}/{pattern.name}"

        self._cache[pattern_id] = pattern
        self._metadata_cache[pattern_id] = PatternMetadata.from_pattern(pattern)

        return pattern_id

    def _ensure_metadata_loaded(self) -> None:
        """Load metadata for all available patterns."""
        if self._metadata_cache:
            return  # Already loaded

        # Scan library
        if self.library_path and self.library_path.exists():
            self._scan_directory(self.library_path, is_library=True)

        # Scan project (overwrites library patterns)
        if self.project_path and self.project_path.exists():
            self._scan_directory(self.project_path, is_library=False)

    def _scan_directory(self, base_path: Path, is_library: bool) -> None:
        """Scan a directory for patterns."""
        for role_dir in base_path.iterdir():
            if not role_dir.is_dir():
                continue

            # Skip non-role directories
            try:
                role = LayerRole(role_dir.name)
            except ValueError:
                continue

            for pattern_file in role_dir.glob("*.yaml"):
                if pattern_file.name.endswith(".test.yaml"):
                    continue  # Skip test files

                pattern_id = f"{role.value}/{pattern_file.stem}"

                try:
                    with open(pattern_file) as f:
                        data = yaml.safe_load(f)

                    metadata = PatternMetadata(
                        name=data.get("name", pattern_file.stem),
                        role=role,
                        description=data.get("description", ""),
                        version=data.get("version", "1.0.0"),
                        pitched=data.get("pitched", True),
                        variants=list(data.get("variants", {}).keys()),
                        path=str(pattern_file),
                    )

                    self._metadata_cache[pattern_id] = metadata

                except Exception:
                    # Skip files that can't be parsed
                    continue

    def _load_pattern(self, pattern_id: str) -> Pattern | None:
        """Load a pattern from disk."""
        # Parse pattern_id
        parts = pattern_id.split("/")
        if len(parts) != 2:
            return None

        role_str, name = parts

        # Check project first
        if self.project_path:
            project_file = self.project_path / role_str / f"{name}.yaml"
            if project_file.exists():
                return self._load_pattern_file(project_file)

        # Check library
        if self.library_path:
            library_file = self.library_path / role_str / f"{name}.yaml"
            if library_file.exists():
                return self._load_pattern_file(library_file)

        return None

    def _load_pattern_file(self, path: Path) -> Pattern | None:
        """Load a pattern from a YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            return self._pattern_from_yaml_dict(data)

        except Exception:
            return None

    def _pattern_from_yaml_dict(self, data: dict[str, Any]) -> Pattern:
        """Create a Pattern from YAML dict."""
        # Parse parameters
        parameters = {}
        for name, pdata in data.get("parameters", {}).items():
            parameters[name] = PatternParameter(
                name=name,
                type=pdata.get("type", "string"),
                description=pdata.get("description", ""),
                values=pdata.get("values"),
                range=tuple(pdata["range"]) if pdata.get("range") else None,
                default=pdata.get("default"),
            )

        # Parse variants
        variants = {}
        for name, vdata in data.get("variants", {}).items():
            if isinstance(vdata, dict):
                variants[name] = PatternVariant(
                    name=name,
                    description=vdata.get("description", ""),
                    params={k: v for k, v in vdata.items() if k != "description"},
                )

        # Parse constraints
        cdata = data.get("constraints", {})
        constraints = PatternConstraints(
            requires_harmony=cdata.get("requires_harmony", True),
            frequency_range=tuple(cdata["frequency_range"])
            if cdata.get("frequency_range")
            else None,
            compatible_roles=[LayerRole(r) for r in cdata.get("compatible_roles", [])]
            if cdata.get("compatible_roles")
            else None,
            compatible_styles=cdata.get("compatible_styles"),
            max_notes_per_bar=cdata.get("max_notes_per_bar"),
        )

        # Parse template
        tdata = data.get("template", {})
        events = []
        for edata in tdata.get("events", []):
            events.append(
                PatternEvent(
                    beat=edata.get("beat", 0),
                    duration=edata.get("duration", 1),
                    degree=edata.get("degree"),
                    note=edata.get("note"),
                    velocity=edata.get("velocity", 0.8),
                    octave_shift=edata.get("octave_shift", 0),
                )
            )

        template = PatternTemplate(
            bars=tdata.get("bars", 1),
            loop=tdata.get("loop", True),
            events=events,
        )

        return Pattern(
            schema=data.get("schema", "pattern/v1"),
            name=data.get("name", "unknown"),
            role=LayerRole(data.get("role", "melody")),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            pitched=data.get("pitched", True),
            parameters=parameters,
            variants=variants,
            constraints=constraints,
            template=template,
        )

    def _pattern_to_yaml_dict(self, pattern: Pattern) -> dict[str, Any]:
        """Convert a Pattern to YAML dict."""
        result: dict[str, Any] = {
            "schema": pattern.schema_version,
            "name": pattern.name,
            "role": pattern.role.value,
            "description": pattern.description,
            "version": pattern.version,
            "pitched": pattern.pitched,
        }

        # Parameters
        if pattern.parameters:
            result["parameters"] = {}
            for name, param in pattern.parameters.items():
                pdict: dict[str, Any] = {"type": param.param_type.value}
                if param.description:
                    pdict["description"] = param.description
                if param.values:
                    pdict["values"] = param.values
                if param.range:
                    pdict["range"] = list(param.range)
                if param.default is not None:
                    pdict["default"] = param.default
                result["parameters"][name] = pdict

        # Variants
        if pattern.variants:
            result["variants"] = {}
            for name, variant in pattern.variants.items():
                vdict = dict(variant.params)
                if variant.description:
                    vdict["description"] = variant.description
                result["variants"][name] = vdict

        # Constraints
        if pattern.constraints:
            cdict: dict[str, Any] = {}
            if not pattern.constraints.requires_harmony:
                cdict["requires_harmony"] = False
            if pattern.constraints.frequency_range:
                cdict["frequency_range"] = list(pattern.constraints.frequency_range)
            if pattern.constraints.compatible_styles:
                cdict["compatible_styles"] = pattern.constraints.compatible_styles
            if pattern.constraints.max_notes_per_bar:
                cdict["max_notes_per_bar"] = pattern.constraints.max_notes_per_bar
            if cdict:
                result["constraints"] = cdict

        # Template
        result["template"] = {
            "bars": pattern.template.bars,
            "loop": pattern.template.loop,
            "events": [
                {
                    "beat": e.beat,
                    "duration": e.duration,
                    **({"degree": e.degree} if e.degree else {}),
                    **({"note": e.note} if e.note is not None else {}),
                    "velocity": e.velocity,
                    **({"octave_shift": e.octave_shift} if e.octave_shift else {}),
                }
                for e in pattern.template.events
            ],
        }

        return result
