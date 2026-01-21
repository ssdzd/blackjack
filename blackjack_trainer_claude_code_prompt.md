# Blackjack Card Counting Trainer - Claude Code Bootstrap Prompt

## Project Overview

Build a professional-grade blackjack card counting training application in Python. The application is a **statistical engine first, game second**—an advanced blackjack calculator with a playable interface layered on top, designed to teach users card counting through progressive skill development.

**Architecture Philosophy**: Design for UI swappability. The core engine must be 100% UI-agnostic so we can later add:
1. FastAPI + web frontend (primary, build first)
2. Textual CLI (power user mode)  
3. PyGame retro pixel version (commercial aesthetic)

## Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI with WebSocket support for real-time game state
- **Frontend**: Lightweight vanilla JS + htmx (keep it simple, swappable)
- **Session Storage**: Redis (for GCP deployment readiness) with in-memory fallback for local dev
- **Testing**: pytest with hypothesis for property-based testing
- **Type Hints**: Full typing throughout, use Pydantic for all data models

## Project Structure

```
blackjack_trainer/
├── core/                      # Pure Python, ZERO UI dependencies
│   ├── __init__.py
│   ├── cards.py              # Card, Deck, Shoe classes
│   ├── hand.py               # Hand evaluation, soft/hard detection
│   ├── counting/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract counting system interface
│   │   ├── hilo.py           # Hi-Lo implementation
│   │   ├── ko.py             # Knock-Out (unbalanced) implementation
│   │   ├── omega2.py         # Omega II with ace side count
│   │   └── wong_halves.py    # Wong Halves (fractional values)
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── basic.py          # Basic strategy matrices (hard/soft/pairs)
│   │   ├── deviations.py     # Illustrious 18 + Fab 4 index plays
│   │   └── rules.py          # Rule variations (H17/S17, DAS, surrender, etc.)
│   ├── statistics/
│   │   ├── __init__.py
│   │   ├── probability.py    # Dealer outcome distributions, player win odds
│   │   ├── house_edge.py     # House edge calculator by rule set
│   │   ├── kelly.py          # Kelly Criterion bet sizing
│   │   └── bankroll.py       # Risk of ruin, N0 calculations
│   └── game/
│       ├── __init__.py
│       ├── state.py          # Game state machine (use `transitions` library)
│       ├── engine.py         # Core game logic, action processing
│       └── events.py         # Event system for UI subscription
├── api/                       # FastAPI layer
│   ├── __init__.py
│   ├── main.py               # FastAPI app, CORS, middleware
│   ├── routes/
│   │   ├── game.py           # Game endpoints (create, action, state)
│   │   ├── training.py       # Training mode endpoints
│   │   └── stats.py          # Statistics/analytics endpoints
│   ├── websocket.py          # WebSocket manager for real-time updates
│   ├── schemas.py            # Pydantic request/response models
│   └── session.py            # Redis session management
├── frontend/                  # Static files served by FastAPI
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── game.js           # Game UI logic
│       ├── websocket.js      # WebSocket client
│       └── charts.js         # Statistics visualization
├── tests/
│   ├── core/
│   │   ├── test_cards.py
│   │   ├── test_counting.py
│   │   ├── test_strategy.py
│   │   └── test_statistics.py
│   └── api/
│       └── test_endpoints.py
├── config.py                  # Configuration management
├── requirements.txt
└── README.md
```

## Core Engine Specifications

### Card and Shoe System (`core/cards.py`)

