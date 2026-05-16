import type { GameView, LobbyPlayer } from './game';

// ---------------------------------------------------------------------------
// Inbound (server → client)
// ---------------------------------------------------------------------------

export interface LobbyMessage {
  type: 'lobby';
  players: LobbyPlayer[];
}

export interface StateMessage {
  type: 'state';
  data: GameView;
}

export interface ErrorMessage {
  type: 'error';
  detail: string;
}

export interface GameOverMessage {
  type: 'game_over';
  result: string;
}

export interface CombatResultMessage {
  type: 'combat_result';
  attacker: string;
  hit: boolean;
  roll: number;
  distance: number;
}

export interface ItemUsedMessage {
  type: 'item_used';
  item_key: string | null;  // null when hidden from this client
  result: Record<string, unknown>;
}

export interface AbilityResultMessage {
  type: 'ability_result';
  ability: string;
  [key: string]: unknown;  // result fields vary by ability
}

export type InboundMessage =
  | LobbyMessage
  | StateMessage
  | ErrorMessage
  | GameOverMessage
  | CombatResultMessage
  | ItemUsedMessage
  | AbilityResultMessage;

// ---------------------------------------------------------------------------
// Outbound (client → server)
// ---------------------------------------------------------------------------

export interface JoinLobbyMsg {
  type: 'join_lobby';
  role: 'agent' | 'hunter';
  character: string;
  board?: string;
}

export interface StartGameMsg {
  type: 'start_game';
}

export interface PickItemsMsg {
  type: 'pick_items';
  items: string[];
}

export interface StartAgentTurnMsg {
  type: 'start_agent_turn';
}

export interface SubmitPathMsg {
  type: 'submit_path';
  path: string[];
}

export interface EndAgentTurnMsg {
  type: 'end_agent_turn';
}

export interface SetHunterOrderMsg {
  type: 'set_hunter_order';
  order: string[];
}

export interface RetractHunterOrderMsg {
  type: 'retract_hunter_order';
}

export interface StartHunterTurnMsg {
  type: 'start_hunter_turn';
}

export interface SubmitHunterMoveMsg {
  type: 'submit_hunter_move';
  path: string[];
}

export interface SubmitVehicleMoveMsg {
  type: 'submit_vehicle_move';
  path: string[];
}

export interface ExitVehicleMsg {
  type: 'exit_vehicle';
  cell: string;
}

export interface SubmitAttackMsg {
  type: 'submit_attack';
}

export interface EndHunterTurnMsg {
  type: 'end_hunter_turn';
}

export interface UseItemMsg {
  type: 'use_item';
  item_key: string;
  target_cell?: string;    // cell-targeted items (flash_bang, smoke_grenade, etc.)
  target_player?: string;  // player-targeted items (smoke_dagger, tangle_line)
}

export interface UseAbilityMsg {
  type: 'use_ability';
  ability_name: string;
  direction?: string;  // Clairvoyance: NE | NW | SE | SW
}

export interface LeaveGameMsg {
  type: 'leave_game';
}

export type OutboundMessage =
  | JoinLobbyMsg
  | StartGameMsg
  | PickItemsMsg
  | LeaveGameMsg
  | StartAgentTurnMsg
  | SubmitPathMsg
  | EndAgentTurnMsg
  | SetHunterOrderMsg
  | RetractHunterOrderMsg
  | StartHunterTurnMsg
  | SubmitHunterMoveMsg
  | SubmitVehicleMoveMsg
  | ExitVehicleMsg
  | SubmitAttackMsg
  | EndHunterTurnMsg
  | UseItemMsg
  | UseAbilityMsg;
