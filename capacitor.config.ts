import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.stampu.app',
  appName: 'Stampu',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
