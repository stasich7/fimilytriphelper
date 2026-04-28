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

function appendLangParam(path: string, lang?: AppLang): string {
  const normalizedLang = normalizeLang(lang);
  if (normalizedLang === "ru") {
    return path;
  }

  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}lang=${normalizedLang}`;
}

async function requestJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
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
