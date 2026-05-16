"""
test_loop.py — Tests for loop.py

Covers:
  start_agent_turn:
    - clears agent flashbang
    - clears active obstacles
    - resets agent path
    - publishes pending objectives
    - returns HUNTERS_TIMEOUT when round > 40
    - returns NONE and continues when round <= 40

  end_agent_turn:
    - raises in wrong phase
    - sets agent_escaped and returns AGENT_ESCAPE when conditions met
    - does not set agent_escaped when objectives < 3
    - does not set agent_escaped when on-board hunter blocks escape point
    - in-vehicle hunter does not block escape
    - advances phase to HUNTER_NEGOTIATE on no win
    - returns HUNTERS_KILL if agent health is 0

  set_hunter_order:
    - raises in wrong phase
    - raises on unknown name
    - raises on missing name
    - raises on duplicate
    - stores order and advances to HUNTER_TURN

  start_hunter_turn:
    - raises in wrong phase
    - clears active hunter flashbang
    - resets active hunter path
    - does not clear other hunters' flashbang

  end_hunter_turn:
    - raises in wrong phase
    - clears stun unconditionally
    - clears fatigue when ≤ 2 steps
    - does not clear fatigue when > 2 steps
    - reveals agent identity on first sighting
    - does not re-reveal already-revealed identity
    - advances active_hunter_index to next hunter
    - calls end_round after last hunter
    - returns win condition from check_win

  end_round:
    - increments round_number
    - resets vehicle budget
    - clears vehicle path_this_round
    - resets all hunter paths
    - advances phase to AGENT_TURN

  is_agent_visible_to:
    - returns False for in-vehicle hunter
    - returns False for flashbanged hunter
    - returns False when LOS blocked
    - returns True for clear LOS
"""

import pytest
from pathlib import Path


from backend.board import load_board
from backend.state import (
    AgentState, HunterState, VehicleState, GameState,
    StatusEffect, TurnPhase, WinCondition,
)
from backend.loop import (
    start_agent_turn,
    end_agent_turn,
    set_hunter_order,
    start_hunter_turn,
    end_hunter_turn,
    end_round,
    is_agent_visible_to,
)

RESOURCES = Path(__file__).parent.parent / "backend" / "data" / "resources.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent(position="P20", health=4, public_objectives=None) -> AgentState:
    return AgentState(
        character="cobra",
        position=position,
        health=health,
        max_health=4,
        move_speed=4,
        items=[],
        abilities=[],
        public_objectives=public_objectives or [],
    )


def make_hunter(player_name="h1", position="K17", in_vehicle=True) -> HunterState:
    return HunterState(
        character="gun",
        player_name=player_name,
        position=position,
        move_speed=4,
        in_vehicle=in_vehicle,
    )


def make_vehicle(position="K17", budget=10) -> VehicleState:
    return VehicleState(
        name="tracer",
        position=position,
        move_speed=10,
        move_budget_remaining=budget,
    )


def make_game(
    board_name="Broken Covenant",
    phase=TurnPhase.AGENT_TURN,
    round_number=1,
    hunters=None,
    agent_pos="P20",
    agent_health=4,
    agent_public_objectives=None,
    escape_points=None,
    hunter_order=None,
    active_hunter_index=0,
    vehicle_pos="K17",
    vehicle_budget=10,
):
    if hunters is None:
        hunters = [make_hunter()]
    agent = make_agent(
        position=agent_pos,
        health=agent_health,
        public_objectives=agent_public_objectives or [],
    )
    vehicle = make_vehicle(position=vehicle_pos, budget=vehicle_budget)
    game = GameState(
        board_name=board_name,
        player_count=1 + len(hunters),
        agent=agent,
        hunters=hunters,
        vehicle=vehicle,
        objectives=["B17", "C28", "V22", "M12"],
        objectives_visible=True,
        escape_points=escape_points or ["A3", "M1", "W1"],
        round_number=round_number,
        phase=phase,
        hunter_order=hunter_order or [],
        active_hunter_index=active_hunter_index,
    )
    return game


def get_board(board_name="Broken Covenant"):
    return load_board(board_name, RESOURCES)


