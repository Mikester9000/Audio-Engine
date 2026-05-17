"""
PS1 era inference backend.

Wraps :class:`~audio_engine.ai.backend.ProceduralBackend` and runs the
generated audio through the :class:`~audio_engine.dsp.ps1_effects.PS1EffectsChain`
to produce the FF7/FF8-era PlayStation SPU sound character:

* 14-bit effective bit depth (ADPCM quantisation noise)
* Optional 22 050 Hz internal sample rate reduction
* SPU reverb (Room/Hall/Space/Echo/Pipe modes)

Default reverb mode is ``"room"`` which approximates the Studio A/Room
setting used heavily in FF7 background tracks.  Boss themes benefit from
``"hall"`` or ``"space"``.

Usage
-----
>>> from audio_engine.ai.ps1_backend import PS1Backend
>>> backend = PS1Backend(sample_rate=44100, seed=42, reverb_mode="hall")
>>> audio = backend.generate_music_audio(style="ff7_battle", duration=30.0)
"""

from __future__ import annotations

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend
from audio_engine.dsp.ps1_effects import PS1EffectsChain, SPUReverbMode

__all__ = ["PS1Backend"]


class PS1Backend(InferenceBackend):
    """PS1/PS2 SPU-character backend for FF7/FF8-style audio.

    Parameters
    ----------
    sample_rate:
        Engine sample rate in Hz.
    seed:
        RNG seed for reproducibility.
    reverb_mode:
        SPU reverb mode to apply.  ``"room"`` matches the character of most
        FF7 background tracks; ``"hall"`` suits dungeon/boss tracks;
        ``"space"`` gives the cavernous PS1 sound.  Use ``"off"`` for raw
        bit-crush only.
    bit_depth:
        Effective bit depth after ADPCM simulation (default 14).
    enable_downsample:
        If ``True``, adds the 22 050 Hz artefact pass common in PS1 samples
        that were internally stored at half the output rate.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
        reverb_mode: SPUReverbMode = "room",
        bit_depth: int = 14,
        enable_downsample: bool = False,
    ) -> None:
        super().__init__(sample_rate)
        self._seed = seed
        self._reverb_mode = reverb_mode
        self._chain = PS1EffectsChain(
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            enable_downsample=enable_downsample,
        )
        self._procedural = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return "ps1"

    def dependency_summary(self) -> str:
        return "numpy/scipy procedural pipeline + PS1 SPU DSP chain (bundled)"

    def supported_modalities(self) -> tuple[str, ...]:
        return ("music", "sfx", "voice")

    def generate_music_audio(
        self,
        style: str,
        duration: float,
        bpm: float | None = None,
        reverb_mode: SPUReverbMode | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate music with PS1 SPU character.

        Parameters
        ----------
        style:
            Style preset.  FF7/FF8-specific presets (``"ff7_battle"``,
            ``"ff7_overworld"``, etc.) give the most authentic result.
        duration:
            Target duration in seconds.
        bpm:
            Optional BPM override.
        reverb_mode:
            Override the instance reverb mode for this call only.
        """
        audio = self._procedural.generate_music_audio(style=style, duration=duration, bpm=bpm)
        mode = reverb_mode or self._reverb_mode
        return self._chain.apply(audio, mode=mode)

    def generate_sfx_audio(
        self,
        sfx_type: str,
        duration: float,
        pitch_hz: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate SFX.  SFX uses *lighter* PS1 processing (bit-crush only,
        no reverb) to preserve modern punch and transient clarity."""
        audio = self._procedural.generate_sfx_audio(
            sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz
        )
        # Mono input — bit-crush only for SFX (modern feel, retro noise floor)
        return self._chain.bit_crush(audio)

    def generate_voice_audio(
        self,
        text: str,
        voice_preset: str = "narrator",
        speed: float = 1.0,
        **kwargs,
    ) -> np.ndarray:
        """Generate voice with mild PS1 warmth (light bit-crush, room reverb)."""
        audio = self._procedural.generate_voice_audio(
            text=text, voice_preset=voice_preset, speed=speed
        )
        # Light bit-crush at 15 bits + very short room — retro-but-intelligible
        light_chain = PS1EffectsChain(
            sample_rate=self.sample_rate, bit_depth=15, enable_downsample=False
        )
        crushed = light_chain.bit_crush(audio)
        return light_chain.spu_reverb(crushed, mode="room")
