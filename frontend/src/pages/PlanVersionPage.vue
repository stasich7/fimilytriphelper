<template>
  <section class="layout">
    <article class="card" v-if="loading">
      <p class="card__label">Версия плана</p>
      <h2>Загружаем версию...</h2>
    </article>

    <article class="card" v-else-if="error">
      <p class="card__label">Версия плана</p>
      <h2>Не удалось загрузить версию</h2>
      <p>{{ error }}</p>
    </article>

    <template v-else-if="version">
      <article class="card">
        <p class="card__label">Версия плана</p>
        <h2>{{ version.versionCode }} - {{ version.title }}</h2>
        <p>Здесь собраны все варианты и общие комментарии к этой версии поездки.</p>
        <a class="anchor-link" href="#version-comments">Общие комментарии к версии</a>
      </article>

      <article v-for="section in sections" :key="section.type" class="card">
        <p class="card__label">{{ section.label }}</p>
        <div v-for="item in section.items" :key="item.id" class="item">
          <h3>{{ item.title }}</h3>
          <p class="preview">{{ preview(item.bodyMarkdown) }}</p>
          <button type="button" class="link-button" @click="openItem(item.id)">Открыть карточку</button>
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
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { createComment, getGuest, getVersion } from "../api";
import { buildItemPath } from "../paths";
import type { Comment, PlanItem, PlanVersion } from "../types/api";

const RETURN_PATH_KEY = "family-trip-helper:return-path";
const RETURN_SCROLL_KEY = "family-trip-helper:return-scroll";

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

const guestToken = computed(() => {
  const token = String(route.params.guestToken || "");
  return token || "";
});

const sectionOrder = ["route_option", "stay", "transport", "activity", "note"];
const sectionLabels: Record<string, string> = {
  route_option: "Маршрут",
  stay: "Проживание",
  transport: "Транспорт",
  activity: "Активности",
  note: "Заметки",
};

const sections = computed(() =>
  sectionOrder
    .map((type) => ({
      type,
      label: sectionLabels[type] || type,
      items: items.value.filter((item) => item.type === type),
    }))
    .filter((section) => section.items.length > 0),
);

function preview(value: string): string {
  if (value.length <= 220) {
    return value;
  }

  return `${value.slice(0, 220)}...`;
}

async function loadVersion(versionId: string): Promise<void> {
  loading.value = true;
  error.value = "";

  try {
    const response = await getVersion(versionId);
    version.value = response.version;
    items.value = response.items ?? [];
    versionComments.value = response.comments ?? [];

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

function openItem(itemId: number): void {
  sessionStorage.setItem(RETURN_PATH_KEY, route.fullPath);
  sessionStorage.setItem(RETURN_SCROLL_KEY, String(window.scrollY));
  void router.push(buildItemPath(itemId, guestToken.value || undefined));
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
  white-space: pre-wrap;
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
