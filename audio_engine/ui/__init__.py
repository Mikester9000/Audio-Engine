"""Local Tkinter studio GUI for quick music/SFX/voice generation."""

from audio_engine.ui.studio import (
    launch_studio,
    _build_synth_patch,
    _build_synth_patch_ext,
    _export_synth_patch,
    _compose_piece_to_file,
    _preview_instrument_note,
    _render_piano_roll_to_file,
    _NOTE_FREQS,
    _NOTE_NAMES,
    _PC_SECTION_TYPES,
    _PC_VOCAL_PRESETS,
)

__all__ = [
    "launch_studio",
    "_build_synth_patch",
    "_build_synth_patch_ext",
    "_export_synth_patch",
    "_compose_piece_to_file",
    "_preview_instrument_note",
    "_render_piano_roll_to_file",
    "_NOTE_FREQS",
    "_NOTE_NAMES",
    "_PC_SECTION_TYPES",
    "_PC_VOCAL_PRESETS",
]
