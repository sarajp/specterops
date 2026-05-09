"""
loop.py — Turn orchestration. No I/O, no WebSocket.

Sits between engine.py (pure logic) and main.py (WebSocket layer).
Each function advances one discrete phase of the game loop and returns
a WinCondition so the caller can short-circuit on a terminal result.

All functions raise ValueError for illegal calls (e.g. wrong phase,
unknown player name). They do not raise on a game that is already over —
callers should check game.is_over before dispatching.

Turn order (claude.md §Game Loop):

  Agent turn
  ──────────
  start_agent_turn()       phase: any → AGENT_TURN
    - check_timeout (round > 40)
    - publish pending objectives
    - clear agent flashbang
    - clear smoke obstacles
    - reset agent path

  end_agent_turn()         phase: AGENT_TURN → HUNTER_NEGOTIATE
    - evaluate agent_escaped flag → check_win
    - advance phase

  Hunter turns
  ────────────
  set_hunter_order()       phase: HUNTER_NEGOTIATE → HUNTER_TURN
    - validate and store agreed order

  start_hunter_turn()      phase: HUNTER_TURN (index unchanged)
    - clear active hunter's flashbang

  end_hunter_turn()        phase: HUNTER_TURN → HUNTER_TURN | AGENT_TURN
    - run LOS for active hunter
    - set agent_escaped flag if conditions met (hunter LOS does not block escape;
      escape is evaluated on the agent's previously confirmed end position)
    - check agent visible → reveal identity on first sighting
    - clear status effects per rules
    - check_win
    - advance to next hunter, or call end_round() if last hunter

  end_round()              called internally by end_hunter_turn
    - increment round_number
    - reset vehicle budget and path
    - reset all hunter paths
    - advance phase to AGENT_TURN

  Helpers
  ───────
  is_agent_visible_to()    thin LOS wrapper respecting flashbang and in_vehicle

Assumptions:
  - Combat (resolve_combat) is called by the WebSocket layer between
    start_hunter_turn and end_hunter_turn, after LOS is confirmed visible.
    loop does not call resolve_combat directly.
  - Item use is deferred; loop has no item logic.
  - Barrier terminal interactions (Arctic Archives) are deferred.
  - Supply cache interactions are deferred.
"""

from backend.board import BoardData, has_los
from backend.engine import check_win, check_timeout, publish_pending_objectives
from backend.state import (
    GameState,
    HunterState,
    StatusEffect,
    TurnPhase,
    WinCondition,
)


# ---------------------------------------------------------------------------
# Agent turn
# ---------------------------------------------------------------------------

def start_agent_turn(game: GameState, board: BoardData) -> WinCondition:
    """
    Begin the agent's turn.

    Steps:
      1. check_timeout — hunters win immediately if round_number > 40.
      2. publish_pending_objectives — pending → public.
      3. Clear agent's FLASHBANGED effect if present.
      4. Clear active_obstacles (smoke grenade expires at start of agent turn).
      5. Reset agent.path_this_turn.

    Returns the WinCondition. If HUNTERS_TIMEOUT, caller should not proceed.
    """
    result = check_timeout(game)
    if result != WinCondition.NONE:
        return result

    publish_pending_objectives(game)

    game.agent.status_effects.discard(StatusEffect.FLASHBANGED)
    game.active_obstacles.clear()
    game.agent.path_this_turn = []

    game.phase = TurnPhase.AGENT_TURN
    return WinCondition.NONE


def end_agent_turn(game: GameState, board: BoardData) -> WinCondition:
    """
    End the agent's turn.

    Evaluates the agent_escaped flag: set it here if the agent is currently
    on an escape point with 3+ public objectives and no on-board hunter
    blocking that cell.

    Then calls check_win and advances phase to HUNTER_NEGOTIATE.

    Raises ValueError if not in AGENT_TURN phase.
    """
    if game.phase != TurnPhase.AGENT_TURN:
        raise ValueError(
            f"end_agent_turn called in wrong phase: {game.phase}"
        )

    _evaluate_escape(game)
    result = check_win(game)
    if result != WinCondition.NONE:
        return result

    game.phase = TurnPhase.HUNTER_NEGOTIATE
    game.hunter_order_proposals = {}
    game.order_mismatch = False
    return WinCondition.NONE


def _evaluate_escape(game: GameState) -> None:
    """
    Set game.agent_escaped if the agent is on a valid escape point.

    Conditions (claude.md):
      - 3+ public objectives completed
      - agent on an escape point
      - no on-board hunter on that escape point
    """
    agent = game.agent
    if len(agent.public_objectives) < 3:
        return
    if agent.position not in game.escape_points:
        return
    hunter_positions = {h.position for h in game.hunters if not h.in_vehicle}
    if agent.position not in hunter_positions:
        game.agent_escaped = True


# ---------------------------------------------------------------------------
# Hunter turns
# ---------------------------------------------------------------------------

def submit_hunter_order_proposal(game: GameState, player_name: str, order: list[str]) -> None:
    """
    Record one hunter's proposed turn order.

    Advances to HUNTER_TURN (via set_hunter_order) when every hunter has
    submitted a proposal and all proposals match.

    Raises ValueError if phase is wrong, the player is not a hunter, or the
    order list is invalid.
    """
    if game.phase != TurnPhase.HUNTER_NEGOTIATE:
        raise ValueError(f"submit_hunter_order_proposal called in wrong phase: {game.phase}")

    known = {h.player_name for h in game.hunters}
    if player_name not in known:
        raise ValueError(f"{player_name!r} is not a hunter in this game")

    if len(order) != len(set(order)):
        raise ValueError("Duplicate player names in order")
    if set(order) != known:
        raise ValueError("Order must contain exactly all hunter player names")

    game.order_mismatch = False
    game.hunter_order_proposals[player_name] = list(order)

    if len(game.hunter_order_proposals) == len(game.hunters):
        proposals = list(game.hunter_order_proposals.values())
        if all(p == proposals[0] for p in proposals):
            set_hunter_order(game, proposals[0])
            game.hunter_order_proposals = {}
        else:
            game.hunter_order_proposals = {}
            game.order_mismatch = True


