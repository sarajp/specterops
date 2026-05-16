"""
engine.py — Core game logic. No I/O, no persistence, no WebSocket.

Functions:
  setup_game()                Build initial GameState from config
  get_legal_moves()           Valid next steps from a given cell
  apply_move()                Execute confirmed agent path step-by-step
  publish_pending_objectives() Flush pending→public at turn start
  compute_last_seen()         Determine last-seen token after agent turn
  resolve_combat()            Roll combat for a hunter attacking the agent
  apply_vehicle_move()        Move vehicle, apply run-over damage
  check_win()                 Kill/escape win conditions (called after every turn)
  check_timeout()             Timeout check; called only at start of agent turn when round > 40
  roll_d6()                   Exploding d6

Agent movement flow:
  1. Agent client calls get_legal_moves(game, board, from_cell) repeatedly
     as it builds a proposed path (pass the last cell of the proposed path
     as from_cell to get valid continuations).
  2. Agent confirms the full path.
  3. Game loop calls apply_move(game, board, path), which validates and
     executes each step, calls _mark_objectives_pending() per step, then
     compute_last_seen() once at end.

Assumptions:
  - All hunters start in the vehicle (in_vehicle=True).
  - A hunter is either in_vehicle=True (position field not meaningful for
    movement/LOS) or on the board. Callers must check in_vehicle.
  - Items and abilities deferred per claude.md §Deferred.
  - Supply caches and barrier terminals stubbed.
  - Hunter order negotiation handled by loop.py.
"""

import json
import random
from pathlib import Path
from typing import Optional

from backend.board import (
    BoardData,
    load_board,
    has_los,
    neighbors,
    adjacent,
    cell_col,
    cell_row,
    chebyshev_distance,
)
from backend.state import (
    AgentState,
    HunterState,
    VehicleState,
    GameState,
    ItemState,
    StatusEffect,
    TurnPhase,
    WinCondition,
)

# ---------------------------------------------------------------------------
# Dice
# ---------------------------------------------------------------------------

def roll_d6() -> int:
    """Exploding d6: roll of 6 rerolls and adds (repeatable)."""
    total = 0
    while True:
        result = random.randint(1, 6)
        total += result
        if result != 6:
            break
    return total


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_BASE_ESCAPE_POINTS = {
    "Shadow of Babel": ["A3", "N1", "W3"],
    "Broken Covenant": ["A3", "M1", "W1"],
    "Arctic Archives": ["A3", "M1", "W1"],
}

_EXTRA_ESCAPE_POINTS = ["A6", "W6"]  # 4p and 5p

_AGENT_START = {
    "Shadow of Babel": "N1",
    "Broken Covenant": "M1",
    "Arctic Archives": "M1",
}

_VEHICLE_START = {
    "small": "K17",            # 2–3p
    "Shadow of Babel": "K23",  # 4–5p
    "Broken Covenant": "K24",
    "Arctic Archives": "K25",
}


