"""
Pattern model - the shadcn layer.

Patterns are copyable, ownable, modifiable templates.
They define musical building blocks with parameters and variants.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from chuk_mcp_music.models.arrangement import LayerRole


class ParameterType(str, Enum):
    """Types of pattern parameters."""

    ENUM = "enum"
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"


class PatternParameter(BaseModel):
    """
    A parameter that can be configured on a pattern.

    Parameters allow patterns to be customized without modification.
    """

    name: str = Field(..., description="Parameter name")
    param_type: ParameterType = Field(..., alias="type", description="Parameter type")
    description: str = Field("", description="Human-readable description")

    # Type-specific constraints
    values: list[str] | None = Field(None, description="Allowed values for enum type")
    range: tuple[float, float] | None = Field(None, description="Range for numeric types")
    default: Any = Field(None, description="Default value")

    model_config = {"populate_by_name": True}

    def validate_value(self, value: Any) -> bool:
        """Check if a value is valid for this parameter."""
        if value is None:
            return self.default is not None

        if self.param_type == ParameterType.ENUM:
            return self.values is not None and str(value) in self.values
        elif self.param_type == ParameterType.FLOAT:
            if self.range:
                return self.range[0] <= float(value) <= self.range[1]
            return isinstance(value, (int, float))
        elif self.param_type == ParameterType.INT:
            if self.range:
                return self.range[0] <= int(value) <= self.range[1]
            return isinstance(value, int)
        elif self.param_type == ParameterType.BOOL:
            return isinstance(value, bool)
        elif self.param_type == ParameterType.STRING:
            return isinstance(value, str)

        return True

    def get_default(self) -> Any:
        """Get the default value."""
        return self.default


class PatternEvent(BaseModel):
    """
    A single event in a pattern template.

    Events can reference harmony symbolically (chord.root, chord.fifth)
    or use absolute values (for drums).
    """

    # Timing (in beats relative to pattern start)
    beat: float = Field(..., ge=0, description="Beat position within pattern")
    duration: str | float = Field(..., description="Duration (name or beats)")

    # Pitch - either symbolic or absolute
    degree: str | None = Field(None, description="Symbolic degree (chord.root, scale.1, etc.)")
    note: int | None = Field(None, ge=0, le=127, description="Absolute MIDI note (for drums)")

    # Expression
    velocity: float | str = Field(0.8, description="Velocity (0-1 float or $param)")

    # Octave modifier
    octave_shift: int = Field(0, description="Octave shift from default register")

    model_config = {"frozen": True}


class PatternTemplate(BaseModel):
    """
    The template section of a pattern - defines the actual musical content.
    """

    bars: int = Field(1, gt=0, description="Pattern length in bars")
    loop: bool = Field(True, description="Whether pattern loops")
    events: list[PatternEvent] = Field(default_factory=list, description="Pattern events")


class PatternVariant(BaseModel):
    """
    A variant is a preset parameter combination.

    Variants allow quick selection of common configurations.
    """

    name: str = Field(..., description="Variant name")
    description: str = Field("", description="Variant description")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameter overrides")


class PatternConstraints(BaseModel):
    """
    Constraints on when/how a pattern can be used.
    """

    requires_harmony: bool = Field(True, description="Pattern needs harmony context")
    frequency_range: tuple[int, int] | None = Field(None, description="Valid frequency range in Hz")
    compatible_roles: list[LayerRole] | None = Field(None, description="Compatible layer roles")
    compatible_styles: list[str] | None = Field(None, description="Compatible style names")
    max_notes_per_bar: int | None = Field(None, description="Maximum note density")


class Pattern(BaseModel):
    """
    A complete pattern definition.

    Patterns are the shadcn layer - copyable, ownable, modifiable.
    They define musical building blocks with parameters and variants.
    """

    # Metadata
    schema_version: str = Field("pattern/v1", alias="schema", description="Schema version")
    name: str = Field(..., description="Pattern name")
    role: LayerRole = Field(..., description="Target layer role")
    description: str = Field("", description="Human-readable description")
    version: str = Field("1.0.0", description="Pattern version")

    # Is this pattern pitched or unpitched (like drums)?
    pitched: bool = Field(True, description="Whether pattern uses pitch (false for drums)")

    # Parameters
    parameters: dict[str, PatternParameter] = Field(
        default_factory=dict, description="Configurable parameters"
    )

    # Variants (preset parameter combinations)
    variants: dict[str, PatternVariant] = Field(default_factory=dict, description="Named variants")

    # Constraints
    constraints: PatternConstraints = Field(
        default_factory=PatternConstraints, description="Usage constraints"
    )

    # The actual pattern content
    template: PatternTemplate = Field(..., description="Pattern template")

    model_config = {"populate_by_name": True}

    def get_resolved_params(
        self, variant: str | None = None, overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Get fully resolved parameters.

        Resolution order:
        1. Parameter defaults
        2. Variant overrides
        3. Explicit overrides

        Args:
            variant: Optional variant name
            overrides: Optional parameter overrides

        Returns:
            Fully resolved parameter dict
        """
        # Start with defaults
        result = {name: param.get_default() for name, param in self.parameters.items()}

        # Apply variant
        if variant and variant in self.variants:
            result.update(self.variants[variant].params)

        # Apply overrides
        if overrides:
            result.update(overrides)

        return result

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Validate a set of parameters.

        Returns list of error messages (empty if valid).
        """
        errors = []

        for name, value in params.items():
            if name not in self.parameters:
                errors.append(f"Unknown parameter: {name}")
            elif not self.parameters[name].validate_value(value):
                errors.append(f"Invalid value for {name}: {value}")

        return errors


class PatternMetadata(BaseModel):
    """
    Lightweight pattern metadata for listing/discovery.
    """

    name: str = Field(..., description="Pattern name")
    role: LayerRole = Field(..., description="Target layer role")
    description: str = Field("", description="Human-readable description")
    version: str = Field("1.0.0", description="Pattern version")
    pitched: bool = Field(True, description="Whether pattern uses pitch")
    variants: list[str] = Field(default_factory=list, description="Available variants")
    path: str | None = Field(None, description="Path to pattern file")

    @classmethod
    def from_pattern(cls, pattern: Pattern, path: str | None = None) -> PatternMetadata:
        """Create metadata from a full pattern."""
        return cls(
            name=pattern.name,
            role=pattern.role,
            description=pattern.description,
            version=pattern.version,
            pitched=pattern.pitched,
            variants=list(pattern.variants.keys()),
            path=path,
        )
