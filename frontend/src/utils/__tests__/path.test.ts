import { describe, it, expect } from 'vitest';
import { buildPath, getMoveSpeed } from '../path';
import type { AgentGameView, HunterGameView } from '../../types/game';

// ── buildPath ────────────────────────────────────────────────────────────────

describe('buildPath', () => {
  it('appends a new cell when under the move limit', () => {
    expect(buildPath(['A1', 'A2'], 'A3', 4)).toEqual(['A1', 'A2', 'A3']);
  });

  it('starts a path from empty', () => {
    expect(buildPath([], 'A1', 4)).toEqual(['A1']);
  });

  it('does not append when at the move limit', () => {
    expect(buildPath(['A1', 'A2', 'A3', 'A4'], 'A5', 4)).toEqual(['A1', 'A2', 'A3', 'A4']);
  });

  it('backtracks to a middle cell already in the path', () => {
    expect(buildPath(['A1', 'A2', 'A3', 'A4'], 'A2', 4)).toEqual(['A1', 'A2']);
  });

  it('backtracks to the start cell', () => {
    expect(buildPath(['A1', 'A2', 'A3'], 'A1', 4)).toEqual(['A1']);
  });

  it('clicking the current last cell is a no-op', () => {
    expect(buildPath(['A1', 'A2', 'A3'], 'A3', 4)).toEqual(['A1', 'A2', 'A3']);
  });

  it('uses lastIndexOf when a cell appears twice — snaps to the later occurrence', () => {
    // path visited A1 twice after a backtrack; clicking A1 again is a no-op
    expect(buildPath(['A1', 'A2', 'A1'], 'A1', 4)).toEqual(['A1', 'A2', 'A1']);
  });

  it('always appends when moveSpeed is Infinity (out-of-turn guard is off)', () => {
    const path = Array.from({ length: 10 }, (_, i) => `A${i + 1}`);
    expect(buildPath(path, 'B1', Infinity)).toEqual([...path, 'B1']);
  });
});

// ── getMoveSpeed ─────────────────────────────────────────────────────────────

describe('getMoveSpeed', () => {
  it("returns the agent's move_speed during AGENT_TURN", () => {
    const view = {
      role: 'agent',
      phase: 'AGENT_TURN',
      agent: { move_speed: 4 },
    } as AgentGameView;
    expect(getMoveSpeed(view, 'alice')).toBe(4);
  });

  it("returns the matching hunter's move_speed during HUNTER_TURN", () => {
    const view = {
      role: 'hunter',
      phase: 'HUNTER_TURN',
      hunters: [
        { player_name: 'alice', move_speed: 3 },
        { player_name: 'bob', move_speed: 5 },
      ],
    } as HunterGameView;
    expect(getMoveSpeed(view, 'alice')).toBe(3);
  });

  it('returns Infinity for the agent during HUNTER_TURN', () => {
    const view = {
      role: 'agent',
      phase: 'HUNTER_TURN',
      agent: { move_speed: 4 },
    } as AgentGameView;
    expect(getMoveSpeed(view, 'alice')).toBe(Infinity);
  });

  it('returns Infinity for a hunter during AGENT_TURN', () => {
    const view = {
      role: 'hunter',
      phase: 'AGENT_TURN',
      hunters: [{ player_name: 'alice', move_speed: 3 }],
    } as HunterGameView;
    expect(getMoveSpeed(view, 'alice')).toBe(Infinity);
  });

  it('returns Infinity when playerName is not in the hunters list', () => {
    const view = {
      role: 'hunter',
      phase: 'HUNTER_TURN',
      hunters: [{ player_name: 'bob', move_speed: 3 }],
    } as HunterGameView;
    expect(getMoveSpeed(view, 'alice')).toBe(Infinity);
  });
});