def setup_game(
    board_name: str,
    agent_player: str,
    agent_character: str,
    hunter_players: list[str],
    hunter_characters: list[str],
    agent_items: list[str],
    resources_path: Optional[Path] = None,
) -> tuple[GameState, BoardData]:
    """
    Build the initial GameState and BoardData from setup parameters.

    agent_items: item keys from resources.json, already validated against
                 character availability by the caller.

    All hunters start in the vehicle (in_vehicle=True). Their position field
    is set to the vehicle start cell for reference but is not authoritative
    while in_vehicle is True.

    Returns (game_state, board_data). BoardData is separate so it is available
    for LOS queries without embedding it in GameState.

    Raises ValueError for invalid configurations.
    """
    player_count = 1 + len(hunter_players)
    if player_count < 2 or player_count > 5:
        raise ValueError(f"Player count must be 2–5, got {player_count}")
    if len(hunter_players) != len(hunter_characters):
        raise ValueError("hunter_players and hunter_characters must be same length")

    if resources_path is None:
        resources_path = Path(__file__).parent / "data" / "resources.json"
    with open(resources_path, encoding="utf-8-sig") as f:
        resources = json.load(f)["resources"]

    board = load_board(board_name, resources_path)

    if player_count <= 3:
        agent_hp = 4
        max_equipment = 3
        objectives_visible = True
        vehicle_start = _VEHICLE_START["small"]
        escape_points = list(_BASE_ESCAPE_POINTS[board_name])
    elif player_count == 4:
        agent_hp = 6
        max_equipment = 5
        objectives_visible = False
        vehicle_start = _VEHICLE_START[board_name]
        escape_points = list(_BASE_ESCAPE_POINTS[board_name]) + _EXTRA_ESCAPE_POINTS
    else:  # 5p
        agent_hp = 4
        max_equipment = 3
        objectives_visible = False
        vehicle_start = _VEHICLE_START[board_name]
        escape_points = list(_BASE_ESCAPE_POINTS[board_name]) + _EXTRA_ESCAPE_POINTS

    if len(agent_items) > max_equipment:
        raise ValueError(
            f"Agent has {len(agent_items)} items but max for {player_count}p is {max_equipment}"
        )

    objectives = _select_objectives(board)

    item_states = [_make_item(key, resources["items"]) for key in agent_items]
    agent = AgentState(
        character=agent_character,
        position=_AGENT_START[board_name],
        health=agent_hp,
        max_health=agent_hp,
        move_speed=4,
        items=item_states,
        abilities=resources["agents"][agent_character]["abilities"],
    )
    # Toughness (Orangutan): +2 HP
    if agent_character == "orangutan":
        agent.health += 2
        agent.max_health += 2

    hunters = []
    for player_name, character in zip(hunter_players, hunter_characters):
        hunters.append(HunterState(
            character=character,
            player_name=player_name,
            position=vehicle_start,
            move_speed=4,
            in_vehicle=True,
            abilities=resources["hunters"][character]["abilities"],
        ))

    vehicle = VehicleState(
        name="tracer",
        position=vehicle_start,
        move_speed=10,
        move_budget_remaining=10,
    )

    game = GameState(
        board_name=board_name,
        player_count=player_count,
        agent=agent,
        hunters=hunters,
        vehicle=vehicle,
        objectives=objectives,
        objectives_visible=objectives_visible,
        escape_points=escape_points,
        round_number=1,
        phase=TurnPhase.AGENT_TURN,
    )

    return game, board


def _select_objectives(board: BoardData) -> list[str]:
    objectives = []
    for i in range(1, 5):
        candidates = board.potential_objectives[str(i)]
        objectives.append(random.choice(candidates))
    return objectives


def _make_item(key: str, items_data: dict) -> ItemState:
    raw = items_data[key]
    return ItemState(key=key, name=raw["name"], charges=int(raw["charges"]))


# ---------------------------------------------------------------------------
# Agent movement
# ---------------------------------------------------------------------------

def get_legal_moves(
    game: GameState,
    board: BoardData,
    from_cell: Optional[str] = None,
) -> list[str]:
    """
    Valid next-step cells from from_cell (defaults to agent's current position).

    Call with the last cell of the proposed path to get valid continuations.
    Remaining budget is derived from agent.path_this_turn.

    Rules enforced:
      - Must be a valid, passable cell (not wall or active barrier)
      - Not occupied by a hunter on the board (in_vehicle hunters excluded)
      - Not the vehicle space
      - Within remaining move budget

    Returns empty list if budget is exhausted.
    """
    agent = game.agent

    steps_used = len(agent.path_this_turn) - 1 if agent.path_this_turn else 0
    if steps_used >= agent.move_speed:
        return []

    current = from_cell if from_cell is not None else agent.position
    hunter_positions = {h.position for h in game.hunters if not h.in_vehicle}

    legal = []
    for candidate in neighbors(current):
        if not board.is_passable(candidate):
            continue
        if candidate in hunter_positions:
            continue
        if candidate == game.vehicle.position:
            continue
        legal.append(candidate)

    return legal


