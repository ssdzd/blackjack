"""Main entry point for PyGame Balatro-Style Blackjack UI."""

import sys

import pygame

from pygame_ui.config import DIMENSIONS
from pygame_ui.core.scene_manager import SceneManager
from pygame_ui.core.stats_manager import get_stats_manager
from pygame_ui.scenes.title_scene import TitleScene
from pygame_ui.scenes.game_scene import GameScene
from pygame_ui.scenes.settings_scene import SettingsScene
from pygame_ui.scenes.strategy_chart_scene import StrategyChartScene
from pygame_ui.scenes.drill_menu_scene import DrillMenuScene
from pygame_ui.scenes.counting_drill_scene import CountingDrillScene
from pygame_ui.scenes.strategy_drill_scene import StrategyDrillScene
from pygame_ui.scenes.speed_drill_scene import SpeedDrillScene
from pygame_ui.scenes.performance_scene import PerformanceScene
from pygame_ui.core.sound_generator import generate_all_sounds
import os


class Application:
    """Main application class managing the game loop."""

    def __init__(self):
        """Initialize the application."""
        pygame.init()
        pygame.display.set_caption("Blackjack Trainer - Balatro Style")

        self.screen = pygame.display.set_mode(
            (DIMENSIONS.SCREEN_WIDTH, DIMENSIONS.SCREEN_HEIGHT)
        )
        self.clock = pygame.time.Clock()
        self.running = True

        # Ensure sound assets exist
        self._ensure_sounds()

        # Initialize scene manager
        self.scene_manager = SceneManager(self.screen)

        # Register scenes
        self.scene_manager.register("title", TitleScene())
        self.scene_manager.register("game", GameScene())
        self.scene_manager.register("settings", SettingsScene())
        self.scene_manager.register("strategy_chart", StrategyChartScene())
        self.scene_manager.register("drill_menu", DrillMenuScene())
        self.scene_manager.register("counting_drill", CountingDrillScene())
        self.scene_manager.register("strategy_drill", StrategyDrillScene())
        self.scene_manager.register("speed_drill", SpeedDrillScene())
        self.scene_manager.register("performance", PerformanceScene())

        # Mark session start
        get_stats_manager().start_session()

        # Start with title scene
        self.scene_manager.change_to("title", transition=False)

    def _ensure_sounds(self) -> None:
        """Generate sound effects if they don't exist."""
        base = os.path.dirname(os.path.abspath(__file__))
        sounds_dir = os.path.join(base, "assets", "sounds")
        # Check if sounds exist
        if not os.path.exists(os.path.join(sounds_dir, "card_deal.wav")):
            generate_all_sounds(sounds_dir)

    def handle_events(self) -> None:
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            # Pass to scene manager
            self.scene_manager.handle_event(event)

    def update(self, dt: float) -> None:
        """Update application state.

        Args:
            dt: Delta time in seconds
        """
        self.scene_manager.update(dt)

    def draw(self) -> None:
        """Render the application."""
        self.scene_manager.draw()

    def run(self) -> None:
        """Main application loop."""
        while self.running:
            dt = self.clock.tick(DIMENSIONS.TARGET_FPS) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


def main() -> None:
    """Entry point for the pygame UI."""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