def retract_hunter_order_proposal(game: GameState, player_name: str) -> None:
    """Remove a hunter's proposal, allowing them to re-order and re-confirm."""
    if game.phase != TurnPhase.HUNTER_NEGOTIATE:
        raise ValueError(f"retract_hunter_order_proposal called in wrong phase: {game.phase}")
    game.hunter_order_proposals.pop(player_name, None)


def set_hunter_order(game: GameState, order: list[str]) -> None:
    """
    Record the agreed hunter turn order for this round.

    order: list of player_names in the order hunters will take their turns.
    Must contain exactly the player_name of every hunter, no duplicates.

    Advances phase from HUNTER_NEGOTIATE to HUNTER_TURN.

    Raises ValueError if phase is wrong, names are missing, unknown, or duplicated.
    """
    if game.phase != TurnPhase.HUNTER_NEGOTIATE:
        raise ValueError(
            f"set_hunter_order called in wrong phase: {game.phase}"
        )

    if len(order) != len(set(order)):
        raise ValueError("Duplicate player names in order")

    known = {h.player_name for h in game.hunters}
    provided = set(order)

    unknown = provided - known
    if unknown:
        raise ValueError(f"Unknown player names in order: {unknown}")

    missing = known - provided
    if missing:
        raise ValueError(f"Missing player names in order: {missing}")

    game.hunter_order = list(order)
    game.active_hunter_index = 0
    game.phase = TurnPhase.HUNTER_TURN


def start_hunter_turn(game: GameState) -> None:
    """
    Begin the active hunter's turn.

    Clears the active hunter's FLASHBANGED effect (per claude.md: clears at
    start of that hunter's own turn).
    Resets the hunter's path_this_turn.

    Raises ValueError if not in HUNTER_TURN phase.
    """
    if game.phase != TurnPhase.HUNTER_TURN:
        raise ValueError(
            f"start_hunter_turn called in wrong phase: {game.phase}"
        )

    hunter = game.current_hunter
    if hunter is None:
        raise ValueError("No active hunter")

    hunter.status_effects.discard(StatusEffect.FLASHBANGED)
    hunter.path_this_turn = []
    hunter.moved_this_turn = False


def end_hunter_turn(game: GameState, board: BoardData) -> WinCondition:
    """
    End the active hunter's turn.

    Steps:
      1. Run LOS for this hunter against agent's current position.
         - If visible and identity not yet revealed: reveal it.
      2. Clear status effects per rules:
         - STUNNED clears unconditionally.
         - FATIGUED clears if hunter moved ≤ 2 spaces this turn.
         - FLASHBANGED was already cleared at turn start; should not be present.
      3. check_win.
      4. Advance to next hunter, or call end_round() if this was the last.

    Combat (resolve_combat) is called by the WebSocket layer before this,
    after LOS is confirmed. loop does not call it directly.

    Returns WinCondition. Advances phase/index as a side effect.

    Raises ValueError if not in HUNTER_TURN phase.
    """
    if game.phase != TurnPhase.HUNTER_TURN:
        raise ValueError(
            f"end_hunter_turn called in wrong phase: {game.phase}"
        )

    hunter = game.current_hunter
    if hunter is None:
        raise ValueError("No active hunter")

    # LOS check
    if is_agent_visible_to(hunter, game, board):
        if not game.agent.identity_revealed:
            game.agent.identity_revealed = True

    # Clear status effects
    hunter.status_effects.discard(StatusEffect.STUNNED)

    steps = len(hunter.path_this_turn) - 1 if hunter.path_this_turn else 0
    if steps <= 2:
        hunter.status_effects.discard(StatusEffect.FATIGUED)

    # Win check
    result = check_win(game)
    if result != WinCondition.NONE:
        return result

    # Advance turn
    if game.active_hunter_index >= len(game.hunter_order) - 1:
        end_round(game)
    else:
        game.active_hunter_index += 1

    return WinCondition.NONE


def end_round(game: GameState) -> None:
    """
    Close the current round and prepare for the next agent turn.

    Steps:
      - Increment round_number.
      - Reset vehicle move budget and clear path_this_round.
      - Reset all hunter path_this_turn lists.
      - Advance phase to AGENT_TURN.

    Called internally by end_hunter_turn after the last hunter's turn.
    """
    game.round_number += 1
    game.vehicle.move_budget_remaining = game.vehicle.move_speed
    game.vehicle.path_this_round = []

    for hunter in game.hunters:
        hunter.path_this_turn = []

    game.phase = TurnPhase.AGENT_TURN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_agent_visible_to(
    hunter: HunterState,
    game: GameState,
    board: BoardData,
) -> bool:
    """
    True if the hunter has LOS to the agent's current position.

    Returns False immediately if:
      - hunter is in the vehicle (cannot see from vehicle)
      - hunter has FLASHBANGED status
      - no clear LOS per board blockers + active obstacles

    Note: this checks current state only. Last-seen token placement uses
    the full path scan in compute_last_seen (engine.py).
    """
    if StatusEffect.FLASHBANGED in hunter.status_effects:
        return False

    pos = game.vehicle.position if hunter.in_vehicle else hunter.position
    blockers = board.get_blockers(game.active_obstacles)
    return has_los(pos, game.agent.position, blockers)