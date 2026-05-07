import { useState } from 'react';
import type { LobbyPlayer } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import styles from '../styles/Lobby.module.css';

const AGENT_CHARS = [
  { key: 'blue_jay', name: 'Blue Jay', speed: 4 },
  { key: 'cobra', name: 'Cobra', speed: 4 },
  { key: 'fox', name: 'Fox', speed: 5 },
  { key: 'mantis', name: 'Mantis', speed: 4 },
  { key: 'orangutan', name: 'Orangutan', speed: 4 },
  { key: 'panther', name: 'Panther', speed: 4 },
  { key: 'raven', name: 'Raven', speed: 4 },
  { key: 'spider', name: 'Spider', speed: 4 },
];

const HUNTER_CHARS = [
  { key: 'beast', name: 'Beast', speed: 5 },
  { key: 'gun', name: 'Gun', speed: 4 },
  { key: 'heat', name: 'Heat', speed: 4 },
  { key: 'judge', name: 'Judge', speed: 4 },
  { key: 'prophet', name: 'Prophet', speed: 4 },
  { key: 'puppet', name: 'Puppet', speed: 4 },
  { key: 'tracker', name: 'Tracker', speed: 4 },
  { key: 'watcher', name: 'Watcher', speed: 4 },
];

const BOARDS = ['Shadow of Babel', 'Broken Covenant', 'Arctic Archives'];

const agentImgs = import.meta.glob<{ default: string }>('../assets/agent_assets/*.png', { eager: true });
const hunterImgs = import.meta.glob<{ default: string }>('../assets/hunter_assets/*.png', { eager: true });

function agentImg(key: string) {
  return agentImgs[`../assets/agent_assets/${key}.png`]?.default ?? '';
}
function hunterImg(key: string) {
  return hunterImgs[`../assets/hunter_assets/${key}.png`]?.default ?? '';
}

interface Props {
  players: LobbyPlayer[];
  playerName: string;
  send: (msg: OutboundMessage) => void;
}

export default function Lobby({ players, playerName, send }: Props) {
  const [role, setRole] = useState<'agent' | 'hunter'>('hunter');
  const [character, setCharacter] = useState('');
  const [board, setBoard] = useState('Shadow of Babel');

  const takenChars = new Set(
    players.filter(p => p.player_name !== playerName).map(p => p.character)
  );
  const agentTaken = players.some(
    p => p.player_name !== playerName && p.role === 'agent'
  );

  const myEntry = players.find(p => p.player_name === playerName);
  const isAgent = myEntry?.role === 'agent';
  const canStart = isAgent && !!myEntry?.character && players.some(p => p.role === 'hunter');

  const chars = role === 'agent' ? AGENT_CHARS : HUNTER_CHARS;
  const imgFn = role === 'agent' ? agentImg : hunterImg;

  function join(char: string) {
    if (role === 'agent' && agentTaken) return;
    setCharacter(char);
    send({
      type: 'join_lobby',
      role,
      character: char,
      ...(role === 'agent' ? { board } : {}),
    });
  }

  function handleRoleChange(r: 'agent' | 'hunter') {
    setRole(r);
    setCharacter('');
  }

  function handleBoardChange(b: string) {
    setBoard(b);
    if (myEntry?.role === 'agent' && myEntry.character) {
      send({ type: 'join_lobby', role: 'agent', character: myEntry.character, board: b });
    }
  }

  return (
    <div className={styles.lobby}>
      <div className={styles.picker}>
        <h2>Join as</h2>

        <div className={styles.roleToggle}>
          <button
            className={role === 'agent' ? styles.active : ''}
            onClick={() => handleRoleChange('agent')}
            disabled={agentTaken}
          >
            Agent {agentTaken ? '(taken)' : ''}
          </button>
          <button
            className={role === 'hunter' ? styles.active : ''}
            onClick={() => handleRoleChange('hunter')}
          >
            Hunter
          </button>
        </div>

        <div className={styles.charGrid}>
          {chars.map(c => {
            const taken = takenChars.has(c.key);
            const selected = myEntry?.character === c.key;
            return (
              <button
                key={c.key}
                className={`${styles.charCard} ${taken ? styles.taken : ''} ${selected ? styles.selected : ''}`}
                onClick={() => !taken && join(c.key)}
                disabled={taken}
                title={taken ? 'Already taken' : `Speed: ${c.speed}`}
              >
                <img src={imgFn(c.key)} alt={c.name} />
                <span>{c.name}</span>
                <span className={styles.speed}>Spd {c.speed}</span>
              </button>
            );
          })}
        </div>

        {role === 'agent' && (
          <div className={styles.boardPicker}>
            <h3>Board</h3>
            <div className={styles.boardOptions}>
              {BOARDS.map(b => (
                <button
                  key={b}
                  className={board === b ? styles.active : ''}
                  onClick={() => handleBoardChange(b)}
                >
                  {b}
                </button>
              ))}
            </div>
          </div>
        )}

        {isAgent && (
          <button
            className={styles.startBtn}
            disabled={!canStart}
            onClick={() => send({ type: 'start_game' })}
          >
            Start Game
          </button>
        )}
      </div>

      <div className={styles.playerList}>
        <h2>Players ({players.length})</h2>
        {players.length === 0 && <p className={styles.empty}>Waiting for players…</p>}
        {players.map(p => (
          <div key={p.player_name} className={styles.playerRow}>
            <span className={p.role === 'agent' ? styles.agentLabel : styles.hunterLabel}>
              {p.role === 'agent' ? 'AGENT' : 'HUNTER'}
            </span>
            <span className={styles.pName}>{p.player_name}</span>
            <span className={styles.pChar}>{p.character}</span>
            {p.role === 'agent' && p.board && (
              <span className={styles.pBoard}>· {p.board}</span>
            )}
          </div>
        ))}
        {!canStart && isAgent && (
          <p className={styles.hint}>Need at least one hunter to start.</p>
        )}
      </div>
    </div>
  );
}
