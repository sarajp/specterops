import { useState } from 'react';
import type { HunterGameView, AbilityState } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import AbilityCard from './AbilityCard';
import { getHunterImage } from '../utils/hunterImages';
import styles from '../styles/HunterAbilities.module.css';

const CLAIRVOYANCE_DIRECTIONS = ['NE', 'NW', 'SE', 'SW'] as const;
const INSTEAD_OF_MOVING = new Set(['Post-Cognition', 'Catch the Scent', 'Clairvoyance',
  'Control Relay', 'Remote Link']);

interface Props {
  view: HunterGameView;
  playerName: string;
  send: (msg: OutboundMessage) => void;
}

export default function HunterAbilities({ view, playerName, send }: Props) {
  const [activeAbility, setActiveAbility] = useState<AbilityState | null>(null);
  const [pendingDirection, setPendingDirection] = useState(false);

  const me = view.hunters.find(h => h.player_name === playerName);
  if (!me || me.abilities.length === 0) return null;

  const isMyTurn = view.phase === 'HUNTER_TURN' &&
    view.hunter_order[view.active_hunter_index] === playerName;
  const stunned = me.status_effects.includes('STUNNED');
  const fatigued = me.status_effects.includes('FATIGUED');

  function canUse(ability: AbilityState): boolean {
    if (!ability.active) return false;
    if (!isMyTurn) return false;
    if (stunned || fatigued) return false;
    if (me!.abilities_used_this_turn.includes(ability.name)) return false;
    if (INSTEAD_OF_MOVING.has(ability.name) && me!.moved_this_turn) return false;
    return true;
  }

  function useAbility(ability: AbilityState, direction?: string) {
    send({ type: 'use_ability', ability_name: ability.name, ...(direction ? { direction } : {}) });
    setActiveAbility(null);
    setPendingDirection(false);
  }

  function handleUseClick(ability: AbilityState) {
    if (ability.name === 'Clairvoyance') {
      setPendingDirection(true);
    } else {
      useAbility(ability);
    }
  }

  return (
    <div className={styles.wrap}>
      {me.abilities.map(ability => (
        <AbilityCard
          key={ability.name}
          character={me.character}
          name={ability.name}
          onClick={() => { setActiveAbility(ability); setPendingDirection(false); }}
        />
      ))}

      {activeAbility && (
        <div className={styles.overlay} onClick={() => { setActiveAbility(null); setPendingDirection(false); }}>
          <div className={styles.zoom} onClick={e => e.stopPropagation()}>
            <div className={styles.zoomImgOuter}>
              <img src={getHunterImage(me.character)} alt={me.character} className={styles.zoomImg} />
            </div>
            <p className={styles.abilityName}>{activeAbility.name}</p>
            <p className={styles.description}>{activeAbility.description}</p>
            {activeAbility.active && (
              <div className={styles.zoomActions}>
                {pendingDirection ? (
                  <>
                    {CLAIRVOYANCE_DIRECTIONS.map(dir => (
                      <button key={dir} className={styles.useBtn} onClick={() => useAbility(activeAbility, dir)}>
                        {dir}
                      </button>
                    ))}
                    <button className={styles.closeBtn} onClick={() => setPendingDirection(false)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className={styles.useBtn}
                      disabled={!canUse(activeAbility)}
                      onClick={() => handleUseClick(activeAbility)}
                    >
                      Use Ability
                    </button>
                    <button className={styles.closeBtn} onClick={() => setActiveAbility(null)}>
                      Close
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