```python
from dataclasses import dataclass
from enum import Enum
from typing import List
import random

class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Rank(Enum):
    TWO = 2
    THREE = 3
    # ... through ACE = 14 (or 1, your choice)

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit
    
    @property
    def value(self) -> int:
        """Blackjack value (face cards = 10, Ace = 11 initially)"""
        ...
    
    @property  
    def is_ace(self) -> bool:
        ...

class Shoe:
    """Multi-deck shoe with penetration tracking"""
    
    def __init__(self, num_decks: int = 6, penetration: float = 0.75):
        self.num_decks = num_decks
        self.penetration = penetration  # Cut card position (0.75 = 75% dealt)
        self.cards: List[Card] = []
        self.dealt_cards: List[Card] = []
        self.shuffle()
    
    def shuffle(self) -> None:
        """Fisher-Yates shuffle, reset dealt cards"""
        ...
    
    def deal(self) -> Card:
        """Deal one card, track in dealt_cards"""
        ...
    
    @property
    def cards_remaining(self) -> int:
        ...
    
    @property
    def decks_remaining(self) -> float:
        """For true count calculation, minimum 0.5"""
        return max(len(self.cards) / 52.0, 0.5)
    
    @property
    def needs_shuffle(self) -> bool:
        """True if penetration point reached"""
        ...
```

### Counting Systems (`core/counting/`)

Create an abstract base class and implement all four systems:

```python
from abc import ABC, abstractmethod
from typing import Dict, Optional
from core.cards import Card, Rank

class CountingSystem(ABC):
    """Abstract base for all counting systems"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        ...
    
    @property
    @abstractmethod
    def card_values(self) -> Dict[Rank, float]:
        """Map of rank to count value"""
        ...
    
    @property
    @abstractmethod
    def is_balanced(self) -> bool:
        """True if full deck sums to zero"""
        ...
    
    def __init__(self, num_decks: int = 6):
        self.num_decks = num_decks
        self.running_count: float = 0
        self.cards_seen: int = 0
        self.reset()
    
    def reset(self) -> None:
        """Reset for new shoe - override for unbalanced systems"""
        self.running_count = 0
        self.cards_seen = 0
    
    def count_card(self, card: Card) -> float:
        """Process a card, return its count value"""
        value = self.card_values[card.rank]
        self.running_count += value
        self.cards_seen += 1
        return value
    
    def get_true_count(self, decks_remaining: float) -> float:
        """Convert running count to true count"""
        if not self.is_balanced:
            # Unbalanced systems use running count directly
            return self.running_count
        return self.running_count / decks_remaining
    
    @property
    def betting_correlation(self) -> float:
        """System's correlation with optimal betting"""
        ...
    
    @property
    def playing_efficiency(self) -> float:
        """System's efficiency for strategy deviations"""
        ...


class HiLoCount(CountingSystem):
    """
    Hi-Lo: The gold standard balanced count
    2-6: +1, 7-9: 0, 10-A: -1
    BC: 0.97, PE: 0.51
    """
    
    @property
    def card_values(self) -> Dict[Rank, float]:
        return {
            Rank.TWO: 1, Rank.THREE: 1, Rank.FOUR: 1,
            Rank.FIVE: 1, Rank.SIX: 1,
            Rank.SEVEN: 0, Rank.EIGHT: 0, Rank.NINE: 0,
            Rank.TEN: -1, Rank.JACK: -1, Rank.QUEEN: -1,
            Rank.KING: -1, Rank.ACE: -1
        }


class KOCount(CountingSystem):
    """
    Knock-Out: Unbalanced system, no true count needed
    2-7: +1, 8-9: 0, 10-A: -1
    Initial RC = 4 - (4 * num_decks)
    Pivot point: +4 indicates ~1.5% advantage
    """
    
    def reset(self) -> None:
        # KO starts at negative IRC
        self.running_count = 4 - (4 * self.num_decks)
        self.cards_seen = 0
    
    @property
    def pivot_point(self) -> int:
        return 4  # Bet big when RC >= pivot
    
    @property
    def key_count(self) -> int:
        return self.pivot_point - 1  # Start ramping bets


class OmegaIICount(CountingSystem):
    """
    Omega II: Level 2 balanced count with ace side count
    2,3,7: +1, 4,5,6: +2, 8,A: 0, 9: -1, 10s: -2
    BC: 0.92 (0.99 with side count), PE: 0.67
    """
    
    def __init__(self, num_decks: int = 6):
        super().__init__(num_decks)
        self.ace_side_count: int = 0  # Track aces separately
        self.expected_aces_per_deck: float = 4.0
    
    def reset(self) -> None:
        super().reset()
        self.ace_side_count = 0
    
    def count_card(self, card: Card) -> float:
        if card.is_ace:
            self.ace_side_count += 1
        return super().count_card(card)
    
    @property
    def ace_richness(self) -> float:
        """Positive = ace rich, negative = ace poor"""
        decks_seen = self.cards_seen / 52.0
        expected_aces = decks_seen * self.expected_aces_per_deck
        return self.ace_side_count - expected_aces


class WongHalvesCount(CountingSystem):
    """
    Wong Halves: Highest accuracy, fractional values
    2,7: +0.5, 3,4,6: +1, 5: +1.5, 8: 0, 9: -0.5, 10-A: -1
    BC: 0.99, PE: 0.57
    
    Implementation note: Can double all values internally
    and halve when displaying/calculating TC
    """
    ...
```

