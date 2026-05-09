import { useState } from 'react';
import type { HunterGameView, AbilityState } from '../types/game';
import AbilityCard from './AbilityCard';
import { getHunterImage } from '../utils/hunterImages';
import styles from '../styles/HunterAbilities.module.css';

interface Props {
  view: HunterGameView;
  playerName: string;
}

export default function HunterAbilities({ view, playerName }: Props) {
  const [activeAbility, setActiveAbility] = useState<AbilityState | null>(null);

  const me = view.hunters.find(h => h.player_name === playerName);
  if (!me || me.abilities.length === 0) return null;

  return (
    <div className={styles.wrap}>
      {me.abilities.map(ability => (
        <AbilityCard
          key={ability.name}
          character={me.character}
          name={ability.name}
          onClick={() => setActiveAbility(ability)}
        />
      ))}

      {activeAbility && (
        <div className={styles.overlay} onClick={() => setActiveAbility(null)}>
          <div className={styles.zoom} onClick={e => e.stopPropagation()}>
            <div className={styles.zoomImgOuter}>
              <img src={getHunterImage(me.character)} alt={me.character} className={styles.zoomImg} />
            </div>
            <p className={styles.abilityName}>{activeAbility.name}</p>
            <p className={styles.description}>{activeAbility.description}</p>
            {activeAbility.active && (
              <div className={styles.zoomActions}>
                <button className={styles.useBtn} disabled>
                  Use Ability
                </button>
                <button className={styles.closeBtn} onClick={() => setActiveAbility(null)}>
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
