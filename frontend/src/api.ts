import type {
  CommentCreateResponse,
  GuestLookupResponse,
  ItemDetailsResponse,
  OverviewResponse,
  VersionDetailsResponse,
  VersionsResponse,
} from "./types/api";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

async function requestJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
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

export function getOverview(): Promise<OverviewResponse> {
  return requestJSON<OverviewResponse>("/overview");
}

export function getVersions(): Promise<VersionsResponse> {
  return requestJSON<VersionsResponse>("/versions");
}

export function getVersion(versionId: string): Promise<VersionDetailsResponse> {
  return requestJSON<VersionDetailsResponse>(`/versions/${versionId}`);
}

export function getItem(itemId: string): Promise<ItemDetailsResponse> {
  return requestJSON<ItemDetailsResponse>(`/items/${itemId}`);
}

export function getGuest(guestToken: string): Promise<GuestLookupResponse> {
  return requestJSON<GuestLookupResponse>(`/guests/${guestToken}`);
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
