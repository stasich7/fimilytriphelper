function escapeHTML(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export interface MarkdownRenderOptions {
  resolveItemLink?: (stableKey: string) => string | null;
}

const imagePattern = /!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g;
const markdownLinkPattern = /\[([^\]]+)\]\(([^\s)]+)\)/g;
const plainURLPattern = /(^|[\s(>])((https?:\/\/[^\s<]+))/g;

function restoreTokens(value: string, tokens: string[]): string {
  return value.replace(/@@TOKEN_(\d+)@@/g, (_match, index: string) => tokens[Number(index)] || "");
}

function isExternalURL(value: string): boolean {
  return /^https?:\/\//.test(value);
}

function renderInline(text: string, options: MarkdownRenderOptions): string {
  const tokens: string[] = [];
  const storeToken = (html: string): string => {
    const key = `@@TOKEN_${tokens.length}@@`;
    tokens.push(html);
    return key;
  };

  let rendered = escapeHTML(text);

  rendered = rendered.replace(imagePattern, (_match, alt: string, url: string) =>
    storeToken(
      `<img class="markdown-image" src="${url}" alt="${alt}" loading="lazy" referrerpolicy="no-referrer" />`,
    ),
  );

  rendered = rendered.replace(markdownLinkPattern, (match: string, label: string, url: string) => {
    if (isExternalURL(url)) {
      return storeToken(`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`);
    }

    if (url.startsWith("item:")) {
      const stableKey = url.slice("item:".length);
      const href = options.resolveItemLink?.(stableKey);

      if (href) {
        return storeToken(`<a href="${href}" data-internal-item-link="true">${label}</a>`);
      }
    }

    return match;
  });

  rendered = rendered.replace(plainURLPattern, (_match, prefix: string, url: string) => {
    const link = storeToken(`<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`);
    return `${prefix}${link}`;
  });

  return restoreTokens(rendered, tokens);
}

export function renderMarkdown(value: string): string {
  return renderMarkdownWithOptions(value, {});
}

export function renderMarkdownWithOptions(value: string, options: MarkdownRenderOptions): string {
  const lines = value.split(/\r?\n/);
  const blocks: string[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];

  const flushParagraph = (): void => {
    if (paragraph.length === 0) {
      return;
    }

    blocks.push(`<p>${paragraph.map((line) => renderInline(line, options)).join("<br />")}</p>`);
    paragraph = [];
  };

  const flushList = (): void => {
    if (listItems.length === 0) {
      return;
    }

    blocks.push(`<ul>${listItems.map((item) => `<li>${renderInline(item, options)}</li>`).join("")}</ul>`);
    listItems = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const bulletMatch = line.match(/^\s*-\s+(.*)$/);

    if (bulletMatch) {
      flushParagraph();
      listItems.push(bulletMatch[1]);
      continue;
    }

    if (line.trim() === "") {
      flushParagraph();
      flushList();
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  return blocks.join("");
}

export function renderMarkdownPreview(value: string, maxLength = 220): string {
  return renderMarkdownPreviewWithOptions(value, {}, maxLength);
}

export function renderMarkdownPreviewWithOptions(
  value: string,
  options: MarkdownRenderOptions,
  maxLength = 220,
): string {
  const firstImage = value.match(imagePattern)?.[0] || "";
  const plainText = value
    .replace(imagePattern, "")
    .replace(markdownLinkPattern, "$1")
    .replace(/https?:\/\/[^\s<]+/g, "")
    .replace(/\s+/g, " ")
    .trim();

  const previewText = plainText.length <= maxLength ? plainText : `${plainText.slice(0, maxLength).trimEnd()}...`;
  const previewSource = [firstImage, previewText].filter(Boolean).join("\n\n");

  return renderMarkdownWithOptions(previewSource, options);
}
