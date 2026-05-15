import { useState, useEffect } from 'react';
import styles from '../styles/DiceRoll.module.css';

interface Props {
  attacker: string;
  hit: boolean;
  roll: number;
  distance: number;
  onDone: () => void;
}

const PIPS: Record<number, [number, number][]> = {
  1: [[50, 50]],
  2: [[30, 30], [70, 70]],
  3: [[30, 30], [50, 50], [70, 70]],
  4: [[30, 30], [70, 30], [30, 70], [70, 70]],
  5: [[30, 30], [70, 30], [50, 50], [30, 70], [70, 70]],
  6: [[30, 25], [70, 25], [30, 50], [70, 50], [30, 75], [70, 75]],
};

function DieFace({ value, spinning }: { value: number; spinning: boolean }) {
  const face = ((value - 1) % 6) + 1;
  return (
    <svg viewBox="0 0 100 100" className={`${styles.die} ${spinning ? styles.spinning : ''}`}>
      <rect x="4" y="4" width="92" height="92" rx="18" ry="18" fill="#f5f0e8" stroke="#2a2a2a" strokeWidth="4" />
      {PIPS[face].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="9" fill="#1a1a1a" />
      ))}
    </svg>
  );
}

export default function DiceRoll({ attacker, hit, roll, distance, onDone }: Props) {
  const [displayed, setDisplayed] = useState(1);
  const [settled, setSettled] = useState(false);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const spinInterval = setInterval(() => {
      setDisplayed(Math.floor(Math.random() * 6) + 1);
    }, 70);

    const settleTimer = setTimeout(() => {
      clearInterval(spinInterval);
      setDisplayed(roll);
      setSettled(true);
    }, 900);

    const fadeTimer = setTimeout(() => setFading(true), 2400);
    const doneTimer = setTimeout(onDone, 2900);

    return () => {
      clearInterval(spinInterval);
      clearTimeout(settleTimer);
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, []);

  const exploding = roll > 6;

  return (
    <div className={`${styles.wrap} ${fading ? styles.fadeOut : ''}`}>
      <div className={styles.attacker}>{attacker} attacks!</div>
      <DieFace value={displayed} spinning={!settled} />
      {settled && (
        <>
          <div className={styles.rollLine}>
            {exploding
              ? <span className={styles.exploding}>💥 {roll} (exploding!)</span>
              : <span className={styles.rollNum}>rolled {roll}</span>
            }
            <span className={styles.vs}>vs distance {distance}</span>
          </div>
          <div className={`${styles.verdict} ${hit ? styles.hit : styles.miss}`}>
            {hit ? 'HIT' : 'MISS'}
          </div>
        </>
      )}
    </div>
  );
}
