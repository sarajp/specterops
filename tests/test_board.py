"""
test_board.py — Tests for board.py

Covers:
  - has_los: clear, blocked, degenerate (row/col), corner-blocking
  - load_board: sanity checks for all three maps
  - Coordinate helpers: chebyshev_distance, neighbors, adjacent
"""

import pytest
from pathlib import Path

# Adjust import path if running from project root

from backend.board import (
    has_los,
    build_blocker_set,
    load_board,
    index_to_cell,
    chebyshev_distance,
    neighbors,
    orthogonal_neighbors,
    adjacent,
    cell_col,
    cell_row,
    _cells_in_bounding_rect,
    ALL_CELLS,
)

RESOURCES = Path(__file__).parent.parent / "backend" / "data" / "resources.json"


# ---------------------------------------------------------------------------
# has_los
# ---------------------------------------------------------------------------

class TestHasLos:

    def test_clear_line_no_blockers(self):
        # A1 to A5: interior is A2, A3, A4 — none are blockers
        assert has_los("A1", "A5", frozenset()) is True

    def test_blocked_on_same_column(self):
        blockers = frozenset(["A3"])
        assert has_los("A1", "A5", blockers) is False

    def test_blocked_on_same_row(self):
        blockers = frozenset(["C1"])
        assert has_los("A1", "E1", blockers) is False

    def test_not_blocked_by_endpoint(self):
        # Blocker at endpoint should not block LOS (endpoints excluded from interior)
        blockers = frozenset(["A5"])
        assert has_los("A1", "A5", blockers) is True

    def test_blocked_diagonal(self):
        # A1 to C3: interior includes B2
        blockers = frozenset(["B2"])
        assert has_los("A1", "C3", blockers) is False

    def test_clear_diagonal(self):
        assert has_los("A1", "C3", frozenset()) is True

    def test_corner_blocking(self):
        # A1 to C3 rectangle interior is B1, B2, B3, A2, A3, C1, C2 ... and B2
        # B2 is interior — it blocks
        blockers = frozenset(["B2"])
        assert has_los("A1", "C3", blockers) is False

    def test_far_clear(self):
        assert has_los("A1", "W32", frozenset()) is True

    def test_far_blocked_center(self):
        # Approximate center of the board
        blockers = frozenset(["L16"])
        result = has_los("A1", "W32", blockers)
        # L16 is in interior of A1–W32 bounding rect — should block
        assert result is False

    def test_obstacle_blocks(self):
        # Smoke grenade passed as obstacle
        obstacles = ["D3"]
        blockers = build_blocker_set([], [], obstacles)
        assert has_los("A3", "G3", blockers) is False

    def test_build_blocker_set_merges_all(self):
        walls = ["A2"]
        barriers = ["B3"]
        obstacles = ["C4"]
        bs = build_blocker_set(walls, barriers, obstacles)
        assert "A2" in bs
        assert "B3" in bs
        assert "C4" in bs


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

class TestCoordinates:
    def test_cell_col(self):
        assert cell_col("A1") == 0
        assert cell_col("W1") == 22
        assert cell_col("N1") == 13

    def test_cell_row(self):
        assert cell_row("A1") == 1
        assert cell_row("A32") == 32
        assert cell_row("B15") == 15

    def test_chebyshev_same_cell(self):
        assert chebyshev_distance("A1", "A1") == 0

    def test_chebyshev_orthogonal(self):
        assert chebyshev_distance("A1", "A3") == 2
        assert chebyshev_distance("A1", "C1") == 2

    def test_chebyshev_diagonal(self):
        # diagonal distance is max of abs diffs
        assert chebyshev_distance("A1", "C3") == 2

    def test_chebyshev_mixed(self):
        # A1 to D2: col diff=3, row diff=1 → max=3
        assert chebyshev_distance("A1", "D2") == 3

    def test_neighbors_count_interior(self):
        n = neighbors("D5")
        assert len(n) == 8

    def test_neighbors_count_corner(self):
        n = neighbors("A1")
        assert len(n) == 3  # B1, A2, B2

    def test_neighbors_count_edge(self):
        n = neighbors("A5")
        assert len(n) == 5

    def test_orthogonal_neighbors_count(self):
        assert len(orthogonal_neighbors("D5")) == 4
        assert len(orthogonal_neighbors("A1")) == 2

    def test_adjacent_true(self):
        assert adjacent("A1", "B2") is True
        assert adjacent("A1", "A2") is True

    def test_adjacent_false(self):
        assert adjacent("A1", "A3") is False
        assert adjacent("A1", "C1") is False

    def test_all_cells_count(self):
        assert len(ALL_CELLS) == 23 * 32  # 736


