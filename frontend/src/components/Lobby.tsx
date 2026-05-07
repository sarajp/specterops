import { useState } from 'react';
import type { LobbyPlayer } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import boardSob from '../assets/board_sob.png';
import boardBc from '../assets/board_bc.jpg';
import boardAa from '../assets/board_aa.jpg';
import styles from '../styles/Lobby.module.css';

const BOARD_THUMBS: Record<string, string> = {
  'Shadow of Babel': boardSob,
  'Broken Covenant': boardBc,
  'Arctic Archives': boardAa,
};

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
  const [board, setBoard] = useState('Shadow of Babel');

  const agentTaken = players.some(
    p => p.player_name !== playerName && p.role === 'agent'
  );

  const myEntry = players.find(p => p.player_name === playerName);
  const isAgent = myEntry?.role === 'agent';
  const canStart = isAgent && !!myEntry?.character && players.some(p => p.role === 'hunter');

  function join(char: string, charRole: 'agent' | 'hunter') {
    if (charRole === 'agent' && agentTaken) return;
    send({
      type: 'join_lobby',
      role: charRole,
      character: char,
      ...(charRole === 'agent' ? { board } : {}),
    });
  }

  function handleBoardChange(b: string) {
    setBoard(b);
    if (myEntry?.role === 'agent' && myEntry.character) {
      send({ type: 'join_lobby', role: 'agent', character: myEntry.character, board: b });
    }
  }

  function renderCharCard(
    c: { key: string; name: string; speed: number },
    charRole: 'agent' | 'hunter',
    imgFn: (key: string) => string
  ) {
    const claimer = players.find(p => p.character === c.key);
    const isMe = claimer?.player_name === playerName;
    const isTaken = !!claimer && !isMe;
    const isDisabled = isTaken || (charRole === 'agent' && agentTaken && !isMe);

    // Hunters cannot see which agent character was picked — grey all agent cards
    const hunterViewingAgent = charRole === 'agent' && !isAgent;
    const showGreyed = isTaken || (hunterViewingAgent && agentTaken);
    const showSelected = isMe && !hunterViewingAgent;

    return (
      <button
        key={c.key}
        className={`${styles.charCard} ${showGreyed ? styles.taken : ''} ${showSelected ? styles.selected : ''}`}
        onClick={() => !isDisabled && join(c.key, charRole)}
        disabled={isDisabled}
        title={hunterViewingAgent ? (agentTaken ? 'Agent slot taken' : c.name) : (isTaken ? `Taken by ${claimer!.player_name}` : c.name)}
      >
        <img src={imgFn(c.key)} alt={c.name} className={styles.charImg} />
        {!hunterViewingAgent && claimer && (
          <span className={isMe ? styles.claimerOverlayMe : styles.claimerOverlay}>
            {claimer.player_name}
          </span>
        )}
      </button>
    );
  }

  const agentBoard = players.find(p => p.role === 'agent')?.board ?? board;

  return (
    <div className={styles.lobby}>

      <div className={styles.main}>
        <section className={`${styles.section} ${styles.agentSection}`}>
          <h2>Agent</h2>
          <div className={styles.charGrid}>
            {AGENT_CHARS.map(c => renderCharCard(c, 'agent', agentImg))}
          </div>
        </section>

        <section className={`${styles.section} ${styles.hunterSection}`}>
          <h2>Hunters</h2>
          <div className={styles.charGrid}>
            {HUNTER_CHARS.map(c => renderCharCard(c, 'hunter', hunterImg))}
          </div>
        </section>
      </div>

      <div className={styles.sidebar}>
        <section className={styles.section}>
          <h2>
            Board
          </h2>
          <div className={styles.boardOptions}>
            {BOARDS.map(b => (
              <button
                key={b}
                className={`${styles.boardCard} ${agentBoard === b ? styles.active : ''}`}
                onClick={() => isAgent && handleBoardChange(b)}
                disabled={!isAgent}
              >
                <div className={styles.imgWrap}>
                  <img src={BOARD_THUMBS[b]} alt={b} />
                </div>
                <span>{b}</span>
              </button>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h2>Players <span className={styles.sectionHint}>{players.length} / 5</span></h2>
          <div className={styles.playerList}>
            {players.length === 0
              ? <span className={styles.emptyHint}>No one yet</span>
              : players.map(p => {
                  const char = [...AGENT_CHARS, ...HUNTER_CHARS].find(c => c.key === p.character);
                  const isMe = p.player_name === playerName;
                  return (
                    <div key={p.player_name} className={styles.playerEntry}>
                      <span className={`${styles.roleTag} ${p.role === 'agent' ? styles.agentTag : styles.hunterTag}`}>
                        {p.role === 'agent' ? 'A' : 'H'}
                      </span>
                      <span className={`${styles.playerName} ${isMe ? styles.playerNameMe : ''}`}>
                        {p.player_name}
                      </span>
                      <span className={styles.charName}>
                        {p.role === 'agent' && !isAgent ? '—' : (char?.name ?? p.character)}
                      </span>
                    </div>
                  );
                })
            }
          </div>
        </section>
      </div>

      {isAgent && (
        <button
          className={styles.startBtn}
          disabled={!canStart}
          onClick={() => send({ type: 'start_game' })}
        >
          {canStart ? 'Start Game' : 'Waiting for hunters…'}
        </button>
      )}
    </div>
  );
}