def apply_move(game: GameState, board: BoardData, path: list[str]) -> list[dict]:
    """
    Execute a confirmed agent path step by step.

    path: full cell sequence including the starting cell, e.g.
          ["M1", "M2", "M3"]. Must start at agent.position.

    For each step after the start:
      1. Validates adjacency, passability, hunter occupancy, vehicle, budget.
      2. Advances agent.position and appends to agent.path_this_turn.
      3. Calls _mark_objectives_pending() for newly adjacent objectives.
      4. Checks Quick Draw (Gun hunter passive): sets quick_draw_triggered_this_turn.

    After all steps, calls compute_last_seen() or uses holo_decoy_cell override.
    If Mantis and a last-seen marker is placed adjacent to a hunter, Blade Strike
    auto-fires (roll d6, 3+ stuns, max 1 hunter per turn).

    If pulse_blades is armed and a last-seen marker is placed, stuns all adjacent
    hunters and consumes a charge.

    Returns a list of passive trigger events for the WebSocket layer to broadcast.

    Caller is responsible for check_win() after this returns.

    Raises ValueError if:
      - path is empty
      - path does not start at agent.position
      - any step is non-adjacent, impassable, hunter-occupied, vehicle, or over budget
    """
    agent = game.agent
    events: list[dict] = []

    if not path:
        raise ValueError("Path must not be empty")
    if path[0] != agent.position:
        raise ValueError(
            f"Path must start at agent position {agent.position!r}, got {path[0]!r}"
        )

    if not agent.path_this_turn:
        agent.path_this_turn.append(path[0])

    hunter_positions = {h.position for h in game.hunters if not h.in_vehicle}
    blockers = board.get_blockers(game.active_obstacles)

    # Gun hunters eligible for Quick Draw (not flashbanged, on board)
    gun_hunters = [
        h for h in game.hunters
        if h.character == "gun" and not h.in_vehicle
        and StatusEffect.FLASHBANGED not in h.status_effects
    ]

    for i, destination in enumerate(path[1:], start=1):
        steps_used = len(agent.path_this_turn) - 1
        if steps_used >= agent.move_speed:
            raise ValueError(
                f"Step {i}: move budget exhausted ({steps_used}/{agent.move_speed})"
            )

        prev = agent.path_this_turn[-1]

        if chebyshev_distance(prev, destination) != 1:
            raise ValueError(
                f"Step {i}: {destination!r} is not adjacent to {prev!r}"
            )
        if not board.is_passable(destination):
            raise ValueError(f"Step {i}: {destination!r} is not passable")
        if destination in hunter_positions:
            raise ValueError(f"Step {i}: {destination!r} is occupied by a hunter")
        if destination == game.vehicle.position:
            raise ValueError(f"Step {i}: {destination!r} is the vehicle space")

        agent.position = destination
        agent.path_this_turn.append(destination)
        _mark_objectives_pending(game)

        # Quick Draw: flag on first step where any Gun hunter has LOS
        if not agent.quick_draw_triggered_this_turn:
            for gh in gun_hunters:
                if has_los(gh.position, agent.position, blockers):
                    agent.quick_draw_triggered_this_turn = True
                    break

    # Determine last-seen cell (holo decoy overrides normal computation)
    if agent.holo_decoy_cell is not None:
        agent.last_seen_cell = agent.holo_decoy_cell
        agent.identity_revealed = True
        agent.holo_decoy_cell = None
    else:
        agent.last_seen_cell = compute_last_seen(game, board)
        if agent.last_seen_cell is not None:
            agent.identity_revealed = True

    last_seen = agent.last_seen_cell

    # Mantis Blade Strike: auto-fires when last-seen placed adjacent to a hunter
    if agent.character == "mantis" and last_seen and not agent.blade_strike_used_this_turn:
        for h in game.hunters:
            if h.in_vehicle:
                continue
            if adjacent(last_seen, h.position):
                roll = random.randint(1, 6)
                stunned = roll >= 3
                if stunned:
                    h.status_effects.add(StatusEffect.STUNNED)
                agent.blade_strike_used_this_turn = True
                events.append({
                    "type": "blade_strike",
                    "target": h.player_name,
                    "roll": roll,
                    "stunned": stunned,
                })
                break

    # Pulse Blades: if armed and last-seen placed, stun adjacent hunters and consume charge
    if agent.pulse_blades_armed and last_seen:
        pb_item = next((i for i in agent.items if i.key == "pulse_blades"), None)
        if pb_item and pb_item.charges > 0:
            stunned_by_pb = []
            for h in game.hunters:
                if h.in_vehicle:
                    continue
                if adjacent(last_seen, h.position):
                    h.status_effects.add(StatusEffect.STUNNED)
                    stunned_by_pb.append(h.player_name)
            pb_item.charges -= 1
            events.append({"type": "pulse_blades", "stunned": stunned_by_pb})
        agent.pulse_blades_armed = False

    return events


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------

def publish_pending_objectives(game: GameState) -> None:
    """
    Flush pending objectives to public. Call once at the start of the agent's
    turn, before movement.

    If remote_trigger_active is set, skips publication this turn and clears
    the flag so it publishes normally next turn.
    """
    agent = game.agent
    if agent.remote_trigger_active:
        agent.remote_trigger_active = False
        return
    for cell in list(agent.pending_objectives):
        if cell not in agent.public_objectives:
            agent.public_objectives.append(cell)
        agent.pending_objectives.remove(cell)


def _mark_objectives_pending(game: GameState) -> None:
    """
    Mark objectives adjacent to agent's current position as pending.
    Internal; called per step inside apply_move.
    Frequency Hack (Blue Jay): objectives within 2 spaces complete instead of 1.
    """
    agent = game.agent
    incomplete = [
        obj for obj in game.objectives
        if obj not in agent.public_objectives and obj not in agent.pending_objectives
    ]
    freq_hack = agent.character == "blue_jay"
    for obj in incomplete:
        if freq_hack:
            if chebyshev_distance(agent.position, obj) <= 2:
                agent.pending_objectives.append(obj)
        elif adjacent(agent.position, obj) or agent.position == obj:
            agent.pending_objectives.append(obj)


