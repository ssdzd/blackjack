"""Tests for drill UI components."""

import pytest
from playwright.sync_api import Page, expect


class TestCountingDrill:
    """Tests for counting drill UI."""

    @pytest.fixture
    def drill_page(self, game_page: Page):
        """A page navigated to counting drill."""
        game_page.click("#nav-count-drill")
        game_page.wait_for_selector("#count-drill-area:not(.hidden)")
        return game_page

    def test_drill_area_visible(self, drill_page: Page):
        """Test drill area is visible."""
        expect(drill_page.locator("#count-drill-area")).to_be_visible()

    def test_drill_settings_visible(self, drill_page: Page):
        """Test drill settings inputs are visible."""
        expect(drill_page.locator("#drill-num-cards")).to_be_visible()
        expect(drill_page.locator("#drill-system")).to_be_visible()
        expect(drill_page.locator("#drill-speed")).to_be_visible()

    def test_default_num_cards(self, drill_page: Page):
        """Test default number of cards."""
        expect(drill_page.locator("#drill-num-cards")).to_have_value("10")

    def test_default_system_hilo(self, drill_page: Page):
        """Test default counting system is Hi-Lo."""
        expect(drill_page.locator("#drill-system")).to_have_value("hilo")

    def test_change_counting_system(self, drill_page: Page):
        """Test changing counting system."""
        drill_page.select_option("#drill-system", "ko")
        expect(drill_page.locator("#drill-system")).to_have_value("ko")

    def test_start_drill_button_visible(self, drill_page: Page):
        """Test start drill button is visible."""
        expect(drill_page.locator("#btn-start-drill")).to_be_visible()

    def test_start_drill_shows_cards(self, drill_page: Page):
        """Test starting drill shows cards."""
        drill_page.fill("#drill-num-cards", "3")
        drill_page.fill("#drill-speed", "500")
        drill_page.click("#btn-start-drill")
        # Wait for drill to complete and input to appear
        drill_page.wait_for_selector("#drill-input-area:not(.hidden)", timeout=10000)
        expect(drill_page.locator("#drill-input-area")).to_be_visible()

    def test_count_input_appears_after_drill(self, drill_page: Page):
        """Test count input appears after cards are shown."""
        drill_page.fill("#drill-num-cards", "3")
        drill_page.fill("#drill-speed", "500")
        drill_page.click("#btn-start-drill")
        drill_page.wait_for_selector("#user-count:not([disabled])", timeout=10000)
        expect(drill_page.locator("#user-count")).to_be_visible()

    def test_submit_count(self, drill_page: Page):
        """Test submitting count shows result."""
        drill_page.fill("#drill-num-cards", "3")
        drill_page.fill("#drill-speed", "500")
        drill_page.click("#btn-start-drill")
        drill_page.wait_for_selector("#drill-input-area:not(.hidden)", timeout=10000)
        drill_page.fill("#user-count", "0")
        drill_page.click("#drill-input-area button")
        drill_page.wait_for_selector("#drill-result:not(.hidden)", timeout=5000)
        expect(drill_page.locator("#drill-result")).to_be_visible()


class TestStrategyDrill:
    """Tests for strategy drill UI."""

    @pytest.fixture
    def strategy_page(self, game_page: Page):
        """A page navigated to strategy drill."""
        game_page.click("#nav-strategy-drill")
        game_page.wait_for_selector("#strategy-drill-area:not(.hidden)")
        return game_page

    def test_strategy_area_visible(self, strategy_page: Page):
        """Test strategy drill area is visible."""
        expect(strategy_page.locator("#strategy-drill-area")).to_be_visible()

    def test_new_hand_button_visible(self, strategy_page: Page):
        """Test new hand button is visible."""
        expect(strategy_page.locator("#btn-start-strategy")).to_be_visible()

    def test_deviations_checkbox_visible(self, strategy_page: Page):
        """Test deviations checkbox is visible."""
        expect(strategy_page.locator("#include-deviations")).to_be_visible()

    def test_start_strategy_drill(self, strategy_page: Page):
        """Test starting strategy drill shows cards."""
        strategy_page.click("#btn-start-strategy")
        strategy_page.wait_for_selector("#strategy-dealer-card .card", timeout=5000)
        expect(strategy_page.locator("#strategy-dealer-card")).to_be_visible()
        expect(strategy_page.locator("#strategy-player-cards")).to_be_visible()

    def test_action_buttons_visible(self, strategy_page: Page):
        """Test strategy action buttons are visible."""
        strategy_page.click("#btn-start-strategy")
        strategy_page.wait_for_selector("#strategy-dealer-card .card", timeout=5000)
        action_buttons = strategy_page.locator(".strategy-action-btn")
        expect(action_buttons).to_have_count(5)  # hit, stand, double, split, surrender

    def test_click_action_shows_result(self, strategy_page: Page):
        """Test clicking an action shows result."""
        strategy_page.click("#btn-start-strategy")
        strategy_page.wait_for_selector("#strategy-dealer-card .card", timeout=5000)
        # Click the stand button (usually a safe choice)
        strategy_page.click(".strategy-action-btn[data-action='stand']")
        strategy_page.wait_for_selector("#strategy-result:not(.hidden)", timeout=5000)
        expect(strategy_page.locator("#strategy-result")).to_be_visible()
