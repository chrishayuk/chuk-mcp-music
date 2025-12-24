"""
Arrangement model - the producer mental model.

An Arrangement contains:
- Global context (key, tempo, time signature, style)
- Sections (structural segments with energy levels)
- Layers (tracks with patterns arranged across sections)
- Harmony (chord progressions per section)

This is the central data structure for composition.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from chuk_mcp_music.core.rhythm import TimeSignature
from chuk_mcp_music.core.scale import Key


class LayerRole(str, Enum):
    """
    Frequency/function hierarchy for layers.

    Each role has an implied register range and function.
    """

    SUB = "sub"  # Sub bass (20-60 Hz)
    BASS = "bass"  # Bass (60-250 Hz)
    DRUMS = "drums"  # Rhythm section
    HARMONY = "harmony"  # Chords, pads
    MELODY = "melody"  # Lead lines
    FX = "fx"  # Risers, impacts, ear candy
    VOCAL = "vocal"  # Voice


class EnergyLevel(str, Enum):
    """Semantic energy levels for sections."""

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


class PatternRef(BaseModel):
    """
    Reference to a pattern with optional parameters and variant.

    This is how patterns are assigned to layers.
    """

    ref: str = Field(..., description="Pattern reference (e.g., 'bass/root-pulse')")
    variant: str | None = Field(None, description="Variant name to apply")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameter overrides")

    model_config = {"frozen": True}


class Section(BaseModel):
    """
    A structural segment of the arrangement.

    Sections define the song structure (intro, verse, chorus, etc.)
    and can have associated energy levels.
    """

    name: str = Field(..., description="Section name (e.g., 'intro', 'verse', 'chorus')")
    bars: int = Field(..., gt=0, description="Length in bars")
    energy: EnergyLevel | None = Field(None, description="Energy level for this section")

    model_config = {"frozen": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure section name is valid identifier."""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid section name: {v}")
        return v.lower().replace("-", "_")