### Basic Strategy Engine (`core/strategy/`)

```python
from enum import Enum
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

class Action(Enum):
    HIT = "H"
    STAND = "S"
    DOUBLE = "D"
    SPLIT = "P"
    SURRENDER = "R"
    # Conditional actions
    DOUBLE_OR_HIT = "Dh"      # Double if allowed, else hit
    DOUBLE_OR_STAND = "Ds"    # Double if allowed, else stand
    SURRENDER_OR_HIT = "Rh"   # Surrender if allowed, else hit
    SPLIT_OR_HIT = "Ph"       # Split if DAS, else hit

@dataclass
class RuleSet:
    """Configurable casino rules"""
    num_decks: int = 6
    dealer_hits_soft_17: bool = True   # H17 vs S17
    double_after_split: bool = True    # DAS
    surrender_allowed: bool = True     # Late surrender
    blackjack_payout: float = 1.5      # 3:2 = 1.5, 6:5 = 1.2
    dealer_peeks: bool = True          # Peek for blackjack
    resplit_aces: bool = False
    hit_split_aces: bool = False
    max_splits: int = 4

class BasicStrategy:
    """
    Complete basic strategy matrices
    Indexed by (player_total or hand_type, dealer_upcard)
    """
    
    def __init__(self, rules: RuleSet):
        self.rules = rules
        self._load_strategy_tables()
    
    def _load_strategy_tables(self) -> None:
        # Hard totals: player total 5-21 vs dealer 2-11(A)
        self.hard_totals: Dict[int, Dict[int, Action]] = {
            8:  {2: Action.HIT, 3: Action.HIT, 4: Action.HIT, ...},
            9:  {2: Action.HIT, 3: Action.DOUBLE_OR_HIT, ...},
            # ... complete matrix
        }
        
        # Soft totals: A,2 through A,9 vs dealer 2-11
        self.soft_totals: Dict[int, Dict[int, Action]] = {...}
        
        # Pairs: 2,2 through A,A vs dealer 2-11
        self.pairs: Dict[int, Dict[int, Action]] = {...}
    
    def get_action(self, 
                   hand: 'Hand', 
                   dealer_upcard: Card,
                   can_double: bool = True,
                   can_split: bool = True,
                   can_surrender: bool = True) -> Action:
        """
        Return optimal basic strategy action
        Resolves conditional actions based on available options
        """
        dealer_value = min(dealer_upcard.value, 11)  # Ace = 11
        
        # Check pairs first
        if hand.is_pair and can_split:
            raw_action = self.pairs[hand.pair_rank][dealer_value]
        elif hand.is_soft:
            raw_action = self.soft_totals[hand.soft_total][dealer_value]
        else:
            raw_action = self.hard_totals[hand.hard_total][dealer_value]
        
        # Resolve conditional actions
        return self._resolve_action(raw_action, can_double, can_split, can_surrender)
    
    def _resolve_action(self, action: Action, 
                        can_double: bool,
                        can_split: bool, 
                        can_surrender: bool) -> Action:
        """Convert conditional actions to concrete actions"""
        if action == Action.DOUBLE_OR_HIT:
            return Action.DOUBLE if can_double else Action.HIT
        if action == Action.DOUBLE_OR_STAND:
            return Action.DOUBLE if can_double else Action.STAND
        if action == Action.SURRENDER_OR_HIT:
            return Action.SURRENDER if can_surrender else Action.HIT
        if action == Action.SPLIT_OR_HIT:
            return Action.SPLIT if can_split else Action.HIT
        return action
```