# ---------------------------------------------------------------------------
# start_agent_turn
# ---------------------------------------------------------------------------

class TestStartAgentTurn:
    def test_clears_agent_flashbang(self):
        game = make_game()
        board = get_board()
        game.agent.status_effects.add(StatusEffect.FLASHBANGED)
        start_agent_turn(game, board)
        assert StatusEffect.FLASHBANGED not in game.agent.status_effects

    def test_clears_active_obstacles(self):
        game = make_game()
        board = get_board()
        game.active_obstacles = ["D5", "D6"]
        start_agent_turn(game, board)
        assert game.active_obstacles == []

    def test_resets_agent_path(self):
        game = make_game()
        board = get_board()
        game.agent.path_this_turn = ["P20", "P21", "P22"]
        start_agent_turn(game, board)
        assert game.agent.path_this_turn == []

    def test_publishes_pending_objectives(self):
        game = make_game()
        board = get_board()
        game.agent.pending_objectives = ["B17"]
        start_agent_turn(game, board)
        assert "B17" in game.agent.public_objectives
        assert game.agent.pending_objectives == []

    def test_returns_none_mid_game(self):
        game = make_game(round_number=20)
        board = get_board()
        result = start_agent_turn(game, board)
        assert result == WinCondition.NONE

    def test_returns_timeout_when_round_gt_40(self):
        game = make_game(round_number=41)
        board = get_board()
        result = start_agent_turn(game, board)
        assert result == WinCondition.HUNTERS_TIMEOUT
        assert game.phase == TurnPhase.GAME_OVER

    def test_no_timeout_at_round_40(self):
        game = make_game(round_number=40)
        board = get_board()
        result = start_agent_turn(game, board)
        assert result == WinCondition.NONE

    def test_does_not_clear_other_status_effects(self):
        # STUNNED on agent should not be touched by start_agent_turn
        game = make_game()
        board = get_board()
        game.agent.status_effects.add(StatusEffect.STUNNED)
        start_agent_turn(game, board)
        assert StatusEffect.STUNNED in game.agent.status_effects

    def test_sets_phase_to_agent_turn(self):
        game = make_game(phase=TurnPhase.AGENT_TURN)
        board = get_board()
        start_agent_turn(game, board)
        assert game.phase == TurnPhase.AGENT_TURN


# ---------------------------------------------------------------------------
# end_agent_turn
# ---------------------------------------------------------------------------

class TestEndAgentTurn:
    def test_raises_in_wrong_phase(self):
        game = make_game(phase=TurnPhase.HUNTER_TURN)
        board = get_board()
        with pytest.raises(ValueError):
            end_agent_turn(game, board)

    def test_advances_phase_to_hunter_negotiate(self):
        game = make_game(phase=TurnPhase.AGENT_TURN)
        board = get_board()
        end_agent_turn(game, board)
        assert game.phase == TurnPhase.HUNTER_NEGOTIATE

    def test_sets_escaped_flag_when_conditions_met(self):
        game = make_game(
            phase=TurnPhase.AGENT_TURN,
            agent_pos="A3",
            agent_public_objectives=["B17", "C28", "V22"],
            escape_points=["A3", "M1", "W1"],
            hunters=[make_hunter("h1", "K17", in_vehicle=True)],
        )
        board = get_board()
        result = end_agent_turn(game, board)
        assert game.agent_escaped is True
        assert result == WinCondition.AGENT_ESCAPE

    def test_no_escape_with_fewer_than_3_objectives(self):
        game = make_game(
            phase=TurnPhase.AGENT_TURN,
            agent_pos="A3",
            agent_public_objectives=["B17", "C28"],
            escape_points=["A3", "M1", "W1"],
        )
        board = get_board()
        end_agent_turn(game, board)
        assert game.agent_escaped is False

    def test_no_escape_when_not_on_escape_point(self):
        game = make_game(
            phase=TurnPhase.AGENT_TURN,
            agent_pos="P20",
            agent_public_objectives=["B17", "C28", "V22"],
            escape_points=["A3", "M1", "W1"],
        )
        board = get_board()
        end_agent_turn(game, board)
        assert game.agent_escaped is False

    def test_on_board_hunter_blocks_escape(self):
        game = make_game(
            phase=TurnPhase.AGENT_TURN,
            agent_pos="A3",
            agent_public_objectives=["B17", "C28", "V22"],
            escape_points=["A3", "M1", "W1"],
            hunters=[make_hunter("h1", "A3", in_vehicle=False)],
        )
        board = get_board()
        end_agent_turn(game, board)
        assert game.agent_escaped is False

    def test_in_vehicle_hunter_does_not_block_escape(self):
        game = make_game(
            phase=TurnPhase.AGENT_TURN,
            agent_pos="A3",
            agent_public_objectives=["B17", "C28", "V22"],
            escape_points=["A3", "M1", "W1"],
            hunters=[make_hunter("h1", "A3", in_vehicle=True)],
        )
        board = get_board()
        result = end_agent_turn(game, board)
        assert game.agent_escaped is True
        assert result == WinCondition.AGENT_ESCAPE

    def test_returns_hunters_kill_when_agent_health_zero(self):
        game = make_game(phase=TurnPhase.AGENT_TURN, agent_health=0)
        board = get_board()
        result = end_agent_turn(game, board)
        assert result == WinCondition.HUNTERS_KILL


