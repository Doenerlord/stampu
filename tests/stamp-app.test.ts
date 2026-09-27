import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import 'fake-indexeddb/auto';
import fs from 'node:fs';
import path from 'node:path';

// Mock MapLibre GL for DOM testing
vi.mock('maplibre-gl', () => {
  class MockMap {
    private handlers: Record<string, Function[]> = {};

    on(event: string, cb: Function) {
      if (!this.handlers[event]) this.handlers[event] = [];
      this.handlers[event].push(cb);
      if (event === 'load') {
        setTimeout(cb, 0);
      }
    }
    addControl() {}
    remove() {}
    easeTo() {}
    fitBounds() {}
    getZoom() {
      return 6;
    }
  }

  class MockMarker {
    element: HTMLElement;
    lngLat: [number, number] = [0, 0];

    constructor(options: { element: HTMLElement }) {
      this.element = options.element;
    }

    setLngLat(coords: [number, number]) {
      this.lngLat = coords;
      return this;
    }

    addTo(map: any) {
      // Attach to mock map container in DOM
      document.body.appendChild(this.element);
      return this;
    }

    getElement() {
      return this.element;
    }

    remove() {
      this.element?.remove();
    }
  }

  return {
    Map: MockMap,
    NavigationControl: vi.fn(),
    GeolocateControl: vi.fn(),
    Marker: MockMarker,
    LngLatBounds: class {
      extend() {}
    },
    addProtocol: vi.fn(),
    removeProtocol: vi.fn(),
  };
});

import StampDrawer from '../src/components/StampDrawer.vue';
import CategoryFilters from '../src/components/CategoryFilters.vue';
import MapContainer from '../src/components/MapContainer.vue';
import WishlistModal from '../src/components/WishlistModal.vue';
import App from '../src/App.vue';
import type { Stamp } from '../src/types/stamp';
import {
  db,
  toggleVisitedStamp,
  getVisitedStampIds,
  toggleWishlistStamp,
  getWishlistStampIds,
} from '../src/db';
import { isImageBuffer } from '../src/utils/offlineMap';

const sampleStamp: Stamp = {
  id: 'eki-tokyo',
  name: 'Tokyo Station',
  name_ja: '東京駅',
  name_romaji: 'Tōkyō-eki',
  category: 'eki',
  prefecture: 'Tokyo',
  city: 'Chiyoda-ku',
  address: '1-chome Marunouchi, Chiyoda City, Tokyo 100-0005',
  coordinates: [139.7671, 35.6812],
  stampLocation: 'Marunouchi North Exit, outside ticket gate near the Visitor Center',
  hours: '07:30 - 20:30',
  operator: 'JR East',
  description: 'Featuring the iconic red-brick Marunouchi Station building.',
  imageUrl: '/images/stamps/eki-yamanote-tokyo.jpg',
};

describe('Stamp Dataset (public/data/stamps.json)', () => {
  it('contains valid stamps spanning all 5 categories', () => {
    const raw = fs.readFileSync(path.resolve(__dirname, '../public/data/stamps.json'), 'utf-8');
    const stamps: Stamp[] = JSON.parse(raw);

    expect(stamps.length).toBeGreaterThanOrEqual(15);

    const categories = new Set(stamps.map((s) => s.category));
    expect(categories.has('eki')).toBe(true);
    expect(categories.has('michinoeki')).toBe(true);
    expect(categories.has('highway')).toBe(true);
    expect(categories.has('castle')).toBe(true);
    expect(categories.has('temple_shrine')).toBe(true);

    for (const stamp of stamps) {
      expect(stamp.id).toBeTruthy();
      expect(stamp.name).toBeTruthy();
      expect(stamp.name_ja).toBeTruthy();
      expect(stamp.coordinates).toHaveLength(2);
      expect(stamp.stampLocation).toBeTruthy();
      expect(stamp.hours).toBeTruthy();
    }
  });
});

