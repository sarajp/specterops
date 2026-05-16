import type { AgentGameView, AbilityState } from '../types/game';
import type { OutboundMessage } from '../types/ws';
import styles from '../styles/AgentAbilities.module.css';

interface Props {
  view: AgentGameView;
  send: (msg: OutboundMessage) => void;
}

export default function AgentAbilities({ view, send }: Props) {
  const activeAbilities = view.agent.abilities.filter(a => a.active);
  if (activeAbilities.length === 0) return null;

  const isMyTurn = view.phase === 'AGENT_TURN';
  const fatigued = view.agent.status_effects.includes('FATIGUED');

  function canUse(ability: AbilityState): boolean {
    if (!isMyTurn) return false;
    if (fatigued) return false;
    if (ability.name === 'Dash' && view.agent.path_this_turn.length > 1) return false;
    return true;
  }

  function useAbility(ability: AbilityState) {
    send({ type: 'use_ability', ability_name: ability.name });
  }

  return (
    <div className={styles.wrap}>
      {activeAbilities.map(ability => (
        <div key={ability.name} className={styles.abilityRow}>
          <div className={styles.abilityInfo}>
            <span className={styles.abilityName}>{ability.name}</span>
            <span className={styles.description}>{ability.description}</span>
          </div>
          <button
            className={styles.useBtn}
            disabled={!canUse(ability)}
            onClick={() => useAbility(ability)}
          >
            Use
          </button>
        </div>
      ))}
    </div>
  );
}