# ---------------------------------------------------------------------------
# set_hunter_order
# ---------------------------------------------------------------------------

class TestSetHunterOrder:
    def test_raises_in_wrong_phase(self):
        game = make_game(phase=TurnPhase.AGENT_TURN)
        with pytest.raises(ValueError):
            set_hunter_order(game, ["h1"])

    def test_raises_on_unknown_name(self):
        game = make_game(
            phase=TurnPhase.HUNTER_NEGOTIATE,
            hunters=[make_hunter("alice")],
        )
        with pytest.raises(ValueError, match="Unknown"):
            set_hunter_order(game, ["alice", "ghost"])

    def test_raises_on_missing_name(self):
        game = make_game(
            phase=TurnPhase.HUNTER_NEGOTIATE,
            hunters=[make_hunter("alice"), make_hunter("bob")],
        )
        with pytest.raises(ValueError, match="Missing"):
            set_hunter_order(game, ["alice"])

    def test_raises_on_duplicate(self):
        game = make_game(
            phase=TurnPhase.HUNTER_NEGOTIATE,
            hunters=[make_hunter("alice"), make_hunter("bob")],
        )
        with pytest.raises(ValueError, match="Duplicate"):
            set_hunter_order(game, ["alice", "alice"])

    def test_stores_order_and_advances_phase(self):
        game = make_game(
            phase=TurnPhase.HUNTER_NEGOTIATE,
            hunters=[make_hunter("alice"), make_hunter("bob")],
        )
        set_hunter_order(game, ["bob", "alice"])
        assert game.hunter_order == ["bob", "alice"]
        assert game.phase == TurnPhase.HUNTER_TURN
        assert game.active_hunter_index == 0

    def test_single_hunter(self):
        game = make_game(
            phase=TurnPhase.HUNTER_NEGOTIATE,
            hunters=[make_hunter("solo")],
        )
        set_hunter_order(game, ["solo"])
        assert game.hunter_order == ["solo"]
        assert game.phase == TurnPhase.HUNTER_TURN


# ---------------------------------------------------------------------------
# start_hunter_turn
# ---------------------------------------------------------------------------

class TestStartHunterTurn:
    def test_raises_in_wrong_phase(self):
        game = make_game(phase=TurnPhase.AGENT_TURN)
        with pytest.raises(ValueError):
            start_hunter_turn(game)

    def test_clears_active_hunter_flashbang(self):
        h = make_hunter("h1")
        h.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
            active_hunter_index=0,
        )
        start_hunter_turn(game)
        assert StatusEffect.FLASHBANGED not in h.status_effects

    def test_resets_active_hunter_path(self):
        h = make_hunter("h1")
        h.path_this_turn = ["K17", "L17"]
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
            active_hunter_index=0,
        )
        start_hunter_turn(game)
        assert h.path_this_turn == []

    def test_does_not_clear_other_hunters_flashbang(self):
        h1 = make_hunter("h1")
        h2 = make_hunter("h2")
        h2.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h1, h2],
            hunter_order=["h1", "h2"],
            active_hunter_index=0,  # h1's turn
        )
        start_hunter_turn(game)
        assert StatusEffect.FLASHBANGED in h2.status_effects

    def test_does_not_clear_stunned(self):
        h = make_hunter("h1")
        h.status_effects.add(StatusEffect.STUNNED)
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
        )
        start_hunter_turn(game)
        assert StatusEffect.STUNNED in h.status_effects