describe('StampDrawer Component', () => {
  it('does not display when isOpen is false', () => {
    const wrapper = mount(StampDrawer, {
      props: {
        stamp: sampleStamp,
        isOpen: false,
        isCollected: false,
      },
    });

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
  });

  it('opens and renders stamp details, location, and actions when isOpen is true', async () => {
    const wrapper = mount(StampDrawer, {
      props: {
        stamp: sampleStamp,
        isOpen: true,
        isCollected: false,
      },
    });

    // Verify dialog exists
    const dialog = wrapper.find('[role="dialog"]');
    expect(dialog.exists()).toBe(true);

    // Verify Title & Japanese name
    expect(wrapper.text()).toContain('Tokyo Station');
    expect(wrapper.text()).toContain('東京駅');
    expect(wrapper.text()).toContain('Tōkyō-eki');

    // Verify Stamp desk location callout
    expect(wrapper.text()).toContain('Marunouchi North Exit');
    expect(wrapper.text()).toContain('07:30 - 20:30');

    // Verify Stamp image renders properly
    const img = wrapper.find('img');
    expect(img.exists()).toBe(true);
    expect(img.attributes('src')).toBe('/images/stamps/eki-yamanote-tokyo.jpg');

    // Verify Close button emits close
    const closeBtn = wrapper.find('button[aria-label="Close drawer"]');
    expect(closeBtn.exists()).toBe(true);
    await closeBtn.trigger('click');
    expect(wrapper.emitted('close')).toBeTruthy();

    // Verify Collect button emits toggleCollected with stampId
    const buttons = wrapper.findAll('button');
    const collectBtn = buttons.find((b) => b.text().includes('I Stamped This'));
    expect(collectBtn).toBeDefined();
    await collectBtn!.trigger('click');
    expect(wrapper.emitted('toggleCollected')?.[0]).toEqual(['eki-tokyo']);

    // Verify Wishlist button emits toggleWishlist with stampId
    const wishlistBtn = wrapper.find('button[aria-label="Toggle wishlist"]');
    expect(wishlistBtn.exists()).toBe(true);
    await wishlistBtn.trigger('click');
    expect(wrapper.emitted('toggleWishlist')?.[0]).toEqual(['eki-tokyo']);
  });
});

describe('CategoryFilters Component', () => {
  it('renders categories and emits selection', async () => {
    const counts = {
      all: 20,
      eki: 6,
      michinoeki: 4,
      highway: 3,
      castle: 4,
      temple_shrine: 3,
    };

    const wrapper = mount(CategoryFilters, {
      props: {
        selectedCategory: 'all',
        visitedFilter: 'all',
        searchQuery: '',
        categoryCounts: counts,
        visitedCount: 2,
        wishlistCount: 3,
        totalCount: 20,
      },
    });

    // Check brand, counts, and wishlist pill
    expect(wrapper.text()).toContain('STAMPU');
    expect(wrapper.text()).toContain('All Stamps');
    expect(wrapper.text()).toContain('Eki Stations');
    expect(wrapper.text()).toContain('Wishlist');

    // Click on Eki Stations chip
    const ekiButton = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Eki Stations'));
    expect(ekiButton).toBeDefined();
    await ekiButton!.trigger('click');

    expect(wrapper.emitted('update:selectedCategory')?.[0]).toEqual(['eki']);

    // Click on Wishlist filter button
    const wishlistFilterBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Wishlist') && b.attributes('title')?.includes('wishlist target'));
    expect(wishlistFilterBtn).toBeDefined();
    await wishlistFilterBtn!.trigger('click');
    expect(wrapper.emitted('update:visitedFilter')?.[0]).toEqual(['wishlist']);
  });
});

describe('MapContainer & Marker Click -> Drawer Integration', () => {
  it('clicking on a marker emits selectStamp', async () => {
    const wrapper = mount(MapContainer, {
      props: {
        stamps: [sampleStamp],
        selectedStamp: null,
        visitedStampIds: new Set(),
      },
    });

    // Wait for map load callback
    await new Promise((r) => setTimeout(r, 20));

    // Find the marker element in document.body
    const markerEl = document.querySelector(`[data-stamp-id="${sampleStamp.id}"]`) as HTMLElement;
    expect(markerEl).toBeTruthy();

    // Trigger click on marker
    markerEl.click();

    expect(wrapper.emitted('selectStamp')?.[0]).toEqual([sampleStamp]);
  });

  it('in App.vue, clicking a marker opens StampDrawer with the clicked stamp details', async () => {
    // Mock global fetch to return sample stamp
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [sampleStamp],
    });

    const wrapper = mount(App);

    // Wait for mounted fetch and Dexie
    await new Promise((r) => setTimeout(r, 30));
    await wrapper.vm.$nextTick();

    // Verify initially no drawer is open
    expect(wrapper.findComponent(StampDrawer).props('isOpen')).toBe(false);

    // Simulate marker click from MapContainer
    const mapComp = wrapper.findComponent(MapContainer);
    expect(mapComp.exists()).toBe(true);

    mapComp.vm.$emit('selectStamp', sampleStamp);
    await wrapper.vm.$nextTick();

    // Drawer is now open with the selected stamp!
    const drawer = wrapper.findComponent(StampDrawer);
    expect(drawer.props('isOpen')).toBe(true);
    expect(drawer.props('stamp')?.id).toBe('eki-tokyo');
    expect(drawer.text()).toContain('Tokyo Station');
    expect(drawer.text()).toContain('東京駅');
    expect(drawer.text()).toContain('Marunouchi North Exit');
  });
});

