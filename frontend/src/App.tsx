import { useState, useCallback, useRef } from 'react';
import type { LobbyPlayer, GameView, AgentGameView } from './types/game';
import type { InboundMessage, OutboundMessage } from './types/ws';
import Lobby from './components/Lobby';
import SetupView from './components/SetupView';
import Board from './components/Board';
import ActionBar from './components/ActionBar';
import PlayerPanel from './components/PlayerPanel';
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
    setPendingPath(prev => {
      const lastIdx = prev.lastIndexOf(cell);
      if (lastIdx !== -1) return prev.slice(0, lastIdx + 1);

      let moveSpeed = Infinity;
      if (gameView.role === 'agent' && gameView.phase === 'AGENT_TURN') {
        moveSpeed = gameView.agent.move_speed;
      } else if (gameView.role === 'hunter' && gameView.phase === 'HUNTER_TURN') {
        const me = gameView.hunters.find(h => h.player_name === playerName);
        if (me) moveSpeed = me.move_speed;
      }
      if (prev.length >= moveSpeed) return prev;

      return [...prev, cell];
    });
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
      {error && (
        <div className={styles.error} onClick={() => setError(null)}>
          {error}
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
          </div>
        </div>
      )}
    </div>
  );
}