### Strategy Deviations (`core/strategy/deviations.py`)

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class IndexPlay:
    """A count-based strategy deviation"""
    name: str
    player_hand: str           # e.g., "16", "A,7", "10,10"
    dealer_upcard: int
    basic_strategy: Action     # What basic strategy says
    deviation: Action          # What to do instead
    index: int                 # True count threshold
    direction: str             # ">=", "<=", ">", "<"
    
    def applies(self, true_count: float) -> bool:
        if self.direction == ">=":
            return true_count >= self.index
        elif self.direction == "<=":
            return true_count <= self.index
        # etc.

# The Illustrious 18 - captures 80%+ of deviation value
ILLUSTRIOUS_18: List[IndexPlay] = [
    IndexPlay("Insurance", "any", 11, Action.HIT, Action.STAND, 3, ">="),  # Most valuable
    IndexPlay("16 vs 10", "16", 10, Action.HIT, Action.STAND, 0, ">="),
    IndexPlay("15 vs 10", "15", 10, Action.HIT, Action.STAND, 4, ">="),
    IndexPlay("10,10 vs 5", "10,10", 5, Action.STAND, Action.SPLIT, 5, ">="),
    IndexPlay("10,10 vs 6", "10,10", 6, Action.STAND, Action.SPLIT, 4, ">="),
    IndexPlay("10 vs 10", "10", 10, Action.HIT, Action.DOUBLE, 4, ">="),
    IndexPlay("12 vs 3", "12", 3, Action.HIT, Action.STAND, 2, ">="),
    IndexPlay("12 vs 2", "12", 2, Action.HIT, Action.STAND, 3, ">="),
    IndexPlay("11 vs A", "11", 11, Action.HIT, Action.DOUBLE, 1, ">="),
    IndexPlay("9 vs 2", "9", 2, Action.HIT, Action.DOUBLE, 1, ">="),
    IndexPlay("10 vs A", "10", 11, Action.HIT, Action.DOUBLE, 4, ">="),
    IndexPlay("9 vs 7", "9", 7, Action.HIT, Action.DOUBLE, 3, ">="),
    IndexPlay("16 vs 9", "16", 9, Action.HIT, Action.STAND, 5, ">="),
    IndexPlay("13 vs 2", "13", 2, Action.STAND, Action.HIT, -1, "<="),
    IndexPlay("12 vs 4", "12", 4, Action.STAND, Action.HIT, 0, "<="),
    IndexPlay("12 vs 5", "12", 5, Action.STAND, Action.HIT, -2, "<="),
    IndexPlay("12 vs 6", "12", 6, Action.STAND, Action.HIT, -1, "<="),
    IndexPlay("13 vs 3", "13", 3, Action.STAND, Action.HIT, -2, "<="),
]

# Fab 4 Surrender indices
FAB_4_SURRENDER: List[IndexPlay] = [
    IndexPlay("14 vs 10", "14", 10, Action.HIT, Action.SURRENDER, 3, ">="),
    IndexPlay("15 vs 10", "15", 10, Action.HIT, Action.SURRENDER, 0, ">="),
    IndexPlay("15 vs 9", "15", 9, Action.HIT, Action.SURRENDER, 2, ">="),
    IndexPlay("15 vs A", "15", 11, Action.HIT, Action.SURRENDER, 1, ">="),
]
```

### Statistics Engine (`core/statistics/`)

```python
from dataclasses import dataclass
from typing import Dict, Tuple
import math

@dataclass
class DealerOutcomes:
    """Probability distribution of dealer final hands"""
    bust: float
    seventeen: float
    eighteen: float
    nineteen: float
    twenty: float
    twentyone: float
    blackjack: float  # Natural 21