# ---------------------------------------------------------------------------
# load_board
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("board_name,min_walls,min_roads", [
    ("Shadow of Babel", 100, 100),
    ("Broken Covenant", 80, 80),
    ("Arctic Archives", 80, 100),
])
def test_load_board_sanity(board_name, min_walls, min_roads):
    board = load_board(board_name, RESOURCES)
    assert board.name == board_name
    assert len(board.walls) >= min_walls
    assert len(board.roads) >= min_roads

def test_load_board_all_walls_are_valid_cells():
    for name in ["Shadow of Babel", "Broken Covenant", "Arctic Archives"]:
        board = load_board(name, RESOURCES)
        for cell in board.walls:
            assert cell in ALL_CELLS, f"{cell} in {name} walls is not a valid cell"

def test_load_board_all_roads_are_valid_cells():
    for name in ["Shadow of Babel", "Broken Covenant", "Arctic Archives"]:
        board = load_board(name, RESOURCES)
        for cell in board.roads:
            assert cell in ALL_CELLS, f"{cell} in {name} roads is not a valid cell"

def test_load_board_objectives_four_quadrants():
    for name in ["Shadow of Babel", "Broken Covenant", "Arctic Archives"]:
        board = load_board(name, RESOURCES)
        assert set(board.potential_objectives.keys()) == {"1", "2", "3", "4"}
        for quadrant, candidates in board.potential_objectives.items():
            assert len(candidates) > 0, f"No candidates for quadrant {quadrant} on {name}"

def test_load_board_arctic_has_barriers():
    board = load_board("Arctic Archives", RESOURCES)
    assert len(board.barriers) > 0

def test_load_board_unknown_raises():
    with pytest.raises(ValueError):
        load_board("Nonexistent Board", RESOURCES)

def test_board_is_passable():
    board = load_board("Shadow of Babel", RESOURCES)
    # A road cell should be passable
    assert board.is_passable("N1") is True
    # A wall cell should not
    first_wall = next(iter(board.walls))
    assert board.is_passable(first_wall) is False

def test_board_active_barrier_blocks_passable():
    board = load_board("Arctic Archives", RESOURCES)
    # H8 is a road cell on Arctic Archives
    assert board.is_passable("H8") is True
    board.active_barriers.append("H8")
    assert board.is_passable("H8") is False

def test_shadow_of_babel_uses_bounding_rectangle_los():
    """Integration: use actual wall data to verify a wall blocks LOS."""
    board = load_board("Shadow of Babel", RESOURCES)
    blockers = board.get_blockers()
    # C1 is a wall on Shadow of Babel; it should block LOS from A1 to E1
    # (C1 is in the interior of the A1–E1 horizontal segment)
    assert "C1" in blockers
    assert has_los("A1", "E1", blockers) is False

# ---------------------------------------------------------------------------
# _cells_in_bounding_rect / interior
# ---------------------------------------------------------------------------