# ---------------------------------------------------------------------------
# Last-seen token
# ---------------------------------------------------------------------------

def compute_last_seen(game: GameState, board: BoardData) -> Optional[str]:
    """
    Determine last-seen token placement after agent.path_this_turn is complete.

    Scans path backward. For each cell, checks whether any non-flashbanged,
    on-board hunter had LOS to it (using current blockers).

    Returns:
      None  — agent ends inside LOS (caller places visible marker), or
              agent was never in any hunter's LOS this turn.
      cell  — last path cell where agent was in LOS, when agent ends outside LOS.

    Blocker set uses current state. Per-step obstacle snapshots are deferred.
    """
    agent = game.agent
    blockers = board.get_blockers(game.active_obstacles)

    hunter_positions = []
    for h in game.hunters:
        if StatusEffect.FLASHBANGED in h.status_effects:
            continue
        hunter_positions.append(game.vehicle.position if h.in_vehicle else h.position)

    if not hunter_positions:
        return None

    def in_any_los(cell: str) -> bool:
        return any(has_los(h_pos, cell, blockers) for h_pos in hunter_positions)

    if in_any_los(agent.position):
        return None

    path = agent.path_this_turn or [agent.position]
    for cell in reversed(path):
        if in_any_los(cell):
            return cell

    return None


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

def resolve_combat(
    hunter: HunterState,
    agent: AgentState,
    distance: int,
    forced_roll: Optional[int] = None,
) -> tuple[bool, int]:
    """
    Resolve one attack by a hunter against the agent.

    Returns (hit: bool, roll: int).

    Rules:
      - distance 0: automatic hit
      - roll 1: automatic miss
      - roll 6: explodes (handled by roll_d6)
      - hit if roll >= distance

    Passive modifiers applied by character:
      Sharp Shooting (gun):   roll 2 dice, take higher
      Mind-Reading (prophet): +2 to effective roll (roll of 1 still misses)
      Evasion (spider agent): -2 when hunter is within 3 of agent
      Brutal Strength (beast): on same-space hit, bonus d6 roll of 5+ deals 2 damage
      Judgement (judge):      on hit, agent becomes FATIGUED

    forced_roll: inject a specific result for testing.
    Caller must confirm agent is visible, hunter is on the board, and not stunned.
    """
    if StatusEffect.STUNNED in hunter.status_effects:
        raise ValueError(f"Hunter {hunter.player_name} is stunned and cannot attack")
    if hunter.in_vehicle:
        raise ValueError(f"Hunter {hunter.player_name} is in the vehicle and cannot attack")

    is_brutal_strength = hunter.character == "beast"
    is_judgement = hunter.character == "judge"

    if distance == 0:
        agent.health -= 1
        if is_brutal_strength:
            if random.randint(1, 6) >= 5:
                agent.health -= 1
        if is_judgement:
            agent.status_effects.add(StatusEffect.FATIGUED)
        return True, 0

    # Roll — Sharp Shooting takes the higher of two dice
    if hunter.character == "gun":
        roll1 = forced_roll if forced_roll is not None else roll_d6()
        roll2 = roll_d6()
        roll = max(roll1, roll2)
    else:
        roll = forced_roll if forced_roll is not None else roll_d6()

    if roll == 1:
        return False, roll

    effective_roll = roll
    if hunter.character == "prophet":
        effective_roll += 2
    if agent.character == "spider" and distance <= 3:
        effective_roll -= 2

    hit = effective_roll >= distance
    if hit:
        agent.health -= 1
        if is_judgement:
            agent.status_effects.add(StatusEffect.FATIGUED)

    return hit, roll


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def apply_effect(game: GameState, effect_type: str, params: dict) -> None:
    """
    Apply a single atomic effect to game state.

    Called by apply_item() and apply_ability(). Callers are responsible for
    validating preconditions before calling.

    Supported effect_types:
      STUN            params: player_name
      FLASHBANG       params: player_name
      FATIGUE         params: player_name
      RESTORE_HEALTH  params: amount (default 1)
      GRANT_MOVEMENT  params: move_speed
    """
    if effect_type == "STUN":
        hunter = _get_hunter(game, params["player_name"])
        hunter.status_effects.add(StatusEffect.STUNNED)
    elif effect_type == "FLASHBANG":
        hunter = _get_hunter(game, params["player_name"])
        hunter.status_effects.add(StatusEffect.FLASHBANGED)
    elif effect_type == "FATIGUE":
        hunter = _get_hunter(game, params["player_name"])
        hunter.status_effects.add(StatusEffect.FATIGUED)
    elif effect_type == "RESTORE_HEALTH":
        amount = params.get("amount", 1)
        game.agent.health = min(game.agent.health + amount, game.agent.max_health)
    elif effect_type == "GRANT_MOVEMENT":
        game.agent.move_speed = params["move_speed"]
        game.agent.movement_boosted_by_item = True
    else:
        raise ValueError(f"Unknown effect type: {effect_type!r}")


