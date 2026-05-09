import { getHunterImage } from '../utils/hunterImages';
import styles from '../styles/AbilityCard.module.css';

interface Props {
  character: string;
  name: string;
  onClick?: () => void;
}

export default function AbilityCard({ character, name, onClick }: Props) {
  const img = getHunterImage(character);
  const Tag = onClick ? 'button' : 'div';

  return (
    <Tag className={styles.card} onClick={onClick}>
      {img
        ? <div className={styles.imgOuter}>
            <img src={img} alt={character} className={styles.img} />
          </div>
        : <span className={styles.fallback}>{character}</span>
      }
      <span className={styles.label}>{name}</span>
    </Tag>
  );
}
