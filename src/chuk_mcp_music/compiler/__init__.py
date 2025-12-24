"""
Compilation pipeline - transforms symbolic scores to MIDI.

The pipeline:
    Arrangement YAML → Arrangement (in-memory)
    → PatternInstance (resolved params, diffable)
    → EventList (deterministic note events)
    → MIDI File
"""

# Import MIDI first (no circular dependencies)
from chuk_mcp_music.compiler.midi import (
    DRUM_CHANNEL,
    TICKS_PER_BEAT,
    MidiEvent,
    create_test_midi,
    events_to_midi,
)


def __getattr__(name: str):
    """Lazy imports for arranger to avoid circular dependencies."""
    if name in ("ArrangementCompiler", "CompileResult", "compile_arrangement"):
        from chuk_mcp_music.compiler.arranger import (
            ArrangementCompiler,
            CompileResult,
            compile_arrangement,
        )

        return {
            "ArrangementCompiler": ArrangementCompiler,
            "CompileResult": CompileResult,
            "compile_arrangement": compile_arrangement,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Arranger (lazy loaded)
    "ArrangementCompiler",
    "CompileResult",
    "compile_arrangement",
    # MIDI
    "DRUM_CHANNEL",
    "TICKS_PER_BEAT",
    "MidiEvent",
    "create_test_midi",
    "events_to_midi",
]
