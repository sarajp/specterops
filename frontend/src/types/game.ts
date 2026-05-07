export type TurnPhase =
  | 'SETUP'
  | 'AGENT_TURN'
  | 'HUNTER_NEGOTIATE'
  | 'HUNTER_TURN'
  | 'GAME_OVER';

export type WinCondition =
  | 'NONE'
  | 'AGENT_ESCAPE'
  | 'HUNTERS_KILL'
  | 'HUNTERS_TIMEOUT';

export type StatusEffect = 'STUNNED' | 'FATIGUED' | 'FLASHBANGED';

export interface ItemState {
  key: string;
  name: string;
  charges: number;
  tapped: boolean;
}

// Agent's own view of themselves (full detail)
export interface AgentStateView {
  character: string;
  position: string;
  health: number;
  max_health: number;
  move_speed: number;
  identity_revealed: boolean;
  pending_objectives: string[];
  public_objectives: string[];
  last_seen_cell: string | null;
  path_this_turn: string[];
  status_effects: StatusEffect[];
  items: ItemState[];
}

// Hunters' view of the agent (redacted)
export interface HunterAgentView {
  health: number;
  max_health: number;
  identity_revealed: boolean;
  public_objectives: string[];
  last_seen_cell: string | null;
  status_effects: StatusEffect[];
  position?: string;   // present only when agent is visible to any hunter
  character?: string;  // present only after identity_revealed
}

export interface HunterStateView {
  player_name: string;
  character: string;
  position: string;
  move_speed: number;
  in_vehicle: boolean;
  moved_this_turn: boolean;
  path_this_turn: string[];
  status_effects: StatusEffect[];
}

export interface VehicleStateView {
  name: string;
  position: string;
  move_speed: number;
  move_budget_remaining: number;
  occupied_by: string | null;
  path_this_round: string[];
}

export interface AvailableItem {
  key: string;
  name: string;
  charges: number;
  copies: number;
  ability: string;
}

export interface AgentGameView {
  role: 'agent';
  board_name: string;
  round_number: number;
  phase: TurnPhase;
  win_condition: WinCondition;
  agent_escaped: boolean;
  escape_points: string[];
  objectives: string[];
  objectives_visible: boolean;
  active_obstacles: string[];
  active_barriers: string[];
  agent: AgentStateView;
  hunters: HunterStateView[];
  vehicle: VehicleStateView;
  hunter_order: string[];
  active_hunter_index: number;
  available_items?: AvailableItem[];
  max_equipment?: number;
}

export interface HunterGameView {
  role: 'hunter';
  board_name: string;
  round_number: number;
  phase: TurnPhase;
  win_condition: WinCondition;
  escape_points: string[];
  objectives: string[] | null; // null when hidden (4-5p)
  objectives_visible: boolean;
  active_obstacles: string[];
  active_barriers: string[];
  agent: HunterAgentView;
  hunters: HunterStateView[];
  vehicle: VehicleStateView;
  hunter_order: string[];
  active_hunter_index: number;
}

export type GameView = AgentGameView | HunterGameView;

export interface LobbyPlayer {
  player_name: string;
  role: 'agent' | 'hunter';
  character: string;
  board: string;
}