# ---------------------------------------------------------------------------
# end_hunter_turn
# ---------------------------------------------------------------------------

class TestEndHunterTurn:
    def test_raises_in_wrong_phase(self):
        game = make_game(phase=TurnPhase.AGENT_TURN)
        board = get_board()
        with pytest.raises(ValueError):
            end_hunter_turn(game, board)

    def test_clears_stun_unconditionally(self):
        h = make_hunter("h1", in_vehicle=False, position="A1")
        h.status_effects.add(StatusEffect.STUNNED)
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
        )
        board = get_board()
        end_hunter_turn(game, board)
        assert StatusEffect.STUNNED not in h.status_effects

    def test_clears_fatigue_when_le_2_steps(self):
        h = make_hunter("h1", in_vehicle=False, position="A1")
        h.status_effects.add(StatusEffect.FATIGUED)
        h.path_this_turn = ["A1", "A2"]  # 1 step
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
        )
        board = get_board()
        end_hunter_turn(game, board)
        assert StatusEffect.FATIGUED not in h.status_effects

    def test_does_not_clear_fatigue_when_gt_2_steps(self):
        h = make_hunter("h1", in_vehicle=False, position="A1")
        h.status_effects.add(StatusEffect.FATIGUED)
        h.path_this_turn = ["A1", "A2", "A3", "A4"]  # 3 steps
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
        )
        board = get_board()
        end_hunter_turn(game, board)
        assert StatusEffect.FATIGUED in h.status_effects

    def test_exactly_2_steps_clears_fatigue(self):
        h = make_hunter("h1", in_vehicle=False, position="A1")
        h.status_effects.add(StatusEffect.FATIGUED)
        h.path_this_turn = ["A1", "A2", "A3"]  # 2 steps
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
        )
        board = get_board()
        end_hunter_turn(game, board)
        assert StatusEffect.FATIGUED not in h.status_effects

    def test_reveals_agent_identity_on_first_sighting(self):
        # Hunter on same column as agent with clear LOS
        h = make_hunter("h1", position="P8", in_vehicle=False)
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
            agent_pos="P20",
        )
        board = get_board()
        assert game.agent.identity_revealed is False
        end_hunter_turn(game, board)
        # P8 → P20: check if LOS clear on Broken Covenant
        # N6–N9 are road cells with no walls between — LOS is clear
        assert game.agent.identity_revealed is True

    def test_does_not_re_reveal_identity(self):
        h = make_hunter("h1", position="P8", in_vehicle=False)
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
            agent_pos="P20",
        )
        game.agent.identity_revealed = True
        board = get_board()
        end_hunter_turn(game, board)
        assert game.agent.identity_revealed is True  # unchanged, no error

    def test_advances_index_to_next_hunter(self):
        h1 = make_hunter("h1", in_vehicle=False, position="A1")
        h2 = make_hunter("h2", in_vehicle=False, position="A1")
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h1, h2],
            hunter_order=["h1", "h2"],
            active_hunter_index=0,
        )
        board = get_board()
        end_hunter_turn(game, board)
        assert game.active_hunter_index == 1
        assert game.phase == TurnPhase.HUNTER_TURN

    def test_calls_end_round_after_last_hunter(self):
        h1 = make_hunter("h1", in_vehicle=False, position="A1")
        h2 = make_hunter("h2", in_vehicle=False, position="A1")
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h1, h2],
            hunter_order=["h1", "h2"],
            active_hunter_index=1,  # h2 is last
            round_number=5,
        )
        board = get_board()
        end_hunter_turn(game, board)
        assert game.round_number == 6
        assert game.phase == TurnPhase.AGENT_TURN

    def test_returns_hunters_kill_when_agent_dead(self):
        h = make_hunter("h1", in_vehicle=False, position="A1")
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
            agent_health=0,
        )
        board = get_board()
        result = end_hunter_turn(game, board)
        assert result == WinCondition.HUNTERS_KILL

    def test_returns_none_mid_game(self):
        h = make_hunter("h1", in_vehicle=False, position="A1")
        game = make_game(
            phase=TurnPhase.HUNTER_TURN,
            hunters=[h],
            hunter_order=["h1"],
        )
        board = get_board()
        result = end_hunter_turn(game, board)
        assert result == WinCondition.NONE


