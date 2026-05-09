import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Lobby from '../Lobby';
import type { LobbyPlayer } from '../../types/game';

// ── Fixtures ─────────────────────────────────────────────────────────────────

function p(player_name: string, role: 'agent' | 'hunter', character = '', board = 'Shadow of Babel'): LobbyPlayer {
  return { player_name, role, character, board };
}

// ── Joining ───────────────────────────────────────────────────────────────────

describe('Lobby — joining', () => {
  it('clicking an agent character sends join_lobby with role agent and the board', async () => {
    const send = vi.fn();
    render(<Lobby players={[]} playerName="alice" send={send} />);
    await userEvent.click(screen.getByRole('button', { name: /raven/i }));
    expect(send).toHaveBeenCalledWith({
      type: 'join_lobby',
      role: 'agent',
      character: 'raven',
      board: 'Shadow of Babel',
    });
  });

  it('clicking a hunter character sends join_lobby with role hunter and no board', async () => {
    const send = vi.fn();
    render(<Lobby players={[]} playerName="alice" send={send} />);
    await userEvent.click(screen.getByRole('button', { name: /beast/i }));
    expect(send).toHaveBeenCalledWith({
      type: 'join_lobby',
      role: 'hunter',
      character: 'beast',
    });
  });

  it('agent cards are disabled when another player has claimed the agent slot', async () => {
    const send = vi.fn();
    // bob is the agent; alice is a hunter trying to view the lobby
    render(<Lobby players={[p('bob', 'agent', '')]} playerName="alice" send={send} />);
    await userEvent.click(screen.getByRole('button', { name: /raven/i }));
    expect(send).not.toHaveBeenCalled();
  });

  it('hunter cards are always clickable even when an agent slot is taken', async () => {
    const send = vi.fn();
    render(<Lobby players={[p('bob', 'agent', '')]} playerName="alice" send={send} />);
    await userEvent.click(screen.getByRole('button', { name: /beast/i }));
    expect(send).toHaveBeenCalledWith(expect.objectContaining({ type: 'join_lobby', role: 'hunter' }));
  });
});

// ── Agent character visibility ────────────────────────────────────────────────

describe('Lobby — agent character visibility', () => {
  it("hunters cannot identify which agent character was picked — all agent cards are disabled", async () => {
    const send = vi.fn();
    // Backend sends character: '' for agent in hunter's lobby view
    render(
      <Lobby
        players={[p('bob', 'agent', ''), p('alice', 'hunter', 'beast')]}
        playerName="alice"
        send={send}
      />
    );
    // All 8 agent character buttons should be disabled; none should be clickable
    const agentCharNames = ['Blue Jay', 'Cobra', 'Fox', 'Mantis', 'Orangutan', 'Panther', 'Raven', 'Spider'];
    for (const name of agentCharNames) {
      expect(screen.getByRole('button', { name: new RegExp(name, 'i') })).toBeDisabled();
    }
    // Clicking any agent card sends nothing
    await userEvent.click(screen.getByRole('button', { name: /raven/i }));
    expect(send).not.toHaveBeenCalled();
  });

  it("the agent sees their own character card as selected", () => {
    render(
      <Lobby
        players={[p('alice', 'agent', 'raven')]}
        playerName="alice"
        send={vi.fn()}
      />
    );
    // The raven card should not be disabled (it's the agent's own pick)
    expect(screen.getByRole('button', { name: /raven/i })).not.toBeDisabled();
  });
});

// ── Board selection ───────────────────────────────────────────────────────────

describe('Lobby — board selection', () => {
  it('board buttons are disabled for hunters', () => {
    render(
      <Lobby
        players={[p('alice', 'hunter', 'beast')]}
        playerName="alice"
        send={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /broken covenant/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /arctic archives/i })).toBeDisabled();
  });

  it('changing board while agent re-sends join_lobby with the new board', async () => {
    const send = vi.fn();
    render(
      <Lobby
        players={[p('alice', 'agent', 'raven', 'Shadow of Babel')]}
        playerName="alice"
        send={send}
      />
    );
    await userEvent.click(screen.getByRole('button', { name: /broken covenant/i }));
    expect(send).toHaveBeenCalledWith({
      type: 'join_lobby',
      role: 'agent',
      character: 'raven',
      board: 'Broken Covenant',
    });
  });
});

// ── Start button ──────────────────────────────────────────────────────────────

describe('Lobby — start button', () => {
  it('is not shown to hunters', () => {
    render(
      <Lobby
        players={[p('alice', 'hunter', 'beast')]}
        playerName="alice"
        send={vi.fn()}
      />
    );
    expect(screen.queryByRole('button', { name: /start game|need|select a character/i })).not.toBeInTheDocument();
  });

  it('is disabled and prompts for a character when agent has no character selected', () => {
    render(
      <Lobby
        players={[p('alice', 'agent', ''), p('bob', 'hunter', 'beast'), p('carol', 'hunter', 'heat')]}
        playerName="alice"
        send={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /select a character/i })).toBeDisabled();
  });

  it('is disabled and shows hunter count needed when fewer than 2 hunters', () => {
    render(
      <Lobby
        players={[p('alice', 'agent', 'raven'), p('bob', 'hunter', 'beast')]}
        playerName="alice"
        send={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /need 1 more hunter/i })).toBeDisabled();
  });

  it('is enabled and sends start_game when agent has character and 2+ hunters', async () => {
    const send = vi.fn();
    render(
      <Lobby
        players={[
          p('alice', 'agent', 'raven'),
          p('bob', 'hunter', 'beast'),
          p('carol', 'hunter', 'heat'),
        ]}
        playerName="alice"
        send={send}
      />
    );
    const btn = screen.getByRole('button', { name: /start game/i });
    expect(btn).not.toBeDisabled();
    await userEvent.click(btn);
    expect(send).toHaveBeenCalledWith({ type: 'start_game' });
  });
});
