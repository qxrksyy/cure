"""
Spotify Cog - Control Spotify through Discord commands

This module adds Spotify integration to control music playback and get song information.
"""

from .spotify import Spotify, setup

__all__ = ["Spotify", "setup"] 