# ---------------------------------------------------------------------------
# end_round
# ---------------------------------------------------------------------------

class TestEndRound:
    def test_increments_round_number(self):
        game = make_game(round_number=5)
        end_round(game)
        assert game.round_number == 6

    def test_resets_vehicle_budget(self):
        game = make_game(vehicle_budget=3)
        end_round(game)
        assert game.vehicle.move_budget_remaining == 10  # reset to move_speed

    def test_clears_vehicle_path(self):
        game = make_game()
        game.vehicle.path_this_round = ["K17", "L17", "L16"]
        end_round(game)
        assert game.vehicle.path_this_round == []

    def test_resets_all_hunter_paths(self):
        h1 = make_hunter("h1")
        h2 = make_hunter("h2")
        h1.path_this_turn = ["A1", "A2"]
        h2.path_this_turn = ["B1", "B2"]
        game = make_game(hunters=[h1, h2])
        end_round(game)
        assert h1.path_this_turn == []
        assert h2.path_this_turn == []

    def test_advances_phase_to_agent_turn(self):
        game = make_game(phase=TurnPhase.HUNTER_TURN)
        end_round(game)
        assert game.phase == TurnPhase.AGENT_TURN


# ---------------------------------------------------------------------------
# is_agent_visible_to
# ---------------------------------------------------------------------------

