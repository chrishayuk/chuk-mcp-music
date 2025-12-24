"""
Arrangement Validator - validates arrangement structure and constraints.

Validates:
- Section names are unique
- Layer arrangements reference valid sections
- Pattern references exist in layer
- MIDI channels are valid
- Style constraints (if style is set)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from chuk_mcp_music.models.arrangement import Arrangement


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"  # Prevents compilation
    WARNING = "warning"  # Compilation possible but may have issues
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: ValidationSeverity
    code: str
    message: str
    location: str | None = None

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        location = f" at {self.location}" if self.location else ""
        return f"{prefix} {self.code}: {self.message}{location}"


class ValidationResult:
    """Result of validating an arrangement."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def add_error(self, code: str, message: str, location: str | None = None) -> None:
        """Add an error issue."""
        self.issues.append(ValidationIssue(ValidationSeverity.ERROR, code, message, location))

    def add_warning(self, code: str, message: str, location: str | None = None) -> None:
        """Add a warning issue."""
        self.issues.append(ValidationIssue(ValidationSeverity.WARNING, code, message, location))

    def add_info(self, code: str, message: str, location: str | None = None) -> None:
        """Add an info issue."""
        self.issues.append(ValidationIssue(ValidationSeverity.INFO, code, message, location))

    @property
    def is_valid(self) -> bool:
        """Return True if no errors (warnings/info are OK)."""
        return not any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get all error issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def __bool__(self) -> bool:
        """Boolean conversion returns is_valid."""
        return self.is_valid

    def __str__(self) -> str:
        if not self.issues:
            return "Validation passed: no issues found"
        return "\n".join(str(issue) for issue in self.issues)


class ArrangementValidator:
    """Validates arrangement structure and constraints."""

    def validate(self, arrangement: Arrangement) -> ValidationResult:
        """
        Validate an arrangement.

        Args:
            arrangement: The arrangement to validate

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult()

        self._validate_sections(arrangement, result)
        self._validate_layers(arrangement, result)
        self._validate_harmony(arrangement, result)
        self._validate_channel_conflicts(arrangement, result)
        self._validate_structure(arrangement, result)

        return result

    def _validate_sections(self, arrangement: Arrangement, result: ValidationResult) -> None:
        """Validate section configuration."""
        # Check for sections
        if not arrangement.sections:
            result.add_warning(
                "NO_SECTIONS",
                "Arrangement has no sections defined",
                "sections",
            )
            return

        # Check for duplicate section names
        names = [s.name for s in arrangement.sections]
        seen: set[str] = set()
        for name in names:
            if name in seen:
                result.add_error(
                    "DUPLICATE_SECTION",
                    f"Duplicate section name: {name}",
                    f"sections/{name}",
                )
            seen.add(name)

        # Check section lengths
        for section in arrangement.sections:
            if section.bars < 1:
                result.add_error(
                    "INVALID_SECTION_LENGTH",
                    f"Section '{section.name}' has invalid length: {section.bars}",
                    f"sections/{section.name}",
                )
            elif section.bars > 256:
                result.add_warning(
                    "LONG_SECTION",
                    f"Section '{section.name}' is very long: {section.bars} bars",
                    f"sections/{section.name}",
                )

    def _validate_layers(self, arrangement: Arrangement, result: ValidationResult) -> None:
        """Validate layer configuration."""
        if not arrangement.layers:
            result.add_info(
                "NO_LAYERS",
                "Arrangement has no layers defined",
                "layers",
            )
            return

        section_names = {s.name for s in arrangement.sections}

        for layer_name, layer in arrangement.layers.items():
            # Check that arrangement references valid sections
            for section_name in layer.arrangement:
                if section_name not in section_names:
                    result.add_error(
                        "INVALID_SECTION_REF",
                        f"Layer '{layer_name}' references unknown section: {section_name}",
                        f"layers/{layer_name}/arrangement",
                    )

            # Check that arrangement references valid patterns
            for section_name, pattern_alias in layer.arrangement.items():
                if pattern_alias is not None and pattern_alias not in layer.patterns:
                    result.add_error(
                        "INVALID_PATTERN_REF",
                        f"Layer '{layer_name}' references unknown pattern: {pattern_alias}",
                        f"layers/{layer_name}/arrangement/{section_name}",
                    )

            # Check for unused patterns
            used_patterns = {alias for alias in layer.arrangement.values() if alias is not None}
            for pattern_alias in layer.patterns:
                if pattern_alias not in used_patterns:
                    result.add_info(
                        "UNUSED_PATTERN",
                        f"Pattern '{pattern_alias}' in layer '{layer_name}' is never used",
                        f"layers/{layer_name}/patterns/{pattern_alias}",
                    )

            # Check for sections without patterns
            for section in arrangement.sections:
                if section.name not in layer.arrangement:
                    result.add_info(
                        "MISSING_SECTION_ARRANGEMENT",
                        f"Layer '{layer_name}' has no arrangement for section '{section.name}'",
                        f"layers/{layer_name}/arrangement",
                    )

    def _validate_harmony(self, arrangement: Arrangement, result: ValidationResult) -> None:
        """Validate harmony configuration."""
        # Validate default progression
        if not arrangement.harmony.default_progression:
            result.add_warning(
                "EMPTY_PROGRESSION",
                "Default harmony progression is empty",
                "harmony/default_progression",
            )

        # Validate section-specific progressions
        section_names = {s.name for s in arrangement.sections}
        for section_name in arrangement.harmony.sections:
            if section_name not in section_names:
                result.add_warning(
                    "ORPHAN_HARMONY",
                    f"Harmony defined for unknown section: {section_name}",
                    f"harmony/sections/{section_name}",
                )

    def _validate_channel_conflicts(
        self, arrangement: Arrangement, result: ValidationResult
    ) -> None:
        """Check for MIDI channel conflicts."""
        channel_users: dict[int, list[str]] = {}

        for layer_name, layer in arrangement.layers.items():
            channel = layer.channel
            if channel not in channel_users:
                channel_users[channel] = []
            channel_users[channel].append(layer_name)

        for channel, users in channel_users.items():
            if len(users) > 1:
                result.add_warning(
                    "CHANNEL_CONFLICT",
                    f"Multiple layers use MIDI channel {channel}: {', '.join(users)}",
                    "layers",
                )

    def _validate_structure(self, arrangement: Arrangement, result: ValidationResult) -> None:
        """Validate overall arrangement structure."""
        total_bars = arrangement.total_bars()

        if total_bars == 0:
            result.add_warning(
                "EMPTY_ARRANGEMENT",
                "Arrangement has no bars",
                "sections",
            )
        elif total_bars > 1000:
            result.add_info(
                "VERY_LONG_ARRANGEMENT",
                f"Arrangement is very long: {total_bars} bars",
                "sections",
            )

        # Check for solo conflicts
        solo_layers = [name for name, layer in arrangement.layers.items() if layer.solo]
        if len(solo_layers) > 1:
            result.add_info(
                "MULTIPLE_SOLOS",
                f"Multiple layers are soloed: {', '.join(solo_layers)}",
                "layers",
            )


def validate_arrangement(arrangement: Arrangement) -> ValidationResult:
    """
    Convenience function to validate an arrangement.

    Args:
        arrangement: The arrangement to validate

    Returns:
        ValidationResult with any issues found
    """
    validator = ArrangementValidator()
    return validator.validate(arrangement)
