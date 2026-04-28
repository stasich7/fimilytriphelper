export interface Trip {
  id: number;
  slug: string;
  title: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface PlanVersion {
  id: number;
  versionCode: string;
  language?: string;
  title: string;
  createdAt: string;
}

export interface PlanItem {
  id: number;
  planVersionID: number;
  stableKey: string;
  type: string;
  title: string;
  bodyMarkdown: string;
  likesCount: number;
  likedByCurrentGuest: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: number;
  author: string;
  body: string;
  createdAt: string;
}

export interface Participant {
  id: number;
  displayName: string;
  createdAt: string;
  lastSeenAt: string;
}

export interface ManagedGuest {
  id: number;
  displayName: string;
  guestToken: string;
  createdAt: string;
  lastSeenAt: string | null;
  commentsCount: number;
}

export interface OverviewResponse {
  trip?: Trip;
  currentVersion?: PlanVersion;
  stats: {
    items: number;
    comments: number;
    openComments: number;
  };
}

export interface VersionsResponse {
  versions: PlanVersion[];
}

export interface VersionDetailsResponse {
  version: PlanVersion;
  items: PlanItem[];
  comments: Comment[];
}

export interface ItemDetailsResponse {
  item: PlanItem;
  comments: Comment[];
}

export interface GuestLookupResponse {
  participant: Participant;
}

export interface CommentCreateResponse {
  comment: Comment;
}

export interface ImportMarkdownResponse {
  versionID: number;
  versionCode: string;
  importedItems: number;
}

export interface CodexExportResponse {
  versionID: number;
  versionCode: string;
  markdown: string;
}

export interface ToolsUnlockResponse {
  ok: boolean;
}

export interface ManagedGuestsResponse {
  guests: ManagedGuest[];
}

export interface ManagedGuestResponse {
  guest: ManagedGuest;
}

export interface DeleteGuestResponse {
  deleted: boolean;
}

export interface ItemLikeResponse {
  liked: boolean;
  likesCount: number;
}
