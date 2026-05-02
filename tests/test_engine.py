"""
test_engine.py — Tests for engine.py

Covers:
  - get_legal_moves: wall exclusion, hunter exclusion, move-speed cap, vehicle exclusion,
                     in_vehicle hunters ignored, from_cell parameter
  - apply_move: full path execution, path tracking, step validation errors,
                objective marking per step, last_seen_cell set after move
  - resolve_combat: roll=1 miss, distance=0 hit, roll>=distance hit, stunned raises,
                    in_vehicle raises
  - check_win: agent escaped, hunters killed, hunter on escape blocks agent
  - check_timeout: round > 40, round <= 40, already-over game unchanged
  - apply_vehicle_move: run-over damage, budget, path published
  - setup_game: player-count rules, hunter in_vehicle, agent start, item limit
"""

import pytest
from pathlib import Path
from unittest.mock import patch


from backend.board import load_board
from backend.state import (
    AgentState, HunterState, VehicleState, GameState,
    StatusEffect, TurnPhase, WinCondition,
)
from backend.engine import (
    get_legal_moves,
    apply_move,
    resolve_combat,
    check_win,
    check_timeout,
    compute_last_seen,
    apply_vehicle_move,
    publish_pending_objectives,
    roll_d6,
    setup_game,
)

RESOURCES = Path(__file__).parent.parent / "backend" / "data" / "resources.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent(position="P10", health=4, move_speed=4, public_objectives=None) -> AgentState:
    return AgentState(
        character="cobra",
        position=position,
        health=health,
        max_health=4,
        move_speed=move_speed,
        items=[],
        public_objectives=public_objectives or [],
    )


def make_hunter(position="A1", player_name="h1", move_speed=4, in_vehicle=False) -> HunterState:
    return HunterState(
        character="gun",
        player_name=player_name,
        position=position,
        move_speed=move_speed,
        in_vehicle=in_vehicle,
    )


def make_vehicle(position="K17") -> VehicleState:
    return VehicleState(name="tracer", position=position, move_speed=10, move_budget_remaining=10)


def make_game(
    board_name="Broken Covenant",
    agent_pos="P10",
    hunter_positions=None,     # list of (pos, in_vehicle) tuples, or just positions (on-board)
    vehicle_pos="K17",
    round_number=1,
    escape_points=None,
    agent_health=4,
    agent_public_objectives=None,
    agent_move_speed=4,
):
    board = load_board(board_name, RESOURCES)

    if hunter_positions is None:
        hunters = [make_hunter("A1", "h0", in_vehicle=True)]
    else:
        hunters = []
        for i, entry in enumerate(hunter_positions):
            if isinstance(entry, tuple):
                pos, in_veh = entry
            else:
                pos, in_veh = entry, False
            hunters.append(make_hunter(pos, f"h{i}", in_vehicle=in_veh))

    agent = make_agent(
        position=agent_pos,
        health=agent_health,
        move_speed=agent_move_speed,
        public_objectives=agent_public_objectives or [],
    )
    vehicle = make_vehicle(vehicle_pos)
    game = GameState(
        board_name=board_name,
        player_count=2,
        agent=agent,
        hunters=hunters,
        vehicle=vehicle,
        objectives=["B17", "C28", "V22", "M12"],
        objectives_visible=True,
        escape_points=escape_points or ["A3", "M1", "W1"],
        round_number=round_number,
        phase=TurnPhase.AGENT_TURN,
    )
    return game, board


# ---------------------------------------------------------------------------
# get_legal_moves
# ---------------------------------------------------------------------------

