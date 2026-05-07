import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import PlayerPanel from '../PlayerPanel';
import type { AgentGameView, HunterGameView, HunterStateView } from '../../types/game';

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeHunter(name: string, overrides: Partial<HunterStateView> = {}): HunterStateView {
  return {
    player_name: name,
    character: 'beast',
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
    escape_points: [],
    objectives: [],
    objectives_visible: true,
    active_obstacles: [],
    active_barriers: [],
    agent: {
      character: 'raven',
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
    vehicle: { name: 'car', position: 'K17', move_speed: 6, move_budget_remaining: 6, occupied_by: null, path_this_round: [] },
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
    escape_points: [],
    objectives: [],
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
    vehicle: { name: 'car', position: 'K17', move_speed: 6, move_budget_remaining: 6, occupied_by: null, path_this_round: [] },
    hunter_order: [playerName, 'bob'],
    active_hunter_index: 0,
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PlayerPanel — display basics', () => {
  it('shows the round number', () => {
    render(<PlayerPanel view={makeAgentView({ round_number: 7 })} playerName="alice" />);
    expect(screen.getByText('7 / 40')).toBeInTheDocument();
  });

  it('replaces underscores in phase names with spaces', () => {
    render(<PlayerPanel view={makeAgentView({ phase: 'HUNTER_TURN' })} playerName="alice" />);
    expect(screen.getByText('HUNTER TURN')).toBeInTheDocument();
  });

  it('shows the active hunter name during HUNTER_TURN', () => {
    render(
      <PlayerPanel
        view={makeAgentView({ phase: 'HUNTER_TURN', hunter_order: ['alice', 'bob'], active_hunter_index: 0 })}
        playerName="alice"
      />
    );
    const activeRow = screen.getByText('Active').parentElement!;
    expect(within(activeRow).getByText('alice')).toBeInTheDocument();
  });

  it('does not show an active hunter label outside HUNTER_TURN', () => {
    render(<PlayerPanel view={makeAgentView({ phase: 'AGENT_TURN' })} playerName="alice" />);
    expect(screen.queryByText('Active')).not.toBeInTheDocument();
  });
});

describe('PlayerPanel — agent health', () => {
  it('renders filled and empty health circles', () => {
    render(
      <PlayerPanel
        view={makeAgentView({ agent: { ...makeAgentView().agent, health: 2, max_health: 4 } })}
        playerName="alice"
      />
    );
    expect(screen.getByText('●●○○')).toBeInTheDocument();
  });

  it('renders full health correctly', () => {
    render(<PlayerPanel view={makeAgentView()} playerName="alice" />);
    expect(screen.getByText('●●●●')).toBeInTheDocument();
  });
});

describe('PlayerPanel — last seen cell', () => {
  it('shows last seen cell when present', () => {
    render(
      <PlayerPanel
        view={makeAgentView({ agent: { ...makeAgentView().agent, last_seen_cell: 'G7' } })}
        playerName="alice"
      />
    );
    expect(screen.getByText('G7')).toBeInTheDocument();
  });

  it('does not show last seen row when null', () => {
    render(<PlayerPanel view={makeAgentView()} playerName="alice" />);
    expect(screen.queryByText('Last seen')).not.toBeInTheDocument();
  });
});

describe('PlayerPanel — role-gated agent info', () => {
  it('shows agent position to the agent', () => {
    render(
      <PlayerPanel
        view={makeAgentView({ agent: { ...makeAgentView().agent, position: 'N1' } })}
        playerName="alice"
      />
    );
    expect(screen.getByText('Position')).toBeInTheDocument();
    expect(screen.getByText('N1')).toBeInTheDocument();
  });

  it('does not show agent position to hunters', () => {
    render(<PlayerPanel view={makeHunterView('alice')} playerName="alice" />);
    // Scope to the Agent section — hunters legitimately see a Position row in their own "You" section
    const agentSection = screen.getByText('Agent').parentElement!;
    expect(within(agentSection).queryByText('Position')).not.toBeInTheDocument();
  });

  it('shows agent objectives as pending + public for the agent', () => {
    const agent = {
      ...makeAgentView().agent,
      public_objectives: ['B5', 'G12'],
      pending_objectives: ['N20'],
    };
    render(<PlayerPanel view={makeAgentView({ agent })} playerName="alice" />);
    const row = screen.getByText('Objectives').parentElement!;
    expect(within(row).getByText('3 / 3')).toBeInTheDocument();
  });

  it('shows only public objective count to hunters when > 0', () => {
    render(
      <PlayerPanel
        view={makeHunterView('alice', {
          agent: { health: 4, max_health: 4, identity_revealed: false, public_objectives: ['B5', 'G12'], last_seen_cell: null, status_effects: [] },
        })}
        playerName="alice"
      />
    );
    const row = screen.getByText('Objectives').parentElement!;
    expect(within(row).getByText('2')).toBeInTheDocument();
  });

  it('does not show objectives row to hunters when count is 0', () => {
    render(<PlayerPanel view={makeHunterView('alice')} playerName="alice" />);
    expect(screen.queryByText('Objectives')).not.toBeInTheDocument();
  });
});

describe('PlayerPanel — status effects', () => {
  it('shows agent status effects when present', () => {
    const agent = { ...makeAgentView().agent, status_effects: ['STUNNED' as const, 'FLASHBANGED' as const] };
    render(<PlayerPanel view={makeAgentView({ agent })} playerName="alice" />);
    expect(screen.getByText('STUNNED, FLASHBANGED')).toBeInTheDocument();
  });

  it('does not show agent effects row when empty', () => {
    render(<PlayerPanel view={makeAgentView()} playerName="alice" />);
    // No status effects — only the two "Effects" labels should be absent entirely
    expect(screen.queryByText('Effects')).not.toBeInTheDocument();
  });
});

describe('PlayerPanel — my hunter section', () => {
  it('shows hunter position and speed for the current hunter player', () => {
    render(
      <PlayerPanel
        view={makeHunterView('alice', {
          hunters: [makeHunter('alice', { position: 'D8', move_speed: 5, character: 'beast' }), makeHunter('bob')],
        })}
        playerName="alice"
      />
    );
    // Scope to the "You" section — D8 also appears in the all-hunters list
    const mySection = screen.getByText('You (beast)').parentElement!;
    expect(within(mySection).getByText('D8')).toBeInTheDocument();
    expect(within(mySection).getByText('5')).toBeInTheDocument();
  });

  it('does not show a "You" section for the agent', () => {
    render(<PlayerPanel view={makeAgentView()} playerName="alice" />);
    expect(screen.queryByText(/you \(/i)).not.toBeInTheDocument();
  });

  it('shows hunter status effects in the my-hunter section when present', () => {
    render(
      <PlayerPanel
        view={makeHunterView('alice', {
          hunters: [makeHunter('alice', { status_effects: ['STUNNED'] }), makeHunter('bob')],
        })}
        playerName="alice"
      />
    );
    expect(screen.getByText('STUNNED')).toBeInTheDocument();
  });
});

describe('PlayerPanel — hunters list', () => {
  it('lists all hunters by name', () => {
    render(
      <PlayerPanel
        view={makeHunterView('alice', { hunters: [makeHunter('alice'), makeHunter('bob'), makeHunter('carol')] })}
        playerName="alice"
      />
    );
    expect(screen.getAllByText('alice').length).toBeGreaterThan(0);
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('carol')).toBeInTheDocument();
  });
});
