import { useState, useCallback, useRef } from 'react';
import type { LobbyPlayer, GameView, AgentGameView } from './types/game';
import { buildPath, getMoveSpeed, getStartPosition } from './utils/path';
import type { InboundMessage, OutboundMessage } from './types/ws';
import Lobby from './components/Lobby';
import SetupView from './components/SetupView';
import Board from './components/Board';
import ActionBar from './components/ActionBar';
import PlayerPanel from './components/PlayerPanel';
import AgentItems from './components/AgentItems';
import HunterAbilities from './components/HunterAbilities';
import DiceRoll from './components/DiceRoll';
import type { AbilityResultMessage, CombatResultMessage } from './types/ws';
import styles from './styles/App.module.css';

export default function App() {
  const [nameInput, setNameInput] = useState('');
  const [playerName, setPlayerName] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  const [lobbyPlayers, setLobbyPlayers] = useState<LobbyPlayer[]>([]);
  const [gameView, setGameView] = useState<GameView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingPath, setPendingPath] = useState<string[]>([]);
  const [combatResult, setCombatResult] = useState<CombatResultMessage | null>(null);
  const [abilityResult, setAbilityResult] = useState<AbilityResultMessage | null>(null);

  const send = useCallback((msg: OutboundMessage) => {
    wsRef.current?.send(JSON.stringify(msg));
  }, []);

  function connect() {
    const name = nameInput.trim();
    if (!name) return;

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/${encodeURIComponent(name)}`);

    ws.onopen = () => {
      setPlayerName(name);
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (e: MessageEvent) => {
      let msg: InboundMessage;
      try {
        msg = JSON.parse(e.data as string) as InboundMessage;
      } catch {
        return;
      }

      if (msg.type === 'lobby') {
        setLobbyPlayers(msg.players);
        setGameView(null);
        setPendingPath([]);
      } else if (msg.type === 'state') {
        setGameView(msg.data);
        setPendingPath([]);
      } else if (msg.type === 'error') {
        setError(msg.detail);
      } else if (msg.type === 'game_over') {
        setError(`Game over: ${msg.result}`);
      } else if (msg.type === 'combat_result') {
        setCombatResult(msg);
      } else if (msg.type === 'ability_result') {
        setAbilityResult(msg);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setPlayerName('');
      setGameView(null);
      setLobbyPlayers([]);
      wsRef.current = null;
    };

    wsRef.current = ws;
  }

  function handleCellClick(cell: string) {
    if (!gameView) return;
    const moveSpeed = getMoveSpeed(gameView, playerName);
    const startCell = getStartPosition(gameView, playerName);
    if (!startCell) return;
    setPendingPath(prev => buildPath(prev, cell, moveSpeed, startCell));
  }

  function clearPath() {
    setPendingPath([]);
  }

  function leave() {
    send({ type: 'leave_game' });
    wsRef.current?.close();
  }

  if (!connected) {
    return (
      <div className={styles.connect}>
        <h1>Specter Ops</h1>
        <input
          className={styles.nameInput}
          placeholder="Your name"
          value={nameInput}
          onChange={e => setNameInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && connect()}
        />
        <button className={styles.btn} onClick={connect}>Connect</button>
      </div>
    );
  }

  return (
    <div className={styles.app}>
      <button className={styles.leaveBtn} onClick={leave}>Leave</button>
      {combatResult && (
        <DiceRoll
          attacker={combatResult.attacker}
          hit={combatResult.hit}
          roll={combatResult.roll}
          distance={combatResult.distance}
          onDone={() => setCombatResult(null)}
        />
      )}
      {error && (
        <div className={styles.error} onClick={() => setError(null)}>
          {error}
        </div>
      )}
      {abilityResult && (
        <div className={styles.error} onClick={() => setAbilityResult(null)}>
          {abilityResult.ability}: {JSON.stringify(Object.fromEntries(
            Object.entries(abilityResult).filter(([k]) => k !== 'type' && k !== 'ability')
          ))}
        </div>
      )}

      {!gameView ? (
        <Lobby
          players={lobbyPlayers}
          playerName={playerName}
          send={send}
        />
      ) : gameView.phase === 'SETUP' && gameView.role === 'agent' ? (
        <SetupView view={gameView as AgentGameView} send={send} />
      ) : (
        <div className={styles.game}>
          {gameView.phase === 'SETUP' && (
            <div className={styles.setupBanner}>
              Waiting for the agent to select items before the game can begin…
            </div>
          )}
          <Board
            view={gameView}
            playerName={playerName}
            pendingPath={pendingPath}
            onCellClick={handleCellClick}
          />
          <div className={styles.sidebar}>
            <PlayerPanel view={gameView} playerName={playerName} />
            <ActionBar
              view={gameView}
              playerName={playerName}
              pendingPath={pendingPath}
              send={send}
              clearPath={clearPath}
            />
            {gameView.role === 'agent' && (
              <div className={styles.itemsFooter}>
                <AgentItems view={gameView} send={send} />
              </div>
            )}
            {gameView.role === 'hunter' && (
              <div className={styles.itemsFooter}>
                <HunterAbilities view={gameView} playerName={playerName} send={send} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
