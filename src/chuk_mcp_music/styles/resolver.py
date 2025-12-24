"""
Style resolver - resolves semantic tokens using style constraints.

The resolver translates high-level concepts (energy, role) into
concrete constraints and pattern suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from chuk_mcp_music.models.arrangement import EnergyLevel, LayerRole
from chuk_mcp_music.models.pattern import Pattern
from chuk_mcp_music.models.style import (
    EnergyConstraints,
    LayerHint,
    PercussionDensity,
    Style,
)


class ViolationSeverity(str, Enum):
    """Severity of a style violation."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class StyleViolation:
    """A style constraint violation."""

    message: str
    severity: ViolationSeverity
    element: str  # What was violated (pattern, tempo, etc.)


@dataclass(frozen=True)
class PatternSuggestion:
    """A pattern suggestion with relevance score."""

    pattern_id: str
    score: float  # 0.0 to 1.0
    reason: str


class StyleResolver:
    """
    Resolves semantic tokens using style constraints.

    The resolver:
    - Converts energy levels to specific layer/density constraints
    - Suggests patterns appropriate for role + energy + style
    - Validates patterns against style constraints
    """

    def __init__(self, style: Style):
        """
        Initialize the resolver with a style.

        Args:
            style: The style to use for resolution
        """
        self.style = style

    def resolve_energy(self, energy: str | EnergyLevel) -> EnergyConstraints:
        """
        Convert an energy level to specific constraints.

        Args:
            energy: Energy level (string or enum)

        Returns:
            Concrete constraints for that energy level
        """
        energy_str = energy.value if isinstance(energy, EnergyLevel) else energy
        return self.style.energy_mapping.get_constraints(energy_str)

    def get_layer_hint(self, role: LayerRole) -> LayerHint:
        """
        Get pattern hints for a layer role.

        Args:
            role: Layer role

        Returns:
            Layer hints from the style
        """
        return self.style.get_layer_hint(role)

    def suggest_patterns(
        self,
        available_patterns: list[Pattern],
        role: LayerRole,
        energy: str | EnergyLevel | None = None,
    ) -> list[PatternSuggestion]:
        """
        Get style-appropriate patterns for a role.

        Args:
            available_patterns: Patterns to consider
            role: Layer role
            energy: Optional energy level for additional filtering

        Returns:
            Sorted list of pattern suggestions (highest score first)
        """
        suggestions: list[PatternSuggestion] = []
        hint = self.get_layer_hint(role)

        for pattern in available_patterns:
            # Skip patterns for wrong role
            if pattern.role != role:
                continue

            pattern_id = f"{pattern.role.value}/{pattern.name}"

            # Check if forbidden
            if self.style.is_pattern_forbidden(pattern_id):
                continue

            # Check if avoided
            if self.style.is_pattern_avoided(pattern_id, role):
                continue

            # Calculate score
            score = 0.5  # Base score

            # Bonus for suggested patterns
            if self.style.is_pattern_suggested(pattern_id, role):
                score += 0.3
                reason = "Suggested for this style"
            else:
                reason = "Compatible with style"

            # Consider register preference
            if hint.pitch_register and pattern.constraints:
                # This would need pattern metadata about register
                pass

            # Consider density preference for energy
            if energy:
                constraints = self.resolve_energy(energy)
                # Higher energy = prefer denser patterns
                if (
                    constraints.percussion == PercussionDensity.FULL
                    and len(pattern.template.events) > 8
                ):
                    score += 0.1

            suggestions.append(
                PatternSuggestion(
                    pattern_id=pattern_id,
                    score=min(1.0, score),
                    reason=reason,
                )
            )

        # Sort by score descending
        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions

    def validate_pattern(
        self,
        pattern: Pattern,
        role: LayerRole,
    ) -> list[StyleViolation]:
        """
        Check if a pattern fits style constraints.

        Args:
            pattern: Pattern to validate
            role: Role it's being used for

        Returns:
            List of violations (empty if valid)
        """
        violations: list[StyleViolation] = []
        pattern_id = f"{pattern.role.value}/{pattern.name}"

        # Check if forbidden
        if self.style.is_pattern_forbidden(pattern_id):
            violations.append(
                StyleViolation(
                    message=f"Pattern '{pattern_id}' is forbidden by style '{self.style.name}'",
                    severity=ViolationSeverity.ERROR,
                    element=pattern_id,
                )
            )

        # Check if avoided (warning only)
        if self.style.is_pattern_avoided(pattern_id, role):
            violations.append(
                StyleViolation(
                    message=f"Pattern '{pattern_id}' is discouraged for '{role.value}' in style '{self.style.name}'",
                    severity=ViolationSeverity.WARNING,
                    element=pattern_id,
                )
            )

        # Check role match
        if pattern.role != role:
            violations.append(
                StyleViolation(
                    message=f"Pattern '{pattern_id}' is for role '{pattern.role.value}', not '{role.value}'",
                    severity=ViolationSeverity.ERROR,
                    element=pattern_id,
                )
            )

        return violations

    def validate_tempo(self, tempo: int) -> list[StyleViolation]:
        """
        Validate tempo against style constraints.

        Args:
            tempo: Tempo in BPM

        Returns:
            List of violations (empty if valid)
        """
        violations: list[StyleViolation] = []

        if not self.style.validate_tempo(tempo):
            violations.append(
                StyleViolation(
                    message=f"Tempo {tempo} BPM is outside range [{self.style.tempo.min_bpm}-{self.style.tempo.max_bpm}] for style '{self.style.name}'",
                    severity=ViolationSeverity.WARNING,
                    element="tempo",
                )
            )

        return violations

    def validate_structure(
        self,
        section_bars: dict[str, int],
        has_breakdown: bool,
    ) -> list[StyleViolation]:
        """
        Validate arrangement structure against style hints.

        Args:
            section_bars: Mapping of section name to bar count
            has_breakdown: Whether arrangement has a breakdown section

        Returns:
            List of violations (warnings only)
        """
        violations: list[StyleViolation] = []
        hints = self.style.structure_hints

        # Check breakdown requirement
        if hints.breakdown_required and not has_breakdown:
            violations.append(
                StyleViolation(
                    message=f"Style '{self.style.name}' typically includes a breakdown section",
                    severity=ViolationSeverity.WARNING,
                    element="structure",
                )
            )

        # Check total length
        total_bars = sum(section_bars.values())
        min_bars, max_bars = hints.typical_length_bars
        if total_bars < min_bars or total_bars > max_bars:
            violations.append(
                StyleViolation(
                    message=f"Total length ({total_bars} bars) outside typical range [{min_bars}-{max_bars}] for style '{self.style.name}'",
                    severity=ViolationSeverity.WARNING,
                    element="structure",
                )
            )

        # Check section multiples
        for section, bars in section_bars.items():
            if bars % hints.section_multiples != 0:
                violations.append(
                    StyleViolation(
                        message=f"Section '{section}' ({bars} bars) is not a multiple of {hints.section_multiples}",
                        severity=ViolationSeverity.WARNING,
                        element=f"section:{section}",
                    )
                )

        return violations

    def get_default_tempo(self) -> int:
        """Get the default tempo for this style."""
        return self.style.tempo.default_bpm

    def get_suggested_key_quality(self) -> str:
        """Get the suggested key quality (major/minor)."""
        return self.style.key_preference.value