# Base dealer probabilities by upcard (infinite deck approximation)
DEALER_PROBABILITIES: Dict[int, DealerOutcomes] = {
    2: DealerOutcomes(bust=0.3536, seventeen=0.1395, ...),
    3: DealerOutcomes(bust=0.3754, ...),
    # Through Ace (11)
}

class ProbabilityEngine:
    """Real-time probability calculations"""
    
    def __init__(self, shoe: 'Shoe', rules: RuleSet):
        self.shoe = shoe
        self.rules = rules
    
    def dealer_bust_probability(self, upcard: Card) -> float:
        """P(dealer busts | upcard)"""
        # Start with base probability, adjust for deck composition
        base = DEALER_PROBABILITIES[upcard.value].bust
        # TODO: Adjust based on remaining deck composition
        return base
    
    def player_win_probability(self, 
                               player_hand: 'Hand',
                               dealer_upcard: Card) -> float:
        """P(player wins | current hands)"""
        ...
    
    def expected_value(self,
                       player_hand: 'Hand',
                       dealer_upcard: Card,
                       action: Action) -> float:
        """EV of taking a specific action"""
        ...


class HouseEdgeCalculator:
    """Calculate house edge for given rule set"""
    
    BASE_EDGE = 0.0042  # ~0.42% for 6-deck, S17, DAS, no surrender
    
    RULE_ADJUSTMENTS = {
        'h17': +0.0022,           # Dealer hits soft 17
        'no_das': +0.0014,        # No double after split
        'no_surrender': +0.0008,  # No late surrender
        '6:5_blackjack': +0.0139, # 6:5 instead of 3:2
        'single_deck': -0.0048,   # Single deck advantage
        'double_deck': -0.0021,   # Double deck advantage
    }
    
    def calculate(self, rules: RuleSet) -> float:
        """Return house edge as decimal (0.005 = 0.5%)"""
        edge = self.BASE_EDGE
        
        if rules.dealer_hits_soft_17:
            edge += self.RULE_ADJUSTMENTS['h17']
        if not rules.double_after_split:
            edge += self.RULE_ADJUSTMENTS['no_das']
        if not rules.surrender_allowed:
            edge += self.RULE_ADJUSTMENTS['no_surrender']
        if rules.blackjack_payout < 1.5:
            edge += self.RULE_ADJUSTMENTS['6:5_blackjack']
        if rules.num_decks == 1:
            edge += self.RULE_ADJUSTMENTS['single_deck']
        elif rules.num_decks == 2:
            edge += self.RULE_ADJUSTMENTS['double_deck']
        
        return edge


class KellyCalculator:
    """Kelly Criterion bet sizing"""
    
    BLACKJACK_VARIANCE = 1.3225  # SD ≈ 1.15
    
    def optimal_bet_fraction(self, edge: float) -> float:
        """Full Kelly bet as fraction of bankroll"""
        if edge <= 0:
            return 0
        return edge / self.BLACKJACK_VARIANCE
    
    def recommended_bet(self,
                        bankroll: float,
                        edge: float,
                        kelly_fraction: float = 0.5) -> float:
        """
        Recommended bet amount
        kelly_fraction: 0.5 = half Kelly (recommended), 1.0 = full Kelly
        """
        full_kelly = self.optimal_bet_fraction(edge)
        return bankroll * full_kelly * kelly_fraction
    
    def risk_of_ruin(self,
                     bankroll_units: float,
                     edge: float) -> float:
        """Probability of losing entire bankroll"""
        if edge <= 0:
            return 1.0
        return math.exp(-2 * edge * bankroll_units / self.BLACKJACK_VARIANCE)
    
    def bet_spread_recommendation(self,
                                  true_count: float,
                                  base_bet: float,
                                  max_spread: int = 12) -> float:
        """
        Suggested bet based on true count
        Standard spread: bet TC-1 units when TC >= 2
        """
        if true_count < 1:
            return base_bet
        
        units = max(1, min(true_count - 1, max_spread))
        return base_bet * units
```

### Game State Machine (`core/game/`)

```python
from enum import Enum, auto
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from transitions import Machine

