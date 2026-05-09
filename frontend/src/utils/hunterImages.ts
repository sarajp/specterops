const modules = import.meta.glob<{ default: string }>(
  '../assets/hunter_assets/*.png',
  { eager: true }
);

export function getHunterImage(character: string): string | undefined {
  return modules[`../assets/hunter_assets/${character}.png`]?.default;
}