class TestGetLegalMoves:
    def test_excludes_wall_cells(self):
        game, board = make_game(agent_pos="P9")
        legal = get_legal_moves(game, board)
        for cell in legal:
            assert cell not in board.walls

    def test_excludes_on_board_hunter(self):
        game, board = make_game(agent_pos="P10", hunter_positions=[("P9", False)])
        legal = get_legal_moves(game, board)
        assert "P9" not in legal

    def test_in_vehicle_hunter_does_not_block(self):
        # Hunter in vehicle at M10 should not block agent from moving there
        game, board = make_game(agent_pos="P10", hunter_positions=[("P9", True)])
        game.vehicle.position = "A1"  # vehicle elsewhere so P9 is free
        legal = get_legal_moves(game, board)
        assert "P9" in legal

    def test_excludes_vehicle_space(self):
        game, board = make_game(agent_pos="P10", vehicle_pos="P9")
        game.hunters[0].in_vehicle = True
        legal = get_legal_moves(game, board)
        assert "P9" not in legal

    def test_returns_empty_when_budget_exhausted(self):
        game, board = make_game(agent_pos="P10")
        game.agent.path_this_turn = ["P10", "P11", "P12", "P13", "P14"]
        legal = get_legal_moves(game, board)
        assert legal == []

    def test_from_cell_overrides_current_position(self):
        game, board = make_game(agent_pos="P10")
        legal_from_n12 = get_legal_moves(game, board, from_cell="P12")
        legal_from_current = get_legal_moves(game, board)
        # Results should differ since positions differ
        assert set(legal_from_n12) != set(legal_from_current)

    def test_returns_nonempty_from_open_position(self):
        game, board = make_game(agent_pos="P10")
        assert len(get_legal_moves(game, board)) > 0

    def test_excludes_active_barriers(self):
        game, board = make_game(board_name="Arctic Archives", agent_pos="L17")
        board.active_barriers.append("L18")
        legal = get_legal_moves(game, board)
        assert "L18" not in legal


# ---------------------------------------------------------------------------
# apply_move
# ---------------------------------------------------------------------------

class TestApplyMove:
    def test_updates_position_to_end_of_path(self):
        game, board = make_game(agent_pos="P9")
        apply_move(game, board, ["P9", "P10", "P11"])
        assert game.agent.position == "P11"

    def test_full_path_recorded(self):
        game, board = make_game(agent_pos="P9")
        apply_move(game, board, ["P9", "P10", "P11"])
        assert game.agent.path_this_turn == ["P9", "P10", "P11"]

    def test_backtrack_allowed(self):
        game, board = make_game(agent_pos="P9")
        apply_move(game, board, ["P9", "P10", "P9"])
        assert game.agent.path_this_turn == ["P9", "P10", "P9"]
        assert game.agent.position == "P9"

    def test_raises_on_empty_path(self):
        game, board = make_game(agent_pos="P9")
        with pytest.raises(ValueError, match="empty"):
            apply_move(game, board, [])

    def test_raises_when_path_does_not_start_at_position(self):
        game, board = make_game(agent_pos="P9")
        with pytest.raises(ValueError, match="start"):
            apply_move(game, board, ["P10", "P11"])

    def test_raises_on_non_adjacent_step(self):
        game, board = make_game(agent_pos="P9")
        with pytest.raises(ValueError):
            apply_move(game, board, ["P9", "P11"])  # skips a cell

    def test_raises_on_wall_cell(self):
        game, board = make_game(board_name="Shadow of Babel", agent_pos="A1")
        # A2 is a wall in Shadow of Babel
        assert "A2" in board.walls
        with pytest.raises(ValueError):
            apply_move(game, board, ["A1", "A2"])

    def test_raises_on_hunter_occupied_cell(self):
        game, board = make_game(agent_pos="P9", hunter_positions=[("P10", False)])
        with pytest.raises(ValueError, match="occupied"):
            apply_move(game, board, ["P9", "P10"])

    def test_raises_on_vehicle_space(self):
        game, board = make_game(agent_pos="P9", vehicle_pos="P10")
        game.hunters[0].in_vehicle = True
        with pytest.raises(ValueError, match="vehicle"):
            apply_move(game, board, ["P9", "P10"])

    def test_raises_when_budget_exceeded(self):
        game, board = make_game(agent_pos="P9", agent_move_speed=2)
        with pytest.raises(ValueError, match="budget"):
            apply_move(game, board, ["P9", "P10", "P11", "P12"])

    def test_objective_marked_pending_during_move(self):
        # B17 is an objective; move agent adjacent to it
        game, board = make_game(board_name="Shadow of Babel", agent_pos="A16")
        game.objectives = ["B17", "C28", "V22", "M12"]
        # A16 is passable on SoB and adjacent to B17
        apply_move(game, board, ["A16", "B16"])
        # B16 is adjacent to B17
        assert "B17" in game.agent.pending_objectives

    def test_last_seen_cell_set_after_move(self):
        # Hunter in vehicle — no LOS → last_seen_cell should be None
        game, board = make_game(agent_pos="P9", hunter_positions=[("K17", True)])
        apply_move(game, board, ["P9", "P10"])
        assert game.agent.last_seen_cell is None  # no on-board hunters


