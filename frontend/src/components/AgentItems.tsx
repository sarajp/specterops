import { useState } from 'react';
import type { AgentGameView, ItemState } from '../types/game';
import ItemCard from './ItemCard';
import styles from '../styles/AgentItems.module.css';

interface Props {
  view: AgentGameView;
}

export default function AgentItems({ view }: Props) {
  const [activeItem, setActiveItem] = useState<ItemState | null>(null);

  if (view.agent.items.length === 0) return null;

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
            <ItemCard
              itemKey={activeItem.key}
              name={activeItem.name}
              charges={activeItem.charges}
              tapped={activeItem.tapped}
            />
            <div className={styles.zoomActions}>
              <button className={styles.useBtn} disabled>
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
