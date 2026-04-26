<template>
  <section class="layout">
    <article class="card" v-if="loading">
      <h2>Загружаем версию...</h2>
    </article>

    <article class="card" v-else-if="error">
      <h2>Не удалось загрузить версию</h2>
      <p>{{ error }}</p>
    </article>

    <template v-else-if="version">
      <article v-for="section in sections" :key="section.key" class="card">
        <p class="card__label">{{ section.label }}</p>
        <p v-if="likeError" class="submit-error">{{ likeError }}</p>
        <div v-for="item in section.items" :id="itemAnchorId(item.id)" :key="item.id" class="item">
          <div class="item__header">
            <h3>{{ item.title }}</h3>
            <button
              type="button"
              :class="['like-button', { 'like-button--active': item.likedByCurrentGuest }]"
              :disabled="!guestToken || likingItemId === item.id"
              :title="guestToken ? 'Нравится' : 'Откройте по гостевой ссылке, чтобы поставить лайк'"
              @click="toggleLike(item)"
            >
              <span aria-hidden="true">👍</span>
              <span>{{ item.likesCount }}</span>
            </button>
          </div>
          <button type="button" class="link-button" @click="openItem(item.id)">Смотреть</button>
        </div>
      </article>

      <article id="version-comments" class="card">
        <p class="card__label">Общие комментарии к версии</p>
        <p v-if="versionComments.length === 0">Пока нет общих комментариев к этой версии.</p>
        <div v-for="comment in versionComments" :key="comment.id" class="comment">
          <strong>{{ comment.author }}</strong>
          <p>{{ comment.body }}</p>
        </div>

        <p v-if="guestName" class="guest-summary">Комментарий будет отправлен от имени {{ guestName }}</p>
        <p v-else class="guest-hint">Чтобы оставить общий комментарий к версии, откройте ее по персональной гостевой ссылке.</p>
        <p v-if="submitError" class="submit-error">{{ submitError }}</p>

        <div class="comment-form">
          <textarea
            v-model="commentBody"
            rows="4"
            :disabled="!guestToken || submitting"
            placeholder="Напишите общий комментарий к этой версии поездки."
          />
          <button
            type="button"
            :disabled="!guestToken || submitting || !commentBody.trim()"
            @click="submitVersionComment"
          >
            {{ submitting ? "Отправляем..." : "Оставить комментарий" }}
          </button>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { createComment, getGuest, getVersion, toggleItemLike } from "../api";
import { buildReadingSections } from "../planOrder";
import { buildItemPath, buildVersionItemAnchorPath } from "../paths";
import type { Comment, PlanItem, PlanVersion } from "../types/api";

const RETURN_PATH_KEY = "family-trip-helper:return-path";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const error = ref("");
const version = ref<PlanVersion | null>(null);
const items = ref<PlanItem[]>([]);
const versionComments = ref<Comment[]>([]);
const commentBody = ref("");
const guestName = ref("");
const submitError = ref("");
const submitting = ref(false);
const likeError = ref("");
const likingItemId = ref<number | null>(null);

const guestToken = computed(() => {
  const token = String(route.params.guestToken || "");
  return token || "";
});

const sections = computed(() => buildReadingSections(items.value));

async function loadVersion(versionId: string): Promise<void> {
  loading.value = true;
  error.value = "";

  try {
    const response = await getVersion(versionId, guestToken.value || undefined);
    version.value = response.version;
    items.value = response.items ?? [];
    versionComments.value = response.comments ?? [];

    if (guestToken.value) {
      const guest = await getGuest(guestToken.value);
      guestName.value = guest.participant.displayName;
    } else {
      guestName.value = "";
    }

    loading.value = false;
    await scrollToHashTarget();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Неизвестная ошибка";
    loading.value = false;
  }
}

function itemAnchorId(itemId: number): string {
  return `item-${itemId}`;
}

async function scrollToHashTarget(): Promise<void> {
  if (!route.hash) {
    return;
  }

  await nextTick();

  const target = document.getElementById(route.hash.slice(1));
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function toggleLike(item: PlanItem): Promise<void> {
  if (!guestToken.value || likingItemId.value) {
    return;
  }

  likingItemId.value = item.id;
  likeError.value = "";

  try {
    const response = await toggleItemLike(item.id, guestToken.value);
    items.value = items.value.map((currentItem) =>
      currentItem.id === item.id
        ? {
            ...currentItem,
            likedByCurrentGuest: response.liked,
            likesCount: response.likesCount,
          }
        : currentItem,
    );
  } catch (err) {
    likeError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    likingItemId.value = null;
  }
}

async function openItem(itemId: number): Promise<void> {
  const itemPath = buildItemPath(itemId, guestToken.value || undefined);

  if (version.value) {
    const anchorPath = buildVersionItemAnchorPath(version.value.id, itemId, guestToken.value || undefined);
    sessionStorage.setItem(RETURN_PATH_KEY, anchorPath);
    await router.replace(anchorPath);
    await router.push(itemPath);
    return;
  } else {
    sessionStorage.setItem(RETURN_PATH_KEY, route.fullPath);
  }

  await router.push(itemPath);
}

async function submitVersionComment(): Promise<void> {
  if (!version.value || !guestToken.value || !commentBody.value.trim()) {
    return;
  }

  submitting.value = true;
  submitError.value = "";

  try {
    const response = await createComment({
      guestToken: guestToken.value,
      planVersionID: version.value.id,
      body: commentBody.value,
    });

    versionComments.value = [...versionComments.value, response.comment];
    commentBody.value = "";
  } catch (err) {
    submitError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    submitting.value = false;
  }
}

watch(
  () => `${String(route.params.versionId || "")}:${String(route.params.guestToken || "")}`,
  (compositeValue) => {
    const [versionId] = compositeValue.split(":");
    if (versionId) {
      void loadVersion(versionId);
    }
  },
  { immediate: true },
);
</script>

<style scoped>
.layout {
  display: grid;
  gap: 20px;
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

.item {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 18px;
  background: #f3f9fd;
}

.item + .item {
  margin-top: 12px;
}

.item__header {
  display: flex;
  gap: 12px;
  align-items: start;
  justify-content: space-between;
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

.anchor-link {
  display: inline-block;
  margin-top: 12px;
  color: #134c75;
  font-weight: 700;
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

h2,
h3 {
  margin-top: 0;
}

.preview {
  margin: 0;
}

:deep(.markdown-body p) {
  margin: 0;
}

:deep(.markdown-body ul) {
  margin: 0;
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
  max-width: 920px;
  height: auto;
  margin-top: 12px;
  border-radius: 16px;
  object-fit: contain;
  box-shadow: 0 10px 24px rgba(31, 41, 55, 0.12);
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

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  resize: vertical;
}

.link-button,
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
