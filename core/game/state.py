"""Game state enumeration."""

from enum import Enum, auto


class GameState(Enum):
    """
    Game state machine states.

    Flow: WAITING_FOR_BET → DEALING → PLAYER_TURN → DEALER_TURN → RESOLVING → ROUND_COMPLETE
    """

    # Initial/idle state
    WAITING_FOR_BET = auto()

    # Cards being dealt
    DEALING = auto()

    # Player actions
    PLAYER_TURN = auto()

    # Dealer plays
    DEALER_TURN = auto()

    # Determining winners
    RESOLVING = auto()

    # Round finished, ready for next
    ROUND_COMPLETE = auto()

    # Game over (bankroll exhausted or player quit)
    GAME_OVER = auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


# Valid state transitions
VALID_TRANSITIONS: dict[GameState, list[GameState]] = {
    GameState.WAITING_FOR_BET: [GameState.DEALING, GameState.GAME_OVER],
    GameState.DEALING: [GameState.PLAYER_TURN, GameState.RESOLVING],  # RESOLVING if dealer BJ
    GameState.PLAYER_TURN: [GameState.PLAYER_TURN, GameState.DEALER_TURN, GameState.RESOLVING],
    GameState.DEALER_TURN: [GameState.RESOLVING],
    GameState.RESOLVING: [GameState.ROUND_COMPLETE],
    GameState.ROUND_COMPLETE: [GameState.WAITING_FOR_BET, GameState.GAME_OVER],
    GameState.GAME_OVER: [],  # Terminal state
}


def is_valid_transition(from_state: GameState, to_state: GameState) -> bool:
    """
    Check if a state transition is valid.

    Args:
        from_state: Current state
        to_state: Desired state

    Returns:
        True if the transition is allowed
    """
    return to_state in VALID_TRANSITIONS.get(from_state, [])