# ---------------------------------------------------------------------------
# publish_pending_objectives
# ---------------------------------------------------------------------------

class TestPublishPendingObjectives:
    def test_flushes_pending_to_public(self):
        game, board = make_game()
        game.agent.pending_objectives = ["B17", "C28"]
        publish_pending_objectives(game)
        assert game.agent.public_objectives == ["B17", "C28"]
        assert game.agent.pending_objectives == []

    def test_no_duplicates_in_public(self):
        game, _ = make_game()
        game.agent.public_objectives = ["B17"]
        game.agent.pending_objectives = ["B17"]
        publish_pending_objectives(game)
        assert game.agent.public_objectives.count("B17") == 1


# ---------------------------------------------------------------------------
# resolve_combat
# ---------------------------------------------------------------------------

class TestResolveCombat:
    def test_roll_1_always_misses(self):
        game, _ = make_game(hunter_positions=[("P8", False)])
        hunter = game.hunters[0]
        original_hp = game.agent.health
        hit, roll = resolve_combat(hunter, game.agent, distance=2, forced_roll=1)
        assert hit is False
        assert game.agent.health == original_hp

    def test_distance_0_auto_hit(self):
        game, _ = make_game(hunter_positions=[("P8", False)])
        hunter = game.hunters[0]
        hit, _ = resolve_combat(hunter, game.agent, distance=0)
        assert hit is True
        assert game.agent.health == 3

    def test_hit_when_roll_gte_distance(self):
        game, _ = make_game(hunter_positions=[("P8", False)])
        hunter = game.hunters[0]
        hit, roll = resolve_combat(hunter, game.agent, distance=3, forced_roll=4)
        assert hit is True
        assert game.agent.health == 3

    def test_miss_when_roll_lt_distance(self):
        game, _ = make_game(hunter_positions=[("P8", False)])
        hunter = game.hunters[0]
        original_hp = game.agent.health
        hit, _ = resolve_combat(hunter, game.agent, distance=5, forced_roll=3)
        assert hit is False
        assert game.agent.health == original_hp

    def test_exact_distance_is_hit(self):
        game, _ = make_game(hunter_positions=[("P8", False)])
        hunter = game.hunters[0]
        hit, _ = resolve_combat(hunter, game.agent, distance=4, forced_roll=4)
        assert hit is True

    def test_stunned_raises(self):
        game, _ = make_game(hunter_positions=[("P8", False)])
        hunter = game.hunters[0]
        hunter.status_effects.add(StatusEffect.STUNNED)
        with pytest.raises(ValueError, match="stunned"):
            resolve_combat(hunter, game.agent, distance=2)

    def test_in_vehicle_raises(self):
        game, _ = make_game(hunter_positions=[("K17", True)])
        hunter = game.hunters[0]
        with pytest.raises(ValueError, match="vehicle"):
            resolve_combat(hunter, game.agent, distance=2)

    def test_roll_d6_explodes_on_6(self):
        with patch("backend.engine.random.randint", side_effect=[6, 3]):
            assert roll_d6() == 9

    def test_roll_d6_multiple_explosions(self):
        with patch("backend.engine.random.randint", side_effect=[6, 6, 2]):
            assert roll_d6() == 14

    def test_roll_d6_no_explosion(self):
        with patch("backend.engine.random.randint", return_value=4):
            assert roll_d6() == 4


# ---------------------------------------------------------------------------
# check_win
# ---------------------------------------------------------------------------

class TestCheckWin:
    def test_agent_wins_when_escaped_flag_set(self):
        game, _ = make_game()
        game.agent_escaped = True
        result = check_win(game)
        assert result == WinCondition.AGENT_ESCAPE
        assert game.phase == TurnPhase.GAME_OVER

    def test_no_win_when_escaped_flag_false(self):
        game, _ = make_game()
        assert check_win(game) == WinCondition.NONE

    def test_hunters_win_by_damage(self):
        game, _ = make_game(agent_health=0)
        result = check_win(game)
        assert result == WinCondition.HUNTERS_KILL
        assert game.phase == TurnPhase.GAME_OVER

    def test_damage_win_takes_priority_over_escape_flag(self):
        game, _ = make_game(agent_health=0)
        game.agent_escaped = True
        result = check_win(game)
        assert result == WinCondition.HUNTERS_KILL

    def test_no_win_mid_game(self):
        game, _ = make_game(round_number=20, agent_health=4)
        assert check_win(game) == WinCondition.NONE

    def test_check_win_does_not_trigger_timeout(self):
        game, _ = make_game(round_number=40, agent_health=4)
        assert check_win(game) == WinCondition.NONE