describe('Dexie Database Integration', () => {
  beforeEach(async () => {
    await db.visitedStamps.clear();
    await db.wishlistStamps.clear();
  });

  it('tracks visited stamps correctly offline', async () => {
    let visited = await getVisitedStampIds();
    expect(visited.has('eki-tokyo')).toBe(false);

    // Toggle on
    const isAdded = await toggleVisitedStamp('eki-tokyo', 'Stamped on my trip!');
    expect(isAdded).toBe(true);

    visited = await getVisitedStampIds();
    expect(visited.has('eki-tokyo')).toBe(true);
    expect(visited.size).toBe(1);

    // Toggle off
    const isRemoved = await toggleVisitedStamp('eki-tokyo');
    expect(isRemoved).toBe(false);

    visited = await getVisitedStampIds();
    expect(visited.has('eki-tokyo')).toBe(false);
    expect(visited.size).toBe(0);
  });

  it('tracks wishlist target stamps correctly offline', async () => {
    let wishlist = await getWishlistStampIds();
    expect(wishlist.has('castle-himeji')).toBe(false);

    // Toggle on
    const isAdded = await toggleWishlistStamp('castle-himeji');
    expect(isAdded).toBe(true);

    wishlist = await getWishlistStampIds();
    expect(wishlist.has('castle-himeji')).toBe(true);
    expect(wishlist.size).toBe(1);

    // Toggle off
    const isRemoved = await toggleWishlistStamp('castle-himeji');
    expect(isRemoved).toBe(false);

    wishlist = await getWishlistStampIds();
    expect(wishlist.has('castle-himeji')).toBe(false);
    expect(wishlist.size).toBe(0);
  });
});

describe('WishlistModal Component', () => {
  it('renders wishlist modal with saved stamps and handles actions', async () => {
    const wrapper = mount(WishlistModal, {
      props: {
        isOpen: true,
        wishlistStamps: [sampleStamp],
        visitedStampIds: new Set<string>(),
      },
    });

    expect(wrapper.text()).toContain('Stamp Wishlist');
    expect(wrapper.text()).toContain('Tokyo Station');
    expect(wrapper.text()).toContain('東京駅');

    // Click Details button
    const detailsBtn = wrapper.findAll('button').find((b) => b.text().includes('Details'));
    expect(detailsBtn).toBeDefined();
    await detailsBtn!.trigger('click');
    expect(wrapper.emitted('selectStamp')?.[0]).toEqual([sampleStamp]);

    // Click Show All on Map button
    const mapBtn = wrapper.findAll('button').find((b) => b.text().includes('Show All on Map'));
    expect(mapBtn).toBeDefined();
    await mapBtn!.trigger('click');
    expect(wrapper.emitted('fitWishlistOnMap')).toBeTruthy();
  });

  it('shows friendly empty state when wishlist is empty', () => {
    const wrapper = mount(WishlistModal, {
      props: {
        isOpen: true,
        wishlistStamps: [],
        visitedStampIds: new Set<string>(),
      },
    });

    expect(wrapper.text()).toContain('No stamps on your wishlist yet');
  });
});

