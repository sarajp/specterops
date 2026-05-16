"""
test_visibility.py — Tests for visibility.py

Covers:
  is_agent_visible_to_any:
    - all hunters in vehicle → False
    - all hunters flashbanged → False
    - LOS blocked for all hunters → False
    - at least one hunter has clear LOS → True
    - mix of in-vehicle and on-board hunters → uses only on-board

  get_agent_view:
    - role is "agent"
    - includes agent position always
    - includes pending_objectives
    - includes items
    - includes path_this_turn
    - includes all top-level game fields

  get_hunter_view:
    - role is "hunter"
    - omits agent position when not visible
    - includes agent position when visible
    - omits agent character before identity_revealed
    - includes agent character after identity_revealed
    - omits pending_objectives always
    - omits items always
    - omits path_this_turn always
    - includes last_seen_cell always (even when None)
    - includes public_objectives
    - includes all hunter positions and statuses
    - objectives is None when objectives_visible is False
    - objectives is list when objectives_visible is True
    - agent health always included
    - active_obstacles included
    - active_barriers included
"""

import pytest
from pathlib import Path


from backend.board import load_board
from backend.state import (
    AgentState, HunterState, VehicleState, GameState,
    ItemState, StatusEffect, TurnPhase, WinCondition,
)
from backend.visibility import get_agent_view, get_hunter_view, is_agent_visible_to_any

RESOURCES = Path(__file__).parent.parent / "backend" / "data" / "resources.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent(position="P20", **kwargs) -> AgentState:
    defaults = dict(
        character="cobra",
        position=position,
        health=4,
        max_health=4,
        move_speed=4,
        items=[],
        abilities=[],
    )
    defaults.update(kwargs)
    return AgentState(**defaults)


def make_hunter(player_name="h1", position="K17", in_vehicle=True) -> HunterState:
    return HunterState(
        character="gun",
        player_name=player_name,
        position=position,
        move_speed=4,
        in_vehicle=in_vehicle,
    )


def make_game(
    hunters=None,
    agent_pos="P20",
    objectives_visible=True,
    agent_kwargs=None,
) -> GameState:
    if hunters is None:
        hunters = [make_hunter()]
    agent = make_agent(position=agent_pos, **(agent_kwargs or {}))
    return GameState(
        board_name="Broken Covenant",
        player_count=1 + len(hunters),
        agent=agent,
        hunters=hunters,
        vehicle=VehicleState(
            name="tracer", position="K17",
            move_speed=10, move_budget_remaining=10,
        ),
        objectives=["B17", "C28", "V22", "M12"],
        objectives_visible=objectives_visible,
        escape_points=["A3", "M1", "W1"],
        phase=TurnPhase.AGENT_TURN,
    )


def get_board(name="Broken Covenant"):
    return load_board(name, RESOURCES)


# ---------------------------------------------------------------------------
# is_agent_visible_to_any
# ---------------------------------------------------------------------------