class GameState(Enum):
    WAITING_FOR_BET = auto()
    DEALING = auto()
    PLAYER_TURN = auto()
    SPLITTING = auto()      # Handling split hands
    DEALER_TURN = auto()
    RESOLVING = auto()
    ROUND_COMPLETE = auto()

@dataclass
class GameEvent:
    """Events emitted for UI consumption"""
    event_type: str
    data: dict
    timestamp: float = field(default_factory=time.time)

class BlackjackGame:
    """
    Core game engine with state machine
    Emits events for any UI to consume
    """
    
    states = [s.name.lower() for s in GameState]
    
    transitions = [
        {'trigger': 'place_bet', 'source': 'waiting_for_bet', 'dest': 'dealing',
         'before': '_validate_bet'},
        {'trigger': 'deal_complete', 'source': 'dealing', 'dest': 'player_turn',
         'conditions': '_no_blackjacks'},
        {'trigger': 'deal_complete', 'source': 'dealing', 'dest': 'resolving',
         'unless': '_no_blackjacks'},
        {'trigger': 'hit', 'source': 'player_turn', 'dest': 'player_turn',
         'unless': '_is_busted', 'after': '_emit_card_dealt'},
        {'trigger': 'hit', 'source': 'player_turn', 'dest': 'resolving',
         'conditions': '_is_busted'},
        {'trigger': 'stand', 'source': 'player_turn', 'dest': 'dealer_turn'},
        {'trigger': 'double', 'source': 'player_turn', 'dest': 'dealer_turn',
         'conditions': '_can_double', 'before': '_double_bet'},
        {'trigger': 'split', 'source': 'player_turn', 'dest': 'splitting',
         'conditions': '_can_split'},
        {'trigger': 'surrender', 'source': 'player_turn', 'dest': 'resolving',
         'conditions': '_can_surrender'},
        {'trigger': 'dealer_done', 'source': 'dealer_turn', 'dest': 'resolving'},
        {'trigger': 'payout_complete', 'source': 'resolving', 'dest': 'round_complete'},
        {'trigger': 'new_round', 'source': 'round_complete', 'dest': 'waiting_for_bet'},
    ]
    
    def __init__(self, 
                 rules: RuleSet,
                 counting_system: Optional[CountingSystem] = None):
        self.rules = rules
        self.shoe = Shoe(rules.num_decks)
        self.counting_system = counting_system
        self.strategy = BasicStrategy(rules)
        self.probability_engine = ProbabilityEngine(self.shoe, rules)
        self.kelly = KellyCalculator()
        
        # Game state
        self.player_hands: List[Hand] = []
        self.dealer_hand: Optional[Hand] = None
        self.current_hand_index: int = 0
        self.current_bet: float = 0
        self.bankroll: float = 10000  # Starting bankroll
        
        # Event subscribers
        self._event_handlers: List[Callable[[GameEvent], None]] = []
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='waiting_for_bet'
        )
    
    def subscribe(self, handler: Callable[[GameEvent], None]) -> None:
        """Subscribe to game events"""
        self._event_handlers.append(handler)
    
    def _emit(self, event_type: str, data: dict) -> None:
        """Emit event to all subscribers"""
        event = GameEvent(event_type, data)
        for handler in self._event_handlers:
            handler(event)
    
    def get_state_snapshot(self) -> dict:
        """Complete game state for API/UI"""
        return {
            'state': self.state,
            'player_hands': [h.to_dict() for h in self.player_hands],
            'dealer_hand': self.dealer_hand.to_dict() if self.dealer_hand else None,
            'dealer_showing': self.dealer_hand.cards[0].to_dict() if self.dealer_hand else None,
            'current_bet': self.current_bet,
            'bankroll': self.bankroll,
            'shoe': {
                'cards_remaining': self.shoe.cards_remaining,
                'decks_remaining': self.shoe.decks_remaining,
                'needs_shuffle': self.shoe.needs_shuffle,
            },
            'counting': self._get_counting_info(),
            'statistics': self._get_statistics(),
            'available_actions': self._get_available_actions(),
            'strategy_hint': self._get_strategy_hint(),
        }
    
    def _get_counting_info(self) -> Optional[dict]:
        """Count information (visibility controlled by training mode)"""
        if not self.counting_system:
            return None
        return {
            'system': self.counting_system.name,
            'running_count': self.counting_system.running_count,
            'true_count': self.counting_system.get_true_count(
                self.shoe.decks_remaining
            ),
            'cards_seen': self.counting_system.cards_seen,
        }
    
    def _get_statistics(self) -> dict:
        """Real-time statistics"""
        if not self.player_hands or not self.dealer_hand:
            return {}
        
        player_hand = self.player_hands[self.current_hand_index]
        dealer_upcard = self.dealer_hand.cards[0]
        
        return {
            'dealer_bust_probability': self.probability_engine.dealer_bust_probability(
                dealer_upcard
            ),
            'player_win_probability': self.probability_engine.player_win_probability(
                player_hand, dealer_upcard
            ),
            'current_house_edge': HouseEdgeCalculator().calculate(self.rules),
            'player_edge_with_count': self._calculate_player_edge(),
            'recommended_bet': self._get_recommended_bet(),
        }
