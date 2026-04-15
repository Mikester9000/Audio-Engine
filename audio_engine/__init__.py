"""
Audio Engine – produce music, SFX, and voice for games with AI assistance.

Quick-start
-----------
>>> from audio_engine import AudioEngine
>>> engine = AudioEngine()
>>> engine.generate_track("battle", bars=8, output_path="battle.wav")

AI generation pipeline
----------------------
>>> from audio_engine.ai import MusicGen, SFXGen, VoiceGen
>>> MusicGen().generate_to_file("ambient dungeon loop", "dungeon.wav", duration=60, loopable=True)
>>> SFXGen().generate_to_file("coin collect", "coin.wav")
>>> VoiceGen().generate_to_file("Level complete!", "level_done.wav", voice="announcer")

Quality assurance
-----------------
>>> from audio_engine.qa import LoudnessMeter, ClippingDetector, LoopAnalyzer
>>> result = LoudnessMeter(44100).measure(audio)
"""

from audio_engine.engine import AudioEngine

__all__ = ["AudioEngine"]
__version__ = "2.0.0"