class TestBoundingRectInterior:
    def test_same_cell_has_no_interior(self):
        # has_los handles same-cell early, but interior should be empty
        interior = _cells_in_bounding_rect("D5", "D5")
        assert len(interior) == 0

    def test_horizontal_segment_interior(self):
        # A1 to E1: interior is B1, C1, D1
        interior = _cells_in_bounding_rect("A1", "E1")
        assert interior == frozenset(["B1", "C1", "D1"])

    def test_vertical_segment_interior(self):
        interior = _cells_in_bounding_rect("A1", "A4")
        assert interior == frozenset(["A2", "A3"])

    def test_endpoints_excluded(self):
        interior = _cells_in_bounding_rect("A1", "C3")
        assert "A1" not in interior
        assert "C3" not in interior

    def test_square_diagonal_interior_contains_off_diagonal_cells(self):
        # A1 to C3: interior includes B1, B2, B3, A2, A3, C1, C2 — not just B2
        interior = _cells_in_bounding_rect("A1", "C3")
        assert "B2" in interior      # on the diagonal
        assert "B1" in interior      # off diagonal but inside rect
        assert "A2" in interior

    def test_non_square_rect_interior(self):
        # A1 to C5: 3 cols wide, 5 rows tall
        interior = _cells_in_bounding_rect("A1", "C5")
        assert "B3" in interior
        assert "A1" not in interior
        assert "C5" not in interior


# ---------------------------------------------------------------------------
# has_los — endpoint blocking
# ---------------------------------------------------------------------------

class TestHasLosEndpoints:
    def test_endpoint_in_blockers_does_not_block(self):
        # Blocker at the source endpoint
        blockers = frozenset(["A1"])
        assert has_los("A1", "C1", blockers) is True

    def test_destination_in_blockers_does_not_block(self):
        blockers = frozenset(["C1"])
        assert has_los("A1", "C1", blockers) is True

    def test_cell_one_from_source_blocks(self):
        blockers = frozenset(["B1"])
        assert has_los("A1", "D1", blockers) is False

    def test_cell_one_from_destination_blocks(self):
        blockers = frozenset(["C1"])
        assert has_los("A1", "D1", blockers) is False


# ---------------------------------------------------------------------------
# has_los — non-square diagonals
# ---------------------------------------------------------------------------

class TestHasLosNonSquare:
    def test_non_square_blocked_by_off_diagonal_cell(self):
        # A1 to C5: B3 is interior; should block
        blockers = frozenset(["B3"])
        assert has_los("A1", "C5", blockers) is False


# ---------------------------------------------------------------------------
# build_blocker_set
# ---------------------------------------------------------------------------

class TestBuildBlockerSet:
    def test_deduplicates_across_sources(self):
        bs = build_blocker_set(["A1"], ["A1"], ["A1"])
        assert len(bs) == 1


# ---------------------------------------------------------------------------
# load_board — field integrity
# ---------------------------------------------------------------------------

class TestLoadBoardIntegrity:
    @pytest.mark.parametrize("board_name", [
        "Shadow of Babel", "Broken Covenant", "Arctic Archives"
    ])
    def test_walls_and_roads_disjoint(self, board_name):
        board = load_board(board_name, RESOURCES)
        overlap = board.walls & board.roads
        assert len(overlap) == 0, f"Overlap on {board_name}: {overlap}"

    @pytest.mark.parametrize("board_name", [
        "Shadow of Babel", "Broken Covenant", "Arctic Archives"
    ])
    def test_supply_caches_are_valid_cells(self, board_name):
        board = load_board(board_name, RESOURCES)
        for cell in board.supply_caches:
            assert cell in ALL_CELLS, f"{cell} in {board_name} supply_caches is not a valid cell"

    @pytest.mark.parametrize("board_name", [
        "Shadow of Babel", "Broken Covenant", "Arctic Archives"
    ])
    def test_objective_candidates_are_valid_cells(self, board_name):
        board = load_board(board_name, RESOURCES)
        for quadrant, candidates in board.potential_objectives.items():
            for cell in candidates:
                assert cell in ALL_CELLS, f"{cell} in quadrant {quadrant} on {board_name} is not valid"

    def test_arctic_barriers_are_pairs(self):
        board = load_board("Arctic Archives", RESOURCES)
        for pair in board.barriers:
            assert len(pair) == 2, f"Barrier {pair} is not a pair"

    def test_arctic_barrier_cells_are_valid(self):
        board = load_board("Arctic Archives", RESOURCES)
        for pair in board.barriers:
            for cell in pair:
                assert cell in ALL_CELLS, f"Barrier cell {cell} is not a valid cell"

    def test_arctic_barrier_cells_are_adjacent(self):
        board = load_board("Arctic Archives", RESOURCES)
        for pair in board.barriers:
            assert adjacent(pair[0], pair[1]), f"Barrier pair {pair} cells are not adjacent"

    def test_shadow_of_babel_has_no_supply_caches(self):
        board = load_board("Shadow of Babel", RESOURCES)
        assert board.supply_caches == []


