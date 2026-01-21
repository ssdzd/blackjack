"""Tests for stats panel UI."""

import pytest
from playwright.sync_api import Page, expect


class TestStatsPanel:
    """Tests for stats panel displays."""

    def test_stats_panel_visible(self, game_page: Page):
        """Test stats panel is visible."""
        expect(game_page.locator("#stats-panel")).to_be_visible()

    def test_running_count_visible(self, game_page: Page):
        """Test running count display is visible."""
        expect(game_page.locator("#running-count")).to_be_visible()

    def test_true_count_visible(self, game_page: Page):
        """Test true count display is visible."""
        expect(game_page.locator("#true-count")).to_be_visible()

    def test_cards_remaining_visible(self, game_page: Page):
        """Test cards remaining display is visible."""
        expect(game_page.locator("#cards-remaining")).to_be_visible()

    def test_initial_running_count(self, game_page: Page):
        """Test initial running count is zero."""
        running_count = game_page.locator("#running-count span")
        expect(running_count).to_have_text("0")

    def test_initial_true_count(self, game_page: Page):
        """Test initial true count is zero."""
        true_count = game_page.locator("#true-count span")
        expect(true_count).to_have_text("0")

    def test_initial_cards_remaining(self, game_page: Page):
        """Test initial cards remaining is 312 (6 decks)."""
        cards_remaining = game_page.locator("#cards-remaining span")
        expect(cards_remaining).to_have_text("312")

    def test_session_stats_visible(self, game_page: Page):
        """Test session stats are visible."""
        expect(game_page.locator("#hands-played")).to_be_visible()
        expect(game_page.locator("#win-rate")).to_be_visible()
        expect(game_page.locator("#net-result")).to_be_visible()

    def test_initial_hands_played(self, game_page: Page):
        """Test initial hands played is zero."""
        hands_played = game_page.locator("#hands-played span")
        expect(hands_played).to_have_text("0")

    def test_toggle_count_button_visible(self, game_page: Page):
        """Test toggle count button is visible."""
        expect(game_page.locator("#toggle-count")).to_be_visible()

    def test_count_updates_after_hand(self, game_page: Page):
        """Test count updates after playing a hand."""
        initial_cards = game_page.locator("#cards-remaining span").text_content()

        # Play a hand
        game_page.click("#btn-bet")
        game_page.wait_for_selector("#action-controls:not(.hidden)", timeout=5000)
        game_page.click("#btn-stand")
        game_page.wait_for_selector("#result-controls:not(.hidden)", timeout=5000)

        # Cards remaining should decrease
        updated_cards = game_page.locator("#cards-remaining span").text_content()
        assert int(updated_cards) < int(initial_cards)

    def test_hands_played_increments(self, game_page: Page):
        """Test hands played increments after completing a hand."""
        # Play a hand
        game_page.click("#btn-bet")
        game_page.wait_for_selector("#action-controls:not(.hidden)", timeout=5000)
        game_page.click("#btn-stand")
        game_page.wait_for_selector("#result-controls:not(.hidden)", timeout=5000)

        hands_played = game_page.locator("#hands-played span")
        expect(hands_played).to_have_text("1")
