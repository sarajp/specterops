import { useState } from 'react';
import type { AgentGameView, ItemState } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import ItemCard from './ItemCard';
import { getItemImage } from '../utils/itemImages';
import styles from '../styles/AgentItems.module.css';

interface Props {
  view: AgentGameView;
  send: (msg: OutboundMessage) => void;
}

export default function AgentItems({ view, send }: Props) {
  const [activeItem, setActiveItem] = useState<ItemState | null>(null);

  if (view.agent.items.length === 0) return null;

  function canUse(item: ItemState): boolean {
    if (view.phase !== 'AGENT_TURN') return false;
    if (view.agent.item_used_this_turn) return false;
    if (item.charges <= 0 || item.tapped) return false;
    if (item.key === 'med_kit' && view.agent.path_this_turn.length > 1) return false;
    return true;
  }

  function useItem(item: ItemState) {
    send({ type: 'use_item', item_key: item.key });
    setActiveItem(null);
  }

  return (
    <div className={styles.wrap}>
      {view.agent.items.map(item => (
        <ItemCard
          key={item.key}
          itemKey={item.key}
          name={item.name}
          charges={item.charges}
          tapped={item.tapped}
          onClick={() => setActiveItem(item)}
        />
      ))}

      {activeItem && (
        <div className={styles.overlay} onClick={() => setActiveItem(null)}>
          <div className={styles.zoom} onClick={e => e.stopPropagation()}>
            <div className={styles.zoomImgOuter}>
              <img src={getItemImage(activeItem.key)} alt={activeItem.name} className={styles.zoomImg} />
            </div>
            <div className={styles.zoomActions}>
              <button
                className={styles.useBtn}
                disabled={!canUse(activeItem)}
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