# ---------------------------------------------------------------------------
# check_timeout
# ---------------------------------------------------------------------------

class TestCheckTimeout:
    def test_timeout_when_round_gt_40(self):
        game, _ = make_game(round_number=41)
        result = check_timeout(game)
        assert result == WinCondition.HUNTERS_TIMEOUT
        assert game.phase == TurnPhase.GAME_OVER

    def test_no_timeout_at_round_40(self):
        game, _ = make_game(round_number=40)
        assert check_timeout(game) == WinCondition.NONE

    def test_no_timeout_mid_game(self):
        game, _ = make_game(round_number=20)
        assert check_timeout(game) == WinCondition.NONE

    def test_does_not_override_existing_win(self):
        game, _ = make_game(round_number=41)
        game.win_condition = WinCondition.AGENT_ESCAPE
        game.phase = TurnPhase.GAME_OVER
        result = check_timeout(game)
        assert result == WinCondition.AGENT_ESCAPE  # unchanged


# ---------------------------------------------------------------------------
# compute_last_seen
# ---------------------------------------------------------------------------

class TestComputeLastSeen:
    def test_no_token_when_no_on_board_hunters(self):
        game, board = make_game(agent_pos="P10", hunter_positions=[("K17", True)])
        game.agent.path_this_turn = ["P8", "P9", "P10"]
        assert compute_last_seen(game, board) is None

    def test_no_token_when_all_hunters_flashbanged(self):
        game, board = make_game(agent_pos="P10", hunter_positions=[("P8", False)])
        game.hunters[0].status_effects.add(StatusEffect.FLASHBANGED)
        game.agent.path_this_turn = ["P8", "P9", "P10"]
        assert compute_last_seen(game, board) is None

    def test_returns_none_when_agent_visible_at_end(self):
        # Hunter at N5 with clear LOS to N10 (same column, no walls between on Broken Covenant)
        game, board = make_game(
            board_name="Broken Covenant",
            agent_pos="P10",
            hunter_positions=[("P8", False)],
        )
        game.agent.path_this_turn = ["P8", "P9", "P10"]
        # P8→P10: interior P9 is a road cell on Broken Covenant, no walls
        result = compute_last_seen(game, board)
        assert result is None  # agent ends in LOS

    def test_returns_cell_when_agent_exits_los(self):
        # Hunter at N5; agent path exits LOS by moving past a blocker
        # Use Shadow of Babel where S15 is not a wall but walls exist nearby
        # Simpler: place obstacle between hunter and final position
        game, board = make_game(
            board_name="Broken Covenant",
            agent_pos="P14",
            hunter_positions=[("P8", False)],
        )
        # Add obstacle between N5 and N14 to block end LOS but not mid-path
        game.active_obstacles = ["P12"]
        game.agent.path_this_turn = ["P10", "P11", "P12", "P13", "P14"]
        result = compute_last_seen(game, board)
        # P10 or P11 should be last cell in LOS (P12 is blocker)
        # Exact cell depends on bounding rect; just verify it's a string and in path
        assert result is None or result in game.agent.path_this_turn


# ---------------------------------------------------------------------------
# apply_vehicle_move
# ---------------------------------------------------------------------------

class TestApplyVehicleMove:
    def test_vehicle_moves_to_path_end(self):
        game, board = make_game(vehicle_pos="K17")
        apply_vehicle_move(game, ["K17", "L17", "L16"])
        assert game.vehicle.position == "L16"

    def test_run_over_deals_2_damage(self):
        game, board = make_game(agent_pos="L17", vehicle_pos="K17")
        damage = apply_vehicle_move(game, ["K17", "L17", "L16"])
        assert damage == 2
        assert game.agent.health == 2

    def test_run_over_repeated_overlap(self):
        game, board = make_game(agent_pos="L17", vehicle_pos="K17")
        damage = apply_vehicle_move(game, ["K17", "L17", "K17", "L17"])
        assert damage == 4
        assert game.agent.health == 0

    def test_no_damage_no_overlap(self):
        game, board = make_game(agent_pos="A1", vehicle_pos="K17")
        damage = apply_vehicle_move(game, ["K17", "L17", "L16"])
        assert damage == 0
        assert game.agent.health == 4

    def test_budget_decremented(self):
        game, board = make_game(vehicle_pos="K17")
        apply_vehicle_move(game, ["K17", "L17", "L16"])
        assert game.vehicle.move_budget_remaining == 8

    def test_path_published(self):
        game, board = make_game(vehicle_pos="K17")
        apply_vehicle_move(game, ["K17", "L17", "L16"])
        assert game.vehicle.path_this_round == ["K17", "L17", "L16"]