def _get_hunter(game: GameState, player_name: str) -> HunterState:
    hunter = next((h for h in game.hunters if h.player_name == player_name), None)
    if hunter is None:
        raise ValueError(f"No hunter with player_name {player_name!r}")
    return hunter


# ---------------------------------------------------------------------------
# Vehicle movement
# ---------------------------------------------------------------------------

def apply_vehicle_move(game: GameState, path: list[str]) -> int:
    """
    Move vehicle along path (road-only, validated by caller).
    Records the full path. Applies run-over damage to agent for each cell
    in path that matches agent.position at that moment.

    Returns total damage dealt.

    House rule (claude.md): 2 damage per overlap, immediate, repeatable.
    """
    vehicle = game.vehicle
    agent = game.agent
    damage = 0

    for cell in path:
        vehicle.path_this_round.append(cell)
        if cell == agent.position:
            agent.health -= 2
            damage += 2

    if path:
        vehicle.position = path[-1]
        for h in game.hunters:
            if h.in_vehicle:
                h.position = path[-1]

    steps = len(path) - 1 if len(path) > 1 else 0
    vehicle.move_budget_remaining -= steps

    return damage


def enter_vehicle(game: GameState, hunter: HunterState) -> None:
    """
    Place hunter into the vehicle. Hunter must be on the vehicle's cell and not already in it.
    Sets in_vehicle=True and ends movement for this turn.
    """
    if hunter.in_vehicle:
        raise ValueError(f"Hunter {hunter.player_name!r} is already in the vehicle")
    if hunter.position != game.vehicle.position:
        raise ValueError(
            f"Hunter {hunter.player_name!r} must be on vehicle cell "
            f"{game.vehicle.position!r} to enter; currently at {hunter.position!r}"
        )
    hunter.in_vehicle = True
    hunter.moved_this_turn = True


def exit_vehicle(
    game: GameState,
    board: BoardData,
    hunter: HunterState,
    destination: str,
) -> None:
    """
    Remove hunter from vehicle and place on an adjacent, passable cell.
    Destination must be adjacent to the vehicle's current position and not occupied
    by another on-board hunter.
    Sets in_vehicle=False, updates position, ends movement for this turn.
    """
    if not hunter.in_vehicle:
        raise ValueError(f"Hunter {hunter.player_name!r} is not in the vehicle")
    if not adjacent(game.vehicle.position, destination):
        raise ValueError(
            f"Exit destination {destination!r} is not adjacent to vehicle at "
            f"{game.vehicle.position!r}"
        )
    if not board.is_passable(destination):
        raise ValueError(f"Exit destination {destination!r} is not passable")
    occupied = {h.position for h in game.hunters if not h.in_vehicle and h is not hunter}
    if destination in occupied:
        raise ValueError(f"Exit destination {destination!r} is occupied by another hunter")
    hunter.in_vehicle = False
    hunter.position = destination
    hunter.moved_this_turn = True


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

def can_use_item(game: GameState, item_key: str) -> tuple[bool, str]:
    """
    Check whether the agent may use item_key right now.
    Returns (allowed, reason). reason is empty string when allowed.
    """
    if game.phase != TurnPhase.AGENT_TURN:
        return False, "Not the agent's turn"
    if game.agent.item_used_this_turn:
        return False, "Already used an item this turn"
    item = next((i for i in game.agent.items if i.key == item_key), None)
    if item is None:
        return False, f"Item {item_key!r} not in inventory"
    if item.tapped:
        return False, "Item is tapped"
    # Proximity mine and pulse_blades don't check charges here (conditional consumption)
    if item_key not in ("proximity_mine", "pulse_blades") and item.charges <= 0:
        return False, "No charges remaining"
    if item_key == "med_kit" and len(game.agent.path_this_turn) > 1:
        return False, "Med Kit must be used before moving"
    return True, ""


