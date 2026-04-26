<template>
  <section class="layout">
    <article class="card" v-if="loading">
      <p class="card__label">Карточка</p>
      <h2>Загружаем карточку...</h2>
    </article>

    <article class="card" v-else-if="error">
      <p class="card__label">Карточка</p>
      <h2>Не удалось загрузить карточку</h2>
      <p>{{ error }}</p>
    </article>

    <article class="card" v-else-if="item">
      <p v-if="currentSectionLabel" class="card__label">{{ currentSectionLabel }}</p>
      <div class="item-header">
        <h2>{{ item.title }}</h2>
        <button
          type="button"
          :class="['like-button', { 'like-button--active': item.likedByCurrentGuest }]"
          :disabled="!guestToken || liking"
          :title="guestToken ? 'Нравится' : 'Откройте по гостевой ссылке, чтобы поставить лайк'"
          @click="toggleLike"
        >
          <span aria-hidden="true">👍</span>
          <span>{{ item.likesCount }}</span>
        </button>
      </div>
      <p v-if="likeError" class="submit-error">{{ likeError }}</p>
      <div class="body markdown-body" v-html="renderBody(item.bodyMarkdown)" @click="handleMarkdownClick"></div>
    </article>

    <article class="card" v-if="item">
      <p class="card__label">Комментарии</p>
      <p v-if="comments.length === 0">Пока нет комментариев.</p>
      <div v-for="comment in comments" :key="comment.id" class="comment">
        <strong>{{ comment.author }}</strong>
        <p>{{ comment.body }}</p>
      </div>
      <p v-if="guestName" class="guest-summary">Комментарий будет отправлен от имени {{ guestName }}</p>
      <p v-else class="guest-hint">Чтобы оставить комментарий к карточке, откройте ее по персональной гостевой ссылке.</p>
      <p v-if="submitError" class="submit-error">{{ submitError }}</p>
      <div class="comment-form">
        <textarea
          v-model="commentBody"
          rows="4"
          :disabled="!guestToken || submitting"
          placeholder="Напишите комментарий к этому пункту плана."
        />
        <button type="button" :disabled="!guestToken || submitting || !commentBody.trim()" @click="submitComment">
          {{ submitting ? "Отправляем..." : "Оставить комментарий" }}
        </button>
      </div>
    </article>

    <div v-if="item" class="floating-nav" role="navigation" aria-label="Навигация по карточкам">
      <div class="floating-nav__inner">
        <button v-if="returnItemId" type="button" class="floating-nav__button" @click="openReturnItem">
          Назад
        </button>
        <button v-else-if="previousItem" type="button" class="floating-nav__button" @click="openPreviousItem">
          Предыдущий
        </button>
        <button v-else type="button" class="floating-nav__button floating-nav__button--disabled" disabled>
          Предыдущий
        </button>

        <button
          v-if="nextItem"
          type="button"
          class="floating-nav__button"
          @click="openNextItem"
        >
          Следующий
        </button>
        <button v-else type="button" class="floating-nav__button floating-nav__button--disabled" disabled>
          Следующий
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { createComment, getGuest, getItem, getVersion, toggleItemLike } from "../api";
import { renderMarkdownWithOptions } from "../markdown";
import { buildReadingOrder, buildReadingSections } from "../planOrder";
import { buildItemPath, buildOverviewPath, buildVersionItemAnchorPath } from "../paths";
import type { Comment, PlanItem } from "../types/api";

const RETURN_PATH_KEY = "family-trip-helper:return-path";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const error = ref("");
const item = ref<PlanItem | null>(null);
const linkedItems = ref<PlanItem[]>([]);
const currentSectionLabel = ref("");
const comments = ref<Comment[]>([]);
const commentBody = ref("");
const guestName = ref("");
const submitError = ref("");
const submitting = ref(false);
const likeError = ref("");
const liking = ref(false);

const guestToken = computed(() => {
  const token = String(route.params.guestToken || "");
  return token || "";
});

