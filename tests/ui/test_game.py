"""Tests for main game UI."""

import pytest
from playwright.sync_api import Page, expect


class TestNavigation:
    """Tests for tab navigation."""

    def test_play_tab_active_by_default(self, game_page: Page):
        """Test that play tab is active on page load."""
        nav_play = game_page.locator("#nav-play")
        expect(nav_play).to_have_class("active")

    def test_navigate_to_count_drill(self, game_page: Page):
        """Test navigating to count drill area."""
        game_page.click("#nav-count-drill")
        expect(game_page.locator("#count-drill-area")).to_be_visible()
        expect(game_page.locator("#game-area")).to_be_hidden()

    def test_navigate_to_strategy_drill(self, game_page: Page):
        """Test navigating to strategy drill area."""
        game_page.click("#nav-strategy-drill")
        expect(game_page.locator("#strategy-drill-area")).to_be_visible()
        expect(game_page.locator("#game-area")).to_be_hidden()

    def test_navigate_back_to_play(self, game_page: Page):
        """Test navigating back to play area."""
        game_page.click("#nav-count-drill")
        game_page.click("#nav-play")
        expect(game_page.locator("#game-area")).to_be_visible()
        expect(game_page.locator("#count-drill-area")).to_be_hidden()


class TestBetting:
    """Tests for betting controls."""

    def test_bet_input_visible(self, game_page: Page):
        """Test that bet input is visible."""
        expect(game_page.locator("#bet-amount")).to_be_visible()

    def test_bet_input_default_value(self, game_page: Page):
        """Test default bet amount."""
        bet_input = game_page.locator("#bet-amount")
        expect(bet_input).to_have_value("10")

    def test_bet_button_visible(self, game_page: Page):
        """Test that bet button is visible."""
        expect(game_page.locator("#btn-bet")).to_be_visible()

    def test_change_bet_amount(self, game_page: Page):
        """Test changing bet amount."""
        bet_input = game_page.locator("#bet-amount")
        bet_input.fill("50")
        expect(bet_input).to_have_value("50")

    def test_place_bet(self, game_page: Page):
        """Test placing a bet starts the game."""
        game_page.click("#btn-bet")
        # After betting, action controls should become visible
        game_page.wait_for_selector("#action-controls:not(.hidden)", timeout=5000)
        expect(game_page.locator("#action-controls")).to_be_visible()


class TestGameActions:
    """Tests for game action buttons."""

    @pytest.fixture
    def active_game_page(self, game_page: Page):
        """A page with an active game (bet placed)."""
        game_page.click("#btn-bet")
        game_page.wait_for_selector("#action-controls:not(.hidden)", timeout=5000)
        return game_page

    def test_hit_button_visible(self, active_game_page: Page):
        """Test hit button is visible during player turn."""
        expect(active_game_page.locator("#btn-hit")).to_be_visible()

    def test_stand_button_visible(self, active_game_page: Page):
        """Test stand button is visible during player turn."""
        expect(active_game_page.locator("#btn-stand")).to_be_visible()

    def test_double_button_visible(self, active_game_page: Page):
        """Test double button is visible during player turn."""
        expect(active_game_page.locator("#btn-double")).to_be_visible()

    def test_split_button_visible(self, active_game_page: Page):
        """Test split button is visible during player turn."""
        expect(active_game_page.locator("#btn-split")).to_be_visible()

    def test_surrender_button_visible(self, active_game_page: Page):
        """Test surrender button is visible during player turn."""
        expect(active_game_page.locator("#btn-surrender")).to_be_visible()

    def test_stand_action(self, active_game_page: Page):
        """Test standing ends player turn."""
        active_game_page.click("#btn-stand")
        # After standing, game should resolve and show result
        active_game_page.wait_for_selector("#result-controls:not(.hidden)", timeout=5000)
        expect(active_game_page.locator("#result-controls")).to_be_visible()


class TestKeyboardShortcuts:
    """Tests for keyboard shortcuts."""

    @pytest.fixture
    def active_game_page(self, game_page: Page):
        """A page with an active game (bet placed)."""
        game_page.click("#btn-bet")
        game_page.wait_for_selector("#action-controls:not(.hidden)", timeout=5000)
        return game_page

    def test_b_key_places_bet(self, game_page: Page):
        """Test B key places bet."""
        game_page.keyboard.press("b")
        game_page.wait_for_selector("#action-controls:not(.hidden)", timeout=5000)
        expect(game_page.locator("#action-controls")).to_be_visible()

    def test_s_key_stands(self, active_game_page: Page):
        """Test S key stands."""
        active_game_page.keyboard.press("s")
        active_game_page.wait_for_selector("#result-controls:not(.hidden)", timeout=5000)
        expect(active_game_page.locator("#result-controls")).to_be_visible()

    def test_h_key_hits(self, active_game_page: Page):
        """Test H key hits."""
        initial_cards = active_game_page.locator("#hand-0 .cards .card").count()
        active_game_page.keyboard.press("h")
        # Either more cards or game ended
        active_game_page.wait_for_function(
            f"document.querySelectorAll('#hand-0 .cards .card').length > {initial_cards} || "
            "!document.querySelector('#result-controls').classList.contains('hidden')",
            timeout=5000,
        )