```

## Training Mode Features

### Visibility Controls

```python
from enum import Enum

class VisibilityLevel(Enum):
    ALWAYS_VISIBLE = "always"      # Training wheels on
    ON_REQUEST = "on_request"      # Click to reveal
    END_OF_SHOE = "end_of_shoe"    # Verify after shoe complete
    HIDDEN = "hidden"              # Full stealth mode

@dataclass  
class TrainingConfig:
    """User's training preferences"""
    count_visibility: VisibilityLevel = VisibilityLevel.ALWAYS_VISIBLE
    true_count_visibility: VisibilityLevel = VisibilityLevel.ALWAYS_VISIBLE
    strategy_hints: VisibilityLevel = VisibilityLevel.ALWAYS_VISIBLE
    show_probabilities: bool = True
    show_ev_calculations: bool = True
    show_bet_recommendations: bool = True
    counting_system: str = "hilo"
    
    # Training drill modes
    drill_mode: Optional[str] = None  # "count_only", "strategy_only", "full_game"
```

### Training Drills

Implement these as separate game modes:

1. **Count Drill**: Flash cards, user enters running count
2. **True Count Drill**: Given RC and decks remaining, calculate TC
3. **Strategy Drill**: Present hand vs dealer, user picks action
4. **Deviation Drill**: Present situations where index plays apply
5. **Full Integration**: Complete game with configurable hints

### Progress Tracking

```python
@dataclass
class SessionStats:
    """Track user performance"""
    hands_played: int = 0
    correct_strategy_decisions: int = 0
    strategy_accuracy: float = 0.0
    count_checks: int = 0
    count_errors: int = 0
    count_accuracy: float = 0.0
    average_response_time_ms: float = 0.0
    
    # Benchmarks
    deck_countdown_time_seconds: Optional[float] = None
    consecutive_perfect_hands: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
```

## API Endpoints

### FastAPI Routes

```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Blackjack Trainer API")

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Game management
@app.post("/api/game/new")
async def create_game(config: GameConfig) -> GameResponse:
    """Create new game session"""
    ...

@app.post("/api/game/{session_id}/bet")
async def place_bet(session_id: str, bet: BetRequest) -> GameStateResponse:
    ...

@app.post("/api/game/{session_id}/action")
async def player_action(session_id: str, action: ActionRequest) -> GameStateResponse:
    """Hit, Stand, Double, Split, Surrender"""
    ...

@app.get("/api/game/{session_id}/state")
async def get_state(session_id: str) -> GameStateResponse:
    ...

@app.get("/api/game/{session_id}/count")
async def reveal_count(session_id: str) -> CountResponse:
    """Reveal count (for on-request visibility)"""
    ...

# Training endpoints
@app.post("/api/training/drill/{drill_type}")
async def start_drill(drill_type: str, config: DrillConfig) -> DrillResponse:
    ...