class TestIsAgentVisibleTo:
    def test_false_for_in_vehicle_hunter(self):
        h = make_hunter("h1", position="P8", in_vehicle=True)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()
        assert is_agent_visible_to(h, game, board) is False

    def test_false_for_flashbanged_hunter(self):
        h = make_hunter("h1", position="P8", in_vehicle=False)
        h.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()
        assert is_agent_visible_to(h, game, board) is False

    def test_false_when_los_blocked_by_obstacle(self):
        h = make_hunter("h1", position="P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.active_obstacles = ["P13"]  # blocks P8→P20
        board = get_board()
        assert is_agent_visible_to(h, game, board) is False

    def test_true_for_clear_los(self):
        # P8 → P20: road cells P9–P19, no walls on Broken Covenant
        h = make_hunter("h1", position="P8", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        board = get_board()
        assert is_agent_visible_to(h, game, board) is True

    def test_false_when_wall_blocks_los(self):
        # Use Shadow of Babel where A2 is a wall — blocks A1 → A3
        h = make_hunter("h1", position="A1", in_vehicle=False)
        game = make_game(
            board_name="Shadow of Babel",
            hunters=[h],
            agent_pos="A3",
        )
        board = load_board("Shadow of Babel", RESOURCES)
        assert "A2" in board.walls
        assert is_agent_visible_to(h, game, board) is False


# ---------------------------------------------------------------------------
# is_agent_visible_to — stealth field
# ---------------------------------------------------------------------------

class TestIsAgentVisibleToStealthField:
    def test_stealth_field_hides_agent_beyond_2_spaces(self):
        # Hunter at A1, agent at P20 (far away); stealth field active → not visible
        h = make_hunter("h1", position="A1", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.agent.stealth_field_active = True
        board = get_board()
        assert is_agent_visible_to(h, game, board) is False

    def test_stealth_field_reveals_agent_within_2_spaces(self):
        # Hunter at P19, agent at P20 (chebyshev 1); stealth field active → still visible
        h = make_hunter("h1", position="P19", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.agent.stealth_field_active = True
        board = get_board()
        assert is_agent_visible_to(h, game, board) is True

    def test_stealth_field_off_uses_normal_los(self):
        # No stealth field; same positions as above should still see agent
        h = make_hunter("h1", position="P19", in_vehicle=False)
        game = make_game(hunters=[h], agent_pos="P20")
        game.agent.stealth_field_active = False
        board = get_board()
        assert is_agent_visible_to(h, game, board) is True


# ---------------------------------------------------------------------------
# start_agent_turn — phase 5/6 flag resets
# ---------------------------------------------------------------------------

class TestStartAgentTurnFlagResets:
    def _game_with_flags(self):
        game = make_game(phase=TurnPhase.HUNTER_TURN)
        game.agent.stealth_field_active = True
        game.agent.pulse_blades_armed = True
        game.agent.quick_draw_triggered_this_turn = True
        game.agent.blade_strike_used_this_turn = True
        game.vehicle.emp_disabled = True
        return game

    def test_clears_stealth_field_active(self):
        game = self._game_with_flags()
        start_agent_turn(game, get_board())
        assert game.agent.stealth_field_active is False

    def test_clears_pulse_blades_armed(self):
        game = self._game_with_flags()
        start_agent_turn(game, get_board())
        assert game.agent.pulse_blades_armed is False

    def test_clears_quick_draw_triggered(self):
        game = self._game_with_flags()
        start_agent_turn(game, get_board())
        assert game.agent.quick_draw_triggered_this_turn is False

    def test_clears_blade_strike_used(self):
        game = self._game_with_flags()
        start_agent_turn(game, get_board())
        assert game.agent.blade_strike_used_this_turn is False

    def test_clears_emp_disabled(self):
        game = self._game_with_flags()
        start_agent_turn(game, get_board())
        assert game.vehicle.emp_disabled is False

    def test_clears_fatigued_when_last_turn_steps_le_2(self):
        game = make_game(phase=TurnPhase.HUNTER_TURN)
        game.agent.status_effects.add(StatusEffect.FATIGUED)
        game.agent.last_turn_steps = 2
        start_agent_turn(game, get_board())
        assert StatusEffect.FATIGUED not in game.agent.status_effects

    def test_keeps_fatigued_when_last_turn_steps_gt_2(self):
        game = make_game(phase=TurnPhase.HUNTER_TURN)
        game.agent.status_effects.add(StatusEffect.FATIGUED)
        game.agent.last_turn_steps = 3
        start_agent_turn(game, get_board())
        assert StatusEffect.FATIGUED in game.agent.status_effects


# ---------------------------------------------------------------------------
# end_agent_turn — smoke dagger cleanup
# ---------------------------------------------------------------------------

class TestEndAgentTurnSmokeDagger:
    def test_clears_flashbang_from_smoke_dagger_target(self):
        h = make_hunter("h1", position="P19", in_vehicle=False)
        h.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(hunters=[h], agent_pos="P20")
        game.smoke_dagger_targets = ["h1"]
        board = get_board()
        end_agent_turn(game, board)
        assert StatusEffect.FLASHBANGED not in h.status_effects

    def test_clears_smoke_dagger_targets_list(self):
        h = make_hunter("h1", position="P19", in_vehicle=False)
        h.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(hunters=[h], agent_pos="P20")
        game.smoke_dagger_targets = ["h1"]
        board = get_board()
        end_agent_turn(game, board)
        assert game.smoke_dagger_targets == []

    def test_does_not_clear_flashbang_from_non_target(self):
        h1 = make_hunter("h1", position="P19", in_vehicle=False)
        h2 = make_hunter("h2", position="P18", in_vehicle=False)
        h1.status_effects.add(StatusEffect.FLASHBANGED)
        h2.status_effects.add(StatusEffect.FLASHBANGED)
        game = make_game(hunters=[h1, h2], agent_pos="P20")
        game.smoke_dagger_targets = ["h1"]  # only h1 was smoke-daggered
        board = get_board()
        end_agent_turn(game, board)
        assert StatusEffect.FLASHBANGED not in h1.status_effects
        assert StatusEffect.FLASHBANGED in h2.status_effects