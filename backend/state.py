"""
state.py — Pure data. No logic.

Dataclasses for AgentState, HunterState, VehicleState, and GameState.
Enums for status effects and turn phase.

Ground truth lives in GameState. Role-filtered views are produced elsewhere
(main.py / WebSocket layer); this file has no concept of what each client
is allowed to see.

Assumptions / open questions noted inline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StatusEffect(Enum):
    STUNNED     = auto()   # cannot attack or use abilities; movement capped at 2
    FATIGUED    = auto()   # abilities disabled; clears when ≤2 spaces moved
    FLASHBANGED = auto()   # vision disabled; clears at start of that hunter's turn


class TurnPhase(Enum):
    SETUP            = auto()
    AGENT_TURN       = auto()
    HUNTER_NEGOTIATE = auto()  # hunters agree on order
    HUNTER_TURN      = auto()
    GAME_OVER        = auto()


class WinCondition(Enum):
    NONE            = auto()
    AGENT_ESCAPE    = auto()
    HUNTERS_KILL    = auto()    # agent health ≤ 0
    HUNTERS_TIMEOUT = auto()    # round > 40, agent not escaped


# ---------------------------------------------------------------------------
# Item state
# ---------------------------------------------------------------------------

@dataclass
class ItemState:
    key: str          # matches resources.json key, e.g. "flash_bang"
    name: str
    charges: int      # remaining uses
    tapped: bool = False  # tapped items are exhausted until refreshed


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    character: str          # e.g. "blue_jay" — hidden from hunters until first sighting
    position: str           # current cell, e.g. "N1"
    health: int             # 4 (2–3p / 5p) or 6 (4p)
    max_health: int
    move_speed: int         # from resources.json; always 4 for all current characters
    items: list[ItemState]  # filtered by character availability at setup

    # Visibility / identity
    identity_revealed: bool = False  # True after first confirmed hunter sighting

    # Objectives: 4 total; each is a cell string
    # pending = completed this turn, not yet public; public_complete = published
    pending_objectives: list[str] = field(default_factory=list)
    public_objectives: list[str] = field(default_factory=list)

    # Movement tracking
    path_this_turn: list[str] = field(default_factory=list)  # includes backtracks

    # Last-seen token: cell where agent was last seen, or None
    last_seen_cell: Optional[str] = None

    # Status effects
    status_effects: set[StatusEffect] = field(default_factory=set)

    # Traitor stub (deferred per claude.md)
    is_traitor: bool = False

    @property
    def completed_objectives_count(self) -> int:
        return len(self.public_objectives) + len(self.pending_objectives)


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------

@dataclass
class HunterState:
    character: str      # e.g. "beast"
    player_name: str    # human-readable player identifier
    position: str       # current cell

    move_speed: int     # from resources.json

    # True while hunter has not yet exited the vehicle onto the board.
    # Distinct from VehicleState.occupied_by, which names the current driver.
    in_vehicle: bool = False

    # Movement tracking this turn
    path_this_turn: list[str] = field(default_factory=list)
    moved_this_turn: bool = False  # True once submit_hunter_move is accepted

    # Status effects (set of StatusEffect)
    status_effects: set[StatusEffect] = field(default_factory=set)

    abilities: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

@dataclass
class VehicleState:
    name: str           # e.g. "tracer"
    position: str       # current cell
    move_speed: int     # total budget per round
    move_budget_remaining: int  # decremented as hunters spend it

    # player_name of the hunter currently driving, or None.
    # Distinct from HunterState.in_vehicle, which marks hunters not yet deployed.
    occupied_by: Optional[str] = None

    # Full path driven this round — published to all clients
    # Used by run-over rule: agent checks own position against every cell
    path_this_round: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# GameState — ground truth
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    # Identity
    board_name: str         # "Shadow of Babel" | "Broken Covenant" | "Arctic Archives"
    player_count: int       # 2–5

    # Sub-states
    agent: AgentState
    hunters: list[HunterState]
    vehicle: VehicleState

    # Board objectives (4 cells chosen at setup)
    objectives: list[str]           # cell strings, order matches agent's objective lists
    objectives_visible: bool        # True for 2–3p; False for 4–5p

    # Escape points (base + extras for 4–5p)
    escape_points: list[str]

    # Turn tracking
    round_number: int = 1           # 1–40
    phase: TurnPhase = TurnPhase.SETUP
    active_hunter_index: int = 0    # index into hunter_order
    hunter_order: list[str] = field(default_factory=list)  # player_names in agreed order

    # Win state
    win_condition: WinCondition = WinCondition.NONE
    agent_escaped: bool = False  # set by agent when ending turn on a valid escape point

    # Transient obstacles for LOS (e.g. active smoke grenade cells)
    # Each entry is a cell string; cleared per game-loop rules
    active_obstacles: list[str] = field(default_factory=list)

    # Active barriers (Arctic Archives only; mutable during play)
    active_barriers: list[str] = field(default_factory=list)

    # Hunter turn-order negotiation: player_name → proposed order
    # Cleared once consensus is reached or on each new HUNTER_NEGOTIATE phase
    hunter_order_proposals: dict = field(default_factory=dict)
    order_mismatch: bool = False  # True when all proposals came in but disagreed

    @property
    def is_over(self) -> bool:
        return self.win_condition != WinCondition.NONE

    @property
    def current_hunter(self) -> Optional[HunterState]:
        """The hunter whose turn it currently is, or None."""
        if self.phase != TurnPhase.HUNTER_TURN:
            return None
        if not self.hunter_order:
            return None
        if self.active_hunter_index >= len(self.hunter_order):
            return None
        name = self.hunter_order[self.active_hunter_index]
        return next((h for h in self.hunters if h.player_name == name), None)