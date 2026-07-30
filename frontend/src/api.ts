import type {
  CodexExportResponse,
  CommentCreateResponse,
  DeleteGuestResponse,
  GuestLookupResponse,
  ImportMarkdownResponse,
  ItemLikeResponse,
  ItemDetailsResponse,
  ManagedGuestResponse,
  ManagedGuestsResponse,
  OverviewResponse,
  ToolsUnlockResponse,
  VersionDetailsResponse,
  VersionsResponse,
} from "./types/api";
import { normalizeLang, type AppLang } from "./lang";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
const API_CACHE_NAME = "family-trip-helper-api-v1";

function appendLangParam(path: string, lang?: AppLang): string {
  const normalizedLang = normalizeLang(lang);
  if (normalizedLang === "ru") {
    return path;
  }

  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}lang=${normalizedLang}`;
}

function canUseCache(init?: RequestInit): boolean {
  return !init || !init.method || init.method.toUpperCase() === "GET";
}

async function readCachedJSON<T>(url: string): Promise<T | null> {
  if (!("caches" in window)) {
    return null;
  }

  try {
    const cachedResponse = await caches.match(url);
    if (!cachedResponse) {
      return null;
    }

    return (await cachedResponse.json()) as T;
  } catch {
    return null;
  }
}

async function writeCachedJSON(url: string, response: Response): Promise<void> {
  if (!("caches" in window)) {
    return;
  }

  try {
    const cache = await caches.open(API_CACHE_NAME);
    await cache.put(url, response.clone());
  } catch {
    // API cache is a convenience layer; online reads must still succeed if storage is unavailable.
  }
}

async function requestJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const shouldCache = canUseCache(init);
  let response: Response;

  try {
    response = await fetch(url, init);
  } catch (err) {
    if (shouldCache) {
      const cachedPayload = await readCachedJSON<T>(url);
      if (cachedPayload) {
        return cachedPayload;
      }
    }

    throw err;
  }

  if (!response.ok) {
    if (shouldCache) {
      const cachedPayload = await readCachedJSON<T>(url);
      if (cachedPayload) {
        return cachedPayload;
      }
    }

    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { message?: string };
      if (payload.message) {
        message = payload.message;
      }
    } catch {
      // Ignore JSON parsing errors for non-JSON responses.
    }

    throw new Error(message);
  }

  if (shouldCache) {
    await writeCachedJSON(url, response);
  }

  return (await response.json()) as T;
}

export function getOverview(lang?: AppLang): Promise<OverviewResponse> {
  return requestJSON<OverviewResponse>(appendLangParam("/overview", lang));
}

export function getVersions(lang?: AppLang): Promise<VersionsResponse> {
  return requestJSON<VersionsResponse>(appendLangParam("/versions", lang));
}

export function getVersion(versionId: string | number, guestToken?: string, lang?: AppLang): Promise<VersionDetailsResponse> {
  const query = guestToken ? `?guestToken=${encodeURIComponent(guestToken)}` : "";
  return requestJSON<VersionDetailsResponse>(appendLangParam(`/versions/${versionId}${query}`, lang));
}

export function getItem(itemId: string, guestToken?: string, lang?: AppLang): Promise<ItemDetailsResponse> {
  const query = guestToken ? `?guestToken=${encodeURIComponent(guestToken)}` : "";
  return requestJSON<ItemDetailsResponse>(appendLangParam(`/items/${itemId}${query}`, lang));
}

export function getGuest(guestToken: string): Promise<GuestLookupResponse> {
  return requestJSON<GuestLookupResponse>(`/guests/${guestToken}`);
}

export function toggleItemLike(itemId: number, guestToken: string): Promise<ItemLikeResponse> {
  return requestJSON<ItemLikeResponse>(`/items/${itemId}/like`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ guestToken }),
  });
}

export async function createComment(input: {
  guestToken: string;
  planVersionID?: number;
  planItemID?: number;
  body: string;
}): Promise<CommentCreateResponse> {
  const response = await fetch(`${API_BASE}/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { message?: string };
      if (payload.message) {
        message = payload.message;
      }
    } catch {
      // Ignore JSON parsing errors for non-JSON responses.
    }

    throw new Error(message);
  }

  return (await response.json()) as CommentCreateResponse;
}

export function unlockTools(pin: string): Promise<ToolsUnlockResponse> {
  return requestJSON<ToolsUnlockResponse>("/tools/unlock", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ pin }),
  });
}

export function getManagedGuests(): Promise<ManagedGuestsResponse> {
  return requestJSON<ManagedGuestsResponse>("/tools/guests");
}

export function createManagedGuest(displayName: string): Promise<ManagedGuestResponse> {
  return requestJSON<ManagedGuestResponse>("/tools/guests", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ displayName }),
  });
}

export function deleteManagedGuest(guestId: number): Promise<DeleteGuestResponse> {
  return requestJSON<DeleteGuestResponse>(`/tools/guests/${guestId}`, {
    method: "DELETE",
  });
}

export async function importMarkdown(source: string): Promise<ImportMarkdownResponse> {
  const response = await fetch(`${API_BASE}/imports/markdown`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ source }),
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { message?: string };
      if (payload.message) {
        message = payload.message;
      }
    } catch {
      // Ignore JSON parsing errors for non-JSON responses.
    }

    throw new Error(message);
  }

  return (await response.json()) as ImportMarkdownResponse;
}

export function getCodexExport(versionId: string): Promise<CodexExportResponse> {
  return requestJSON<CodexExportResponse>(`/exports/codex?versionId=${encodeURIComponent(versionId)}`);
}
