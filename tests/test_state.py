"""
test_state.py — Tests for state.py dataclasses and status effect logic.

state.py is pure data. These tests verify:
  - Dataclasses construct with correct defaults
  - Status effect set membership and clearing
  - GameState helpers (is_over, current_hunter)
  - AgentState.completed_objectives_count
  - HunterState.in_vehicle default and semantics
"""

import pytest
from pathlib import Path


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
# Helpers
# ---------------------------------------------------------------------------

def make_agent(**kwargs) -> AgentState:
    defaults = dict(
        character="cobra",
        position="P10",
        health=4,
        max_health=4,
        move_speed=4,
        items=[],
        abilities=[],
    )
    defaults.update(kwargs)
    return AgentState(**defaults)


def make_hunter(player_name="h1", **kwargs) -> HunterState:
    defaults = dict(
        character="gun",
        player_name=player_name,
        position="K17",
        move_speed=4,
        in_vehicle=True,
    )
    defaults.update(kwargs)
    return HunterState(**defaults)


def make_vehicle(**kwargs) -> VehicleState:
    defaults = dict(
        name="tracer",
        position="K17",
        move_speed=10,
        move_budget_remaining=10,
    )
    defaults.update(kwargs)
    return VehicleState(**defaults)


def make_game(**kwargs) -> GameState:
    defaults = dict(
        board_name="Broken Covenant",
        player_count=2,
        agent=make_agent(),
        hunters=[make_hunter()],
        vehicle=make_vehicle(),
        objectives=["B17", "C28", "V22", "M12"],
        objectives_visible=True,
        escape_points=["A3", "M1", "W1"],
    )
    defaults.update(kwargs)
    return GameState(**defaults)


# ---------------------------------------------------------------------------
# AgentState
# ---------------------------------------------------------------------------

