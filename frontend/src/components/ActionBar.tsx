import { useState, useEffect } from 'react';
import type { GameView, HunterGameView } from '../types/game';
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

  const [localOrder, setLocalOrder] = useState<string[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  useEffect(() => {
    if (view.phase === 'HUNTER_NEGOTIATE') {
      setLocalOrder(
        view.hunter_order.length > 0
          ? [...view.hunter_order]
          : view.hunters.map(h => h.player_name)
      );
    }
  }, [view.phase]);

  function handleDrop(dropIdx: number) {
    if (dragIdx === null || dragIdx === dropIdx) { setDragIdx(null); return; }
    const next = [...localOrder];
    const [item] = next.splice(dragIdx, 1);
    next.splice(dropIdx, 0, item);
    setLocalOrder(next);
    setDragIdx(null);
  }

  function characterOf(pname: string) {
    return view.hunters.find(h => h.player_name === pname)?.character ?? pname;
  }

  function submitPath() {
    if (pendingPath.length === 0) return;
    const startPos = view.role === 'agent' ? view.agent.position : myHunter?.position;
    if (!startPos) return;
    const fullPath = [startPos, ...pendingPath];
    if (isAgent) {
      send({ type: 'submit_path', path: fullPath });
    } else {
      send({ type: 'submit_hunter_move', path: fullPath });
    }
    clearPath();
  }

  function submitVehicleMove() {
    if (pendingPath.length === 0) return;
    send({ type: 'submit_vehicle_move', path: [view.vehicle.position, ...pendingPath] });
    clearPath();
  }

  function exitVehicleTo(cell: string) {
    send({ type: 'exit_vehicle', cell });
    clearPath();
  }

  function vehicleAdjacentCells(): string[] {
    const cols = 'ABCDEFGHIJKLMNOPQRSTUVW';
    const pos = view.vehicle.position;
    const colIdx = cols.indexOf(pos[0]);
    const row = parseInt(pos.slice(1), 10);
    const result: string[] = [];
    for (let dc = -1; dc <= 1; dc++) {
      for (let dr = -1; dr <= 1; dr++) {
        if (dc === 0 && dr === 0) continue;
        const c = colIdx + dc;
        const r = row + dr;
        if (c >= 0 && c <= 22 && r >= 1 && r <= 32) {
          result.push(cols[c] + r);
        }
      }
    }
    return result;
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
    const hunterView = view as HunterGameView;
    const proposals = hunterView.hunter_order_proposals ?? {};
    const confirmedNames = Object.keys(proposals);
    const hasConfirmed = confirmedNames.includes(playerName);
    return (
      <div className={styles.bar}>
        {hunterView.order_mismatch && (
          <p className={styles.mismatch}>Orders didn't match — all confirmations cleared. Try again.</p>
        )}
        <div className={styles.orderWidget}>
          {localOrder.map((pname, idx) => (
            <div
              key={pname}
              className={`${styles.orderItem}${dragIdx === idx ? ` ${styles.dragging}` : ''}${hasConfirmed ? ` ${styles.locked}` : ''}`}
              draggable={!hasConfirmed}
              onDragStart={!hasConfirmed ? () => setDragIdx(idx) : undefined}
              onDragOver={!hasConfirmed ? e => e.preventDefault() : undefined}
              onDrop={!hasConfirmed ? () => handleDrop(idx) : undefined}
              onDragEnd={!hasConfirmed ? () => setDragIdx(null) : undefined}
            >
              <span className={styles.orderNum}>{idx + 1}</span>
              <span className={styles.orderName}>{characterOf(pname)}</span>
              {confirmedNames.includes(pname) && <span className={styles.confirmed}>✓</span>}
            </div>
          ))}
        </div>
        {hasConfirmed ? (
          <button className={styles.btnSecondary} onClick={() => send({ type: 'retract_hunter_order' })}>
            Unconfirm
          </button>
        ) : (
          <button className={styles.btn} onClick={() => send({ type: 'set_hunter_order', order: localOrder })}>
            Confirm Order
          </button>
        )}
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

    // ── In vehicle, not yet moved: can drive or exit ──────────────
    if (myHunter?.in_vehicle && !myHunter?.moved_this_turn) {
      return (
        <div className={styles.bar}>
          {pendingPath.length === 0 ? (
            <p className={styles.hint}>Click road cells to drive.</p>
          ) : (
            <>
              <span className={styles.pathInfo}>{pendingPath.length} steps</span>
              <button className={styles.btn} onClick={submitVehicleMove}>Move Vehicle</button>
            </>
          )}
          <span className={styles.hint}>Exit:</span>
          {vehicleAdjacentCells().map(cell => (
            <button key={cell} className={styles.btnSecondary} onClick={() => exitVehicleTo(cell)}>
              {cell}
            </button>
          ))}
          <button className={styles.btnEnd} onClick={() => send({ type: 'end_hunter_turn' })}>
            Stay / End Turn
          </button>
        </div>
      );
    }

    // ── In vehicle, drove this turn: can exit or stay ──────────────
    if (myHunter?.in_vehicle && myHunter?.moved_this_turn) {
      return (
        <div className={styles.bar}>
          <span className={styles.hint}>Exit:</span>
          {vehicleAdjacentCells().map(cell => (
            <button key={cell} className={styles.btnSecondary} onClick={() => exitVehicleTo(cell)}>
              {cell}
            </button>
          ))}
          <button className={styles.btnEnd} onClick={() => send({ type: 'end_hunter_turn' })}>
            Stay / End Turn
          </button>
        </div>
      );
    }

    // ── On board, not yet moved: foot move ──────────────────────────
    if (!myHunter?.moved_this_turn) {
      return (
        <div className={styles.bar}>
          {pendingPath.length === 0 ? (
            <p className={styles.hint}>Click cells to move, or submit empty to stay.</p>
          ) : (
            <>
              <span className={styles.pathInfo}>{pendingPath.length - 1} steps</span>
              <button className={styles.btn} onClick={submitPath}>Submit Move</button>
            </>
          )}
        </div>
      );
    }

    // ── On board, moved: attack + end ───────────────────────────────
    return (
      <div className={styles.bar}>
        {canAttack && (
          <button className={styles.btnAttack} onClick={() => send({ type: 'submit_attack' })}>
            Attack
          </button>
        )}
        <button className={styles.btnEnd} onClick={() => send({ type: 'end_hunter_turn' })}>
          End Turn
        </button>
      </div>
    );
  }

  return <div className={styles.bar}><p className={styles.hint}>Game over.</p></div>;
}
