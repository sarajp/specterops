"""
test_items.py — Tests for apply_item, can_use_item, can_use_agent_ability,
                and apply_agent_ability in engine.py.

Covers every item key that has logic in apply_item, plus the Dash agent ability.
Items requiring board LOS (flash_bang, tangle_line) use a real board so actual
LOS geometry is exercised.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from backend.board import load_board
from backend.state import (
    AgentState, HunterState, VehicleState, GameState,
    ItemState, StatusEffect, TurnPhase, WinCondition,
)
from backend.engine import (
    apply_item,
    can_use_item,
    can_use_agent_ability,
    apply_agent_ability,
)

RESOURCES = Path(__file__).parent.parent / "backend" / "data" / "resources.json"

# ---------------------------------------------------------------------------
# Raw item_def dicts (mirroring resources.json)
# ---------------------------------------------------------------------------

ITEM_DEFS = {
    "adrenal_surge":      {"tap": "True",  "charges": 1, "range": 6},
    "med_kit":            {"tap": "False", "charges": 1, "range": 0},
    "remote_trigger":     {"tap": "False", "charges": 1, "range": 0},
    "flash_bang":         {"tap": "False", "charges": 1, "range": 4},
    "smoke_grenade":      {"tap": "False", "charges": 1, "range": 4},
    "concussion_grenade": {"tap": "False", "charges": 1, "range": 4},
    "emp_grenade":        {"tap": "False", "charges": 2, "range": 4},
    "power_fists":        {"tap": "True",  "charges": 2, "range": 2},
    "holo_decoy":         {"tap": "False", "charges": 1, "range": 4},
    "smoke_dagger":       {"tap": "True",  "charges": 2, "range": 4},
    "stealth_field":      {"tap": "True",  "charges": 1, "range": 2},
    "proximity_mine":     {"tap": "False", "charges": 1, "range": 2},
    "pulse_blades":       {"tap": "True",  "charges": 2, "range": 0},
    "tangle_line":        {"tap": "True",  "charges": 2, "range": 99},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_item(key: str, charges: int = 1, tapped: bool = False) -> ItemState:
    names = {
        "adrenal_surge": "Adrenal Surge", "med_kit": "Med Kit",
        "remote_trigger": "Remote Trigger", "flash_bang": "Flash Bang",
        "smoke_grenade": "Smoke Grenade", "concussion_grenade": "Concussion Grenade",
        "emp_grenade": "EMP Grenade", "power_fists": "Power Fists",
        "holo_decoy": "Holo Decoy", "smoke_dagger": "Smoke Dagger",
        "stealth_field": "Stealth Field", "proximity_mine": "Proximity Mine",
        "pulse_blades": "Pulse Blades", "tangle_line": "Tangle Line",
    }
    return ItemState(key=key, name=names.get(key, key), charges=charges, tapped=tapped)


def make_agent(position="P10", character="cobra", items=None, abilities=None, health=4) -> AgentState:
    return AgentState(
        character=character,
        position=position,
        health=health,
        max_health=4,
        move_speed=4,
        items=items or [],
        abilities=abilities or [],
    )


def make_hunter(player_name="h1", position="A1", in_vehicle=False, character="puppet") -> HunterState:
    return HunterState(
        character=character,
        player_name=player_name,
        position=position,
        move_speed=4,
        in_vehicle=in_vehicle,
    )


def make_vehicle(position="K17") -> VehicleState:
    return VehicleState(name="tracer", position=position, move_speed=10, move_budget_remaining=10)


def make_game(agent_pos="P10", agent_char="cobra", items=None, hunters=None,
              vehicle_pos="K17", abilities=None, agent_health=4) -> GameState:
    agent = make_agent(position=agent_pos, character=agent_char,
                       items=items or [], abilities=abilities or [],
                       health=agent_health)
    h_list = hunters if hunters is not None else [make_hunter()]
    return GameState(
        board_name="Broken Covenant",
        player_count=2,
        agent=agent,
        hunters=h_list,
        vehicle=make_vehicle(vehicle_pos),
        objectives=["B17", "C28", "V22", "M12"],
        objectives_visible=True,
        escape_points=["A3", "M1", "W1"],
        phase=TurnPhase.AGENT_TURN,
    )


def get_board(name="Broken Covenant"):
    return load_board(name, RESOURCES)


# ---------------------------------------------------------------------------
# can_use_item
# ---------------------------------------------------------------------------

class TestCanUseItem:
    def test_wrong_phase_returns_false(self):
        game = make_game(items=[make_item("flash_bang")])
        game.phase = TurnPhase.HUNTER_TURN
        ok, _ = can_use_item(game, "flash_bang")
        assert not ok

    def test_already_used_returns_false(self):
        game = make_game(items=[make_item("flash_bang")])
        game.agent.item_used_this_turn = True
        ok, _ = can_use_item(game, "flash_bang")
        assert not ok

    def test_item_not_in_inventory_returns_false(self):
        game = make_game(items=[])
        ok, _ = can_use_item(game, "flash_bang")
        assert not ok

    def test_tapped_item_returns_false(self):
        game = make_game(items=[make_item("adrenal_surge", tapped=True)])
        ok, _ = can_use_item(game, "adrenal_surge")
        assert not ok

    def test_zero_charges_returns_false(self):
        game = make_game(items=[make_item("flash_bang", charges=0)])
        ok, _ = can_use_item(game, "flash_bang")
        assert not ok

    def test_proximity_mine_zero_charges_allowed(self):
        # Proximity mine skips charge check (conditional consumption)
        game = make_game(items=[make_item("proximity_mine", charges=0)])
        ok, _ = can_use_item(game, "proximity_mine")
        assert ok

    def test_pulse_blades_zero_charges_allowed(self):
        game = make_game(items=[make_item("pulse_blades", charges=0)])
        ok, _ = can_use_item(game, "pulse_blades")
        assert ok

    def test_med_kit_after_move_returns_false(self):
        game = make_game(items=[make_item("med_kit")])
        game.agent.path_this_turn = ["P10", "P11"]
        ok, reason = can_use_item(game, "med_kit")
        assert not ok
        assert "before moving" in reason

    def test_med_kit_before_move_returns_true(self):
        game = make_game(items=[make_item("med_kit")])
        game.agent.path_this_turn = ["P10"]  # only starting cell, no movement
        ok, _ = can_use_item(game, "med_kit")
        assert ok

    def test_valid_item_returns_true(self):
        game = make_game(items=[make_item("flash_bang")])
        ok, _ = can_use_item(game, "flash_bang")
        assert ok


# ---------------------------------------------------------------------------
# apply_item — adrenal_surge
# ---------------------------------------------------------------------------

class TestAdrenalSurge:
    def test_sets_move_speed_6(self):
        game = make_game(items=[make_item("adrenal_surge")])
        apply_item(game, "adrenal_surge", ITEM_DEFS["adrenal_surge"])
        assert game.agent.move_speed == 6

    def test_taps_item(self):
        game = make_game(items=[make_item("adrenal_surge")])
        apply_item(game, "adrenal_surge", ITEM_DEFS["adrenal_surge"])
        assert game.agent.items[0].tapped is True

    def test_marks_item_used(self):
        game = make_game(items=[make_item("adrenal_surge")])
        apply_item(game, "adrenal_surge", ITEM_DEFS["adrenal_surge"])
        assert game.agent.item_used_this_turn is True

    def test_returns_movement_boosted(self):
        game = make_game(items=[make_item("adrenal_surge")])
        result = apply_item(game, "adrenal_surge", ITEM_DEFS["adrenal_surge"])
        assert result["effect"] == "movement_boosted"
        assert result["move_speed"] == 6


# ---------------------------------------------------------------------------
# apply_item — med_kit
# ---------------------------------------------------------------------------

class TestMedKit:
    def test_restores_health(self):
        game = make_game(items=[make_item("med_kit")], agent_health=3)
        apply_item(game, "med_kit", ITEM_DEFS["med_kit"])
        assert game.agent.health == 4

    def test_sets_move_speed_2(self):
        game = make_game(items=[make_item("med_kit")])
        apply_item(game, "med_kit", ITEM_DEFS["med_kit"])
        assert game.agent.move_speed == 2

    def test_consumes_charge(self):
        game = make_game(items=[make_item("med_kit", charges=1)])
        apply_item(game, "med_kit", ITEM_DEFS["med_kit"])
        assert game.agent.items[0].charges == 0

    def test_returns_healed(self):
        game = make_game(items=[make_item("med_kit")], agent_health=3)
        result = apply_item(game, "med_kit", ITEM_DEFS["med_kit"])
        assert result["effect"] == "healed"


# ---------------------------------------------------------------------------
# apply_item — remote_trigger
# ---------------------------------------------------------------------------

class TestRemoteTrigger:
    def test_arms_remote_trigger(self):
        game = make_game(items=[make_item("remote_trigger")])
        apply_item(game, "remote_trigger", ITEM_DEFS["remote_trigger"])
        assert game.agent.remote_trigger_active is True

    def test_consumes_charge(self):
        game = make_game(items=[make_item("remote_trigger", charges=1)])
        apply_item(game, "remote_trigger", ITEM_DEFS["remote_trigger"])
        assert game.agent.items[0].charges == 0


# ---------------------------------------------------------------------------
# apply_item — flash_bang
# ---------------------------------------------------------------------------

class TestFlashBang:
    def _game_with_hunters(self, agent_pos, *hunter_positions):
        hunters = [make_hunter(f"h{i}", pos) for i, pos in enumerate(hunter_positions)]
        return make_game(agent_pos=agent_pos, items=[make_item("flash_bang")], hunters=hunters)

    def test_flashbangs_hunter_in_los(self):
        # Agent P10, flash bang at P12, hunter P12 — same cell as token, LOS trivially clear
        game = self._game_with_hunters("P10", "P12")
        board = get_board()
        apply_item(game, "flash_bang", ITEM_DEFS["flash_bang"],
                   board=board, target_cell="P12")
        assert StatusEffect.FLASHBANGED in game.hunters[0].status_effects

    def test_does_not_flashbang_hunter_out_of_los(self):
        # Put flash_bang token somewhere the hunter can't see (blocked by structure)
        # The engine checks LOS from hunter_pos to target_cell.
        # Use a real board with a structure between hunter and token.
        # P10 (agent), flash bang at R10, hunter at A1 (far corner — no clear LOS to R10)
        game = self._game_with_hunters("P10", "A1")
        board = get_board()
        apply_item(game, "flash_bang", ITEM_DEFS["flash_bang"],
                   board=board, target_cell="P12")
        # A1 → P12: long distance with structures in the way; hunter should NOT be flashbanged
        assert StatusEffect.FLASHBANGED not in game.hunters[0].status_effects

    def test_consumes_charge(self):
        game = self._game_with_hunters("P10", "P12")
        board = get_board()
        apply_item(game, "flash_bang", ITEM_DEFS["flash_bang"],
                   board=board, target_cell="P12")
        assert game.agent.items[0].charges == 0

    def test_raises_when_target_out_of_range(self):
        game = make_game(agent_pos="A1", items=[make_item("flash_bang")])
        board = get_board()
        with pytest.raises(ValueError, match="out of range"):
            apply_item(game, "flash_bang", ITEM_DEFS["flash_bang"],
                       board=board, target_cell="W32")

    def test_raises_without_target_cell(self):
        game = make_game(items=[make_item("flash_bang")])
        with pytest.raises(ValueError):
            apply_item(game, "flash_bang", ITEM_DEFS["flash_bang"])


# ---------------------------------------------------------------------------
# apply_item — smoke_grenade
# ---------------------------------------------------------------------------

class TestSmokeGrenade:
    def test_adds_target_cell_to_obstacles(self):
        game = make_game(agent_pos="P10", items=[make_item("smoke_grenade")])
        apply_item(game, "smoke_grenade", ITEM_DEFS["smoke_grenade"], target_cell="P12")
        assert "P12" in game.active_obstacles

    def test_adds_neighbors_to_obstacles(self):
        game = make_game(agent_pos="P10", items=[make_item("smoke_grenade")])
        apply_item(game, "smoke_grenade", ITEM_DEFS["smoke_grenade"], target_cell="P12")
        # Must have more than just the center cell
        assert len(game.active_obstacles) > 1

    def test_no_duplicates_if_already_an_obstacle(self):
        game = make_game(agent_pos="P10", items=[make_item("smoke_grenade")])
        game.active_obstacles.append("P12")
        apply_item(game, "smoke_grenade", ITEM_DEFS["smoke_grenade"], target_cell="P12")
        assert game.active_obstacles.count("P12") == 1

    def test_consumes_charge(self):
        game = make_game(agent_pos="P10", items=[make_item("smoke_grenade")])
        apply_item(game, "smoke_grenade", ITEM_DEFS["smoke_grenade"], target_cell="P12")
        assert game.agent.items[0].charges == 0

    def test_raises_out_of_range(self):
        game = make_game(agent_pos="A1", items=[make_item("smoke_grenade")])
        with pytest.raises(ValueError, match="out of range"):
            apply_item(game, "smoke_grenade", ITEM_DEFS["smoke_grenade"], target_cell="W32")


# ---------------------------------------------------------------------------
# apply_item — concussion_grenade
# ---------------------------------------------------------------------------

class TestConcussionGrenade:
    def test_stuns_hunter_adjacent_to_target_on_low_roll(self):
        # Hunter at P12, target at P12 (distance 0 = adjacent), roll ≤4 → stun
        hunter = make_hunter("h1", "P12")
        game = make_game(agent_pos="P10", items=[make_item("concussion_grenade")], hunters=[hunter])
        with patch("backend.engine.random.randint", return_value=3):
            apply_item(game, "concussion_grenade", ITEM_DEFS["concussion_grenade"], target_cell="P12")
        assert StatusEffect.STUNNED in game.hunters[0].status_effects

    def test_does_not_stun_on_high_roll(self):
        hunter = make_hunter("h1", "P12")
        game = make_game(agent_pos="P10", items=[make_item("concussion_grenade")], hunters=[hunter])
        with patch("backend.engine.random.randint", return_value=5):
            apply_item(game, "concussion_grenade", ITEM_DEFS["concussion_grenade"], target_cell="P12")
        assert StatusEffect.STUNNED not in game.hunters[0].status_effects

    def test_ignores_hunter_out_of_blast_radius(self):
        # Hunter at A1, far from P12 — chebyshev > 1
        hunter = make_hunter("h1", "A1")
        game = make_game(agent_pos="P10", items=[make_item("concussion_grenade")], hunters=[hunter])
        with patch("backend.engine.random.randint", return_value=1):
            apply_item(game, "concussion_grenade", ITEM_DEFS["concussion_grenade"], target_cell="P12")
        assert StatusEffect.STUNNED not in game.hunters[0].status_effects

    def test_consumes_charge(self):
        hunter = make_hunter("h1", "P12")
        game = make_game(agent_pos="P10", items=[make_item("concussion_grenade")], hunters=[hunter])
        with patch("backend.engine.random.randint", return_value=1):
            apply_item(game, "concussion_grenade", ITEM_DEFS["concussion_grenade"], target_cell="P12")
        assert game.agent.items[0].charges == 0


# ---------------------------------------------------------------------------
# apply_item — emp_grenade
# ---------------------------------------------------------------------------

class TestEmpGrenade:
    def test_disables_vehicle(self):
        # Vehicle at P12, agent at P10 — within range 4
        game = make_game(agent_pos="P10", items=[make_item("emp_grenade")], vehicle_pos="P12")
        apply_item(game, "emp_grenade", ITEM_DEFS["emp_grenade"])
        assert game.vehicle.emp_disabled is True

    def test_consumes_charge(self):
        game = make_game(agent_pos="P10", items=[make_item("emp_grenade", charges=2)], vehicle_pos="P12")
        apply_item(game, "emp_grenade", ITEM_DEFS["emp_grenade"])
        assert game.agent.items[0].charges == 1

    def test_raises_when_vehicle_out_of_range(self):
        game = make_game(agent_pos="A1", items=[make_item("emp_grenade")], vehicle_pos="W32")
        with pytest.raises(ValueError, match="spaces away"):
            apply_item(game, "emp_grenade", ITEM_DEFS["emp_grenade"])


# ---------------------------------------------------------------------------
# apply_item — power_fists
# ---------------------------------------------------------------------------

class TestPowerFists:
    def test_stuns_hunter_within_2(self):
        hunter = make_hunter("h1", "P11")  # 1 space from P10
        game = make_game(agent_pos="P10", items=[make_item("power_fists")], hunters=[hunter])
        apply_item(game, "power_fists", ITEM_DEFS["power_fists"])
        assert StatusEffect.STUNNED in game.hunters[0].status_effects

    def test_does_not_stun_hunter_beyond_2(self):
        hunter = make_hunter("h1", "P14")  # 4 spaces from P10
        game = make_game(agent_pos="P10", items=[make_item("power_fists")], hunters=[hunter])
        apply_item(game, "power_fists", ITEM_DEFS["power_fists"])
        assert StatusEffect.STUNNED not in game.hunters[0].status_effects

    def test_taps_item(self):
        hunter = make_hunter("h1", "P11")
        game = make_game(agent_pos="P10", items=[make_item("power_fists", charges=2)], hunters=[hunter])
        apply_item(game, "power_fists", ITEM_DEFS["power_fists"])
        assert game.agent.items[0].tapped is True

    def test_returns_stunned_list(self):
        hunter = make_hunter("h1", "P11")
        game = make_game(agent_pos="P10", items=[make_item("power_fists")], hunters=[hunter])
        result = apply_item(game, "power_fists", ITEM_DEFS["power_fists"])
        assert result["effect"] == "power_fists"
        assert "h1" in result["stunned"]


# ---------------------------------------------------------------------------
# apply_item — holo_decoy
# ---------------------------------------------------------------------------

class TestHoloDecoy:
    def test_sets_holo_decoy_cell(self):
        game = make_game(agent_pos="P10", items=[make_item("holo_decoy")])
        apply_item(game, "holo_decoy", ITEM_DEFS["holo_decoy"], target_cell="P12")
        assert game.agent.holo_decoy_cell == "P12"

    def test_consumes_charge(self):
        game = make_game(agent_pos="P10", items=[make_item("holo_decoy", charges=1)])
        apply_item(game, "holo_decoy", ITEM_DEFS["holo_decoy"], target_cell="P12")
        assert game.agent.items[0].charges == 0

    def test_raises_out_of_range(self):
        game = make_game(agent_pos="A1", items=[make_item("holo_decoy")])
        with pytest.raises(ValueError, match="out of range"):
            apply_item(game, "holo_decoy", ITEM_DEFS["holo_decoy"], target_cell="W32")

    def test_raises_without_target_cell(self):
        game = make_game(agent_pos="P10", items=[make_item("holo_decoy")])
        with pytest.raises(ValueError):
            apply_item(game, "holo_decoy", ITEM_DEFS["holo_decoy"])


# ---------------------------------------------------------------------------
# apply_item — smoke_dagger
# ---------------------------------------------------------------------------

class TestSmokeDagger:
    def test_flashbangs_target_hunter(self):
        hunter = make_hunter("h1", "P11")
        game = make_game(agent_pos="P10", items=[make_item("smoke_dagger", charges=2)], hunters=[hunter])
        apply_item(game, "smoke_dagger", ITEM_DEFS["smoke_dagger"], target_player="h1")
        assert StatusEffect.FLASHBANGED in game.hunters[0].status_effects

    def test_adds_to_smoke_dagger_targets(self):
        hunter = make_hunter("h1", "P11")
        game = make_game(agent_pos="P10", items=[make_item("smoke_dagger", charges=2)], hunters=[hunter])
        apply_item(game, "smoke_dagger", ITEM_DEFS["smoke_dagger"], target_player="h1")
        assert "h1" in game.smoke_dagger_targets

    def test_taps_item(self):
        hunter = make_hunter("h1", "P11")
        game = make_game(agent_pos="P10", items=[make_item("smoke_dagger", charges=2)], hunters=[hunter])
        apply_item(game, "smoke_dagger", ITEM_DEFS["smoke_dagger"], target_player="h1")
        assert game.agent.items[0].tapped is True

    def test_raises_when_out_of_range(self):
        hunter = make_hunter("h1", "A1")
        game = make_game(agent_pos="W32", items=[make_item("smoke_dagger", charges=2)], hunters=[hunter])
        with pytest.raises(ValueError, match="out of range"):
            apply_item(game, "smoke_dagger", ITEM_DEFS["smoke_dagger"], target_player="h1")

    def test_raises_without_target_player(self):
        game = make_game(items=[make_item("smoke_dagger", charges=2)])
        with pytest.raises(ValueError):
            apply_item(game, "smoke_dagger", ITEM_DEFS["smoke_dagger"])


# ---------------------------------------------------------------------------
# apply_item — stealth_field
# ---------------------------------------------------------------------------

class TestStealthField:
    def test_activates_stealth_field(self):
        game = make_game(items=[make_item("stealth_field")])
        apply_item(game, "stealth_field", ITEM_DEFS["stealth_field"])
        assert game.agent.stealth_field_active is True

    def test_taps_item(self):
        game = make_game(items=[make_item("stealth_field")])
        apply_item(game, "stealth_field", ITEM_DEFS["stealth_field"])
        assert game.agent.items[0].tapped is True

    def test_returns_stealth_field_effect(self):
        game = make_game(items=[make_item("stealth_field")])
        result = apply_item(game, "stealth_field", ITEM_DEFS["stealth_field"])
        assert result["effect"] == "stealth_field"


# ---------------------------------------------------------------------------
# apply_item — proximity_mine
# ---------------------------------------------------------------------------

class TestProximityMine:
    def test_sets_mine_cell(self):
        # Range 2: P10 → P12 is within 2
        game = make_game(agent_pos="P10", items=[make_item("proximity_mine")])
        apply_item(game, "proximity_mine", ITEM_DEFS["proximity_mine"], target_cell="P12")
        assert game.agent.proximity_mine_cell == "P12"

    def test_does_not_consume_charge(self):
        game = make_game(agent_pos="P10", items=[make_item("proximity_mine", charges=1)])
        apply_item(game, "proximity_mine", ITEM_DEFS["proximity_mine"], target_cell="P12")
        assert game.agent.items[0].charges == 1

    def test_raises_out_of_range(self):
        game = make_game(agent_pos="A1", items=[make_item("proximity_mine")])
        with pytest.raises(ValueError, match="out of range"):
            apply_item(game, "proximity_mine", ITEM_DEFS["proximity_mine"], target_cell="W32")

    def test_raises_without_target_cell(self):
        game = make_game(agent_pos="P10", items=[make_item("proximity_mine")])
        with pytest.raises(ValueError):
            apply_item(game, "proximity_mine", ITEM_DEFS["proximity_mine"])

    def test_returns_mine_placed(self):
        game = make_game(agent_pos="P10", items=[make_item("proximity_mine")])
        result = apply_item(game, "proximity_mine", ITEM_DEFS["proximity_mine"], target_cell="P12")
        assert result["effect"] == "mine_placed"
        assert result["cell"] == "P12"


# ---------------------------------------------------------------------------
# apply_item — pulse_blades
# ---------------------------------------------------------------------------

class TestPulseBlades:
    def test_arms_pulse_blades(self):
        game = make_game(items=[make_item("pulse_blades", charges=2)])
        apply_item(game, "pulse_blades", ITEM_DEFS["pulse_blades"])
        assert game.agent.pulse_blades_armed is True

    def test_does_not_consume_charge(self):
        game = make_game(items=[make_item("pulse_blades", charges=2)])
        apply_item(game, "pulse_blades", ITEM_DEFS["pulse_blades"])
        assert game.agent.items[0].charges == 2

    def test_returns_pulse_blades_armed(self):
        game = make_game(items=[make_item("pulse_blades", charges=2)])
        result = apply_item(game, "pulse_blades", ITEM_DEFS["pulse_blades"])
        assert result["effect"] == "pulse_blades_armed"


# ---------------------------------------------------------------------------
# apply_item — tangle_line
# ---------------------------------------------------------------------------

class TestTangleLine:
    def _spider_game(self, agent_pos, hunter_pos):
        hunter = make_hunter("h1", hunter_pos)
        return make_game(
            agent_pos=agent_pos,
            agent_char="spider",
            items=[make_item("tangle_line", charges=2)],
            hunters=[hunter],
        ), hunter

    def test_stuns_hunter_on_hit(self):
        # Agent P10, hunter P13 (distance 3), roll=3 → 3 >= 3 = hit
        game, hunter = self._spider_game("P10", "P13")
        board = get_board()
        with patch("backend.engine.random.randint", return_value=3):
            apply_item(game, "tangle_line", ITEM_DEFS["tangle_line"],
                       board=board, target_player="h1")
        assert StatusEffect.STUNNED in game.hunters[0].status_effects

    def test_does_not_stun_on_miss(self):
        # Agent P10, hunter P13 (distance 3), roll=2 → 2 < 3 = miss
        game, hunter = self._spider_game("P10", "P13")
        board = get_board()
        with patch("backend.engine.random.randint", return_value=2):
            apply_item(game, "tangle_line", ITEM_DEFS["tangle_line"],
                       board=board, target_player="h1")
        assert StatusEffect.STUNNED not in game.hunters[0].status_effects

    def test_consumes_charge_on_hit(self):
        game, _ = self._spider_game("P10", "P13")
        board = get_board()
        with patch("backend.engine.random.randint", return_value=3):
            apply_item(game, "tangle_line", ITEM_DEFS["tangle_line"],
                       board=board, target_player="h1")
        assert game.agent.items[0].tapped is True

    def test_does_not_consume_charge_on_miss(self):
        game, _ = self._spider_game("P10", "P13")
        board = get_board()
        with patch("backend.engine.random.randint", return_value=2):
            apply_item(game, "tangle_line", ITEM_DEFS["tangle_line"],
                       board=board, target_player="h1")
        # taps=True means the charge gate is tapped; on miss, should not tap
        assert game.agent.items[0].tapped is False

    def test_raises_without_target_player(self):
        game = make_game(agent_char="spider", items=[make_item("tangle_line", charges=2)])
        with pytest.raises(ValueError):
            apply_item(game, "tangle_line", ITEM_DEFS["tangle_line"])


# ---------------------------------------------------------------------------
# can_use_agent_ability
# ---------------------------------------------------------------------------

class TestCanUseAgentAbility:
    def _game_with_dash(self):
        return make_game(
            agent_char="fox",
            abilities=[{"name": "Dash", "active": True}],
        )

    def test_wrong_phase_returns_false(self):
        game = self._game_with_dash()
        game.phase = TurnPhase.HUNTER_TURN
        ok, _ = can_use_agent_ability(game, "Dash")
        assert not ok

    def test_fatigued_returns_false(self):
        game = self._game_with_dash()
        game.agent.status_effects.add(StatusEffect.FATIGUED)
        ok, _ = can_use_agent_ability(game, "Dash")
        assert not ok

    def test_ability_not_in_list_returns_false(self):
        game = make_game(abilities=[])
        ok, _ = can_use_agent_ability(game, "Dash")
        assert not ok

    def test_passive_ability_returns_false(self):
        game = make_game(abilities=[{"name": "Dash", "active": False}])
        ok, _ = can_use_agent_ability(game, "Dash")
        assert not ok

    def test_dash_after_moving_returns_false(self):
        game = self._game_with_dash()
        game.agent.path_this_turn = ["P10", "P11"]
        ok, reason = can_use_agent_ability(game, "Dash")
        assert not ok
        assert "before moving" in reason

    def test_dash_before_moving_returns_true(self):
        game = self._game_with_dash()
        game.agent.path_this_turn = ["P10"]
        ok, _ = can_use_agent_ability(game, "Dash")
        assert ok


# ---------------------------------------------------------------------------
# apply_agent_ability — Dash
# ---------------------------------------------------------------------------

class TestApplyAgentAbilityDash:
    def _game_with_dash(self):
        return make_game(
            agent_char="fox",
            abilities=[{"name": "Dash", "active": True}],
        )

    def test_sets_move_speed_5(self):
        game = self._game_with_dash()
        apply_agent_ability(game, "Dash", {})
        assert game.agent.move_speed == 5

    def test_applies_fatigued_normally(self):
        game = self._game_with_dash()
        apply_agent_ability(game, "Dash", {})
        assert StatusEffect.FATIGUED in game.agent.status_effects

    def test_no_fatigued_when_movement_boosted_by_item(self):
        game = self._game_with_dash()
        game.agent.movement_boosted_by_item = True
        apply_agent_ability(game, "Dash", {})
        assert StatusEffect.FATIGUED not in game.agent.status_effects

    def test_returns_dash_result(self):
        game = self._game_with_dash()
        result = apply_agent_ability(game, "Dash", {})
        assert result["ability"] == "Dash"
        assert result["move_speed"] == 5

    def test_unknown_ability_raises(self):
        game = make_game(abilities=[{"name": "Teleport", "active": True}])
        with pytest.raises(ValueError, match="Teleport"):
            apply_agent_ability(game, "Teleport", {})
