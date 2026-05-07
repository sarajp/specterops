import type { GameView } from '../types/game';
import styles from '../styles/PlayerPanel.module.css';

interface Props {
  view: GameView;
  playerName: string;
}

export default function PlayerPanel({ view, playerName }: Props) {
  const myHunter = view.role === 'hunter'
    ? view.hunters.find(h => h.player_name === playerName)
    : null;

  const activeHunterName = view.hunter_order[view.active_hunter_index] ?? null;

  return (
    <div className={styles.panel}>
      <div className={styles.row}>
        <span className={styles.label}>Round</span>
        <span>{view.round_number} / 40</span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Phase</span>
        <span className={styles.phase}>{view.phase.replace('_', ' ')}</span>
      </div>

      {view.phase === 'HUNTER_TURN' && activeHunterName && (
        <div className={styles.row}>
          <span className={styles.label}>Active</span>
          <span>{activeHunterName}</span>
        </div>
      )}

      <hr className={styles.divider} />

      {/* Agent info */}
      <div className={styles.section}>
        <span className={styles.sectionLabel}>Agent</span>
        <div className={styles.row}>
          <span className={styles.label}>HP</span>
          <span className={styles.hp}>
            {'●'.repeat(view.agent.health)}{'○'.repeat(view.agent.max_health - view.agent.health)}
          </span>
        </div>
        {view.agent.last_seen_cell && (
          <div className={styles.row}>
            <span className={styles.label}>Last seen</span>
            <span>{view.agent.last_seen_cell}</span>
          </div>
        )}
        {view.role === 'agent' && (
          <>
            <div className={styles.row}>
              <span className={styles.label}>Position</span>
              <span>{view.agent.position}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.label}>Objectives</span>
              <span>{view.agent.public_objectives.length + view.agent.pending_objectives.length} / 3</span>
            </div>
          </>
        )}
        {view.role === 'hunter' && view.agent.public_objectives.length > 0 && (
          <div className={styles.row}>
            <span className={styles.label}>Objectives</span>
            <span>{view.agent.public_objectives.length}</span>
          </div>
        )}
        {view.agent.status_effects.length > 0 && (
          <div className={styles.row}>
            <span className={styles.label}>Effects</span>
            <span className={styles.effects}>{view.agent.status_effects.join(', ')}</span>
          </div>
        )}
      </div>

      {/* My hunter info */}
      {myHunter && (
        <>
          <hr className={styles.divider} />
          <div className={styles.section}>
            <span className={styles.sectionLabel}>You ({myHunter.character})</span>
            <div className={styles.row}>
              <span className={styles.label}>Position</span>
              <span>{myHunter.position}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.label}>Speed</span>
              <span>{myHunter.move_speed}</span>
            </div>
            {myHunter.status_effects.length > 0 && (
              <div className={styles.row}>
                <span className={styles.label}>Effects</span>
                <span className={styles.effects}>{myHunter.status_effects.join(', ')}</span>
              </div>
            )}
          </div>
        </>
      )}

      {/* All hunters */}
      <hr className={styles.divider} />
      <div className={styles.section}>
        <span className={styles.sectionLabel}>Hunters</span>
        {view.hunters.map(h => (
          <div key={h.player_name} className={styles.hunterRow}>
            <span className={h.player_name === activeHunterName ? styles.activeHunter : ''}>
              {h.player_name}
            </span>
            <span className={styles.pos}>{h.position}</span>
            {h.status_effects.length > 0 && (
              <span className={styles.effects}> [{h.status_effects.join(',')}]</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
