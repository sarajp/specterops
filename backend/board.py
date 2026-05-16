"""
board.py — BoardData dataclass, JSON loader, coordinate helpers, and LOS.

Grid convention: columns A–W (index 0–22), rows 1–32.
Cell strings are column-letter + row-number, e.g. "A1", "W32".
A1 is top-left; W32 is bottom-right.

Structures are any coordinate outside the valid grid — they are never
represented explicitly; callers simply cannot reference them.

Walls and barriers are impassable cells (not edges).
Barriers are mutable; walls are fixed per board.
Active obstacles (smoke grenades, etc.) are passed in at query time so
the blocker set can be rebuilt without mutating board state.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLUMNS = [chr(ord("A") + i) for i in range(23)]  # A–W
ROWS = list(range(1, 33))                           # 1–32
ALL_CELLS: frozenset[str] = frozenset(
    col + str(row) for col in COLUMNS for row in ROWS
)

BOARD_KEYS = {
    "Shadow of Babel": "shadow_of_babel",
    "Broken Covenant": "broken_covenant",
    "Arctic Archives": "arctic_archives",
}


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def cell_col(cell: str) -> int:
    """Zero-based column index (A=0 … W=22)."""
    return ord(cell[0]) - ord("A")


def cell_row(cell: str) -> int:
    """One-based row number (1–32)."""
    return int(cell[1:])


def index_to_cell(col: int, row: int) -> Optional[str]:
    """Return cell string for (col 0-based, row 1-based), or None if out of bounds."""
    if 0 <= col <= 22 and 1 <= row <= 32:
        return COLUMNS[col] + str(row)
    return None


def chebyshev_distance(a: str, b: str) -> int:
    """
    Chebyshev (king-move) distance between two cells.
    This matches game distance: orthogonal and diagonal steps both cost 1.
    """
    return max(abs(cell_col(a) - cell_col(b)), abs(cell_row(a) - cell_row(b)))


def neighbors(cell: str) -> list[str]:
    """All valid orthogonal and diagonal neighbors (up to 8)."""
    col, row = cell_col(cell), cell_row(cell)
    result = []
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            candidate = index_to_cell(col + dc, row + dr)
            if candidate is not None:
                result.append(candidate)
    return result


def orthogonal_neighbors(cell: str) -> list[str]:
    """Four orthogonal neighbors only."""
    col, row = cell_col(cell), cell_row(cell)
    result = []
    for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        candidate = index_to_cell(col + dc, row + dr)
        if candidate is not None:
            result.append(candidate)
    return result


def adjacent(a: str, b: str) -> bool:
    """True if a and b are orthogonally or diagonally adjacent (Chebyshev distance == 1)."""
    return chebyshev_distance(a, b) == 1


def orthogonal_adjacent(a: str, b: str) -> bool:
    """True if a and b are orthogonally adjacent (N/S/E/W only, not diagonal)."""
    ac, ar = cell_col(a), cell_row(a)
    bc, br = cell_col(b), cell_row(b)
    dc, dr = abs(ac - bc), abs(ar - br)
    return (dc == 1 and dr == 0) or (dc == 0 and dr == 1)


# ---------------------------------------------------------------------------
# LOS
# ---------------------------------------------------------------------------

def _cells_in_bounding_rect(a: str, b: str) -> frozenset[str]:
    """
    All cells strictly inside the bounding rectangle of a and b
    (endpoints excluded).

    For a degenerate rectangle (same row or column), this is the cells
    strictly between a and b on that line.
    """
    col_a, row_a = cell_col(a), cell_row(a)
    col_b, row_b = cell_col(b), cell_row(b)

    col_min, col_max = min(col_a, col_b), max(col_a, col_b)
    row_min, row_max = min(row_a, row_b), max(row_a, row_b)

    interior: set[str] = set()
    for c in range(col_min, col_max + 1):
        for r in range(row_min, row_max + 1):
            # exclude endpoints
            if (c == col_a and r == row_a) or (c == col_b and r == row_b):
                continue
            cell = index_to_cell(c, r)
            if cell is not None:
                interior.add(cell)
    return frozenset(interior)


def has_los(a: str, b: str, blockers: frozenset[str]) -> bool:
    """
    Return True if cell a has line of sight to cell b given the blocker set.

    Rule (from claude.md):
      Bounding rectangle between two cells; any blocker cell inside
      (excluding endpoints) blocks LOS.  Corners block.

    Blocker set should include: walls + active barriers + active obstacles
    (smoke grenades, etc.).  Roads are NOT blockers.

    Same cell always has LOS to itself.
    """
    if a == b:
        return True
    interior = _cells_in_bounding_rect(a, b)
    return interior.isdisjoint(blockers)


def build_blocker_set(
    walls: list[str],
    barriers: list[str],
    obstacles: list[str],
) -> frozenset[str]:
    """
    Merge fixed walls, current barriers, and transient obstacles into one
    blocker set for LOS queries.
    """
    return frozenset(walls) | frozenset(barriers) | frozenset(obstacles)


# ---------------------------------------------------------------------------
# BoardData
# ---------------------------------------------------------------------------

@dataclass
class BoardData:
    name: str                              # display name, e.g. "Shadow of Babel"
    roads: frozenset[str]
    walls: frozenset[str]
    supply_caches: list[str]
    barriers: list[list[str]]             # mutable barrier pairs/cells per map spec
    potential_objectives: dict[str, list[str]]  # "1"–"4" → list of candidate cells

    # Active state — mutated during play
    active_barriers: list[str] = field(default_factory=list)

    @property
    def fixed_blockers(self) -> frozenset[str]:
        """Walls only — does not include barriers or obstacles."""
        return self.walls

    def get_blockers(self, obstacles: Optional[list[str]] = None) -> frozenset[str]:
        """
        Current full blocker set: walls + active barriers + optional transient obstacles.
        Pass obstacles=[] or omit for no transient obstacles.
        """
        return build_blocker_set(
            list(self.walls),
            self.active_barriers,
            obstacles or [],
        )

    def is_passable(self, cell: str) -> bool:
        """
        True if a cell is within the grid and not a wall or active barrier.
        Does NOT check hunter occupancy or vehicle position — callers handle that.
        """
        return cell in ALL_CELLS and cell not in self.walls and cell not in self.active_barriers


def load_board(board_name: str, resources_path: Optional[Path] = None) -> BoardData:
    """
    Load a BoardData from resources.json.

    board_name must be one of: "Shadow of Babel", "Broken Covenant", "Arctic Archives".
    resources_path defaults to backend/data/resources.json relative to this file.
    """
    if board_name not in BOARD_KEYS:
        raise ValueError(f"Unknown board: {board_name!r}. Valid: {list(BOARD_KEYS)}")

    if resources_path is None:
        resources_path = Path(__file__).parent / "data" / "resources.json"

    with open(resources_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    key = BOARD_KEYS[board_name]
    raw = data["resources"]["boards"][key]

    return BoardData(
        name=board_name,
        roads=frozenset(raw["roads"]),
        walls=frozenset(raw["walls"]),
        supply_caches=list(raw.get("supply_caches", [])),
        barriers=list(raw.get("barriers", [])),
        potential_objectives=raw["potential_objectives"],
    )