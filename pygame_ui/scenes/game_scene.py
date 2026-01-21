"""Main game scene with blackjack table - integrated with core engine."""

from decimal import Decimal
from typing import List, Optional

import pygame

from core.game.state import GameState

from pygame_ui.config import ANIMATION, COLORS, DIMENSIONS
from pygame_ui.core.animation import EaseType
from pygame_ui.core.engine_adapter import EngineAdapter, UICardInfo
from pygame_ui.components.card import CardSprite, CardGroup
from pygame_ui.components.counter import CountDisplay, BankrollDisplay
from pygame_ui.components.toast import ToastManager, ToastType
from pygame_ui.components.panel import InfoPanel
from pygame_ui.components.button import ActionButton, Button
from pygame_ui.effects.screen_shake import ScreenShake, SHAKE_IMPACT
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.scenes.base_scene import BaseScene


class GameScene(BaseScene):
    """Main blackjack game scene integrated with the core engine."""

    def __init__(self):
        super().__init__()

        # Engine adapter
        self.engine: Optional[EngineAdapter] = None

        # Card groups
        self.dealer_hand = CardGroup()
        self.player_hands: List[CardGroup] = [CardGroup()]
        self.deck_position = DIMENSIONS.DECK_POSITION

        # Track hovered card
        self.hovered_card: Optional[CardSprite] = None

        # Deck visual
        self.deck_sprite: Optional[CardSprite] = None

        # Visual effects
        self.screen_shake = ScreenShake(SHAKE_IMPACT)
        self.crt_filter = CRTFilter(
            scanline_alpha=25,
            vignette_strength=0.25,
            enabled=True,
        )

        # UI Components
        self.count_display: Optional[CountDisplay] = None
        self.true_count_display: Optional[CountDisplay] = None
        self.bankroll_display: Optional[BankrollDisplay] = None
        self.toast_manager: Optional[ToastManager] = None
        self.deck_panel: Optional[InfoPanel] = None
        self.buttons: List[ActionButton] = []
        self.bet_button: Optional[Button] = None

        # Current bet amount
        self.current_bet = 100

        # Render surface
        self._render_surface: Optional[pygame.Surface] = None

        # Animation queue for delayed card reveals
        self._pending_cards: List[tuple] = []  # (hand_type, card_info, hand_index, delay)
        self._animation_time = 0.0

    def on_enter(self) -> None:
        """Initialize the game scene."""
        super().on_enter()

        # Initialize render surface
        self._render_surface = pygame.Surface(
            (DIMENSIONS.SCREEN_WIDTH, DIMENSIONS.SCREEN_HEIGHT)
        )

        # Initialize engine
        self.engine = EngineAdapter(initial_bankroll=1000)
        self.engine.set_callbacks(
            on_card_dealt=self._on_card_dealt,
            on_hand_result=self._on_hand_result,
            on_dealer_reveal=self._on_dealer_reveal,
            on_shuffle=self._on_shuffle,
            on_count_update=self._on_count_update,
            on_invalid_action=self._on_invalid_action,
        )

        # Initialize deck sprite
        self.deck_sprite = CardSprite(
            x=self.deck_position[0],
            y=self.deck_position[1],
            face_up=False,
        )

        # Initialize UI
        self._setup_ui()

        # Clear hands
        self._clear_hands()

    def on_exit(self) -> None:
        """Clean up when leaving the scene."""
        super().on_exit()
        self._clear_hands()

    def _clear_hands(self) -> None:
        """Clear all card hands."""
        self.dealer_hand.clear()
        for hand in self.player_hands:
            hand.clear()
        self.player_hands = [CardGroup()]

    def _setup_ui(self) -> None:
        """Initialize UI components."""
        # Running count display (top right)
        self.count_display = CountDisplay(
            x=DIMENSIONS.SCREEN_WIDTH - 100,
            y=60,
            initial_value=0,
            font_size=48,
            label="RUNNING",
        )

        # True count display
        self.true_count_display = CountDisplay(
            x=DIMENSIONS.SCREEN_WIDTH - 100,
            y=130,
            initial_value=0,
            font_size=36,
            label="TRUE",
        )
        self.true_count_display.show_decimals = True
        self.true_count_display.decimal_places = 1

        # Bankroll display (top left)
        self.bankroll_display = BankrollDisplay(
            x=120,
            y=80,
            initial_value=self.engine.bankroll if self.engine else 1000,
        )

        # Toast manager
        self.toast_manager = ToastManager()

        # Info panel (deck info)
        self.deck_panel = InfoPanel(
            x=self.deck_position[0],
            y=self.deck_position[1] + 120,
            width=140,
            title="SHOE",
        )
        self._update_deck_panel()

        # Create buttons
        self._setup_buttons()

    def _setup_buttons(self) -> None:
        """Set up action buttons."""
        button_y = DIMENSIONS.PLAYER_HAND_Y + 160
        button_spacing = 110

        # Main action buttons
        hit_button = ActionButton(
            x=DIMENSIONS.CENTER_X - button_spacing * 1.5,
            y=button_y,
            text="HIT",
            action="hit",
            on_click=self._on_hit,
            hotkey="H",
            bg_color=(60, 100, 60),
            hover_color=(80, 130, 80),
        )

        stand_button = ActionButton(
            x=DIMENSIONS.CENTER_X - button_spacing * 0.5,
            y=button_y,
            text="STAND",
            action="stand",
            on_click=self._on_stand,
            hotkey="S",
            bg_color=(100, 60, 60),
            hover_color=(130, 80, 80),
        )

        double_button = ActionButton(
            x=DIMENSIONS.CENTER_X + button_spacing * 0.5,
            y=button_y,
            text="DOUBLE",
            action="double",
            on_click=self._on_double,
            hotkey="D",
            bg_color=(100, 80, 40),
            hover_color=(130, 100, 60),
        )

        split_button = ActionButton(
            x=DIMENSIONS.CENTER_X + button_spacing * 1.5,
            y=button_y,
            text="SPLIT",
            action="split",
            on_click=self._on_split,
            hotkey="P",
            bg_color=(60, 60, 100),
            hover_color=(80, 80, 130),
        )

        self.buttons = [hit_button, stand_button, double_button, split_button]

        # Bet/Deal button
        self.bet_button = Button(
            x=DIMENSIONS.CENTER_X,
            y=DIMENSIONS.SCREEN_HEIGHT // 2,
            text=f"DEAL (${self.current_bet})",
            font_size=36,
            on_click=self._on_deal,
            bg_color=(60, 100, 60),
            hover_color=(80, 130, 80),
            width=200,
            height=60,
        )

    def _update_deck_panel(self) -> None:
        """Update the deck info panel."""
        if self.deck_panel and self.engine:
            self.deck_panel.set_content([
                ("Cards:", str(self.engine.cards_remaining)),
                ("Decks:", f"{self.engine.decks_remaining:.1f}"),
            ])

    def _update_button_states(self) -> None:
        """Update button enabled states based on game state."""
        if not self.engine:
            return

        snapshot = self.engine.get_snapshot()
        state = snapshot.state

        # Show/hide buttons based on state
        show_action_buttons = state == GameState.PLAYER_TURN
        show_bet_button = state == GameState.WAITING_FOR_BET

        for button in self.buttons:
            if show_action_buttons:
                if button.action == "hit":
                    button.set_enabled(snapshot.can_hit)
                elif button.action == "stand":
                    button.set_enabled(snapshot.can_stand)
                elif button.action == "double":
                    button.set_enabled(snapshot.can_double)
                elif button.action == "split":
                    button.set_enabled(snapshot.can_split)
            else:
                button.set_enabled(False)

        if self.bet_button:
            self.bet_button.set_enabled(show_bet_button)

    # Engine callbacks

    def _on_card_dealt(self, hand_type: str, card_info: UICardInfo, hand_index: int) -> None:
        """Handle card dealt event from engine."""
        # Calculate delay based on current card count
        total_cards = len(self.dealer_hand.cards)
        for hand in self.player_hands:
            total_cards += len(hand.cards)
        delay = total_cards * 0.15

        self._pending_cards.append((hand_type, card_info, hand_index, self._animation_time + delay))

    def _process_pending_cards(self) -> None:
        """Process pending card animations."""
        cards_to_remove = []

        for i, (hand_type, card_info, hand_index, trigger_time) in enumerate(self._pending_cards):
            if self._animation_time >= trigger_time:
                self._spawn_card(hand_type, card_info, hand_index)
                cards_to_remove.append(i)

        for i in reversed(cards_to_remove):
            self._pending_cards.pop(i)

    def _spawn_card(self, hand_type: str, card_info: UICardInfo, hand_index: int) -> None:
        """Spawn a card sprite with animation."""
        # Create card at deck position
        card = CardSprite(
            x=self.deck_position[0],
            y=self.deck_position[1],
            face_up=False,
            card_value=card_info.value if card_info.face_up else None,
            card_suit=card_info.suit if card_info.face_up else None,
        )
        card.scale = 0.9

        # Add to appropriate hand
        if hand_type == "dealer":
            self.dealer_hand.add(card)
            target_y = DIMENSIONS.DEALER_HAND_Y
            hand = self.dealer_hand
        else:
            # Ensure we have enough player hands
            while len(self.player_hands) <= hand_index:
                self.player_hands.append(CardGroup())
            self.player_hands[hand_index].add(card)
            target_y = DIMENSIONS.PLAYER_HAND_Y
            hand = self.player_hands[hand_index]

        # Calculate target position
        card_index = len(hand.cards) - 1
        total_width = (len(hand.cards) - 1) * DIMENSIONS.HAND_SPACING
        start_x = DIMENSIONS.CENTER_X - total_width / 2
        target_x = start_x + card_index * DIMENSIONS.HAND_SPACING

        # Animate
        card.animate_to(
            target_x,
            target_y,
            duration=ANIMATION.CARD_DEAL_DURATION,
            ease_type=EaseType.EASE_OUT_BACK,
        )
        card.scale_to(1.0, duration=0.2)

        if card_info.face_up:
            card.flip(
                to_face_up=True,
                delay=ANIMATION.CARD_DEAL_DURATION * 0.5,
            )

        # Rearrange other cards
        self._rearrange_hand(hand, target_y)

        # Update deck panel
        self._update_deck_panel()

    def _rearrange_hand(self, hand: CardGroup, y: float) -> None:
        """Rearrange cards in hand to be centered."""
        if len(hand.cards) <= 1:
            return

        total_width = (len(hand.cards) - 1) * DIMENSIONS.HAND_SPACING
        start_x = DIMENSIONS.CENTER_X - total_width / 2

        for i, card in enumerate(hand.cards[:-1]):
            target_x = start_x + i * DIMENSIONS.HAND_SPACING
            if abs(card.x - target_x) > 1:
                card.animate_to(target_x, y, duration=0.25)

    def _on_hand_result(self, result: str, hand_index: int, amount: float) -> None:
        """Handle hand result event."""
        if self.toast_manager:
            if result == "win":
                self.toast_manager.spawn_result("win", DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 2, amount)
                self.screen_shake.add_trauma(0.3)
            elif result == "blackjack":
                self.toast_manager.spawn_result("blackjack", DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 2, amount)
                self.screen_shake.add_trauma(0.5)
            elif result == "lose":
                self.toast_manager.spawn_result("lose", DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 2, amount)
                self.screen_shake.add_trauma(0.4)
            elif result == "push":
                self.toast_manager.spawn_result("push", DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 2)
            elif result == "bust":
                self.toast_manager.spawn(
                    "BUST!",
                    DIMENSIONS.CENTER_X,
                    DIMENSIONS.PLAYER_HAND_Y - 50,
                    ToastType.ERROR,
                )
                self.screen_shake.add_trauma(0.3)

        # Update bankroll display
        if self.bankroll_display and self.engine:
            self.bankroll_display.set_value(self.engine.bankroll)

    def _on_dealer_reveal(self, card_info: UICardInfo) -> None:
        """Handle dealer hole card reveal."""
        # Find the face-down card and flip it
        for card in self.dealer_hand.cards:
            if not card.is_face_up:
                card.card_value = card_info.value
                card.card_suit = card_info.suit
                card.flip(to_face_up=True)
                break

    def _on_shuffle(self) -> None:
        """Handle shuffle event."""
        if self.toast_manager:
            self.toast_manager.spawn(
                "Shuffling...",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.SCREEN_HEIGHT // 2,
                ToastType.WARNING,
            )
        self.screen_shake.add_trauma(0.2)
        self._update_deck_panel()

    def _on_count_update(self, running: int, true: float) -> None:
        """Handle count update event."""
        if self.count_display:
            flash_color = COLORS.COUNT_POSITIVE if running > self.count_display.value else COLORS.COUNT_NEGATIVE
            self.count_display.set_value(running, flash_color=flash_color if running != self.count_display.value else None)

        if self.true_count_display:
            self.true_count_display.set_value(true)

    def _on_invalid_action(self, message: str) -> None:
        """Handle invalid action."""
        if self.toast_manager:
            self.toast_manager.spawn(
                message,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.SCREEN_HEIGHT // 2,
                ToastType.ERROR,
                duration=1.0,
            )

    # Player actions

    def _on_deal(self) -> None:
        """Start a new round."""
        if not self.engine:
            return

        # Clear previous hands
        self._clear_hands()
        self._pending_cards.clear()
        self._animation_time = 0.0

        # Place bet
        if self.engine.place_bet(self.current_bet):
            self._update_button_states()

    def _on_hit(self) -> None:
        """Player hits."""
        if self.engine:
            self.engine.hit()
            self._update_button_states()

    def _on_stand(self) -> None:
        """Player stands."""
        if self.engine:
            self.engine.stand()
            self._update_button_states()

    def _on_double(self) -> None:
        """Player doubles down."""
        if self.engine:
            self.engine.double_down()
            self._update_button_states()

    def _on_split(self) -> None:
        """Player splits."""
        if self.engine:
            self.engine.split()
            self._update_button_states()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        mouse_pos = pygame.mouse.get_pos()

        # Handle bet button
        if self.bet_button and self.bet_button.enabled:
            if self.bet_button.handle_event(event):
                return True

        # Handle action buttons
        for button in self.buttons:
            if button.enabled and button.handle_event(event):
                return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self._on_hit()
                return True
            elif event.key == pygame.K_s:
                self._on_stand()
                return True
            elif event.key == pygame.K_d:
                self._on_double()
                return True
            elif event.key == pygame.K_p:
                self._on_split()
                return True
            elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                if self.engine and self.engine.state == GameState.WAITING_FOR_BET:
                    self._on_deal()
                return True
            elif event.key == pygame.K_c:
                enabled = self.crt_filter.toggle()
                state = "ON" if enabled else "OFF"
                if self.toast_manager:
                    self.toast_manager.spawn(
                        f"CRT: {state}",
                        DIMENSIONS.CENTER_X,
                        100,
                        ToastType.INFO,
                        duration=1.0,
                    )
                return True
            elif event.key == pygame.K_ESCAPE:
                self.change_scene("title", transition=True)
                return True

        elif event.type == pygame.MOUSEMOTION:
            # Update hover state for player cards
            for hand in self.player_hands:
                new_hovered = hand.get_card_at(mouse_pos)
                if new_hovered != self.hovered_card:
                    if self.hovered_card:
                        self.hovered_card.set_hover(False)
                    if new_hovered:
                        new_hovered.set_hover(True)
                    self.hovered_card = new_hovered
                    break

        return False

    def update(self, dt: float) -> None:
        """Update game state."""
        self._animation_time += dt

        # Process pending card animations
        self._process_pending_cards()

        # Update cards
        self.dealer_hand.update(dt)
        for hand in self.player_hands:
            hand.update(dt)
        if self.deck_sprite:
            self.deck_sprite.update(dt)

        # Update UI
        if self.count_display:
            self.count_display.update(dt)
        if self.true_count_display:
            self.true_count_display.update(dt)
        if self.bankroll_display:
            self.bankroll_display.update(dt)
        if self.toast_manager:
            self.toast_manager.update(dt)

        for button in self.buttons:
            button.update(dt)
        if self.bet_button:
            self.bet_button.update(dt)

        # Update button states
        self._update_button_states()

        # Update effects
        self.screen_shake.update(dt)

    def _draw_game(self, surface: pygame.Surface) -> None:
        """Draw all game elements."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Felt texture
        for x in range(0, DIMENSIONS.SCREEN_WIDTH, 40):
            pygame.draw.line(surface, COLORS.FELT_DARK, (x, 0), (x, DIMENSIONS.SCREEN_HEIGHT), 1)
        for y in range(0, DIMENSIONS.SCREEN_HEIGHT, 40):
            pygame.draw.line(surface, COLORS.FELT_DARK, (0, y), (DIMENSIONS.SCREEN_WIDTH, y), 1)

        # Deck
        if self.deck_sprite:
            self.deck_sprite.draw(surface)
        if self.deck_panel:
            self.deck_panel.draw(surface)

        # Hands
        self.dealer_hand.draw(surface)
        for hand in self.player_hands:
            hand.draw(surface)

        # Labels
        font = pygame.font.Font(None, 36)

        dealer_label = font.render("DEALER", True, COLORS.GOLD)
        dealer_rect = dealer_label.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.DEALER_HAND_Y - 90))
        surface.blit(dealer_label, dealer_rect)

        # Show dealer hand value when revealed
        if self.engine and self.engine.state not in (GameState.WAITING_FOR_BET, GameState.PLAYER_TURN, GameState.DEALING):
            snapshot = self.engine.get_snapshot()
            value_text = font.render(f"({snapshot.dealer_hand_value})", True, COLORS.TEXT_WHITE)
            value_rect = value_text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.DEALER_HAND_Y - 60))
            surface.blit(value_text, value_rect)

        player_label = font.render("PLAYER", True, COLORS.GOLD)
        player_rect = player_label.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.PLAYER_HAND_Y + 90))
        surface.blit(player_label, player_rect)

        # Show player hand values
        if self.engine:
            snapshot = self.engine.get_snapshot()
            for i, value in enumerate(snapshot.player_hand_values):
                if value > 0:
                    value_text = font.render(f"({value})", True, COLORS.TEXT_WHITE)
                    value_rect = value_text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.PLAYER_HAND_Y + 115))
                    surface.blit(value_text, value_rect)

        # UI
        if self.count_display:
            self.count_display.draw(surface)
        if self.true_count_display:
            self.true_count_display.draw(surface)
        if self.bankroll_display:
            self.bankroll_display.draw(surface)

        # Buttons - show appropriate set
        if self.engine and self.engine.state == GameState.WAITING_FOR_BET:
            if self.bet_button:
                self.bet_button.draw(surface)
        else:
            for button in self.buttons:
                button.draw(surface)

        # Toasts
        if self.toast_manager:
            self.toast_manager.draw(surface)

        # State indicator
        if self.engine:
            font_small = pygame.font.Font(None, 24)
            state_text = str(self.engine.state).replace("_", " ").title()
            state_rendered = font_small.render(state_text, True, COLORS.TEXT_MUTED)
            state_rect = state_rendered.get_rect(center=(DIMENSIONS.CENTER_X, 30))
            surface.blit(state_rendered, state_rect)

        # Instructions
        font_small = pygame.font.Font(None, 24)
        crt_state = "ON" if self.crt_filter.enabled else "OFF"
        instructions = f"C: CRT ({crt_state}) | ESC: Menu"
        rendered = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        rect = rendered.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 20))
        surface.blit(rendered, rect)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene with effects."""
        if self._render_surface is None:
            self._render_surface = pygame.Surface(surface.get_size())

        # Draw game to render surface
        self._draw_game(self._render_surface)

        # Apply CRT filter
        self.crt_filter.apply(self._render_surface)

        # Apply shake and blit
        shake_x, shake_y = self.screen_shake.offset
        surface.fill((0, 0, 0))
        surface.blit(self._render_surface, (int(shake_x), int(shake_y)))