class TestAgentState:
    def test_default_status_effects_empty(self):
        assert len(make_agent().status_effects) == 0

    def test_identity_hidden_by_default(self):
        assert make_agent().identity_revealed is False

    def test_traitor_false_by_default(self):
        assert make_agent().is_traitor is False

    def test_last_seen_none_by_default(self):
        assert make_agent().last_seen_cell is None

    def test_path_empty_by_default(self):
        assert make_agent().path_this_turn == []

    def test_completed_count_empty(self):
        assert make_agent().completed_objectives_count == 0

    def test_completed_count_public_only(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives"), "AgentState missing field: public_objectives"
        assert hasattr(agent, "pending_objectives"), "AgentState missing field: pending_objectives"
        agent.public_objectives = ["B17", "C28"]
        assert agent.completed_objectives_count == 2

    def test_completed_count_pending_only(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives"), "AgentState missing field: public_objectives"
        assert hasattr(agent, "pending_objectives"), "AgentState missing field: pending_objectives"
        agent.pending_objectives = ["V22"]
        assert agent.completed_objectives_count == 1

    def test_completed_count_both(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives"), "AgentState missing field: public_objectives"
        assert hasattr(agent, "pending_objectives"), "AgentState missing field: pending_objectives"
        agent.public_objectives = ["B17", "C28"]
        agent.pending_objectives = ["V22"]
        assert agent.completed_objectives_count == 3

    def test_multiple_status_effects(self):
        agent = make_agent()
        agent.status_effects.add(StatusEffect.STUNNED)
        agent.status_effects.add(StatusEffect.FLASHBANGED)
        assert len(agent.status_effects) == 2


# ---------------------------------------------------------------------------
# HunterState
# ---------------------------------------------------------------------------

class TestHunterState:
    def test_in_vehicle_can_be_false(self):
        hunter = make_hunter(in_vehicle=False)
        assert hunter.in_vehicle is False

    def test_default_status_empty(self):
        assert len(make_hunter().status_effects) == 0

    def test_in_vehicle_hunter_can_still_hold_status(self):
        # state.py doesn't enforce "can't stun in vehicle" — engine does
        hunter = make_hunter(in_vehicle=True)
        hunter.status_effects.add(StatusEffect.STUNNED)
        assert StatusEffect.STUNNED in hunter.status_effects


# ---------------------------------------------------------------------------
# VehicleState
# ---------------------------------------------------------------------------

class TestVehicleState:
    def test_default_unoccupied(self):
        assert make_vehicle().occupied_by is None

    def test_path_empty_by_default(self):
        assert make_vehicle().path_this_round == []


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------

class TestGameState:
    def test_is_over_false_by_default(self):
        assert make_game().is_over is False

    def test_is_over_true_on_win(self):
        game = make_game()
        game.win_condition = WinCondition.AGENT_ESCAPE
        assert game.is_over is True

    def test_agent_escaped_false_by_default(self):
        assert make_game().agent_escaped is False

    def test_current_hunter_none_during_agent_turn(self):
        game = make_game()
        game.phase = TurnPhase.AGENT_TURN
        assert game.current_hunter is None

    def test_current_hunter_none_when_no_order(self):
        game = make_game()
        game.phase = TurnPhase.HUNTER_TURN
        game.hunter_order = []
        assert game.current_hunter is None

    def test_current_hunter_by_order(self):
        h1 = make_hunter("alice")
        h2 = make_hunter("bob")
        game = make_game(hunters=[h1, h2])
        game.phase = TurnPhase.HUNTER_TURN
        game.hunter_order = ["bob", "alice"]
        game.active_hunter_index = 0
        assert game.current_hunter.player_name == "bob"

    def test_current_hunter_advances_with_index(self):
        h1 = make_hunter("alice")
        h2 = make_hunter("bob")
        game = make_game(hunters=[h1, h2])
        game.phase = TurnPhase.HUNTER_TURN
        game.hunter_order = ["bob", "alice"]
        game.active_hunter_index = 1
        assert game.current_hunter.player_name == "alice"

    def test_active_obstacles_default_empty(self):
        assert make_game().active_obstacles == []

    def test_active_barriers_default_empty(self):
        assert make_game().active_barriers == []


# ---------------------------------------------------------------------------
# ItemState
# ---------------------------------------------------------------------------

class TestItemState:
    def test_construct(self):
        item = ItemState(key="flash_bang", name="Flash Bang", charges=1)
        assert item.charges == 1
        assert item.tapped is False


# ---------------------------------------------------------------------------
# AgentState — field existence
# ---------------------------------------------------------------------------

class TestAgentStateFields:
    def test_has_pending_objectives_field(self):
        agent = make_agent()
        assert hasattr(agent, "pending_objectives"), "AgentState missing: pending_objectives"
        assert isinstance(agent.pending_objectives, list)

    def test_has_public_objectives_field(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives"), "AgentState missing: public_objectives"
        assert isinstance(agent.public_objectives, list)


# ---------------------------------------------------------------------------
# AgentState.completed_objectives_count
# ---------------------------------------------------------------------------

class TestCompletedObjectivesCount:
    def test_empty(self):
        assert make_agent().completed_objectives_count == 0

    def test_public_only(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives")
        assert hasattr(agent, "pending_objectives")
        agent.public_objectives = ["B17", "C28"]
        assert agent.completed_objectives_count == 2

    def test_pending_only(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives")
        assert hasattr(agent, "pending_objectives")
        agent.pending_objectives = ["V22"]
        assert agent.completed_objectives_count == 1

    def test_both(self):
        agent = make_agent()
        assert hasattr(agent, "public_objectives")
        assert hasattr(agent, "pending_objectives")
        agent.public_objectives = ["B17", "C28"]
        agent.pending_objectives = ["V22"]
        assert agent.completed_objectives_count == 3

    def test_does_not_double_count(self):
        # Same cell in both lists should count twice — these are separate lists,
        # not a set. If that's wrong, this test will catch it when dedup logic
        # is added.
        agent = make_agent()
        agent.public_objectives = ["B17"]
        agent.pending_objectives = ["B17"]
        assert agent.completed_objectives_count == 2


# ---------------------------------------------------------------------------
# HunterState — defaults from dataclass (not make_hunter helper)
# ---------------------------------------------------------------------------

class TestHunterStateDefaults:
    def test_in_vehicle_false_by_default(self):
        # Construct directly, bypassing make_hunter which sets in_vehicle=True
        h = HunterState(
            character="gun",
            player_name="p1",
            position="K17",
            move_speed=4,
        )
        assert h.in_vehicle is False


# ---------------------------------------------------------------------------
# GameState.is_over
# ---------------------------------------------------------------------------

class TestIsOver:
    def test_false_when_none(self):
        assert make_game().win_condition == WinCondition.NONE
        assert make_game().is_over is False

    def test_true_for_agent_escape(self):
        game = make_game()
        game.win_condition = WinCondition.AGENT_ESCAPE
        assert game.is_over is True

    def test_true_for_hunters_kill(self):
        game = make_game()
        game.win_condition = WinCondition.HUNTERS_KILL
        assert game.is_over is True

    def test_true_for_hunters_timeout(self):
        game = make_game()
        game.win_condition = WinCondition.HUNTERS_TIMEOUT
        assert game.is_over is True


# ---------------------------------------------------------------------------
# GameState.current_hunter
# ---------------------------------------------------------------------------

class TestCurrentHunter:
    def test_returns_none_out_of_bounds_index(self):
        h1 = make_hunter("alice")
        game = make_game(hunters=[h1])
        game.phase = TurnPhase.HUNTER_TURN
        game.hunter_order = ["alice"]
        game.active_hunter_index = 5  # out of bounds
        assert game.current_hunter is None

    def test_returns_none_for_unknown_player_name(self):
        h1 = make_hunter("alice")
        game = make_game(hunters=[h1])
        game.phase = TurnPhase.HUNTER_TURN
        game.hunter_order = ["bob"]  # not in hunters list
        game.active_hunter_index = 0
        assert game.current_hunter is None

    def test_returns_none_during_negotiate_phase(self):
        h1 = make_hunter("alice")
        game = make_game(hunters=[h1])
        game.phase = TurnPhase.HUNTER_NEGOTIATE
        game.hunter_order = ["alice"]
        game.active_hunter_index = 0
        assert game.current_hunter is None

    def test_returns_none_during_setup(self):
        game = make_game()
        game.phase = TurnPhase.SETUP
        assert game.current_hunter is None