describe('Image Buffer Validation (isImageBuffer)', () => {
  it('correctly identifies valid image formats and rejects HTML/text', () => {
    // Valid JPEG (0xFF, 0xD8, 0xFF)
    const jpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46]);
    expect(isImageBuffer(jpeg.buffer)).toBe(true);

    // Valid PNG (0x89, 0x50, 0x4E, 0x47)
    const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    expect(isImageBuffer(png.buffer)).toBe(true);

    // Valid WebP (RIFF....WEBP)
    const webp = new Uint8Array([0x52, 0x49, 0x46, 0x46, 0x20, 0x00, 0x00, 0x00]);
    expect(isImageBuffer(webp.buffer)).toBe(true);

    // HTML fallback (<!doctype html>)
    const htmlBytes = new TextEncoder().encode('<!doctype html><html><body>Error</body></html>');
    expect(isImageBuffer(htmlBytes.buffer)).toBe(false);

    // Plain text
    const textBytes = new TextEncoder().encode('Tile not found locally');
    expect(isImageBuffer(textBytes.buffer)).toBe(false);

    // Null/undefined/empty
    expect(isImageBuffer(null)).toBe(false);
    expect(isImageBuffer(undefined)).toBe(false);
    expect(isImageBuffer(new ArrayBuffer(4))).toBe(false);
  });
});

import PrefectureDownloadModal from '../src/components/PrefectureDownloadModal.vue';
import { saveDownloadedPack, getDownloadedPackIds, deleteDownloadedPack } from '../src/db';
import type { PrefecturePack } from '../src/types/stamp';

describe('Prefectures Catalog & Offline Download Manager', () => {
  it('public/data/prefectures.json contains all 47 prefectures with valid bounds and counts', () => {
    const raw = fs.readFileSync(path.join(process.cwd(), 'public', 'data', 'prefectures.json'), 'utf-8');
    const prefs: PrefecturePack[] = JSON.parse(raw);

    expect(prefs.length).toBe(47);
    for (const p of prefs) {
      expect(p.id).toBeTruthy();
      expect(p.name).toBeTruthy();
      expect(p.name_ja).toBeTruthy();
      expect(p.region).toBeTruthy();
      expect(p.stampCount).toBeGreaterThan(0);
      expect(p.bounds).toBeDefined();
      expect(p.bounds?.minLat).toBeLessThan(p.bounds?.maxLat!);
      expect(p.bounds?.minLon).toBeLessThan(p.bounds?.maxLon!);
    }
  });

  it('renders PrefectureDownloadModal and filters by region and search query', async () => {
    const samplePrefectures: PrefecturePack[] = [
      {
        id: 'tokyo',
        name: 'Tokyo',
        name_ja: '東京都',
        region: 'Kanto',
        stampCount: 65,
        categories: { eki: 55, castle: 2 },
        bounds: { minLat: 35.5, maxLat: 35.9, minLon: 139.1, maxLon: 139.9 },
        estimatedSizeMB: 5.2,
      },
      {
        id: 'hokkaido',
        name: 'Hokkaido',
        name_ja: '北海道',
        region: 'Hokkaido',
        stampCount: 133,
        categories: { michinoeki: 128, castle: 5 },
        bounds: { minLat: 41.3, maxLat: 45.6, minLon: 139.7, maxLon: 145.8 },
        estimatedSizeMB: 10.6,
      },
    ];

    const wrapper = mount(PrefectureDownloadModal, {
      props: {
        isOpen: true,
        prefectures: samplePrefectures,
        stamps: [sampleStamp],
      },
    });

    expect(wrapper.text()).toContain('Prefecture Offline Packs');
    expect(wrapper.text()).toContain('Tokyo');
    expect(wrapper.text()).toContain('Hokkaido');

    // Search filter
    const input = wrapper.find('input');
    await input.setValue('Tokyo');
    const itemNames = wrapper.findAll('.font-bold.text-sm').map(el => el.text());
    expect(itemNames).toContain('Tokyo');
    expect(itemNames).not.toContain('Hokkaido');
  });

  it('Dexie database persists offline packs correctly', async () => {
    let downloaded = await getDownloadedPackIds();
    expect(downloaded.has('kyoto')).toBe(false);

    await saveDownloadedPack('kyoto', 45, 3500000);
    downloaded = await getDownloadedPackIds();
    expect(downloaded.has('kyoto')).toBe(true);

    await deleteDownloadedPack('kyoto');
    downloaded = await getDownloadedPackIds();
    expect(downloaded.has('kyoto')).toBe(false);
  });
});

