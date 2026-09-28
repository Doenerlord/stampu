/**
 * Material 3 Expressive Dynamic Theming & Monet Color Engine
 * Extracts and harmonizes Android Material You / Monet theme colors for Galaxy S24 Ultra & web.
 */

declare global {
  interface Window {
    AndroidMonetBridge?: {
      getMonetPrimary: () => string | null;
      getMonetContainer: () => string | null;
    };
    __ANDROID_MONET_PRIMARY__?: string;
    applyMonetColor?: (hex: string) => void;
  }
}

export interface MonetPalette {
  id: string;
  name: string;
  seedHex: string;
  label: string;
}

export const PRESET_PALETTES: MonetPalette[] = [
  { id: 'monet', name: 'System Monet', seedHex: '#39c34a', label: '📱 System Monet (Android)' },
  { id: 'vermilion', name: 'Torii Red', seedHex: '#e11d48', label: '⛩️ Japan Torii Red' },
  { id: 'sakura', name: 'Sakura Rose', seedHex: '#f43f5e', label: '🌸 Sakura Rose' },
  { id: 'aoi', name: 'Aoi Ocean', seedHex: '#0284c7', label: '🌊 Aoi Ocean Blue' },
  { id: 'matcha', name: 'Matcha Emerald', seedHex: '#10b981', label: '🍵 Matcha Emerald' },
  { id: 'fuji', name: 'Fuji Purple', seedHex: '#8b5cf6', label: '🪻 Fuji Purple' },
  { id: 'amber', name: 'Kyoto Amber', seedHex: '#f59e0b', label: '🍂 Kyoto Amber' },
];

/**
 * Checks for native Android Monet accent color extracted from device wallpaper
 */
export function getDetectedMonetHex(): string {
  if (typeof window === 'undefined') return '#39c34a';

  // 1. Android native JavascriptInterface bridge
  if (window.AndroidMonetBridge && typeof window.AndroidMonetBridge.getMonetPrimary === 'function') {
    try {
      const hex = window.AndroidMonetBridge.getMonetPrimary();
      if (hex && /^#[0-9a-fA-F]{6}$/.test(hex)) {
        return hex.toLowerCase();
      }
    } catch {
      // fallback
    }
  }

  // 2. Global injected variable from MainActivity
  if (window.__ANDROID_MONET_PRIMARY__ && /^#[0-9a-fA-F]{6}$/.test(window.__ANDROID_MONET_PRIMARY__)) {
    return window.__ANDROID_MONET_PRIMARY__.toLowerCase();
  }

  // 3. Fallback for desktop/web: Material 3 Android Teal/Green or Blue
  return '#10b981';
}

function hexToRgb(hex: string): [number, number, number] {
  let c = hex.replace('#', '');
  if (c.length === 3) {
    c = c.split('').map((x) => x + x).join('');
  }
  const num = parseInt(c, 16);
  if (Number.isNaN(num)) return [16, 185, 129];
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  return (
    '#' +
    [clamp(r), clamp(g), clamp(b)]
      .map((x) => x.toString(16).padStart(2, '0'))
      .join('')
  );
}

function mixRgb(
  rgb1: [number, number, number],
  rgb2: [number, number, number],
  weight: number
): [number, number, number] {
  return [
    rgb1[0] * weight + rgb2[0] * (1 - weight),
    rgb1[1] * weight + rgb2[1] * (1 - weight),
    rgb1[2] * weight + rgb2[2] * (1 - weight),
  ];
}

/**
 * Generates full Material 3 Expressive Tonal Color System from a seed HEX
 */
export function generateM3Tokens(seedHex: string) {
  const rgb = hexToRgb(seedHex);
  const [r, g, b] = rgb;

  // Rich container and surface blends
  const primaryContainer = rgbToHex(...mixRgb(rgb, [15, 23, 42], 0.28));
  const onPrimaryContainer = rgbToHex(...mixRgb(rgb, [255, 255, 255], 0.88));
  const surfaceTint = rgbToHex(...mixRgb(rgb, [9, 13, 22], 0.08));
  const surfaceContainer = rgbToHex(...mixRgb(rgb, [15, 23, 42], 0.14));
  const surfaceElevated = rgbToHex(...mixRgb(rgb, [30, 41, 59], 0.20));

  return {
    primary: seedHex,
    onPrimary: '#ffffff',
    primaryContainer,
    onPrimaryContainer,
    surfaceTint,
    surfaceContainer,
    surfaceElevated,
    surfaceCard: `rgba(15, 23, 42, 0.92)`,
    border: `rgba(${r}, ${g}, ${b}, 0.40)`,
    borderSubtle: `rgba(${r}, ${g}, ${b}, 0.22)`,
    glow: `rgba(${r}, ${g}, ${b}, 0.50)`,
    glowSubtle: `rgba(${r}, ${g}, ${b}, 0.25)`,
    badgeBg: `rgba(${r}, ${g}, ${b}, 0.22)`,
    badgeText: `rgba(${r}, ${g}, ${b}, 0.95)`,
  };
}

/**
 * Initializes Monet dynamic theming on document root
 */
export function initMonetTheming() {
  if (typeof document === 'undefined') return;

  // Listen for native Android Monet color broadcast
  if (typeof window !== 'undefined') {
    window.addEventListener('monet-color-detected', (e: Event) => {
      const customEvent = e as CustomEvent<string>;
      if (customEvent.detail) {
        window.__ANDROID_MONET_PRIMARY__ = customEvent.detail;
        const currentSaved = localStorage.getItem('stampu_theme_palette') || 'monet';
        if (currentSaved === 'monet') {
          applyMonetPalette('monet');
        }
      }
    });

    window.applyMonetColor = (hex: string) => {
      window.__ANDROID_MONET_PRIMARY__ = hex;
      const currentSaved = localStorage.getItem('stampu_theme_palette') || 'monet';
      if (currentSaved === 'monet') {
        applyMonetPalette('monet');
      }
    };
  }

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

  let seedHex = found.seedHex;
  if (found.id === 'monet') {
    seedHex = getDetectedMonetHex();
  }

  const tokens = generateM3Tokens(seedHex);

  root.style.setProperty('--m3-primary', tokens.primary);
  root.style.setProperty('--m3-on-primary', tokens.onPrimary);
  root.style.setProperty('--m3-primary-container', tokens.primaryContainer);
  root.style.setProperty('--m3-on-primary-container', tokens.onPrimaryContainer);
  root.style.setProperty('--m3-surface-tint', tokens.surfaceTint);
  root.style.setProperty('--m3-surface-container', tokens.surfaceContainer);
  root.style.setProperty('--m3-surface-elevated', tokens.surfaceElevated);
  root.style.setProperty('--m3-surface-card', tokens.surfaceCard);
  root.style.setProperty('--m3-border', tokens.border);
  root.style.setProperty('--m3-border-subtle', tokens.borderSubtle);
  root.style.setProperty('--m3-glow', tokens.glow);
  root.style.setProperty('--m3-glow-subtle', tokens.glowSubtle);
  root.style.setProperty('--m3-badge-bg', tokens.badgeBg);
  root.style.setProperty('--m3-badge-text', tokens.badgeText);

  localStorage.setItem('stampu_theme_palette', paletteId);
}
