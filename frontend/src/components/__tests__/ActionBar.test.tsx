import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ActionBar from '../ActionBar';
import type {
  AgentGameView,
  HunterGameView,
  HunterStateView,
  VehicleStateView,
} from '../../types/game';

// ── Fixtures ────────────────────────────────────────────────────────────────

const baseVehicle: VehicleStateView = {
  name: 'car',
  position: 'K17',
  move_speed: 6,
  move_budget_remaining: 6,
  occupied_by: null,
  path_this_round: [],
};

function makeHunter(name: string, overrides: Partial<HunterStateView> = {}): HunterStateView {
  return {
    player_name: name,
    character: 'ghost',
    position: 'C5',
    move_speed: 3,
    in_vehicle: false,
    moved_this_turn: false,
    path_this_turn: [],
    status_effects: [],
    ...overrides,
  };
}

function makeAgentView(overrides: Partial<AgentGameView> = {}): AgentGameView {
  return {
    role: 'agent',
    board_name: 'shadow_of_babel',
    round_number: 1,
    phase: 'AGENT_TURN',
    win_condition: 'NONE',
    agent_escaped: false,
    escape_points: ['A3', 'N1', 'W3'],
    objectives: ['B5', 'G12', 'N20', 'T8'],
    objectives_visible: true,
    active_obstacles: [],
    active_barriers: [],
    agent: {
      character: 'wraith',
      position: 'N1',
      health: 4,
      max_health: 4,
      move_speed: 4,
      identity_revealed: false,
      pending_objectives: [],
      public_objectives: [],
      last_seen_cell: null,
      path_this_turn: [],
      status_effects: [],
      items: [],
    },
    hunters: [makeHunter('alice'), makeHunter('bob')],
    vehicle: baseVehicle,
    hunter_order: ['alice', 'bob'],
    active_hunter_index: 0,
    ...overrides,
  };
}

function makeHunterView(playerName: string, overrides: Partial<HunterGameView> = {}): HunterGameView {
  return {
    role: 'hunter',
    board_name: 'shadow_of_babel',
    round_number: 1,
    phase: 'HUNTER_TURN',
    win_condition: 'NONE',
    escape_points: ['A3', 'N1', 'W3'],
    objectives: ['B5', 'G12', 'N20', 'T8'],
    objectives_visible: true,
    active_obstacles: [],
    active_barriers: [],
    agent: {
      health: 4,
      max_health: 4,
      identity_revealed: false,
      public_objectives: [],
      last_seen_cell: null,
      status_effects: [],
    },
    hunters: [makeHunter(playerName), makeHunter('bob')],
    vehicle: baseVehicle,
    hunter_order: [playerName, 'bob'],
    active_hunter_index: 0,
    ...overrides,
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('ActionBar — agent role', () => {
  it('shows waiting message during SETUP', () => {
    render(
      <ActionBar
        view={makeAgentView({ phase: 'SETUP' })}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByText(/waiting for hunters/i)).toBeInTheDocument();
  });

  it('shows path hint when no path is pending during AGENT_TURN', () => {
    render(
      <ActionBar
        view={makeAgentView({ phase: 'AGENT_TURN' })}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByText(/click cells to build your path/i)).toBeInTheDocument();
  });

  it('shows Submit Move and Clear buttons when a path is pending', () => {
    render(
      <ActionBar
        view={makeAgentView({ phase: 'AGENT_TURN' })}
        playerName="alice"
        pendingPath={['N1', 'N2', 'N3']}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /submit move/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
  });

  it('calls send with submit_path and calls clearPath when Submit Move is clicked', async () => {
    const send = vi.fn();
    const clearPath = vi.fn();
    render(
      <ActionBar
        view={makeAgentView({ phase: 'AGENT_TURN' })}
        playerName="alice"
        pendingPath={['N1', 'N2']}
        send={send}
        clearPath={clearPath}
      />
    );
    await userEvent.click(screen.getByRole('button', { name: /submit move/i }));
    expect(send).toHaveBeenCalledWith({ type: 'submit_path', path: ['N1', 'N2'] });
    expect(clearPath).toHaveBeenCalled();
  });
});

describe('ActionBar — hunter role', () => {
  it('shows Confirm Order button during HUNTER_NEGOTIATE', () => {
    render(
      <ActionBar
        view={makeHunterView('alice', { phase: 'HUNTER_NEGOTIATE' })}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /confirm order/i })).toBeInTheDocument();
  });

  it('shows waiting message when it is another hunter\'s turn', () => {
    render(
      <ActionBar
        view={makeHunterView('alice', {
          hunter_order: ['bob', 'alice'],
          active_hunter_index: 0,
        })}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByText(/waiting for bob/i)).toBeInTheDocument();
  });

  it('shows movement hint on active hunter\'s turn before moving', () => {
    render(
      <ActionBar
        view={makeHunterView('alice')}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByText(/click cells to move/i)).toBeInTheDocument();
  });

  it('shows Attack button after moving when the agent is visible', () => {
    render(
      <ActionBar
        view={makeHunterView('alice', {
          hunters: [makeHunter('alice', { moved_this_turn: true }), makeHunter('bob')],
          agent: {
            health: 4,
            max_health: 4,
            identity_revealed: false,
            public_objectives: [],
            last_seen_cell: null,
            status_effects: [],
            position: 'G7',
          },
        })}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /attack/i })).toBeInTheDocument();
  });

  it('does not show Attack button when the agent is not visible', () => {
    render(
      <ActionBar
        view={makeHunterView('alice', {
          hunters: [makeHunter('alice', { moved_this_turn: true }), makeHunter('bob')],
        })}
        playerName="alice"
        pendingPath={[]}
        send={vi.fn()}
        clearPath={vi.fn()}
      />
    );
    expect(screen.queryByRole('button', { name: /attack/i })).not.toBeInTheDocument();
  });
});
