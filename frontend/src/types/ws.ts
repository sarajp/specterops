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

export type InboundMessage =
  | LobbyMessage
  | StateMessage
  | ErrorMessage
  | GameOverMessage
  | CombatResultMessage;

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

export interface SubmitAttackMsg {
  type: 'submit_attack';
}

export interface EndHunterTurnMsg {
  type: 'end_hunter_turn';
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
  | SubmitAttackMsg
  | EndHunterTurnMsg;
