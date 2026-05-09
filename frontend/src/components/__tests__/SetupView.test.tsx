import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SetupView from '../SetupView';
import type { AgentGameView, AvailableItem } from '../../types/game';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const SMOKE: AvailableItem = { key: 'smoke', name: 'Smoke Grenade', charges: 1, copies: 1, ability: 'Blocks LOS' };
const GUN: AvailableItem   = { key: 'gun',   name: 'Gun',           charges: 2, copies: 2, ability: 'Ranged attack' };
const EMP: AvailableItem   = { key: 'emp',   name: 'EMP',           charges: 1, copies: 1, ability: 'Stuns hunter' };
const FLASH: AvailableItem = { key: 'flash', name: 'Flashbang',     charges: 1, copies: 1, ability: 'Blinds hunter' };

function makeView(items: AvailableItem[], maxEquipment = 3): AgentGameView {
  return {
    role: 'agent',
    board_name: 'shadow_of_babel',
    round_number: 1,
    phase: 'SETUP',
    win_condition: 'NONE',
    agent_escaped: false,
    escape_points: [],
    objectives: [],
    objectives_visible: true,
    active_obstacles: [],
    active_barriers: [],
    agent: {
      character: '', position: 'N1', health: 4, max_health: 4, move_speed: 4,
      identity_revealed: false, pending_objectives: [], public_objectives: [],
      last_seen_cell: null, path_this_turn: [], status_effects: [], items: [],
    },
    hunters: [],
    vehicle: { name: 'car', position: 'K17', move_speed: 6, move_budget_remaining: 6, occupied_by: null, path_this_round: [] },
    hunter_order: [],
    active_hunter_index: 0,
    available_items: items,
    max_equipment: maxEquipment,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('SetupView', () => {
  it('renders a card for each copy of each item', () => {
    render(<SetupView view={makeView([SMOKE, GUN])} send={vi.fn()} />);
    expect(screen.getByRole('button', { name: /smoke grenade/i })).toBeInTheDocument();
    // GUN has copies: 2, so two cards should appear
    expect(screen.getAllByRole('button', { name: /^gun/i })).toHaveLength(2);
  });

  it('selecting an item increments the count display', async () => {
    render(<SetupView view={makeView([SMOKE, GUN])} send={vi.fn()} />);
    expect(screen.getByText(/0 \/ 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /smoke grenade/i }));
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
  });

  it('deselecting an item decrements the count', async () => {
    render(<SetupView view={makeView([SMOKE, GUN])} send={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /smoke grenade/i }));
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /smoke grenade/i }));
    expect(screen.getByText(/0 \/ 3/)).toBeInTheDocument();
  });

  it('cannot select more items than maxEquipment', async () => {
    render(<SetupView view={makeView([SMOKE, EMP, FLASH, GUN], 2)} send={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /smoke grenade/i }));
    await userEvent.click(screen.getByRole('button', { name: /emp/i }));
    expect(screen.getByText(/2 \/ 2/)).toBeInTheDocument();
    // Flashbang click should be a no-op
    await userEvent.click(screen.getByRole('button', { name: /flashbang/i }));
    expect(screen.getByText(/2 \/ 2/)).toBeInTheDocument();
  });

  it('can select both copies of a multi-copy item', async () => {
    render(<SetupView view={makeView([GUN])} send={vi.fn()} />);
    const [copy1, copy2] = screen.getAllByRole('button', { name: /^gun/i });
    await userEvent.click(copy1);
    await userEvent.click(copy2);
    expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
  });

  it('deselecting one copy of a multi-copy item leaves the other selected', async () => {
    render(<SetupView view={makeView([GUN])} send={vi.fn()} />);
    const [copy1, copy2] = screen.getAllByRole('button', { name: /^gun/i });
    await userEvent.click(copy1);
    await userEvent.click(copy2);
    expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
    await userEvent.click(copy2);
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
  });

  it('confirm button sends pick_items with the selected keys', async () => {
    const send = vi.fn();
    render(<SetupView view={makeView([SMOKE, EMP])} send={send} />);
    await userEvent.click(screen.getByRole('button', { name: /smoke grenade/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm items/i }));
    expect(send).toHaveBeenCalledWith({ type: 'pick_items', items: ['smoke'] });
  });

  it('confirm with no selection sends an empty items array', async () => {
    const send = vi.fn();
    render(<SetupView view={makeView([SMOKE])} send={send} />);
    await userEvent.click(screen.getByRole('button', { name: /confirm items/i }));
    expect(send).toHaveBeenCalledWith({ type: 'pick_items', items: [] });
  });
});
