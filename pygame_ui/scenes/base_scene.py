"""Base scene class for all game scenes."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

import pygame

if TYPE_CHECKING:
    from pygame_ui.core.scene_manager import SceneManager


class BaseScene(ABC):
    """Abstract base class for all game scenes.

    Lifecycle:
    - on_enter(): Called when scene becomes active
    - on_exit(): Called when scene is removed
    - on_pause(): Called when another scene is pushed on top
    - on_resume(): Called when scene becomes active again after pop

    Main loop methods:
    - handle_event(event): Process input
    - update(dt): Update game logic
    - draw(surface): Render to surface
    """

    def __init__(self):
        """Initialize the base scene."""
        self.scene_manager: Optional["SceneManager"] = None
        self._is_active = False
        self._is_paused = False

    @property
    def is_active(self) -> bool:
        """Check if this scene is currently active."""
        return self._is_active

    @property
    def is_paused(self) -> bool:
        """Check if this scene is paused (another scene on top)."""
        return self._is_paused

    def on_enter(self) -> None:
        """Called when this scene becomes active.

        Override to initialize scene state, start music, etc.
        """
        self._is_active = True
        self._is_paused = False

    def on_exit(self) -> None:
        """Called when this scene is removed.

        Override to clean up resources, stop music, etc.
        """
        self._is_active = False

    def on_pause(self) -> None:
        """Called when another scene is pushed on top.

        Override to pause gameplay, mute sounds, etc.
        """
        self._is_paused = True

    def on_resume(self) -> None:
        """Called when this scene becomes active again.

        Override to resume gameplay, restore state, etc.
        """
        self._is_paused = False

    def change_scene(self, scene_name: str, transition: bool = True) -> None:
        """Request a scene change.

        Args:
            scene_name: Name of the scene to change to
            transition: Whether to use a transition
        """
        if self.scene_manager:
            self.scene_manager.change_to(scene_name, transition)

    def push_scene(self, scene_name: str, transition: bool = True) -> None:
        """Request to push a scene on top.

        Args:
            scene_name: Name of the scene to push
            transition: Whether to use a transition
        """
        if self.scene_manager:
            self.scene_manager.push(scene_name, transition)

    def pop_scene(self, transition: bool = True) -> None:
        """Request to pop this scene.

        Args:
            transition: Whether to use a transition
        """
        if self.scene_manager:
            self.scene_manager.pop(transition)

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle a pygame event.

        Args:
            event: The pygame event to handle

        Returns:
            True if the event was consumed, False otherwise
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update scene logic.

        Args:
            dt: Delta time in seconds since last update
        """
        pass

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene to a surface.

        Args:
            surface: The pygame surface to draw on
        """
        pass
