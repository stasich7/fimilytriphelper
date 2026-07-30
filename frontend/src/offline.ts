import { getGuest, getOverview, getVersion, getItem } from "./api";
import { normalizeLang, type AppLang } from "./lang";
import type { PlanItem } from "./types/api";

const OFFLINE_STATUS_KEY = "family-trip-helper:offline-guide-status";
const MEDIA_CACHE_NAME = "family-trip-helper-media-v1";
const APP_CACHE_NAME = "family-trip-helper-app-v1";

const markdownImagePattern = /!\[[^\]]*]\(((?:https?:\/\/|\/)[^\s)]+)\)/g;

export interface OfflineGuideStatus {
  available: boolean;
  versionId: number | null;
  lang: AppLang;
  cachedAt: string;
  itemCount: number;
  mediaCount: number;
  failedMediaCount: number;
}

export interface OfflineGuideProgress {
  done: number;
  total: number;
  label: string;
}

export interface CacheGuideInput {
  versionId?: string | number;
  guestToken?: string;
  lang?: AppLang;
  onProgress?: (progress: OfflineGuideProgress) => void;
}

function canUseBrowserCaches(): boolean {
  return "caches" in window;
}

function toAbsoluteURL(url: string): string {
  return new URL(url, window.location.origin).toString();
}

function extractMediaURLs(items: PlanItem[]): string[] {
  const urls = new Set<string>([
    "/",
    "/family-trip-v4.png",
    "/family-trip-v5.png",
    "/chips/map-chip-1.png",
    "/chips/map-chip-2.png",
    "/chips/map-chip-3.png",
    "/chips/map-chip-4.png",
    "/chips/map-chip-5.png",
    "/chips/map-chip-6.png",
  ]);

  for (const item of items) {
    for (const match of item.bodyMarkdown.matchAll(markdownImagePattern)) {
      urls.add(match[1]);
    }
  }

  return [...urls];
}

async function cacheAppShell(): Promise<void> {
  if (!canUseBrowserCaches()) {
    return;
  }

  const urls = new Set<string>(["/", window.location.pathname]);

  for (const element of document.querySelectorAll<HTMLScriptElement | HTMLLinkElement>("script[src], link[rel='stylesheet'][href]")) {
    const url = element instanceof HTMLScriptElement ? element.src : element.href;
    if (url) {
      urls.add(url);
    }
  }

  const cache = await caches.open(APP_CACHE_NAME);
  await Promise.allSettled([...urls].map((url) => cache.add(toAbsoluteURL(url))));
}

async function cacheMedia(urls: string[], onProgress?: (done: number, total: number) => void): Promise<number> {
  if (!canUseBrowserCaches()) {
    return 0;
  }

  const cache = await caches.open(MEDIA_CACHE_NAME);
  let cachedCount = 0;

  for (const [index, url] of urls.entries()) {
    const absoluteURL = toAbsoluteURL(url);
    try {
      const response = await fetch(absoluteURL, { mode: url.startsWith("http") ? "no-cors" : "same-origin" });
      await cache.put(absoluteURL, response);
      cachedCount += 1;
    } catch {
      // Media prefetch is best-effort; cached API data can still work offline.
    } finally {
      onProgress?.(index + 1, urls.length);
    }
  }

  return cachedCount;
}

export function getOfflineGuideStatus(): OfflineGuideStatus | null {
  const rawValue = localStorage.getItem(OFFLINE_STATUS_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as OfflineGuideStatus;
  } catch {
    return null;
  }
}

export async function cacheGuide(input: CacheGuideInput = {}): Promise<OfflineGuideStatus> {
  const lang = normalizeLang(input.lang);
  let done = 0;
  const progress = (label: string, total: number): void => {
    done += 1;
    input.onProgress?.({ done: Math.min(done, total), total, label });
  };

  input.onProgress?.({ done: 0, total: 4, label: lang === "ru" ? "Готовим приложение" : "Preparing app" });
  await cacheAppShell();
  progress(lang === "ru" ? "Загружаем поездку" : "Loading trip", 4);

  const overview = await getOverview(lang);
  const versionId = input.versionId ?? overview.currentVersion?.id;
  if (!versionId) {
    throw new Error(lang === "ru" ? "Нет текущей версии для офлайн-загрузки" : "No current version to cache offline");
  }

  progress(lang === "ru" ? "Загружаем версию" : "Loading version", 4);
  const versionResponse = await getVersion(versionId, input.guestToken, lang);
  const items = versionResponse.items ?? [];

  await Promise.all(items.map((item) => getItem(item.id.toString(), input.guestToken, lang)));
  if (input.guestToken) {
    await getGuest(input.guestToken);
  }

  progress(lang === "ru" ? "Загружаем карточки" : "Loading cards", 4);
  const mediaURLs = extractMediaURLs(items);
  const mediaCount = await cacheMedia(mediaURLs, (mediaDone, mediaTotal) => {
    input.onProgress?.({
      done: 3,
      total: 4,
      label: lang === "ru" ? `Медиа ${mediaDone}/${mediaTotal}` : `Media ${mediaDone}/${mediaTotal}`,
    });
  });

  const status: OfflineGuideStatus = {
    available: true,
    versionId: Number(versionId),
    lang,
    cachedAt: new Date().toISOString(),
    itemCount: items.length,
    mediaCount,
    failedMediaCount: Math.max(mediaURLs.length - mediaCount, 0),
  };

  localStorage.setItem(OFFLINE_STATUS_KEY, JSON.stringify(status));
  progress(lang === "ru" ? "Готово" : "Ready", 4);
  return status;
}