def apply_item(
    game: GameState,
    item_key: str,
    item_def: dict,
    board: Optional[BoardData] = None,
    target_cell: Optional[str] = None,
    target_player: Optional[str] = None,
) -> dict:
    """
    Execute item use. Caller must have verified can_use_item first.

    item_def: the raw dict from resources.json for this item key.
    board: required for items that check LOS (flash_bang, tangle_line).
    target_cell: required for cell-targeted items.
    target_player: required for player-targeted items.

    Returns a result dict broadcast to clients.
    Modifies item.charges / item.tapped and sets item_used_this_turn.
    """
    item = next(i for i in game.agent.items if i.key == item_key)
    taps = item_def.get("tap", "False") == "True"
    item_range = int(item_def.get("range", 0))

    game.agent.item_used_this_turn = True

    # --- Items with conditional charge consumption (place before default tap/charge) ---

    if item_key == "proximity_mine":
        if not target_cell:
            raise ValueError("proximity_mine requires target_cell")
        if chebyshev_distance(game.agent.position, target_cell) > item_range:
            raise ValueError(f"Target cell {target_cell!r} is out of range ({item_range} spaces)")
        game.agent.proximity_mine_cell = target_cell
        return {"effect": "mine_placed", "cell": target_cell}

    if item_key == "pulse_blades":
        # Charges consumed only when the blade strike fires (last-seen is placed)
        game.agent.pulse_blades_armed = True
        return {"effect": "pulse_blades_armed"}

    if item_key == "tangle_line":
        if not target_player:
            raise ValueError("tangle_line requires target_player")
        hunter = _get_hunter(game, target_player)
        h_pos = game.vehicle.position if hunter.in_vehicle else hunter.position
        blockers = board.get_blockers(game.active_obstacles) if board else frozenset()
        if not has_los(h_pos, game.agent.position, blockers):
            raise ValueError("Target hunter does not have LOS to Spider")
        dist = chebyshev_distance(h_pos, game.agent.position)
        roll = random.randint(1, 6)
        hit = roll >= dist
        if hit:
            if taps:
                item.tapped = True
            else:
                item.charges -= 1
            hunter.status_effects.add(StatusEffect.STUNNED)
        return {"effect": "tangle_line", "roll": roll, "distance": dist, "stunned": hit, "target": target_player}

    # --- Default: consume charge / tap ---
    if taps:
        item.tapped = True
    else:
        item.charges -= 1

    # --- Pre-existing items ---
    if item_key == "adrenal_surge":
        apply_effect(game, "GRANT_MOVEMENT", {"move_speed": 6})
        return {"effect": "movement_boosted", "move_speed": 6}

    if item_key == "med_kit":
        apply_effect(game, "RESTORE_HEALTH", {"amount": 1})
        game.agent.move_speed = 2
        return {"effect": "healed", "health": game.agent.health, "move_speed": 2}

    if item_key == "remote_trigger":
        game.agent.remote_trigger_active = True
        return {"effect": "remote_trigger_armed"}

    # --- Phase 5 items ---

    if item_key == "flash_bang":
        if not target_cell:
            raise ValueError("flash_bang requires target_cell")
        if chebyshev_distance(game.agent.position, target_cell) > item_range:
            raise ValueError(f"Target cell {target_cell!r} is out of range ({item_range} spaces)")
        blockers = board.get_blockers(game.active_obstacles) if board else frozenset()
        flashbanged = []
        for h in game.hunters:
            h_pos = game.vehicle.position if h.in_vehicle else h.position
            if has_los(h_pos, target_cell, blockers):
                h.status_effects.add(StatusEffect.FLASHBANGED)
                flashbanged.append(h.player_name)
        return {"effect": "flash_bang", "target_cell": target_cell, "flashbanged": flashbanged}

    if item_key == "smoke_grenade":
        if not target_cell:
            raise ValueError("smoke_grenade requires target_cell")
        if chebyshev_distance(game.agent.position, target_cell) > item_range:
            raise ValueError(f"Target cell {target_cell!r} is out of range ({item_range} spaces)")
        obstacle_cells = [target_cell] + neighbors(target_cell)
        for cell in obstacle_cells:
            if cell not in game.active_obstacles:
                game.active_obstacles.append(cell)
        return {"effect": "smoke_grenade", "center": target_cell, "obstacles": obstacle_cells}

    if item_key == "concussion_grenade":
        if not target_cell:
            raise ValueError("concussion_grenade requires target_cell")
        if chebyshev_distance(game.agent.position, target_cell) > item_range:
            raise ValueError(f"Target cell {target_cell!r} is out of range ({item_range} spaces)")
        results = []
        for h in game.hunters:
            h_pos = game.vehicle.position if h.in_vehicle else h.position
            if chebyshev_distance(h_pos, target_cell) <= 1:
                roll = random.randint(1, 6)
                if roll <= 4:
                    h.status_effects.add(StatusEffect.STUNNED)
                results.append({"player": h.player_name, "roll": roll, "stunned": roll <= 4})
        return {"effect": "concussion_grenade", "target_cell": target_cell, "results": results}

    if item_key == "emp_grenade":
        dist = chebyshev_distance(game.agent.position, game.vehicle.position)
        if dist > item_range:
            raise ValueError(f"Vehicle is {dist} spaces away (range {item_range})")
        game.vehicle.emp_disabled = True
        return {"effect": "emp_grenade"}

    if item_key == "power_fists":
        stunned = []
        for h in game.hunters:
            h_pos = game.vehicle.position if h.in_vehicle else h.position
            if chebyshev_distance(h_pos, game.agent.position) <= 2:
                h.status_effects.add(StatusEffect.STUNNED)
                stunned.append(h.player_name)
        return {"effect": "power_fists", "stunned": stunned}

    if item_key == "holo_decoy":
        if not target_cell:
            raise ValueError("holo_decoy requires target_cell")
        if chebyshev_distance(game.agent.position, target_cell) > item_range:
            raise ValueError(f"Target cell {target_cell!r} is out of range ({item_range} spaces)")
        game.agent.holo_decoy_cell = target_cell
        return {"effect": "holo_decoy_placed"}

    if item_key == "smoke_dagger":
        if not target_player:
            raise ValueError("smoke_dagger requires target_player")
        hunter = _get_hunter(game, target_player)
        h_pos = game.vehicle.position if hunter.in_vehicle else hunter.position
        if chebyshev_distance(game.agent.position, h_pos) > item_range:
            raise ValueError(f"Target hunter is out of range ({item_range} spaces)")
        hunter.status_effects.add(StatusEffect.FLASHBANGED)
        game.smoke_dagger_targets.append(target_player)
        return {"effect": "smoke_dagger", "target": target_player}

    if item_key == "stealth_field":
        game.agent.stealth_field_active = True
        return {"effect": "stealth_field"}

    return {"effect": "used", "item_key": item_key}


