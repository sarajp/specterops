const modules = import.meta.glob<{ default: string }>(
  '../assets/item_assets/*.png',
  { eager: true }
);

export function getItemImage(key: string): string | undefined {
  return modules[`../assets/item_assets/${key}.png`]?.default;
}
