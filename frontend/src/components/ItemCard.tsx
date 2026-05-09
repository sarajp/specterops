import { getItemImage } from '../utils/itemImages';
import styles from '../styles/ItemCard.module.css';

interface Props {
  itemKey: string;
  name: string;
  charges: number;
  tapped?: boolean;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export default function ItemCard({ itemKey, name, charges, tapped, selected, disabled, onClick }: Props) {
  const img = getItemImage(itemKey);
  const Tag = onClick ? 'button' : 'div';

  return (
    <Tag
      className={[
        styles.card,
        selected ? styles.selected : '',
        disabled ? styles.disabled : '',
        tapped ? styles.tapped : '',
      ].filter(Boolean).join(' ')}
      onClick={disabled ? undefined : onClick}
    >
      <div className={styles.charges}>
        {charges > 0
          ? Array.from({ length: charges }, (_, i) => <span key={i} className={styles.pip} />)
          : <span className={styles.spent}>—</span>
        }
      </div>
      {img
        ? <div className={styles.imgOuter}>
            <img src={img} alt={name} className={styles.img} />
          </div>
        : <span className={styles.fallback}>{name}</span>
      }
    </Tag>
  );
}