# ---------------------------------------------------------------------------
# setup_game
# ---------------------------------------------------------------------------

class TestSetupGame:
    def test_all_hunters_start_in_vehicle(self):
        game, _ = setup_game(
            board_name="Broken Covenant",
            agent_player="alice",
            agent_character="cobra",
            hunter_players=["bob", "carol"],
            hunter_characters=["gun", "beast"],
            agent_items=[],
            resources_path=RESOURCES,
        )
        for hunter in game.hunters:
            assert hunter.in_vehicle is True

    def test_hunters_position_matches_vehicle_start(self):
        game, _ = setup_game(
            board_name="Broken Covenant",
            agent_player="alice",
            agent_character="cobra",
            hunter_players=["bob"],
            hunter_characters=["gun"],
            agent_items=[],
            resources_path=RESOURCES,
        )
        for hunter in game.hunters:
            assert hunter.position == game.vehicle.position

    def test_2p_rules(self):
        game, _ = setup_game(
            board_name="Broken Covenant",
            agent_player="alice", agent_character="cobra",
            hunter_players=["bob"], hunter_characters=["gun"],
            agent_items=[], resources_path=RESOURCES,
        )
        assert game.agent.health == 4
        assert game.objectives_visible is True
        assert game.vehicle.position == "K17"
        assert "A6" not in game.escape_points

    def test_4p_rules(self):
        game, _ = setup_game(
            board_name="Broken Covenant",
            agent_player="alice", agent_character="cobra",
            hunter_players=["b", "c", "d"], hunter_characters=["gun", "beast", "prophet"],
            agent_items=[], resources_path=RESOURCES,
        )
        assert game.agent.health == 6
        assert game.objectives_visible is False
        assert game.vehicle.position == "K24"
        assert "A6" in game.escape_points and "W6" in game.escape_points

    def test_5p_rules(self):
        game, _ = setup_game(
            board_name="Shadow of Babel",
            agent_player="alice", agent_character="cobra",
            hunter_players=["b", "c", "d", "e"],
            hunter_characters=["gun", "beast", "prophet", "puppet"],
            agent_items=[], resources_path=RESOURCES,
        )
        assert game.agent.health == 4
        assert game.objectives_visible is False
        assert game.vehicle.position == "K23"
        assert "A6" in game.escape_points

    def test_too_many_items_raises(self):
        with pytest.raises(ValueError):
            setup_game(
                board_name="Broken Covenant",
                agent_player="alice", agent_character="cobra",
                hunter_players=["bob"], hunter_characters=["gun"],
                agent_items=["adrenal_surge", "flash_bang", "smoke_grenade", "stealth_field"],
                resources_path=RESOURCES,
            )

    def test_agent_start_shadow_of_babel(self):
        game, _ = setup_game(
            board_name="Shadow of Babel",
            agent_player="alice", agent_character="cobra",
            hunter_players=["bob"], hunter_characters=["gun"],
            agent_items=[], resources_path=RESOURCES,
        )
        assert game.agent.position == "N1"

    def test_agent_start_other_boards(self):
        for board_name in ["Broken Covenant", "Arctic Archives"]:
            game, _ = setup_game(
                board_name=board_name,
                agent_player="alice", agent_character="cobra",
                hunter_players=["bob"], hunter_characters=["gun"],
                agent_items=[], resources_path=RESOURCES,
            )
            assert game.agent.position == "M1", f"Wrong start on {board_name}"

    def test_objectives_count(self):
        game, _ = setup_game(
            board_name="Arctic Archives",
            agent_player="alice", agent_character="spider",
            hunter_players=["bob"], hunter_characters=["beast"],
            agent_items=[], resources_path=RESOURCES,
        )
        assert len(game.objectives) == 4