import { useState } from 'react';
import type { AgentGameView } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import styles from '../styles/SetupView.module.css';

interface Props {
  view: AgentGameView;
  send: (msg: OutboundMessage) => void;
}

export default function SetupView({ view, send }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const items = view.available_items ?? [];
  const maxItems = view.max_equipment ?? 3;

  // Expand each item into `copies` individual cards
  const cards = items.flatMap(item =>
    Array.from({ length: item.copies ?? 1 }, (_, i) => ({ ...item, copyIndex: i }))
  );

  function toggle(key: string, copyIndex: number) {
    const countSelected = selected.filter(k => k === key).length;
    const isThisCopySelected = copyIndex < countSelected;
    if (isThisCopySelected) {
      // deselect: remove the last instance of this key
      const idx = selected.lastIndexOf(key);
      setSelected(prev => [...prev.slice(0, idx), ...prev.slice(idx + 1)]);
    } else if (selected.length < maxItems) {
      setSelected(prev => [...prev, key]);
    }
  }

  return (
    <div className={styles.setup}>
      <h2 className={styles.title}>
        Select Items
        <span className={styles.hint}> — {selected.length} / {maxItems}</span>
      </h2>
      <div className={styles.itemGrid}>
        {cards.map(card => {
          const countSelected = selected.filter(k => k === card.key).length;
          const isSelected = card.copyIndex < countSelected;
          const isDisabled = !isSelected && selected.length >= maxItems;
          return (
            <button
              key={`${card.key}-${card.copyIndex}`}
              className={`${styles.itemCard} ${isSelected ? styles.selected : ''} ${isDisabled ? styles.dimmed : ''}`}
              onClick={() => toggle(card.key, card.copyIndex)}
            >
              <div className={styles.itemName}>{card.name}</div>
              <div className={styles.itemCharges}>{'●'.repeat(card.charges)}</div>
              <div className={styles.itemAbility}>{card.ability}</div>
            </button>
          );
        })}
      </div>
      <button
        className={styles.confirmBtn}
        onClick={() => send({ type: 'pick_items', items: selected })}
      >
        Confirm Items ({selected.length} selected)
      </button>
    </div>
  );
}
