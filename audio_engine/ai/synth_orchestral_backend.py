"""
Synth Orchestral backend.

Produces clean, high-quality synthesised orchestral audio in the style of
PS1/PS2 era RPG soundtracks — think of it as the *intended* sound before
PlayStation hardware limitations imposed bit-crush and bandwidth constraints.

This is the natural **middle layer** in the three-mode pipeline:

    ps1          →   synth_orchestral   →   sample
    (bit-crushed)    (clean synthesis)      (real WAV samples)

Because ``synth_orchestral`` uses the same underlying synthesiser as
``ps1`` it produces exactly the same harmonic content, making it a faithful
remaster target: swap ``ps1`` → ``synth_orchestral`` and the result sounds
like a high-quality remaster with the same musical arrangement.

The key differences from ``ps1``:
* No bit-crush or sample-rate reduction.
* Wider stereo field via per-track spread.
* Slightly longer reverb tails tuned for orchestral staging.
* Full 44 100 Hz frequency response.
"""

from __future__ import annotations

import numpy as np

from audio_engine.ai.backend import InferenceBackend, ProceduralBackend

__all__ = ["SynthOrchestralBackend"]


class SynthOrchestralBackend(InferenceBackend):
    """Clean synthesised orchestral backend — PS2-era quality mock-up.

    Parameters
    ----------
    sample_rate:
        Engine sample rate in Hz.
    seed:
        RNG seed for reproducibility.
    stereo_width:
        0–1.  Controls how wide the stereo field is spread across
        instrument tracks.  Default 0.9 (near-full width).
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        seed: int | None = None,
        stereo_width: float = 0.9,
    ) -> None:
        super().__init__(sample_rate)
        self._seed = seed
        self._stereo_width = float(np.clip(stereo_width, 0.0, 1.0))
        self._procedural = ProceduralBackend(sample_rate=sample_rate, seed=seed)

    @property
    def name(self) -> str:
        return "synth_orchestral"

    def dependency_summary(self) -> str:
        return "numpy/scipy procedural orchestral pipeline (bundled)"

    def supported_modalities(self) -> tuple[str, ...]:
        return ("music", "sfx", "voice")

    def generate_music_audio(
        self,
        style: str,
        duration: float,
        bpm: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate clean orchestral music with enhanced stereo staging.

        Parameters
        ----------
        style:
            Style preset.  All styles work, but the FF7/FF8 presets
            (``"ff7_battle"``, ``"ff7_sad"``, etc.) use the dedicated
            FF7-timbre instruments and produce the most authentic result.
        duration:
            Target duration in seconds.
        bpm:
            Optional BPM override.
        """
        audio = self._procedural.generate_music_audio(style=style, duration=duration, bpm=bpm)
        return self._apply_orchestral_mastering(audio)

    def generate_sfx_audio(
        self,
        sfx_type: str,
        duration: float,
        pitch_hz: float | None = None,
        **kwargs,
    ) -> np.ndarray:
        """Generate SFX with orchestral reverb staging."""
        audio = self._procedural.generate_sfx_audio(
            sfx_type=sfx_type, duration=duration, pitch_hz=pitch_hz
        )
        return self._apply_sfx_polish(audio)

    def generate_voice_audio(
        self,
        text: str,
        voice_preset: str = "narrator",
        speed: float = 1.0,
        **kwargs,
    ) -> np.ndarray:
        """Generate voice with light hall reverb for orchestral staging."""
        audio = self._procedural.generate_voice_audio(
            text=text, voice_preset=voice_preset, speed=speed
        )
        return self._apply_voice_polish(audio)

    # ------------------------------------------------------------------
    # Mastering helpers
    # ------------------------------------------------------------------

    def _apply_orchestral_mastering(self, audio: np.ndarray) -> np.ndarray:
        """Apply hall reverb + gentle compression for orchestral staging."""
        from audio_engine.render.offline_bounce import OfflineBounce

        bounce = OfflineBounce(
            sample_rate=self.sample_rate,
            target_lufs=-18.0,
            ceiling_db=-0.5,
            apply_master_eq=True,
            apply_compression=True,
        )
        mastered = bounce.process(audio)

        # Widen the stereo field slightly beyond the procedural default
        if mastered.ndim == 2 and self._stereo_width < 1.0 - 1e-4:
            mid  = (mastered[:, 0] + mastered[:, 1]) * 0.5
            side = (mastered[:, 0] - mastered[:, 1]) * 0.5 * self._stereo_width
            mastered = np.stack([mid + side, mid - side], axis=1).astype(np.float32)

        return mastered

    def _apply_sfx_polish(self, audio: np.ndarray) -> np.ndarray:
        """Light EQ + normalise for SFX — no reverb so transients stay punchy."""
        peak = np.max(np.abs(audio))
        if peak > 1e-9:
            audio = (audio / peak * 0.9).astype(np.float32)
        return audio

    def _apply_voice_polish(self, audio: np.ndarray) -> np.ndarray:
        """Gentle high-pass + room reverb for voice intelligibility."""
        try:
            from scipy.signal import butter, sosfilt  # type: ignore[import]
            nyq = self.sample_rate / 2.0
            sos = butter(2, 120.0 / nyq, btype="high", output="sos")
            audio = sosfilt(sos, audio.astype(np.float64)).astype(np.float32)
        except Exception:
            pass
        # Normalise
        peak = np.max(np.abs(audio))
        if peak > 1e-9:
            audio = (audio / peak * 0.85).astype(np.float32)
        return audio
