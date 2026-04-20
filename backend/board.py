from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class BoardData:
    name: str
    walls: list[str]
    roads: list[str]
    barriers: list[list[str]]
    supply_caches: list[str]
    potential_objectives: dict[str, list[str]]
    escape_points: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    active_blockers: list[str] = field(default_factory=list)  # walls + barriers + obstacles


# --- Loading ---

def load_board(board_name: str, resources_path: str) -> BoardData:
    # read resources.json
    # extract walls, roads, barriers, supply_caches, potential_objectives for board_name
    # return BoardData
    pass


# --- Coordinate system ---

def build_coordinate_system() -> list[str]:
    # generate all valid cell labels (A-W, 1-32)
    pass

def is_valid_cell(cell: str, board: BoardData) -> bool:
    # return True if cell is within A-W, 1-32 and not a wall
    pass

def get_neighbors(cell: str, board: BoardData) -> list[str]:
    # return orthogonal + diagonal adjacent valid cells
    pass

def cell_to_coords(cell: str) -> tuple[int, int]:
    # convert e.g. "N14" to (col_index, row_index)
    pass

def coords_to_cell(col: int, row: int) -> str:
    # inverse of cell_to_coords
    pass


# --- LOS ---

def get_active_blockers(board: BoardData) -> list[str]:
    # return walls + barrier cells + active obstacle cells
    pass

def is_los_clear(cell_a: str, cell_b: str, blockers: list[str]) -> bool:
    # build axis-aligned bounding rectangle between cell_a and cell_b
    # if any blocker falls inside rectangle (excluding endpoints): return False
    # same logic applies to degenerate case (same row or col)
    # barrier pairs: if either cell in a pair is inside rectangle, block
    pass

def get_road_los_cells(cell: str, board: BoardData) -> list[str]:
    # if cell is on a road, extend LOS along the road stretch in all road directions
    # return all cells visible via road LOS
    pass


# --- Objectives ---

def select_objectives(board: BoardData) -> list[str]:
    # pick 4 objectives, one from each pool, without duplicates
    pass


# --- Escape points ---

def get_escape_points(board_name: str, player_count: int) -> list[str]:
    # base escape points per board
    # add A6, W6 if player_count >= 4
    pass


# --- Supply caches ---

def get_supply_cache_at(cell: str, board: BoardData) -> Optional[str]:
    # return cache item at cell if present, else None
    pass

def remove_supply_cache(cell: str, board: BoardData) -> None:
    # remove cache from board after it has been collected
    pass