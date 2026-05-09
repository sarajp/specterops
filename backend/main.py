"""
main.py — FastAPI app, WebSocket endpoints, message dispatch.

Single game instance (claude.md: personal use). Game and board are
module-level singletons, initialised when the agent sends start_game.

WebSocket endpoint: /ws/{player_name}
  One connection per player. player_name is a display name chosen by the user.

Inbound message format (JSON):
  { "type": "<message_type>", ...payload fields }

Lobby message types (before game starts):
  join_lobby          — register/update role, character, board selection
                        { role: "agent"|"hunter", character: str, board: str (agent only) }
  start_game          — agent only; assembles game from lobby state

Game message types:
  start_agent_turn    — agent signals start of their turn
  submit_path         — agent submits confirmed movement path
  end_agent_turn      — agent confirms end of turn
  set_hunter_order    — hunters agree on turn order
  start_hunter_turn   — active hunter signals start of their turn
  submit_hunter_move  — active hunter submits confirmed movement path
                        (path of length 1 = no movement)
  submit_attack       — active hunter attacks agent (only if visible)
  end_hunter_turn     — active hunter confirms end of turn

After every state-mutating message, broadcast_state() pushes role-filtered
views: agent gets get_agent_view, all hunters get get_hunter_view.
After every lobby change, broadcast_lobby() pushes the current player list.

Errors (ValueError from engine/loop) are returned as an error message
to the sender only; state is not broadcast on error.

Assumptions:
  - No authentication. Player names are trusted as passed.
  - No reconnection handling; dropped connections are removed from the dict.
  - Only one game at a time; restart the server to reset.
  - Items and abilities deferred; their message types are not yet handled.
  - If the agent disconnects during the lobby, the agent slot reopens.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.board import BoardData
from backend.engine import (
    apply_move,
    get_legal_moves,
    resolve_combat,
    setup_game,
    chebyshev_distance,
)
from backend.loop import (
    end_agent_turn,
    end_hunter_turn,
    set_hunter_order,
    start_agent_turn,
    start_hunter_turn,
    is_agent_visible_to,
)
from backend.state import GameState, ItemState, StatusEffect, TurnPhase, WinCondition
from backend.visibility import get_agent_view, get_hunter_view

logger = logging.getLogger(__name__)

RESOURCES = Path(__file__).parent / "data" / "resources.json"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

game: Optional[GameState] = None
board: Optional[BoardData] = None
connections: dict[str, WebSocket] = {}       # player_name → WebSocket
lobby: dict[str, dict] = {}                  # player_name → {role, character, board}
agent_player_name: Optional[str] = None      # connection key of the agent; set on game start
available_items: list[dict] = []             # item options sent to agent during SETUP phase
max_equipment: int = 0                       # how many items the agent may pick
_item_defs: dict = {}                        # raw item data from resources.json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def send_to(player_name: str, message: dict) -> None:
    ws = connections.get(player_name)
    if ws:
        await ws.send_text(json.dumps(message))


async def send_error(player_name: str, detail: str) -> None:
    await send_to(player_name, {"type": "error", "detail": detail})


async def broadcast_lobby() -> None:
    """Push current lobby player list to every connected client.

    Hunters must not learn which agent character was picked, so their view
    receives the agent entry with character redacted to an empty string.
    """
    players = list(lobby.values())
    hunter_view = json.dumps({
        "type": "lobby",
        "players": [
            {**p, "character": ""} if p["role"] == "agent" else p
            for p in players
        ],
    })
    agent_view = json.dumps({"type": "lobby", "players": players})
    for player_name, ws in list(connections.items()):
        is_agent = lobby.get(player_name, {}).get("role") == "agent"
        try:
            await ws.send_text(agent_view if is_agent else hunter_view)
        except Exception:
            pass


async def broadcast_state() -> None:
    """Push role-filtered game state to every connected client."""
    if game is None or board is None:
        return
    agent_view = get_agent_view(game)
    if game.phase == TurnPhase.SETUP:
        agent_view["available_items"] = available_items
        agent_view["max_equipment"] = max_equipment
    hunter_view = get_hunter_view(game, board)
    for player_name, ws in list(connections.items()):
        try:
            view = agent_view if player_name == agent_player_name else hunter_view
            await ws.send_text(json.dumps({"type": "state", "data": view}))
        except Exception:
            logger.warning("Failed to send state to %s", player_name)


def _require_game(player_name: str) -> bool:
    """Return True if game exists, else False (caller should send error)."""
    return game is not None and board is not None


def _active_hunter_name() -> Optional[str]:
    if game is None or not game.hunter_order:
        return None
    return game.hunter_order[game.active_hunter_index]


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

async def handle_leave_game(player_name: str) -> None:
    global game, board, agent_player_name, available_items, max_equipment, _item_defs
    logger.info("Game reset by %s", player_name)
    game = None
    board = None
    agent_player_name = None
    available_items = []
    max_equipment = 0
    _item_defs = {}
    lobby.clear()
    await broadcast_lobby()


async def handle_join_lobby(player_name: str, msg: dict) -> None:
    if game is not None:
        await send_error(player_name, "Game already in progress")
        return

    role = msg.get("role")
    character = msg.get("character", "")
    board_name = msg.get("board", "")

    if role not in ("agent", "hunter"):
        await send_error(player_name, "role must be 'agent' or 'hunter'")
        return
    if not character:
        await send_error(player_name, "character is required")
        return
    if role == "agent" and not board_name:
        await send_error(player_name, "board is required for agent")
        return

    if player_name not in lobby and len(lobby) >= 5:
        await send_error(player_name, "Game is full (5 players max)")
        return

    for pname, entry in lobby.items():
        if pname == player_name:
            continue
        if entry["character"] == character:
            await send_error(player_name, f"{character!r} is already taken by {pname}")
            return
        if role == "agent" and entry["role"] == "agent":
            await send_error(player_name, f"{pname} is already the agent")
            return

    lobby[player_name] = {
        "player_name": player_name,
        "role": role,
        "character": character,
        "board": board_name if role == "agent" else "",
    }
    await broadcast_lobby()


async def handle_start_game(player_name: str) -> None:
    global game, board, agent_player_name, available_items, max_equipment, _item_defs

    if game is not None:
        await send_error(player_name, "Game already in progress")
        return

    entry = lobby.get(player_name)
    if not entry or entry["role"] != "agent":
        await send_error(player_name, "Only the agent can start the game")
        return

    hunter_entries = [e for e in lobby.values() if e["role"] == "hunter"]
    if len(hunter_entries) < 2:
        await send_error(player_name, "Need at least 2 hunters to start")
        return

    try:
        game, board = setup_game(
            board_name=entry["board"],
            agent_player=player_name,
            agent_character=entry["character"],
            hunter_players=[e["player_name"] for e in hunter_entries],
            hunter_characters=[e["character"] for e in hunter_entries],
            agent_items=[],
            resources_path=RESOURCES,
        )
        agent_player_name = player_name
        game.phase = TurnPhase.SETUP

        player_count = len(lobby)
        max_equipment = 5 if player_count == 4 else 3

        with open(RESOURCES) as f:
            res = json.load(f)["resources"]
        _item_defs = res["items"]
        agent_display_name = res["agents"].get(entry["character"], {}).get("name", "")

        available_items = [
            {
                "key": key,
                "name": item["name"],
                "charges": int(item["charges"]),
                "copies": int(item.get("copies", 1)),
                "ability": item["abilities"][0] if item["abilities"] else "",
            }
            for key, item in _item_defs.items()
            if not item.get("availability") or agent_display_name in item["availability"]
        ]
    except (KeyError, ValueError) as e:
        game = None
        board = None
        agent_player_name = None
        await send_error(player_name, f"start_game failed: {e}")
        return

    await broadcast_state()


async def handle_pick_items(player_name: str, msg: dict) -> None:
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    if player_name != agent_player_name:
        await send_error(player_name, "Only the agent can pick items")
        return
    if game.phase != TurnPhase.SETUP:
        await send_error(player_name, "Not in setup phase")
        return

    selected = msg.get("items", [])
    if not isinstance(selected, list):
        await send_error(player_name, "items must be a list")
        return
    if len(selected) > max_equipment:
        await send_error(player_name, f"Too many items: max is {max_equipment}")
        return

    valid_keys = {item["key"] for item in available_items}
    for key in selected:
        if key not in valid_keys:
            await send_error(player_name, f"Invalid item: {key!r}")
            return

    game.agent.items = [
        ItemState(key=key, name=_item_defs[key]["name"], charges=int(_item_defs[key]["charges"]))
        for key in selected
    ]
    game.phase = TurnPhase.AGENT_TURN
    await broadcast_state()


async def handle_setup_game(player_name: str, msg: dict) -> None:
    global game, board

    if game is not None:
        await send_error(player_name, "Game already in progress")
        return

    try:
        game, board = setup_game(
            board_name=msg["board_name"],
            agent_player=msg["agent_player"],
            agent_character=msg["agent_character"],
            hunter_players=msg["hunter_players"],
            hunter_characters=msg["hunter_characters"],
            agent_items=msg.get("agent_items", []),
            resources_path=RESOURCES,
        )
        # moved_this_turn starts False on each HunterState (reset each turn by start_hunter_turn)
    except (KeyError, ValueError) as e:
        game = None
        board = None
        await send_error(player_name, f"setup_game failed: {e}")
        return

    await broadcast_state()


async def handle_start_agent_turn(player_name: str) -> None:
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    if player_name != agent_player_name:
        await send_error(player_name, "Only the agent can start the agent turn")
        return
    try:
        result = start_agent_turn(game, board)
    except ValueError as e:
        await send_error(player_name, str(e))
        return
    await broadcast_state()
    if result != WinCondition.NONE:
        await _broadcast_game_over(result)


async def handle_submit_path(player_name: str, msg: dict) -> None:
    """Agent submits their confirmed movement path."""
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    if player_name != agent_player_name:
        await send_error(player_name, "Only the agent can submit a path")
        return
    try:
        path = msg["path"]
        apply_move(game, board, path)
    except (KeyError, ValueError) as e:
        await send_error(player_name, str(e))
        return
    await broadcast_state()


async def handle_end_agent_turn(player_name: str) -> None:
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    if player_name != agent_player_name:
        await send_error(player_name, "Only the agent can end the agent turn")
        return
    try:
        result = end_agent_turn(game, board)
    except ValueError as e:
        await send_error(player_name, str(e))
        return
    await broadcast_state()
    if result != WinCondition.NONE:
        await _broadcast_game_over(result)


async def handle_set_hunter_order(player_name: str, msg: dict) -> None:
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    try:
        order = msg["order"]
        set_hunter_order(game, order)
    except (KeyError, ValueError) as e:
        await send_error(player_name, str(e))
        return
    await broadcast_state()


async def handle_start_hunter_turn(player_name: str) -> None:
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    active = _active_hunter_name()
    if player_name != active:
        await send_error(player_name, f"It is {active}'s turn, not {player_name}'s")
        return
    try:
        start_hunter_turn(game)  # resets hunter.moved_this_turn
    except ValueError as e:
        await send_error(player_name, str(e))
        return
    await broadcast_state()


async def handle_submit_hunter_move(player_name: str, msg: dict) -> None:
    """
    Active hunter submits their confirmed movement path.
    A path of length 1 (start cell only) means no movement.
    """
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    active = _active_hunter_name()
    if player_name != active:
        await send_error(player_name, f"It is {active}'s turn, not {player_name}'s")
        return

    hunter = next((h for h in game.hunters if h.player_name == player_name), None)
    if hunter is None:
        await send_error(player_name, "Hunter not found")
        return

    try:
        path = msg["path"]
        if not path:
            raise ValueError("Path must not be empty")

        # Validate start cell
        if path[0] != hunter.position:
            raise ValueError(
                f"Path must start at hunter position {hunter.position!r}, got {path[0]!r}"
            )

        # Validate each step: passable, within move_speed, no structures
        # Hunter movement validation is simpler than agent — hunters can share
        # cells freely and are not blocked by the vehicle or each other for now.
        # Full hunter movement validation (stun cap, road-only for vehicle) is
        # deferred to when hunter movement rules are more fully specified.
        steps = len(path) - 1
        if StatusEffect.STUNNED in hunter.status_effects:
            effective_speed = 2
        else:
            effective_speed = hunter.move_speed

        if steps > effective_speed:
            raise ValueError(
                f"Path has {steps} steps but hunter move speed is {effective_speed}"
            )

        for i in range(1, len(path)):
            if not board.is_passable(path[i]):
                raise ValueError(f"Step {i}: {path[i]!r} is not passable")
            if chebyshev_distance(path[i - 1], path[i]) != 1:
                raise ValueError(
                    f"Step {i}: {path[i]!r} is not adjacent to {path[i-1]!r}"
                )

        # Apply movement
        hunter.position = path[-1]
        hunter.path_this_turn = path
        hunter.moved_this_turn = True

    except (KeyError, ValueError) as e:
        await send_error(player_name, str(e))
        return

    await broadcast_state()


async def handle_submit_attack(player_name: str) -> None:
    """
    Active hunter attacks the agent.

    Valid only after submit_hunter_move this turn.
    Agent must be visible to the attacking hunter at their current position.
    Distance is Chebyshev distance between hunter and agent.
    """
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    active = _active_hunter_name()
    if player_name != active:
        await send_error(player_name, f"It is {active}'s turn, not {player_name}'s")
        return
    hunter = next((h for h in game.hunters if h.player_name == player_name), None)
    if hunter is None:
        await send_error(player_name, "Hunter not found")
        return
    if not hunter.moved_this_turn:
        await send_error(player_name, "Must submit a move before attacking")
        return

    if not is_agent_visible_to(hunter, game, board):
        await send_error(player_name, "Agent is not visible")
        return

    try:
        distance = chebyshev_distance(hunter.position, game.agent.position)
        hit, roll = resolve_combat(hunter, game.agent, distance)
    except ValueError as e:
        await send_error(player_name, str(e))
        return

    await broadcast_state()
    await _broadcast_combat_result(player_name, hit, roll, distance)

    if game.agent.health <= 0:
        from backend.engine import check_win
        result = check_win(game)
        await broadcast_state()
        if result != WinCondition.NONE:
            await _broadcast_game_over(result)


async def handle_end_hunter_turn(player_name: str) -> None:
    if not _require_game(player_name):
        await send_error(player_name, "No game in progress")
        return
    active = _active_hunter_name()
    if player_name != active:
        await send_error(player_name, f"It is {active}'s turn, not {player_name}'s")
        return
    hunter = next((h for h in game.hunters if h.player_name == player_name), None)
    if hunter is None:
        await send_error(player_name, "Hunter not found")
        return
    if not hunter.moved_this_turn:
        await send_error(player_name, "Must submit a move before ending turn")
        return
    try:
        result = end_hunter_turn(game, board)
    except ValueError as e:
        await send_error(player_name, str(e))
        return
    await broadcast_state()
    if result != WinCondition.NONE:
        await _broadcast_game_over(result)


# ---------------------------------------------------------------------------
# Broadcast helpers
# ---------------------------------------------------------------------------

async def _broadcast_game_over(result: WinCondition) -> None:
    msg = {"type": "game_over", "result": result.name}
    for ws in list(connections.values()):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            pass


async def _broadcast_combat_result(
    attacker: str, hit: bool, roll: int, distance: int
) -> None:
    msg = {
        "type": "combat_result",
        "attacker": attacker,
        "hit": hit,
        "roll": roll,
        "distance": distance,
    }
    for ws in list(connections.values()):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

async def dispatch(player_name: str, msg: dict) -> None:
    msg_type = msg.get("type")

    if msg_type == "leave_game":
        await handle_leave_game(player_name)
    elif msg_type == "join_lobby":
        await handle_join_lobby(player_name, msg)
    elif msg_type == "start_game":
        await handle_start_game(player_name)
    elif msg_type == "pick_items":
        await handle_pick_items(player_name, msg)
    elif msg_type == "setup_game":
        await handle_setup_game(player_name, msg)
    elif msg_type == "start_agent_turn":
        await handle_start_agent_turn(player_name)
    elif msg_type == "submit_path":
        await handle_submit_path(player_name, msg)
    elif msg_type == "end_agent_turn":
        await handle_end_agent_turn(player_name)
    elif msg_type == "set_hunter_order":
        await handle_set_hunter_order(player_name, msg)
    elif msg_type == "start_hunter_turn":
        await handle_start_hunter_turn(player_name)
    elif msg_type == "submit_hunter_move":
        await handle_submit_hunter_move(player_name, msg)
    elif msg_type == "submit_attack":
        await handle_submit_attack(player_name)
    elif msg_type == "end_hunter_turn":
        await handle_end_hunter_turn(player_name)
    else:
        await send_error(player_name, f"Unknown message type: {msg_type!r}")


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str) -> None:
    await websocket.accept()
    connections[player_name] = websocket
    logger.info("Player connected: %s", player_name)

    # Send current state immediately on connect
    try:
        if game is not None and board is not None:
            view = get_agent_view(game) if player_name == agent_player_name else get_hunter_view(game, board)
            await websocket.send_text(json.dumps({"type": "state", "data": view}))
        else:
            await websocket.send_text(json.dumps({"type": "lobby", "players": list(lobby.values())}))
    except Exception:
        pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_error(player_name, "Invalid JSON")
                continue
            await dispatch(player_name, msg)
    except WebSocketDisconnect:
        logger.info("Player disconnected: %s", player_name)
    finally:
        connections.pop(player_name, None)
        # If no game yet and this player was in the lobby, free their slot.
        # Agent slot reopens automatically since we just remove the entry.
        if game is None and player_name in lobby:
            lobby.pop(player_name)
            await broadcast_lobby()