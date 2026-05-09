import type { GameView } from '../types/game';

const COLS = 'ABCDEFGHIJKLMNOPQRSTUVW';

function chebyshevDistance(a: string, b: string): number {
  const colA = COLS.indexOf(a[0]);
  const rowA = parseInt(a.slice(1), 10);
  const colB = COLS.indexOf(b[0]);
  const rowB = parseInt(b.slice(1), 10);
  return Math.max(Math.abs(colA - colB), Math.abs(rowA - rowB));
}

export function buildPath(prev: string[], cell: string, moveSpeed: number, startCell: string): string[] {
  const lastIdx = prev.lastIndexOf(cell);
  if (lastIdx !== -1) return prev.slice(0, lastIdx);
  if (prev.length >= moveSpeed) return prev;
  const tip = prev.length > 0 ? prev[prev.length - 1] : startCell;
  if (chebyshevDistance(tip, cell) !== 1) return prev;
  return [...prev, cell];
}

export function getMoveSpeed(view: GameView, playerName: string): number {
  if (view.role === 'agent' && view.phase === 'AGENT_TURN') {
    return view.agent.move_speed;
  }
  if (view.role === 'hunter' && view.phase === 'HUNTER_TURN') {
    const me = view.hunters.find(h => h.player_name === playerName);
    if (me) return me.in_vehicle ? view.vehicle.move_budget_remaining : me.move_speed;
  }
  return Infinity;
}

export function getStartPosition(view: GameView, playerName: string): string | null {
  if (view.role === 'agent') return view.agent.position;
  const me = view.hunters.find(h => h.player_name === playerName);
  if (!me) return null;
  return me.in_vehicle ? view.vehicle.position : me.position;
}