const returnItemId = computed(() => {
  const rawValue = String(route.query.from || "");
  const parsedValue = Number(rawValue);
  return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : 0;
});

const currentItemIndex = computed(() => {
  if (!item.value) {
    return -1;
  }

  return linkedItems.value.findIndex((currentItem) => currentItem.id === item.value?.id);
});

const nextItem = computed(() => {
  const nextIndex = currentItemIndex.value + 1;
  if (nextIndex <= 0 || nextIndex >= linkedItems.value.length) {
    return null;
  }

  return linkedItems.value[nextIndex];
});

const previousItem = computed(() => {
  const previousIndex = currentItemIndex.value - 1;
  if (previousIndex < 0 || previousIndex >= linkedItems.value.length) {
    return null;
  }

  return linkedItems.value[previousIndex];
});

function renderBody(value: string): string {
  return renderMarkdownWithOptions(value, {
    resolveItemLink,
  });
}

async function loadItem(itemId: string): Promise<void> {
  loading.value = true;
  error.value = "";

  try {
    const response = await getItem(itemId, guestToken.value || undefined);
    item.value = response.item;
    comments.value = response.comments ?? [];
    linkedItems.value = [];

    if (response.item.planVersionID) {
      const versionResponse = await getVersion(response.item.planVersionID, guestToken.value || undefined);
      const versionItems = versionResponse.items ?? [];
      linkedItems.value = buildReadingOrder(versionItems);

      const section = buildReadingSections(versionItems).find((currentSection) =>
        currentSection.items.some((currentItem) => currentItem.id === response.item.id),
      );
      currentSectionLabel.value = section?.label || "";
    } else {
      currentSectionLabel.value = "";
    }

    if (guestToken.value) {
      const guest = await getGuest(guestToken.value);
      guestName.value = guest.participant.displayName;
    } else {
      guestName.value = "";
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    loading.value = false;
  }
}

function resolveItemLink(stableKey: string): string | null {
  const linkedItem = linkedItems.value.find((currentItem) => currentItem.stableKey === stableKey);

  if (!linkedItem) {
    return null;
  }

  return buildItemPath(linkedItem.id, guestToken.value || undefined);
}

function handleMarkdownClick(event: MouseEvent): void {
  const target = event.target;

  if (!(target instanceof Element)) {
    return;
  }

  const link = target.closest<HTMLAnchorElement>("a[data-internal-item-link='true']");
  const href = link?.getAttribute("href");

  if (!href) {
    return;
  }

  event.preventDefault();
  sessionStorage.setItem(RETURN_PATH_KEY, route.fullPath);
  const currentItemId = item.value?.id;
  const nextHref = currentItemId ? `${href}${href.includes("?") ? "&" : "?"}from=${currentItemId}` : href;
  void router.push(nextHref);
}

async function toggleLike(): Promise<void> {
  if (!item.value || !guestToken.value || liking.value) {
    return;
  }

  liking.value = true;
  likeError.value = "";

  try {
    const response = await toggleItemLike(item.value.id, guestToken.value);
    item.value = {
      ...item.value,
      likedByCurrentGuest: response.liked,
      likesCount: response.likesCount,
    };
  } catch (err) {
    likeError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    liking.value = false;
  }
}

async function submitComment(): Promise<void> {
  if (!item.value || !guestToken.value || !commentBody.value.trim()) {
    return;
  }

  submitting.value = true;
  submitError.value = "";

  try {
    const response = await createComment({
      guestToken: guestToken.value,
      planItemID: item.value.id,
      body: commentBody.value,
    });

    comments.value = [...comments.value, response.comment];
    commentBody.value = "";
  } catch (err) {
    submitError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    submitting.value = false;
  }
}

async function goBack(): Promise<void> {
  const fallbackPath = item.value?.planVersionID
    ? buildVersionItemAnchorPath(item.value.planVersionID, item.value.id, guestToken.value || undefined)
    : buildOverviewPath(guestToken.value || undefined);
  const returnPath = sessionStorage.getItem(RETURN_PATH_KEY);

  if (returnPath) {
    sessionStorage.removeItem(RETURN_PATH_KEY);
    await router.push(returnPath);
    return;
  }

  await router.push(fallbackPath);
}

function openNextItem(): void {
  if (!nextItem.value) {
    return;
  }

  void router.push(buildItemPath(nextItem.value.id, guestToken.value || undefined));
}

function openPreviousItem(): void {
  if (!previousItem.value) {
    return;
  }

  void router.push(buildItemPath(previousItem.value.id, guestToken.value || undefined));
}

function openReturnItem(): void {
  if (!returnItemId.value) {
    return;
  }

  void router.push(buildItemPath(returnItemId.value, guestToken.value || undefined));
}

watch(
  () => `${String(route.params.itemId || "")}:${String(route.params.guestToken || "")}`,
  (compositeValue) => {
    const [itemId] = compositeValue.split(":");
    if (itemId) {
      void loadItem(itemId);
    }
  },
  { immediate: true },
);
</script>

<style scoped>
.layout {
  display: grid;
  gap: 20px;
  padding-bottom: calc(92px + env(safe-area-inset-bottom, 0px));
}

.card {
  padding: 24px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
}

.card__label {
  margin: 0 0 8px;
  color: #2c6f9e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.item-header {
  display: flex;
  gap: 12px;
  align-items: start;
  justify-content: space-between;
}

.item-header h2 {
  margin-top: 0;
}

.like-button {
  display: inline-flex;
  min-width: 64px;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(19, 76, 117, 0.2);
  border-radius: 999px;
  background: #fff;
  color: #134c75;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
}

.like-button--active {
  border-color: #134c75;
  background: #dff0f8;
}

.like-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.body {
}

.floating-nav {
  position: fixed;
  z-index: 50;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px 12px calc(10px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid rgba(39, 74, 103, 0.14);
  box-shadow: 0 -14px 30px rgba(31, 41, 55, 0.08);
  backdrop-filter: blur(10px);
}

.floating-nav__inner {
  max-width: 1160px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.floating-nav__button {
  width: 100%;
  min-height: 44px;
  padding: 12px 16px;
  border: 0;
  border-radius: 999px;
  background: #134c75;
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 800;
}

.floating-nav__button--disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

:deep(.markdown-body p) {
  margin: 0;
}

:deep(.markdown-body p + p) {
  margin-top: 12px;
}

:deep(.markdown-body ul) {
  margin: 12px 0 12px 0;
  padding-left: 20px;
}

:deep(.markdown-body li + li) {
  margin-top: 4px;
}

:deep(.markdown-body a) {
  color: #134c75;
  font-weight: 700;
}

:deep(.markdown-body img) {
  display: block;
  width: 100%;
  max-width: 1080px;
  height: auto;
  margin-top: 16px;
  border-radius: 18px;
  object-fit: contain;
  box-shadow: 0 14px 30px rgba(31, 41, 55, 0.12);
}

:deep(.markdown-body img.markdown-chip) {
  display: inline-block;
  width: 1.45em;
  height: 1.45em;
  margin: 0 0.22em 0 0;
  border-radius: 999px;
  vertical-align: -0.34em;
  box-shadow: none;
}

.comment {
  padding: 16px;
  border-radius: 18px;
  background: #f7fbfe;
}

.comment + .comment {
  margin-top: 12px;
}

.comment-form {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.guest-summary {
  margin-top: 16px;
  color: #134c75;
  font-weight: 700;
}

.guest-hint {
  margin-top: 16px;
  color: #4b5563;
}

.submit-error {
  margin-top: 16px;
  color: #b42318;
  font-weight: 700;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  resize: vertical;
}

button {
  justify-self: start;
  padding: 10px 16px;
  border: 0;
  border-radius: 999px;
  background: #134c75;
  color: #fff;
  cursor: pointer;
  font: inherit;
}

button:disabled,
textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
