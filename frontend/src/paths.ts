import { normalizeLang, type AppLang } from "./lang";

function withLang(path: string, lang?: AppLang): string {
  const normalizedLang = normalizeLang(lang);
  if (normalizedLang === "ru") {
    return path;
  }

  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}lang=${normalizedLang}`;
}

export function buildOverviewPath(guestToken?: string, lang?: AppLang): string {
  return withLang(guestToken ? `/guest/${guestToken}` : "/", lang);
}

export function buildVersionPath(versionId: number | string, guestToken?: string, lang?: AppLang): string {
  return withLang(guestToken ? `/guest/${guestToken}/versions/${versionId}` : `/versions/${versionId}`, lang);
}

export function buildVersionItemAnchorPath(
  versionId: number | string,
  itemId: number | string,
  guestToken?: string,
  lang?: AppLang,
): string {
  return `${buildVersionPath(versionId, guestToken, lang)}#item-${itemId}`;
}

export function buildItemPath(itemId: number | string, guestToken?: string, lang?: AppLang): string {
  return withLang(guestToken ? `/guest/${guestToken}/items/${itemId}` : `/items/${itemId}`, lang);
}

export function buildToolsPath(): string {
  return "/tools";
}