@app.get("/api/training/stats/{session_id}")
async def get_training_stats(session_id: str) -> SessionStats:
    ...

# Statistics/calculator endpoints
@app.post("/api/calculator/house-edge")
async def calculate_house_edge(rules: RuleSet) -> HouseEdgeResponse:
    ...

@app.post("/api/calculator/kelly")
async def calculate_kelly(request: KellyRequest) -> KellyResponse:
    ...

# WebSocket for real-time updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            result = await process_action(session_id, data)
            await manager.broadcast(session_id, result)
    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

## Testing Requirements

Write comprehensive tests for:

1. **Card/Shoe Tests**
   - Deck composition is correct
   - Shuffle produces valid random order
   - Penetration calculation is accurate
   - Deal properly moves cards to dealt pile

2. **Counting System Tests**
   - Each system sums to correct value for full deck
   - Hi-Lo: full deck = 0
   - KO: full deck = +4
   - True count calculation is correct
   - Reset properly initializes IRC for unbalanced systems

3. **Strategy Tests**
   - Verify against published basic strategy charts
   - Test all conditional action resolutions
   - Test rule variation impacts (H17 vs S17, DAS, etc.)
   - Deviation triggers at correct indices

4. **Statistics Tests**
   - House edge calculation matches known values
   - Kelly calculations are mathematically correct
   - Probability calculations sum to 1.0

5. **Game State Tests**
   - State machine transitions correctly
   - Cannot take invalid actions in each state
   - Blackjack detection works
   - Split handling is correct
   - Payouts are accurate

## Development Phases

### Phase 1: Core Engine (Week 1)
- [ ] Card, Deck, Shoe classes with tests
- [ ] Hand evaluation with soft/hard detection
- [ ] All four counting systems with tests
- [ ] Basic strategy matrices
- [ ] House edge calculator

### Phase 2: Game Logic (Week 2)
- [ ] State machine implementation
- [ ] Full game flow (bet → deal → play → resolve)
- [ ] Split handling
- [ ] Probability engine basics
- [ ] Kelly calculator

### Phase 3: API Layer (Week 3)
- [ ] FastAPI endpoints
- [ ] WebSocket real-time updates
- [ ] Session management
- [ ] Pydantic schemas

### Phase 4: Frontend (Week 4)
- [ ] Basic HTML/CSS card display
- [ ] Game controls
- [ ] Count/stats display panels
- [ ] Visibility toggle controls

### Phase 5: Training Features (Week 5)
- [ ] Training drills
- [ ] Progress tracking
- [ ] Strategy hints system
- [ ] Deviation training

### Phase 6: Polish (Week 6)
- [ ] Statistics dashboard
- [ ] Session history
- [ ] Performance optimization
- [ ] Documentation

## Key Implementation Notes

1. **Keep core/ completely UI-agnostic** - No imports from api/, no print statements, no input(). All communication through return values and event subscriptions.

2. **Use immutable dataclasses** for Card, make Hand mutations explicit methods that return new Hand instances when practical.

3. **Pre-compute strategy tables** - Don't calculate basic strategy on the fly. Load complete matrices at initialization.

4. **Event-driven architecture** - The game engine emits events (card_dealt, hand_resolved, count_updated). Any UI subscribes to relevant events.

5. **Floating point caution** - Use Decimal for money calculations. Wong Halves uses 0.5 increments, so floats are fine for counts but consider implications.

6. **Testing is critical** - The counting math and strategy must be provably correct. Write tests first for core calculations.

## Getting Started

```bash
# Create project
mkdir blackjack_trainer && cd blackjack_trainer

# Set up environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn redis pydantic transitions pytest hypothesis

# Create directory structure
mkdir -p core/{counting,strategy,statistics,game} api/routes frontend/{css,js} tests/{core,api}

# Start with core/cards.py - build up from there
```

Now build this thing. Start with `core/cards.py` and work your way up through the architecture. Test each module before moving to the next. The statistical engine is the foundation—get that rock solid before worrying about the UI.
