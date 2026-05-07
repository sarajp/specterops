import type { GameView } from '../types/game';

export function buildPath(prev: string[], cell: string, moveSpeed: number): string[] {
  const lastIdx = prev.lastIndexOf(cell);
  if (lastIdx !== -1) return prev.slice(0, lastIdx + 1);
  if (prev.length >= moveSpeed) return prev;
  return [...prev, cell];
}

export function getMoveSpeed(view: GameView, playerName: string): number {
  if (view.role === 'agent' && view.phase === 'AGENT_TURN') {
    return view.agent.move_speed;
  }
  if (view.role === 'hunter' && view.phase === 'HUNTER_TURN') {
    const me = view.hunters.find(h => h.player_name === playerName);
    if (me) return me.move_speed;
  }
  return Infinity;
}