# ---------------------------------------------------------------------------
# BoardData.is_passable
# ---------------------------------------------------------------------------

class TestIsPassable:
    def test_wall_cell_not_passable(self):
        board = load_board("Shadow of Babel", RESOURCES)
        # C1 is a wall on Shadow of Babel per resources.json
        assert board.is_passable("C1") is False

    def test_road_cell_passable(self):
        board = load_board("Shadow of Babel", RESOURCES)
        assert board.is_passable("N1") is True

    def test_active_barrier_blocks_passable(self):
        board = load_board("Arctic Archives", RESOURCES)
        assert board.is_passable("H8") is True
        board.active_barriers.append("H8")
        assert board.is_passable("H8") is False

    def test_active_barrier_removed_restores_passable(self):
        board = load_board("Arctic Archives", RESOURCES)
        board.active_barriers.append("H8")
        board.active_barriers.remove("H8")
        assert board.is_passable("H8") is True


# ---------------------------------------------------------------------------
# BoardData.get_blockers
# ---------------------------------------------------------------------------

class TestGetBlockers:
    def test_walls_always_included(self):
        board = load_board("Shadow of Babel", RESOURCES)
        blockers = board.get_blockers()
        assert board.walls.issubset(blockers)

    def test_active_barriers_included(self):
        board = load_board("Arctic Archives", RESOURCES)
        board.active_barriers.append("H8")
        blockers = board.get_blockers()
        assert "H8" in blockers

    def test_obstacles_included(self):
        board = load_board("Shadow of Babel", RESOURCES)
        blockers = board.get_blockers(obstacles=["D5"])
        assert "D5" in blockers


# ---------------------------------------------------------------------------
# Coordinate helpers — symmetry and edge cases
# ---------------------------------------------------------------------------

class TestCoordinateHelpers:
    def test_chebyshev_symmetric(self):
        assert chebyshev_distance("A1", "D5") == chebyshev_distance("D5", "A1")

    def test_chebyshev_large(self):
        # A1 to W32: col diff=22, row diff=31 → 31
        assert chebyshev_distance("A1", "W32") == 31

    def test_neighbors_corner_w1(self):
        n = neighbors("W1")
        assert len(n) == 3

    def test_neighbors_corner_a32(self):
        n = neighbors("A32")
        assert len(n) == 3

    def test_neighbors_corner_w32(self):
        n = neighbors("W32")
        assert len(n) == 3

    def test_orthogonal_neighbors_corner(self):
        assert len(orthogonal_neighbors("A1")) == 2
        assert len(orthogonal_neighbors("W32")) == 2

    def test_orthogonal_neighbors_edge(self):
        # A5: left edge, interior row
        assert len(orthogonal_neighbors("A5")) == 3

    def test_index_to_cell_out_of_bounds_col(self):
        assert index_to_cell(-1, 1) is None
        assert index_to_cell(23, 1) is None

    def test_index_to_cell_out_of_bounds_row(self):
        assert index_to_cell(0, 0) is None
        assert index_to_cell(0, 33) is None

    def test_adjacent_is_symmetric(self):
        assert adjacent("A1", "B2") == adjacent("B2", "A1")

    def test_not_adjacent_distance_2(self):
        assert adjacent("A1", "C1") is False
        assert adjacent("A1", "A3") is False
        assert adjacent("A1", "C3") is False