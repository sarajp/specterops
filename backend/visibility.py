"""
visibility.py — Role-filtered views of GameState for WebSocket dispatch.

All hunters share a single view (traitor rules deferred).
The agent gets full unfiltered state.

Functions:
  get_agent_view(game)          Full state dict for the agent client.
  get_hunter_view(game, board)  Shared filtered dict for all hunter clients.
  is_agent_visible_to_any(game, board)
                                True if any on-board, non-flashbanged hunter
                                has LOS to the agent's current position.

Views are plain dicts suitable for JSON serialisation. They are snapshots —
callers should regenerate after every state mutation rather than caching.

Hunter view omits:
  - agent.position (unless agent is currently visible to any hunter)
  - agent.character (until identity_revealed)
  - agent.pending_objectives (always hidden from hunters)
  - agent.items (always hidden)
  - agent.path_this_turn (always hidden)
  - agent.is_traitor (deferred)
  - agent.last_seen_cell is INCLUDED (hunters can see the token)
"""

from __future__ import annotations

from backend.board import BoardData
from backend.loop import is_agent_visible_to
from backend.state import GameState, HunterState, StatusEffect


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_agent_visible_to_any(game: GameState, board: BoardData) -> bool:
    """
    True if at least one on-board, non-flashbanged hunter has LOS to the agent.
    Used to decide whether to include agent position in the hunter view.
    """
    return any(is_agent_visible_to(h, game, board) for h in game.hunters)


def get_agent_view(game: GameState) -> dict:
    """
    Full game state for the agent client. Nothing redacted.
    """
    return {
        "role": "agent",
        "board_name": game.board_name,
        "round_number": game.round_number,
        "phase": game.phase.name,
        "win_condition": game.win_condition.name,
        "agent_escaped": game.agent_escaped,
        "escape_points": game.escape_points,
        "objectives": game.objectives,
        "objectives_visible": game.objectives_visible,
        "active_obstacles": game.active_obstacles,
        "active_barriers": game.active_barriers,
        "agent": {
            "character": game.agent.character,
            "position": game.agent.position,
            "health": game.agent.health,
            "max_health": game.agent.max_health,
            "move_speed": game.agent.move_speed,
            "identity_revealed": game.agent.identity_revealed,
            "pending_objectives": game.agent.pending_objectives,
            "public_objectives": game.agent.public_objectives,
            "last_seen_cell": game.agent.last_seen_cell,
            "path_this_turn": game.agent.path_this_turn,
            "status_effects": [e.name for e in game.agent.status_effects],
            "items": [
                {
                    "key": item.key,
                    "name": item.name,
                    "charges": item.charges,
                    "tapped": item.tapped,
                }
                for item in game.agent.items
            ],
            "abilities": game.agent.abilities,
            "item_used_this_turn": game.agent.item_used_this_turn,
        },
        "hunters": [_hunter_dict(h) for h in game.hunters],
        "vehicle": _vehicle_dict(game),
        "hunter_order": game.hunter_order,
        "active_hunter_index": game.active_hunter_index,
    }


def get_hunter_view(game: GameState, board: BoardData) -> dict:
    """
    Shared view for all hunter clients.

    Agent position is included only if visible to any hunter.
    Agent character is included only if identity_revealed.
    Pending objectives, items, path, and traitor flag are always omitted.
    Last-seen token cell is always included (hunters can see it on the board).
    """
    agent_visible = is_agent_visible_to_any(game, board)

    agent_dict: dict = {
        "health": game.agent.health,
        "max_health": game.agent.max_health,
        "identity_revealed": game.agent.identity_revealed,
        "public_objectives": game.agent.public_objectives,
        "last_seen_cell": game.agent.last_seen_cell,
        "status_effects": [e.name for e in game.agent.status_effects],
    }

    if agent_visible:
        agent_dict["position"] = game.agent.position
    if game.agent.identity_revealed:
        agent_dict["character"] = game.agent.character

    return {
        "role": "hunter",
        "board_name": game.board_name,
        "round_number": game.round_number,
        "phase": game.phase.name,
        "win_condition": game.win_condition.name,
        "escape_points": game.escape_points,
        "objectives": game.objectives if game.objectives_visible else None,
        "objectives_visible": game.objectives_visible,
        "active_obstacles": game.active_obstacles,
        "active_barriers": game.active_barriers,
        "agent": agent_dict,
        "hunters": [_hunter_dict(h) for h in game.hunters],
        "vehicle": _vehicle_dict(game),
        "hunter_order": game.hunter_order,
        "active_hunter_index": game.active_hunter_index,
        "hunter_order_proposals": game.hunter_order_proposals,
        "order_mismatch": game.order_mismatch,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hunter_dict(h: HunterState) -> dict:
    return {
        "player_name": h.player_name,
        "character": h.character,
        "position": h.position,
        "move_speed": h.move_speed,
        "in_vehicle": h.in_vehicle,
        "moved_this_turn": h.moved_this_turn,
        "path_this_turn": h.path_this_turn,
        "status_effects": [e.name for e in h.status_effects],
        "abilities": h.abilities,
        "abilities_used_this_turn": h.abilities_used_this_turn,
    }


def _vehicle_dict(game: GameState) -> dict:
    return {
        "name": game.vehicle.name,
        "position": game.vehicle.position,
        "move_speed": game.vehicle.move_speed,
        "move_budget_remaining": game.vehicle.move_budget_remaining,
        "occupied_by": game.vehicle.occupied_by,
        "path_this_round": game.vehicle.path_this_round,
    }