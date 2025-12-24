"""
Style models - constraint bundles that narrow the solution space.

Styles don't force specific choices, they narrow what's appropriate.
They're like design tokens for genre/mood constraints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from chuk_mcp_music.models.arrangement import LayerRole


class PercussionDensity(str, Enum):
    """Percussion density levels."""

    NONE = "none"
    MINIMAL = "minimal"
    SPARSE = "sparse"
    STANDARD = "standard"
    FULL = "full"
    DENSE = "dense"


class HarmonyDensity(str, Enum):
    """Harmony density levels."""

    NONE = "none"
    SPARSE = "sparse"
    MODERATE = "moderate"
    RICH = "rich"
    DENSE = "dense"


class KeyPreference(str, Enum):
    """Key preference for a style."""

    MAJOR = "major"
    MINOR = "minor"
    ANY = "any"


class EnergyConstraints(BaseModel):
    """Constraints for a specific energy level."""

    layers: tuple[int, int] = Field(
        default=(1, 5),
        description="Min/max active layers at this energy",
    )
    percussion: PercussionDensity = Field(
        default=PercussionDensity.STANDARD,
        description="Percussion density",
    )
    harmony_density: HarmonyDensity = Field(
        default=HarmonyDensity.MODERATE,
        description="Harmony density",
    )
    velocity_range: tuple[float, float] = Field(
        default=(0.5, 1.0),
        description="Velocity range (0-1)",
    )

    model_config = {"frozen": True}


class EnergyMapping(BaseModel):
    """Maps energy levels to constraints."""

    lowest: EnergyConstraints = Field(
        default_factory=lambda: EnergyConstraints(
            layers=(1, 2),
            percussion=PercussionDensity.NONE,
            harmony_density=HarmonyDensity.SPARSE,
            velocity_range=(0.3, 0.5),
        )
    )
    low: EnergyConstraints = Field(
        default_factory=lambda: EnergyConstraints(
            layers=(1, 3),
            percussion=PercussionDensity.MINIMAL,
            harmony_density=HarmonyDensity.SPARSE,
            velocity_range=(0.4, 0.6),
        )
    )
    medium: EnergyConstraints = Field(
        default_factory=lambda: EnergyConstraints(
            layers=(2, 4),
            percussion=PercussionDensity.STANDARD,
            harmony_density=HarmonyDensity.MODERATE,
            velocity_range=(0.5, 0.8),
        )
    )
    high: EnergyConstraints = Field(
        default_factory=lambda: EnergyConstraints(
            layers=(3, 5),
            percussion=PercussionDensity.FULL,
            harmony_density=HarmonyDensity.RICH,
            velocity_range=(0.7, 1.0),
        )
    )
    highest: EnergyConstraints = Field(
        default_factory=lambda: EnergyConstraints(
            layers=(4, 6),
            percussion=PercussionDensity.DENSE,
            harmony_density=HarmonyDensity.DENSE,
            velocity_range=(0.8, 1.0),
        )
    )

    model_config = {"frozen": True}

    def get_constraints(self, energy: str) -> EnergyConstraints:
        """Get constraints for an energy level."""
        energy_map = {
            "lowest": self.lowest,
            "low": self.low,
            "medium": self.medium,
            "high": self.high,
            "highest": self.highest,
        }
        return energy_map.get(energy, self.medium)


class LayerHint(BaseModel):
    """Hints for pattern selection in a layer."""

    suggested: list[str] = Field(
        default_factory=list,
        description="Suggested pattern IDs (supports wildcards like 'arp-*')",
    )
    avoid: list[str] = Field(
        default_factory=list,
        description="Pattern IDs to avoid (supports wildcards)",
    )
    pitch_register: str | None = Field(
        default=None,
        alias="register",
        description="Preferred register (sub, low, mid, high)",
    )
    density: str | None = Field(
        default=None,
        description="Preferred density (sparse, moderate, dense)",
    )

    model_config = {"frozen": True}


class StructureHints(BaseModel):
    """Hints for arrangement structure."""

    breakdown_required: bool = Field(
        default=False,
        description="Whether a breakdown section is expected",
    )
    typical_length_bars: tuple[int, int] = Field(
        default=(32, 128),
        description="Typical arrangement length in bars",
    )
    intro_bars: tuple[int, int] = Field(
        default=(4, 16),
        description="Typical intro length in bars",
    )
    outro_bars: tuple[int, int] = Field(
        default=(4, 16),
        description="Typical outro length in bars",
    )
    section_multiples: int = Field(
        default=4,
        description="Sections should be multiples of this many bars",
    )

    model_config = {"frozen": True}


class TempoRange(BaseModel):
    """Tempo constraints."""

    min_bpm: int = Field(default=60, ge=20, le=300)
    max_bpm: int = Field(default=200, ge=20, le=300)
    default_bpm: int = Field(default=120, ge=20, le=300)

    model_config = {"frozen": True}

    def is_valid(self, tempo: int) -> bool:
        """Check if tempo is within range."""
        return self.min_bpm <= tempo <= self.max_bpm


class ForbiddenElements(BaseModel):
    """Elements that should not be used with this style."""

    patterns: list[str] = Field(
        default_factory=list,
        description="Pattern IDs to forbid (supports wildcards)",
    )
    progressions: list[str] = Field(
        default_factory=list,
        description="Chord progressions to forbid",
    )

    model_config = {"frozen": True}


class Style(BaseModel):
    """
    A style constraint bundle.

    Styles narrow the solution space without forcing specific choices.
    They're like design tokens for genre/mood constraints.
    """

    # Metadata
    schema_version: str = Field("style/v1", alias="schema")
    name: str = Field(..., description="Style name")
    description: str = Field("", description="Style description")

    # Global tokens
    tempo: TempoRange = Field(default_factory=TempoRange)
    key_preference: KeyPreference = Field(
        default=KeyPreference.ANY,
        description="Preferred key quality",
    )
    time_signature: str = Field(
        default="4/4",
        description="Expected time signature",
    )

    # Energy mapping
    energy_mapping: EnergyMapping = Field(default_factory=EnergyMapping)

    # Layer hints
    layer_hints: dict[str, LayerHint] = Field(
        default_factory=dict,
        description="Per-role pattern hints",
    )

    # Structure hints
    structure_hints: StructureHints = Field(default_factory=StructureHints)

    # Forbidden elements
    forbidden: ForbiddenElements = Field(default_factory=ForbiddenElements)

    model_config = {"frozen": True, "populate_by_name": True}

    def get_layer_hint(self, role: LayerRole) -> LayerHint:
        """Get layer hints for a role."""
        return self.layer_hints.get(role.value, LayerHint())

    def is_pattern_suggested(self, pattern_id: str, role: LayerRole) -> bool:
        """Check if a pattern is suggested for a role."""
        hint = self.get_layer_hint(role)
        return self._matches_any(pattern_id, hint.suggested)

    def is_pattern_avoided(self, pattern_id: str, role: LayerRole) -> bool:
        """Check if a pattern should be avoided for a role."""
        hint = self.get_layer_hint(role)
        return self._matches_any(pattern_id, hint.avoid)

    def is_pattern_forbidden(self, pattern_id: str) -> bool:
        """Check if a pattern is forbidden by this style."""
        return self._matches_any(pattern_id, self.forbidden.patterns)

    def validate_tempo(self, tempo: int) -> bool:
        """Check if tempo is valid for this style."""
        return self.tempo.is_valid(tempo)

    def _matches_any(self, pattern_id: str, patterns: list[str]) -> bool:
        """Check if pattern_id matches any pattern in the list (with wildcards)."""
        import fnmatch

        return any(fnmatch.fnmatch(pattern_id, pattern) for pattern in patterns)

    def to_yaml_dict(self) -> dict[str, Any]:
        """Convert to YAML-serializable dictionary."""
        return {
            "schema": self.schema_version,
            "name": self.name,
            "description": self.description,
            "tokens": {
                "tempo": {
                    "range": [self.tempo.min_bpm, self.tempo.max_bpm],
                    "default": self.tempo.default_bpm,
                },
                "key_preference": self.key_preference.value,
                "time_signature": self.time_signature,
            },
            "energy_mapping": {
                energy: {
                    "layers": list(constraints.layers),
                    "percussion": constraints.percussion.value,
                    "harmony_density": constraints.harmony_density.value,
                }
                for energy, constraints in [
                    ("lowest", self.energy_mapping.lowest),
                    ("low", self.energy_mapping.low),
                    ("medium", self.energy_mapping.medium),
                    ("high", self.energy_mapping.high),
                    ("highest", self.energy_mapping.highest),
                ]
            },
            "layer_hints": {
                role: {
                    "suggested": hint.suggested,
                    "avoid": hint.avoid,
                    "register": hint.pitch_register,
                    "density": hint.density,
                }
                for role, hint in self.layer_hints.items()
            },
            "structure_hints": {
                "breakdown_required": self.structure_hints.breakdown_required,
                "typical_length_bars": list(self.structure_hints.typical_length_bars),
                "intro_bars": list(self.structure_hints.intro_bars),
                "outro_bars": list(self.structure_hints.outro_bars),
                "section_multiples": self.structure_hints.section_multiples,
            },
            "forbidden": {
                "patterns": self.forbidden.patterns,
                "progressions": self.forbidden.progressions,
            },
        }


class StyleMetadata(BaseModel):
    """Lightweight metadata for listing styles."""

    name: str
    description: str
    tempo_range: tuple[int, int]
    key_preference: KeyPreference

    model_config = {"frozen": True}

    @classmethod
    def from_style(cls, style: Style) -> StyleMetadata:
        """Create metadata from a style."""
        return cls(
            name=style.name,
            description=style.description,
            tempo_range=(style.tempo.min_bpm, style.tempo.max_bpm),
            key_preference=style.key_preference,
        )