# ---------------------------------------------------------------------------
# Abilities
# ---------------------------------------------------------------------------

_INSTEAD_OF_MOVING = {"Post-Cognition", "Catch the Scent", "Clairvoyance",
                      "Control Relay", "Remote Link"}


def can_use_ability(
    game: GameState,
    hunter: HunterState,
    ability_name: str,
) -> tuple[bool, str]:
    """
    Check whether hunter may use ability_name right now.
    Returns (allowed, reason).
    """
    if game.phase != TurnPhase.HUNTER_TURN:
        return False, "Not the hunter turn"
    if StatusEffect.STUNNED in hunter.status_effects:
        return False, "Hunter is stunned"
    if StatusEffect.FATIGUED in hunter.status_effects:
        return False, "Hunter is fatigued"
    if ability_name in hunter.abilities_used_this_turn:
        return False, "Ability already used this turn"
    ability = next((a for a in hunter.abilities if a["name"] == ability_name), None)
    if ability is None:
        return False, f"Hunter does not have ability {ability_name!r}"
    if not ability.get("active", False):
        return False, "Ability is passive"
    if ability_name in _INSTEAD_OF_MOVING and hunter.moved_this_turn:
        return False, "This ability must be used instead of moving"
    return True, ""


def apply_ability(
    game: GameState,
    hunter: HunterState,
    ability_name: str,
    params: dict,
) -> dict:
    """
    Execute a hunter active ability. Caller must have verified can_use_ability.

    params: optional extra data from the client (e.g. direction for Clairvoyance).

    Returns a result dict broadcast to all clients.
    """
    hunter.abilities_used_this_turn.append(ability_name)

    if ability_name in _INSTEAD_OF_MOVING:
        hunter.moved_this_turn = True

    if ability_name == "Post-Cognition":
        history = game.agent.position_history
        # "2 turns ago" = position at end of agent turn N-2
        cell = history[-3] if len(history) >= 3 else (history[0] if history else None)
        return {"ability": "Post-Cognition", "cell": cell}

    if ability_name == "Catch the Scent":
        tracker_dist = chebyshev_distance(hunter.position, game.agent.position)
        # Rover deferred — treated as infinitely far, so tracker always wins or ties
        return {"ability": "Catch the Scent", "result": "tracker", "distance": tracker_dist}

    if ability_name == "Clairvoyance":
        direction = params.get("direction", "")
        if direction not in ("NE", "NW", "SE", "SW"):
            raise ValueError(f"direction must be NE, NW, SE, or SW; got {direction!r}")
        sensed = _clairvoyance_check(hunter.position, game.agent.position, direction)
        return {"ability": "Clairvoyance", "direction": direction, "sensed": sensed}

    if ability_name == "Motion Sensor":
        if game.agent.last_turn_steps < 3:
            return {"ability": "Motion Sensor", "direction": None}
        direction = _motion_direction(game.vehicle.position, game.agent.position)
        return {"ability": "Motion Sensor", "direction": direction}

    raise ValueError(f"No apply logic for ability {ability_name!r}")


