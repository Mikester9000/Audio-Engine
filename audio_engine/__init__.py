"""
Audio Engine – produce music and sound effects for Game Engine for Teaching.

Quick-start
-----------
>>> from audio_engine import AudioEngine
>>> engine = AudioEngine()
>>> engine.generate_track("battle", duration=30, output_path="battle.wav")
"""

from audio_engine.engine import AudioEngine

__all__ = ["AudioEngine"]
__version__ = "1.0.0"
