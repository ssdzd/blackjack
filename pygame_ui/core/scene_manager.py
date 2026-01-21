"""Scene manager for handling game states and transitions."""

from typing import Dict, List, Optional, Type, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pygame_ui.scenes.base_scene import BaseScene

from pygame_ui.effects.transitions import TransitionManager, FadeTransition


class SceneManager:
    """Manages game scenes and transitions between them.

    Supports:
    - Scene stack (push/pop for menus, overlays)
    - Named scene registry
    - Transitions between scenes
    - Scene lifecycle (enter/exit)
    """

    def __init__(self, screen: pygame.Surface):
        """Initialize the scene manager.

        Args:
            screen: The main pygame display surface
        """
        self.screen = screen
        self.render_surface = pygame.Surface(screen.get_size())

        # Scene registry and stack
        self._scenes: Dict[str, "BaseScene"] = {}
        self._scene_stack: List["BaseScene"] = []

        # Transition system
        self.transitions = TransitionManager()
        self._pending_scene: Optional[str] = None
        self._pending_push: bool = False

    @property
    def current_scene(self) -> Optional["BaseScene"]:
        """Get the currently active scene."""
        return self._scene_stack[-1] if self._scene_stack else None

    @property
    def is_transitioning(self) -> bool:
        """Check if a transition is in progress."""
        return self.transitions.is_active

    def register(self, name: str, scene: "BaseScene") -> None:
        """Register a scene with a name.

        Args:
            name: Unique identifier for the scene
            scene: The scene instance
        """
        self._scenes[name] = scene
        scene.scene_manager = self

    def get_scene(self, name: str) -> Optional["BaseScene"]:
        """Get a registered scene by name.

        Args:
            name: Scene identifier

        Returns:
            The scene or None if not found
        """
        return self._scenes.get(name)

    def change_to(
        self,
        scene_name: str,
        transition: bool = True,
        transition_duration: float = 0.5,
    ) -> None:
        """Change to a different scene (replaces current).

        Args:
            scene_name: Name of the scene to change to
            transition: Whether to use a fade transition
            transition_duration: Duration of the transition
        """
        if scene_name not in self._scenes:
            raise ValueError(f"Scene '{scene_name}' not registered")

        if transition and self.current_scene:
            self._pending_scene = scene_name
            self._pending_push = False
            self.transitions.start_fade(transition_duration)
        else:
            self._do_change(scene_name)

    def push(
        self,
        scene_name: str,
        transition: bool = True,
        transition_duration: float = 0.3,
    ) -> None:
        """Push a scene onto the stack (for overlays, menus).

        Args:
            scene_name: Name of the scene to push
            transition: Whether to use a fade transition
            transition_duration: Duration of the transition
        """
        if scene_name not in self._scenes:
            raise ValueError(f"Scene '{scene_name}' not registered")

        if transition:
            self._pending_scene = scene_name
            self._pending_push = True
            self.transitions.start_fade(transition_duration)
        else:
            self._do_push(scene_name)

    def pop(
        self,
        transition: bool = True,
        transition_duration: float = 0.3,
    ) -> None:
        """Pop the current scene from the stack.

        Args:
            transition: Whether to use a fade transition
            transition_duration: Duration of the transition
        """
        if len(self._scene_stack) <= 1:
            return  # Don't pop the last scene

        if transition:
            self._pending_scene = None  # Signal a pop
            self._pending_push = False
            self.transitions.start_fade(transition_duration)
        else:
            self._do_pop()

    def _do_change(self, scene_name: str) -> None:
        """Actually perform the scene change."""
        # Exit current scene
        if self.current_scene:
            self.current_scene.on_exit()
            self._scene_stack.pop()

        # Enter new scene
        new_scene = self._scenes[scene_name]
        self._scene_stack.append(new_scene)
        new_scene.on_enter()

    def _do_push(self, scene_name: str) -> None:
        """Actually push a scene."""
        # Pause current scene
        if self.current_scene:
            self.current_scene.on_pause()

        # Enter new scene
        new_scene = self._scenes[scene_name]
        self._scene_stack.append(new_scene)
        new_scene.on_enter()

    def _do_pop(self) -> None:
        """Actually pop a scene."""
        if len(self._scene_stack) <= 1:
            return

        # Exit current scene
        self.current_scene.on_exit()
        self._scene_stack.pop()

        # Resume previous scene
        if self.current_scene:
            self.current_scene.on_resume()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Pass event to current scene.

        Args:
            event: The pygame event

        Returns:
            True if event was consumed
        """
        if self.is_transitioning:
            return False  # Block input during transitions

        if self.current_scene:
            return self.current_scene.handle_event(event)
        return False

    def update(self, dt: float) -> None:
        """Update current scene and transitions.

        Args:
            dt: Delta time in seconds
        """
        # Update transitions
        self.transitions.update(dt)

        # Check for pending scene change at midpoint
        if self.transitions.is_at_midpoint and self._pending_scene is not None:
            if self._pending_push:
                self._do_push(self._pending_scene)
            else:
                self._do_change(self._pending_scene)
            self._pending_scene = None
        elif self.transitions.is_at_midpoint and self._pending_scene is None:
            # Pop operation
            self._do_pop()

        # Update current scene
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self) -> None:
        """Draw current scene with transitions."""
        if not self.current_scene:
            self.screen.fill((0, 0, 0))
            pygame.display.flip()
            return

        # Draw scene to render surface
        self.current_scene.draw(self.render_surface)

        # Blit to screen
        self.screen.blit(self.render_surface, (0, 0))

        # Draw transition on top
        self.transitions.draw(self.screen)

        pygame.display.flip()
