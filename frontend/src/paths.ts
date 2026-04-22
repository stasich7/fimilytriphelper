export function buildOverviewPath(guestToken?: string): string {
  return guestToken ? `/guest/${guestToken}` : "/";
}

export function buildVersionPath(versionId: number | string, guestToken?: string): string {
  return guestToken ? `/guest/${guestToken}/versions/${versionId}` : `/versions/${versionId}`;
}

export function buildItemPath(itemId: number | string, guestToken?: string): string {
  return guestToken ? `/guest/${guestToken}/items/${itemId}` : `/items/${itemId}`;
}
