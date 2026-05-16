import { useState } from 'react';
import type { AgentGameView, ItemState } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import ItemCard from './ItemCard';
import { getItemImage } from '../utils/itemImages';
import styles from '../styles/AgentItems.module.css';

// Items that require the agent to type a cell string before using
const NEEDS_CELL_TARGET = new Set([
  'flash_bang', 'smoke_grenade', 'concussion_grenade',
  'holo_decoy', 'proximity_mine',
]);

// Items that require selecting a hunter by name before using
const NEEDS_PLAYER_TARGET = new Set(['smoke_dagger', 'tangle_line']);

interface Props {
  view: AgentGameView;
  send: (msg: OutboundMessage) => void;
}

export default function AgentItems({ view, send }: Props) {
  const [activeItem, setActiveItem] = useState<ItemState | null>(null);
  const [targetCell, setTargetCell] = useState('');
  const [targetPlayer, setTargetPlayer] = useState('');

  if (view.agent.items.length === 0) return null;

  function canUse(item: ItemState): boolean {
    if (view.phase !== 'AGENT_TURN') return false;
    if (view.agent.item_used_this_turn) return false;
    if (item.tapped) return false;
    if (item.key !== 'proximity_mine' && item.key !== 'pulse_blades' && item.charges <= 0) return false;
    if (item.key === 'med_kit' && view.agent.path_this_turn.length > 1) return false;
    return true;
  }

  function openItem(item: ItemState) {
    setActiveItem(item);
    setTargetCell('');
    setTargetPlayer('');
  }

  function useItem(item: ItemState) {
    const msg: Parameters<typeof send>[0] = { type: 'use_item', item_key: item.key } as any;
    if (NEEDS_CELL_TARGET.has(item.key) && targetCell.trim()) {
      (msg as any).target_cell = targetCell.trim().toUpperCase();
    }
    if (NEEDS_PLAYER_TARGET.has(item.key) && targetPlayer) {
      (msg as any).target_player = targetPlayer;
    }
    send(msg);
    setActiveItem(null);
  }

  function needsTarget(item: ItemState): boolean {
    return NEEDS_CELL_TARGET.has(item.key) || NEEDS_PLAYER_TARGET.has(item.key);
  }

  function targetReady(item: ItemState): boolean {
    if (NEEDS_CELL_TARGET.has(item.key)) return targetCell.trim().length > 0;
    if (NEEDS_PLAYER_TARGET.has(item.key)) return targetPlayer.length > 0;
    return true;
  }

  const hunterNames = view.hunters.map(h => h.player_name);

  return (
    <div className={styles.wrap}>
      {view.agent.items.map(item => (
        <ItemCard
          key={item.key}
          itemKey={item.key}
          name={item.name}
          charges={item.charges}
          tapped={item.tapped}
          onClick={() => openItem(item)}
        />
      ))}

      {activeItem && (
        <div className={styles.overlay} onClick={() => setActiveItem(null)}>
          <div className={styles.zoom} onClick={e => e.stopPropagation()}>
            <div className={styles.zoomImgOuter}>
              <img src={getItemImage(activeItem.key)} alt={activeItem.name} className={styles.zoomImg} />
            </div>

            {needsTarget(activeItem) && (
              <div className={styles.targetRow}>
                {NEEDS_CELL_TARGET.has(activeItem.key) && (
                  <input
                    className={styles.targetInput}
                    placeholder="Target cell (e.g. K5)"
                    value={targetCell}
                    onChange={e => setTargetCell(e.target.value)}
                  />
                )}
                {NEEDS_PLAYER_TARGET.has(activeItem.key) && (
                  <select
                    className={styles.targetInput}
                    value={targetPlayer}
                    onChange={e => setTargetPlayer(e.target.value)}
                  >
                    <option value="">Select hunter…</option>
                    {hunterNames.map(n => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            <div className={styles.zoomActions}>
              <button
                className={styles.useBtn}
                disabled={!canUse(activeItem) || !targetReady(activeItem)}
                onClick={() => useItem(activeItem)}
              >
                Use Item
              </button>
              <button className={styles.closeBtn} onClick={() => setActiveItem(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
