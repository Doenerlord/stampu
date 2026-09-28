/**
 * Material 3 Expressive Dynamic Theming & Monet Color Engine
 * Extracts and harmonizes Android Material You / Monet theme colors for Galaxy S24 Ultra & web.
 */

export interface MonetPalette {
  id: string;
  name: string;
  seedHex: string;
  label: string;
}

export const PRESET_PALETTES: MonetPalette[] = [
  { id: 'monet', name: 'Monet (System)', seedHex: 'AccentColor', label: '📱 System Monet (Android)' },
  { id: 'vermilion', name: 'Vermilion (Torii)', seedHex: '#e11d48', label: '⛩️ Japan Torii Red' },
  { id: 'sakura', name: 'Sakura (Cherry)', seedHex: '#f43f5e', label: '🌸 Sakura Rose' },
  { id: 'aoi', name: 'Aoi (Ocean Blue)', seedHex: '#0284c7', label: '🌊 Aoi Ocean Blue' },
  { id: 'matcha', name: 'Matcha (Emerald)', seedHex: '#059669', label: '🍵 Matcha Emerald' },
  { id: 'fuji', name: 'Fuji (Iris/Purple)', seedHex: '#8b5cf6', label: '🪻 Fuji Purple' },
  { id: 'amber', name: 'Koyo (Autumn Amber)', seedHex: '#d97706', label: '🍂 Kyoto Amber' },
];

/**
 * Initializes Monet dynamic theming on document root
 */
export function initMonetTheming() {
  if (typeof document === 'undefined') return;

  // Check saved theme or default to system Monet
  const saved = localStorage.getItem('stampu_theme_palette') || 'monet';
  applyMonetPalette(saved);
}

/**
 * Applies a given palette ID to CSS custom properties
 */
export function applyMonetPalette(paletteId: string) {
  if (typeof document === 'undefined') return;

  const found = PRESET_PALETTES.find((p) => p.id === paletteId) || PRESET_PALETTES[0];
  const root = document.documentElement;

  if (found.id === 'monet') {
    // Probe AccentColor from browser
    root.style.setProperty('--m3-primary', 'AccentColor');
    root.style.setProperty(
      '--m3-primary-container',
      'color-mix(in srgb, AccentColor 22%, rgba(15, 23, 42, 0.95))'
    );
    root.style.setProperty(
      '--m3-on-primary-container',
      'color-mix(in srgb, AccentColor 85%, white)'
    );
    root.style.setProperty(
      '--m3-surface-tint',
      'color-mix(in srgb, AccentColor 8%, #090d16)'
    );
    root.style.setProperty(
      '--m3-border-tint',
      'color-mix(in srgb, AccentColor 30%, #334155)'
    );
    root.style.setProperty(
      '--m3-glow',
      'color-mix(in srgb, AccentColor 35%, transparent)'
    );
  } else {
    const hex = found.seedHex;
    root.style.setProperty('--m3-primary', hex);
    root.style.setProperty(
      '--m3-primary-container',
      `color-mix(in srgb, ${hex} 22%, rgba(15, 23, 42, 0.95))`
    );
    root.style.setProperty(
      '--m3-on-primary-container',
      `color-mix(in srgb, ${hex} 85%, white)`
    );
    root.style.setProperty(
      '--m3-surface-tint',
      `color-mix(in srgb, ${hex} 8%, #090d16)`
    );
    root.style.setProperty(
      '--m3-border-tint',
      `color-mix(in srgb, ${hex} 30%, #334155)`
    );
    root.style.setProperty(
      '--m3-glow',
      `color-mix(in srgb, ${hex} 35%, transparent)`
    );
  }

  localStorage.setItem('stampu_theme_palette', paletteId);
}
