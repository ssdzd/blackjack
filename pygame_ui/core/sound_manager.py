"""Sound manager for game audio effects."""

import os
from typing import Dict, Optional

import pygame


class SoundManager:
    """Manages game sound effects and music.

    Gracefully handles missing sound files.
    """

    # Sound effect names and default volumes
    SOUNDS = {
        "card_deal": 0.4,
        "card_flip": 0.3,
        "chip_stack": 0.5,
        "chip_single": 0.3,
        "win": 0.6,
        "lose": 0.4,
        "blackjack": 0.7,
        "bust": 0.5,
        "button_hover": 0.1,
        "button_click": 0.2,
        "shuffle": 0.5,
    }

    def __init__(self, assets_path: str = None):
        """Initialize the sound manager.

        Args:
            assets_path: Path to assets/sounds directory
        """
        self._initialized = False
        self._enabled = True
        self._master_volume = 0.7
        self._sounds: Dict[str, pygame.mixer.Sound] = {}

        # Determine assets path
        if assets_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            assets_path = os.path.join(base, "assets", "sounds")
        self._assets_path = assets_path

        self._init_mixer()

    def _init_mixer(self) -> None:
        """Initialize pygame mixer."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._initialized = True
            self._load_sounds()
        except pygame.error as e:
            print(f"Sound initialization failed: {e}")
            self._initialized = False

    def _load_sounds(self) -> None:
        """Load all sound effects."""
        if not self._initialized:
            return

        for name in self.SOUNDS:
            self._load_sound(name)

    def _load_sound(self, name: str) -> Optional[pygame.mixer.Sound]:
        """Load a single sound effect."""
        if not self._initialized:
            return None

        # Try different file extensions
        extensions = [".wav", ".ogg", ".mp3"]
        for ext in extensions:
            path = os.path.join(self._assets_path, f"{name}{ext}")
            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(self.SOUNDS.get(name, 0.5) * self._master_volume)
                    self._sounds[name] = sound
                    return sound
                except pygame.error:
                    pass
        return None

    def play(self, name: str, volume: float = None) -> None:
        """Play a sound effect.

        Args:
            name: Sound effect name
            volume: Optional volume override (0.0 to 1.0)
        """
        if not self._enabled or not self._initialized:
            return

        sound = self._sounds.get(name)
        if sound:
            if volume is not None:
                sound.set_volume(volume * self._master_volume)
            sound.play()

    def play_with_variation(self, name: str, pitch_var: float = 0.1) -> None:
        """Play sound with slight pitch variation for variety.

        Note: pygame doesn't support pitch shifting, so we just play normally.
        This method exists for API consistency if we add a better audio backend later.
        """
        self.play(name)

    @property
    def enabled(self) -> bool:
        """Check if sound is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable sound."""
        self._enabled = value

    def toggle(self) -> bool:
        """Toggle sound on/off. Returns new state."""
        self._enabled = not self._enabled
        return self._enabled

    @property
    def volume(self) -> float:
        """Get master volume."""
        return self._master_volume

    @volume.setter
    def volume(self, value: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        self._master_volume = max(0.0, min(1.0, value))
        # Update all loaded sounds
        for name, sound in self._sounds.items():
            base_vol = self.SOUNDS.get(name, 0.5)
            sound.set_volume(base_vol * self._master_volume)

    def stop_all(self) -> None:
        """Stop all playing sounds."""
        if self._initialized:
            pygame.mixer.stop()


# Global sound manager instance
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Get the global sound manager instance."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager


def play_sound(name: str, volume: float = None) -> None:
    """Convenience function to play a sound."""
    get_sound_manager().play(name, volume)