# ---------------------------------------------------------------------------
# Agent active abilities
# ---------------------------------------------------------------------------

def can_use_agent_ability(game: GameState, ability_name: str) -> tuple[bool, str]:
    """
    Check whether the agent may use ability_name right now.
    Returns (allowed, reason).
    """
    if game.phase != TurnPhase.AGENT_TURN:
        return False, "Not the agent's turn"
    if StatusEffect.FATIGUED in game.agent.status_effects:
        return False, "Agent is fatigued"
    ability = next((a for a in game.agent.abilities if a["name"] == ability_name), None)
    if ability is None:
        return False, f"Agent does not have ability {ability_name!r}"
    if not ability.get("active", False):
        return False, "Ability is passive"

    if ability_name == "Dash":
        if len(game.agent.path_this_turn) > 1:
            return False, "Dash must be used before moving"

    return True, ""


def apply_agent_ability(game: GameState, ability_name: str, _params: dict) -> dict:
    """
    Execute an agent active ability. Caller must have verified can_use_agent_ability.
    Returns a result dict broadcast to clients.
    """
    if ability_name == "Dash":
        game.agent.move_speed = 5
        # FATIGUE applied immediately unless movement was already boosted by an item (Adrenal Surge)
        if not game.agent.movement_boosted_by_item:
            game.agent.status_effects.add(StatusEffect.FATIGUED)
        return {"ability": "Dash", "move_speed": 5}

    raise ValueError(f"No apply logic for agent ability {ability_name!r}")


def _clairvoyance_check(hunter_pos: str, agent_pos: str, direction: str) -> bool:
    hc, hr = cell_col(hunter_pos), cell_row(hunter_pos)
    ac, ar = cell_col(agent_pos), cell_row(agent_pos)
    dc = ac - hc   # positive = East
    dr = ar - hr   # positive = South (row 1 is top)
    if direction == "NE":
        return dc > 0 and dr < 0
    if direction == "NW":
        return dc < 0 and dr < 0
    if direction == "SE":
        return dc > 0 and dr > 0
    if direction == "SW":
        return dc < 0 and dr > 0
    return False


def _motion_direction(vehicle_pos: str, agent_pos: str) -> Optional[str]:
    vc, vr = cell_col(vehicle_pos), cell_row(vehicle_pos)
    ac, ar = cell_col(agent_pos), cell_row(agent_pos)
    dc = ac - vc
    dr = ar - vr
    if dc == 0 and dr == 0:
        return None
    if abs(dc) >= abs(dr):
        return "E" if dc > 0 else "W"
    return "S" if dr > 0 else "N"


# ---------------------------------------------------------------------------
# Win conditions
# ---------------------------------------------------------------------------

def check_win(game: GameState) -> WinCondition:
    """
    Evaluate kill and escape win conditions. Call after every player's turn.
    Does NOT check timeout — use check_timeout() for that.

    Agent wins: game.agent_escaped flag is True (set by game loop when agent
                ends turn on a valid escape point with 3+ public objectives
                and no blocking hunter).
    Hunters win (kill): agent health <= 0.

    Mutates game.win_condition and game.phase on terminal result.
    """
    agent = game.agent

    if agent.health <= 0:
        game.win_condition = WinCondition.HUNTERS_KILL
        game.phase = TurnPhase.GAME_OVER
        return game.win_condition

    if game.agent_escaped:
        game.win_condition = WinCondition.AGENT_ESCAPE
        game.phase = TurnPhase.GAME_OVER
        return game.win_condition

    return WinCondition.NONE


def check_timeout(game: GameState) -> WinCondition:
    """
    Evaluate timeout. Call once at the start of the agent's turn when
    round_number > 40 (hunters completed round 40; this is effectively
    the agent phase of round 41).

    Hunters win if game is not already over.
    Does nothing if round_number <= 40 or game already has a result.

    Mutates game.win_condition and game.phase on terminal result.
    """
    if game.is_over:
        return game.win_condition

    if game.round_number > 40:
        game.win_condition = WinCondition.HUNTERS_TIMEOUT
        game.phase = TurnPhase.GAME_OVER
        return game.win_condition

    return WinCondition.NONE