class TestIsAgentVisibleToAny:
    def test_all_in_vehicle(self):
        game = make_game(hunters=[make_hunter("h1", "P8", in_vehicle=True)])
        board = get_board()
        assert is_agent_visible_to_any(game, board) is False

    def test_all_flashbanged(self):
        h = make_hunter("h1", "P8", in_vehicle=False)
        h.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(hunters=[h])
        board = get_board()
        assert is_agent_visible_to_any(game, board) is False

    def test_los_blocked_for_all(self):
        h = make_hunter("h1", "P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.active_obstacles = ["P13"]
        board = get_board()
        assert is_agent_visible_to_any(game, board) is False

    def test_one_hunter_has_clear_los(self):
        # P8 → P20 on Broken Covenant: P9–P19 are road, no walls
        h = make_hunter("h1", "P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()
        assert is_agent_visible_to_any(game, board) is True

    def test_mix_in_vehicle_and_on_board(self):
        # h1 in vehicle, h2 on board with clear LOS
        h1 = make_hunter("h1", "P8", in_vehicle=True)
        h2 = make_hunter("h2", "P8", in_vehicle=False)
        game = make_game(hunters=[h1, h2], agent_pos="P20")
        board = get_board()
        assert is_agent_visible_to_any(game, board) is True

    def test_on_board_hunter_blocked_in_vehicle_hunter_ignored(self):
        h1 = make_hunter("h1", "P8", in_vehicle=False)
        h1.status_effects.add(StatusEffect.FLASHBANGED)
        h2 = make_hunter("h2", "P8", in_vehicle=True)
        game = make_game(hunters=[h1, h2], agent_pos="P20")
        board = get_board()
        assert is_agent_visible_to_any(game, board) is False

    def test_no_hunters(self):
        game = make_game(hunters=[])
        board = get_board()
        assert is_agent_visible_to_any(game, board) is False


# ---------------------------------------------------------------------------
# get_agent_view
# ---------------------------------------------------------------------------

class TestGetAgentView:
    def test_role_is_agent(self):
        game = make_game()
        assert get_agent_view(game)["role"] == "agent"

    def test_includes_agent_position_always(self):
        game = make_game(agent_pos="P20")
        view = get_agent_view(game)
        assert view["agent"]["position"] == "P20"

    def test_includes_pending_objectives(self):
        game = make_game()
        game.agent.pending_objectives = ["B17"]
        view = get_agent_view(game)
        assert "pending_objectives" in view["agent"]
        assert view["agent"]["pending_objectives"] == ["B17"]

    def test_includes_items(self):
        game = make_game()
        game.agent.items = [ItemState(key="flash_bang", name="Flash Bang", charges=1)]
        view = get_agent_view(game)
        assert "items" in view["agent"]
        assert len(view["agent"]["items"]) == 1
        assert view["agent"]["items"][0]["key"] == "flash_bang"

    def test_includes_path_this_turn(self):
        game = make_game()
        game.agent.path_this_turn = ["P20", "P21"]
        view = get_agent_view(game)
        assert view["agent"]["path_this_turn"] == ["P20", "P21"]

    def test_includes_board_name(self):
        game = make_game()
        assert get_agent_view(game)["board_name"] == "Broken Covenant"

    def test_includes_round_number(self):
        game = make_game()
        game.round_number = 7
        assert get_agent_view(game)["round_number"] == 7

    def test_includes_phase(self):
        game = make_game()
        view = get_agent_view(game)
        assert view["phase"] == TurnPhase.AGENT_TURN.name

    def test_includes_escape_points(self):
        game = make_game()
        view = get_agent_view(game)
        assert view["escape_points"] == ["A3", "M1", "W1"]

    def test_includes_objectives(self):
        game = make_game()
        view = get_agent_view(game)
        assert view["objectives"] == ["B17", "C28", "V22", "M12"]

    def test_includes_win_condition(self):
        game = make_game()
        view = get_agent_view(game)
        assert view["win_condition"] == WinCondition.NONE.name

    def test_includes_agent_escaped(self):
        game = make_game()
        view = get_agent_view(game)
        assert view["agent_escaped"] is False

    def test_includes_active_obstacles(self):
        game = make_game()
        game.active_obstacles = ["D5"]
        view = get_agent_view(game)
        assert view["active_obstacles"] == ["D5"]

    def test_includes_active_barriers(self):
        game = make_game()
        game.active_barriers = ["H8"]
        view = get_agent_view(game)
        assert view["active_barriers"] == ["H8"]

    def test_includes_all_hunters(self):
        hunters = [make_hunter("h1"), make_hunter("h2")]
        game = make_game(hunters=hunters)
        view = get_agent_view(game)
        names = [h["player_name"] for h in view["hunters"]]
        assert "h1" in names and "h2" in names

    def test_includes_vehicle(self):
        game = make_game()
        view = get_agent_view(game)
        assert "vehicle" in view
        assert view["vehicle"]["position"] == "K17"

    def test_agent_status_effects_serialised_as_names(self):
        game = make_game()
        game.agent.status_effects.add(StatusEffect.STUNNED)
        view = get_agent_view(game)
        assert "STUNNED" in view["agent"]["status_effects"]

    def test_agent_character_always_included(self):
        game = make_game()
        game.agent.identity_revealed = False
        view = get_agent_view(game)
        assert view["agent"]["character"] == "cobra"


# ---------------------------------------------------------------------------
# get_hunter_view
# ---------------------------------------------------------------------------

class TestGetHunterView:
    def test_role_is_hunter(self):
        game = make_game()
        board = get_board()
        assert get_hunter_view(game, board)["role"] == "hunter"

    def test_omits_agent_position_when_not_visible(self):
        h = make_hunter("h1", "K17", in_vehicle=True)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()
        view = get_hunter_view(game, board)
        assert "position" not in view["agent"]

    def test_includes_agent_position_when_visible(self):
        h = make_hunter("h1", "P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["agent"]["position"] == "P20"

    def test_omits_agent_character_before_identity_revealed(self):
        h = make_hunter("h1", "P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.agent.identity_revealed = False
        board = get_board()
        view = get_hunter_view(game, board)
        assert "character" not in view["agent"]

    def test_includes_agent_character_after_identity_revealed(self):
        h = make_hunter("h1", "P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.agent.identity_revealed = True
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["agent"]["character"] == "cobra"

    def test_omits_pending_objectives_always(self):
        game = make_game()
        game.agent.pending_objectives = ["B17"]
        board = get_board()
        view = get_hunter_view(game, board)
        assert "pending_objectives" not in view["agent"]

    def test_omits_items_always(self):
        game = make_game()
        game.agent.items = [ItemState(key="flash_bang", name="Flash Bang", charges=1)]
        board = get_board()
        view = get_hunter_view(game, board)
        assert "items" not in view["agent"]

    def test_omits_path_this_turn_always(self):
        game = make_game()
        game.agent.path_this_turn = ["P20", "P21"]
        board = get_board()
        view = get_hunter_view(game, board)
        assert "path_this_turn" not in view["agent"]

    def test_includes_last_seen_cell_when_none(self):
        game = make_game()
        game.agent.last_seen_cell = None
        board = get_board()
        view = get_hunter_view(game, board)
        assert "last_seen_cell" in view["agent"]
        assert view["agent"]["last_seen_cell"] is None

    def test_includes_last_seen_cell_when_set(self):
        game = make_game()
        game.agent.last_seen_cell = "P8"
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["agent"]["last_seen_cell"] == "P8"

    def test_includes_public_objectives(self):
        game = make_game()
        game.agent.public_objectives = ["B17", "C28"]
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["agent"]["public_objectives"] == ["B17", "C28"]

    def test_includes_agent_health(self):
        game = make_game(agent_kwargs={"health": 3, "max_health": 4})
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["agent"]["health"] == 3
        assert view["agent"]["max_health"] == 4

    def test_objectives_none_when_hidden(self):
        game = make_game(objectives_visible=False)
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["objectives"] is None

    def test_objectives_list_when_visible(self):
        game = make_game(objectives_visible=True)
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["objectives"] == ["B17", "C28", "V22", "M12"]

    def test_includes_all_hunter_positions(self):
        h1 = make_hunter("h1", "A1", in_vehicle=False)
        h2 = make_hunter("h2", "B2", in_vehicle=False)
        game = make_game(hunters=[h1, h2])
        board = get_board()
        view = get_hunter_view(game, board)
        positions = {h["player_name"]: h["position"] for h in view["hunters"]}
        assert positions["h1"] == "A1"
        assert positions["h2"] == "B2"

    def test_includes_hunter_status_effects(self):
        h = make_hunter("h1", in_vehicle=False)
        h.status_effects.add(StatusEffect.STUNNED)
        game = make_game(hunters=[h])
        board = get_board()
        view = get_hunter_view(game, board)
        assert "STUNNED" in view["hunters"][0]["status_effects"]

    def test_includes_hunter_in_vehicle_flag(self):
        h = make_hunter("h1", in_vehicle=True)
        game = make_game(hunters=[h])
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["hunters"][0]["in_vehicle"] is True

    def test_includes_active_obstacles(self):
        game = make_game()
        game.active_obstacles = ["D5"]
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["active_obstacles"] == ["D5"]

    def test_includes_active_barriers(self):
        game = make_game()
        game.active_barriers = ["H8"]
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["active_barriers"] == ["H8"]

    def test_includes_vehicle(self):
        game = make_game()
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["vehicle"]["position"] == "K17"

    def test_includes_round_number(self):
        game = make_game()
        game.round_number = 12
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["round_number"] == 12

    def test_includes_phase(self):
        game = make_game()
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["phase"] == TurnPhase.AGENT_TURN.name

    def test_includes_escape_points(self):
        game = make_game()
        board = get_board()
        view = get_hunter_view(game, board)
        assert view["escape_points"] == ["A3", "M1", "W1"]

    def test_agent_status_effects_serialised_as_names(self):
        game = make_game()
        game.agent.status_effects.add(StatusEffect.FLASHBANGED)
        board = get_board()
        view = get_hunter_view(game, board)
        assert "FLASHBANGED" in view["agent"]["status_effects"]

    def test_position_absent_then_present_on_visibility_change(self):
        # Start invisible, then give hunter clear LOS
        h = make_hunter("h1", "K17", in_vehicle=True)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()

        view1 = get_hunter_view(game, board)
        assert "position" not in view1["agent"]

        h.in_vehicle = False
        h.position = "P8"
        view2 = get_hunter_view(game, board)
        assert view2["agent"]["position"] == "P20"

    def test_character_absent_then_present_on_identity_reveal(self):
        game = make_game()
        board = get_board()

        game.agent.identity_revealed = False
        view1 = get_hunter_view(game, board)
        assert "character" not in view1["agent"]

        game.agent.identity_revealed = True
        view2 = get_hunter_view(game, board)
        assert view2["agent"]["character"] == "cobra"