class Layer(BaseModel):
    """
    A single track/stem in the composition.

    Layers have a role (drums, bass, etc.) and contain patterns
    arranged across sections.
    """

    name: str = Field(..., description="Layer name")
    role: LayerRole = Field(..., description="Layer role (drums, bass, harmony, etc.)")
    channel: int = Field(0, ge=0, le=15, description="MIDI channel (0-15, 9 for drums)")

    # Patterns available to this layer
    patterns: dict[str, PatternRef] = Field(
        default_factory=dict, description="Pattern aliases to pattern references"
    )

    # Which pattern plays in which section (section_name → pattern_alias or None)
    arrangement: dict[str, str | None] = Field(
        default_factory=dict, description="Section to pattern alias mapping"
    )

    # Mix controls
    muted: bool = Field(False, description="Layer is muted")
    solo: bool = Field(False, description="Layer is soloed")
    level: float = Field(1.0, ge=0.0, le=2.0, description="Volume level (0-2)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure layer name is valid identifier."""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid layer name: {v}")
        return v.lower().replace("-", "_")

    def get_pattern_for_section(self, section_name: str) -> PatternRef | None:
        """
        Get the pattern reference for a section.

        Returns None if the layer is silent in that section.
        """
        pattern_alias = self.arrangement.get(section_name)
        if pattern_alias is None:
            return None
        return self.patterns.get(pattern_alias)


class HarmonyProgression(BaseModel):
    """
    Chord progression for a section or default.

    Progressions are specified as Roman numerals.
    """

    progression: list[str] = Field(
        ..., min_length=1, description="Chord progression as Roman numerals"
    )
    harmonic_rhythm: str = Field("1bar", description="How often chords change")

    model_config = {"frozen": True}


class Harmony(BaseModel):
    """
    Harmony configuration for the arrangement.

    Defines default progression and per-section overrides.
    """

    default_progression: list[str] = Field(
        default_factory=lambda: ["I"], description="Default chord progression"
    )
    harmonic_rhythm: str = Field("1bar", description="Default harmonic rhythm")
    sections: dict[str, HarmonyProgression] = Field(
        default_factory=dict, description="Per-section harmony overrides"
    )

    def get_progression_for_section(self, section_name: str) -> list[str]:
        """Get the chord progression for a section."""
        if section_name in self.sections:
            return self.sections[section_name].progression
        return self.default_progression


class ArrangementContext(BaseModel):
    """
    Global context for an arrangement.

    Contains key, tempo, time signature, and style.
    """

    key: str = Field(..., description="Key (e.g., 'C_major', 'D_minor')")
    tempo: int = Field(..., gt=0, le=300, description="Tempo in BPM")
    time_signature: str = Field("4/4", description="Time signature")
    style: str | None = Field(None, description="Style constraint bundle")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate key format."""
        # Try to parse it
        Key.parse(v)
        return v

    @field_validator("time_signature")
    @classmethod
    def validate_time_signature(cls, v: str) -> str:
        """Validate time signature format."""
        TimeSignature.parse(v)
        return v

    def get_key(self) -> Key:
        """Get parsed Key object."""
        return Key.parse(self.key)

    def get_time_signature(self) -> TimeSignature:
        """Get parsed TimeSignature object."""
        return TimeSignature.parse(self.time_signature)


class Arrangement(BaseModel):
    """
    A complete music arrangement.

    This is the central model representing a composition.
    It contains all the information needed to compile to MIDI.
    """

    # Metadata
    schema_version: str = Field("arrangement/v1", description="Schema version")
    name: str = Field(..., description="Arrangement name")
    created: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    modified: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last modified"
    )

    # Global context
    context: ArrangementContext = Field(..., description="Global arrangement context")

    # Harmony
    harmony: Harmony = Field(default_factory=Harmony, description="Harmony configuration")

    # Structure
    sections: list[Section] = Field(default_factory=list, description="Arrangement sections")

    # Layers
    layers: dict[str, Layer] = Field(default_factory=dict, description="Arrangement layers")

    def total_bars(self) -> int:
        """Get total number of bars in the arrangement."""
        return sum(section.bars for section in self.sections)

    def get_section_names(self) -> list[str]:
        """Get ordered list of section names."""
        return [section.name for section in self.sections]

    def get_section(self, name: str) -> Section | None:
        """Get a section by name."""
        for section in self.sections:
            if section.name == name:
                return section
        return None

    def get_layer(self, name: str) -> Layer | None:
        """Get a layer by name."""
        return self.layers.get(name)

    def get_active_patterns(self, section_name: str) -> dict[str, PatternRef]:
        """
        Get all active patterns for a section.

        Returns a dict of layer_name → PatternRef for layers
        that have a pattern assigned to this section.
        """
        result = {}
        for layer_name, layer in self.layers.items():
            if layer.muted:
                continue
            pattern = layer.get_pattern_for_section(section_name)
            if pattern is not None:
                result[layer_name] = pattern
        return result

    def add_section(
        self, name: str, bars: int, energy: EnergyLevel | None = None, position: int | None = None
    ) -> Section:
        """
        Add a section to the arrangement.

        Args:
            name: Section name
            bars: Number of bars
            energy: Optional energy level
            position: Optional position (default: append)

        Returns:
            The created section
        """
        section = Section(name=name, bars=bars, energy=energy)

        if position is None:
            self.sections.append(section)
        else:
            self.sections.insert(position, section)

        self.modified = datetime.now(UTC)
        return section

    def remove_section(self, name: str) -> bool:
        """
        Remove a section by name.

        Returns True if removed, False if not found.
        """
        for i, section in enumerate(self.sections):
            if section.name == name:
                self.sections.pop(i)
                self.modified = datetime.now(UTC)
                return True
        return False

    def add_layer(self, name: str, role: LayerRole, channel: int | None = None) -> Layer:
        """
        Add a layer to the arrangement.

        Args:
            name: Layer name
            role: Layer role
            channel: Optional MIDI channel (auto-assigned if None)

        Returns:
            The created layer
        """
        if channel is None:
            # Auto-assign channel based on role
            channel = self._default_channel_for_role(role)

        layer = Layer(name=name, role=role, channel=channel)
        self.layers[name] = layer
        self.modified = datetime.now(UTC)
        return layer

    def remove_layer(self, name: str) -> bool:
        """
        Remove a layer by name.

        Returns True if removed, False if not found.
        """
        if name in self.layers:
            del self.layers[name]
            self.modified = datetime.now(UTC)
            return True
        return False

    def _default_channel_for_role(self, role: LayerRole) -> int:
        """Get default MIDI channel for a role."""
        channel_map = {
            LayerRole.SUB: 0,
            LayerRole.BASS: 1,
            LayerRole.DRUMS: 9,  # GM drums
            LayerRole.HARMONY: 2,
            LayerRole.MELODY: 3,
            LayerRole.FX: 4,
            LayerRole.VOCAL: 5,
        }
        return channel_map.get(role, 0)

    def to_yaml_dict(self) -> dict[str, Any]:
        """
        Convert to a YAML-friendly dict.

        This produces the canonical YAML format for arrangements.
        """
        return {
            "schema": self.schema_version,
            "name": self.name,
            "context": {
                "key": self.context.key,
                "tempo": self.context.tempo,
                "time_signature": self.context.time_signature,
                "style": self.context.style,
            },
            "harmony": {
                "default_progression": self.harmony.default_progression,
                "harmonic_rhythm": self.harmony.harmonic_rhythm,
                "sections": {
                    name: {
                        "progression": prog.progression,
                        "harmonic_rhythm": prog.harmonic_rhythm,
                    }
                    for name, prog in self.harmony.sections.items()
                },
            },
            "sections": [
                {"name": s.name, "bars": s.bars, "energy": s.energy.value if s.energy else None}
                for s in self.sections
            ],
            "layers": {
                name: {
                    "role": layer.role.value,
                    "channel": layer.channel,
                    "patterns": {
                        alias: {"ref": p.ref, "variant": p.variant, "params": p.params}
                        for alias, p in layer.patterns.items()
                    },
                    "arrangement": layer.arrangement,
                    "muted": layer.muted,
                    "solo": layer.solo,
                    "level": layer.level,
                }
                for name, layer in self.layers.items()
            },
        }

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> Arrangement:
        """
        Create an Arrangement from a YAML-parsed dict.

        This parses the canonical YAML format.
        """
        context = ArrangementContext(
            key=data["context"]["key"],
            tempo=data["context"]["tempo"],
            time_signature=data["context"].get("time_signature", "4/4"),
            style=data["context"].get("style"),
        )

        harmony_data = data.get("harmony", {})
        harmony = Harmony(
            default_progression=harmony_data.get("default_progression", ["I"]),
            harmonic_rhythm=harmony_data.get("harmonic_rhythm", "1bar"),
            sections={
                name: HarmonyProgression(
                    progression=prog.get("progression", ["I"]),
                    harmonic_rhythm=prog.get("harmonic_rhythm", "1bar"),
                )
                for name, prog in harmony_data.get("sections", {}).items()
            },
        )

        sections = [
            Section(
                name=s["name"],
                bars=s["bars"],
                energy=EnergyLevel(s["energy"]) if s.get("energy") else None,
            )
            for s in data.get("sections", [])
        ]

        layers = {}
        for name, layer_data in data.get("layers", {}).items():
            patterns = {}
            for alias, pdata in layer_data.get("patterns", {}).items():
                if isinstance(pdata, str):
                    # Simple string reference
                    patterns[alias] = PatternRef(ref=pdata)
                else:
                    patterns[alias] = PatternRef(
                        ref=pdata["ref"],
                        variant=pdata.get("variant"),
                        params=pdata.get("params", {}),
                    )

            layers[name] = Layer(
                name=name,
                role=LayerRole(layer_data["role"]),
                channel=layer_data.get("channel", 0),
                patterns=patterns,
                arrangement=layer_data.get("arrangement", {}),
                muted=layer_data.get("muted", False),
                solo=layer_data.get("solo", False),
                level=layer_data.get("level", 1.0),
            )

        return cls(
            schema_version=data.get("schema", "arrangement/v1"),
            name=data["name"],
            context=context,
            harmony=harmony,
            sections=sections,
            layers=layers,
        )
