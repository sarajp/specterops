import type { GameView } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import styles from '../styles/ActionBar.module.css';

interface Props {
  view: GameView;
  playerName: string;
  pendingPath: string[];
  send: (msg: OutboundMessage) => void;
  clearPath: () => void;
}

export default function ActionBar({ view, playerName, pendingPath, send, clearPath }: Props) {
  const isAgent = view.role === 'agent';
  const phase = view.phase;

  const activeHunterName = view.hunter_order[view.active_hunter_index] ?? null;
  const isMyHunterTurn = !isAgent && phase === 'HUNTER_TURN' && activeHunterName === playerName;

  const myHunter = !isAgent
    ? view.hunters.find(h => h.player_name === playerName)
    : null;

  const agentVisible = !isAgent && !!view.agent.position;
  const canAttack = isMyHunterTurn && myHunter?.moved_this_turn && agentVisible;

  function submitPath() {
    if (pendingPath.length === 0) return;
    if (isAgent) {
      send({ type: 'submit_path', path: pendingPath });
    } else {
      send({ type: 'submit_hunter_move', path: pendingPath });
    }
    clearPath();
  }

  function setHunterOrder() {
    const order = view.hunters.map(h => h.player_name);
    send({ type: 'set_hunter_order', order });
  }

  // ── Agent controls ──────────────────────────────────────────
  if (isAgent) {
    if (phase === 'SETUP') {
      return (
        <div className={styles.bar}>
          <p className={styles.hint}>Waiting for hunters to set turn order…</p>
        </div>
      );
    }

    if (phase === 'HUNTER_NEGOTIATE') {
      return (
        <div className={styles.bar}>
          <p className={styles.hint}>Hunters are negotiating turn order.</p>
        </div>
      );
    }

    if (phase === 'HUNTER_TURN') {
      return (
        <div className={styles.bar}>
          <p className={styles.hint}>Hunter turn: {activeHunterName}</p>
        </div>
      );
    }

    if (phase === 'AGENT_TURN') {
      return (
        <div className={styles.bar}>
          {pendingPath.length === 0 ? (
            <p className={styles.hint}>Click cells to build your path.</p>
          ) : (
            <>
              <span className={styles.pathInfo}>{pendingPath.length} steps</span>
              <button className={styles.btn} onClick={submitPath}>Submit Move</button>
              <button className={styles.btnSecondary} onClick={clearPath}>Clear</button>
            </>
          )}
          <button className={styles.btnEnd} onClick={() => send({ type: 'end_agent_turn' })}>
            End Turn
          </button>
        </div>
      );
    }

    // GAME_OVER
    return <div className={styles.bar}><p className={styles.hint}>Game over.</p></div>;
  }

  // ── Hunter controls ──────────────────────────────────────────
  if (phase === 'SETUP') {
    return (
      <div className={styles.bar}>
        <button className={styles.btn} onClick={() => send({ type: 'start_agent_turn' })}>
          Start Agent Turn
        </button>
      </div>
    );
  }

  if (phase === 'AGENT_TURN') {
    return (
      <div className={styles.bar}>
        <p className={styles.hint}>Agent is taking their turn.</p>
      </div>
    );
  }

  if (phase === 'HUNTER_NEGOTIATE') {
    return (
      <div className={styles.bar}>
        <p className={styles.hint}>Set turn order (current order kept):</p>
        <button className={styles.btn} onClick={setHunterOrder}>
          Confirm Order
        </button>
      </div>
    );
  }

  if (phase === 'HUNTER_TURN') {
    if (!isMyHunterTurn) {
      return (
        <div className={styles.bar}>
          <p className={styles.hint}>Waiting for {activeHunterName}…</p>
        </div>
      );
    }

    return (
      <div className={styles.bar}>
        {!myHunter?.moved_this_turn ? (
          pendingPath.length === 0 ? (
            <p className={styles.hint}>Click cells to move, or submit empty to stay.</p>
          ) : (
            <>
              <span className={styles.pathInfo}>{pendingPath.length - 1} steps</span>
              <button className={styles.btn} onClick={submitPath}>Submit Move</button>
              <button className={styles.btnSecondary} onClick={clearPath}>Clear</button>
            </>
          )
        ) : (
          <>
            {canAttack && (
              <button className={styles.btnAttack} onClick={() => send({ type: 'submit_attack' })}>
                Attack
              </button>
            )}
            <button className={styles.btnEnd} onClick={() => send({ type: 'end_hunter_turn' })}>
              End Turn
            </button>
          </>
        )}
      </div>
    );
  }

  return <div className={styles.bar}><p className={styles.hint}>Game over.</p></div>;
}
