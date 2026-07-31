<template>
  <button
    type="button"
    :class="['offline-button', { 'offline-button--ready': status?.available }]"
    :disabled="saving"
    :aria-label="buttonTitle"
    :title="buttonTitle"
    @click="saveOfflineGuide"
  >
    <span v-if="saving" aria-hidden="true" class="offline-button__spinner"></span>
    <span v-else aria-hidden="true">{{ icon }}</span>
    <span class="offline-button__label">{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { getRouteLang } from "../lang";
import { cacheGuide, getOfflineGuideStatus, type OfflineGuideProgress, type OfflineGuideStatus } from "../offline";

const route = useRoute();
const lang = computed(() => getRouteLang(route));
const saving = ref(false);
const status = ref<OfflineGuideStatus | null>(null);
const progress = ref<OfflineGuideProgress | null>(null);
const lastError = ref("");

const guestToken = computed(() => {
  const token = String(route.params.guestToken || "");
  return token || undefined;
});

const icon = computed(() => {
  if (saving.value) {
    return "…";
  }

  return status.value?.available ? "✓" : "⇩";
});

const label = computed(() => {
  if (saving.value && progress.value) {
    return `${progress.value.done}/${progress.value.total}`;
  }

  if (status.value?.available) {
    return lang.value === "ru" ? "Офлайн" : "Offline";
  }

  return lang.value === "ru" ? "Скачать" : "Save";
});

const buttonTitle = computed(() => {
  if (lastError.value) {
    return lastError.value;
  }

  if (saving.value && progress.value) {
    return progress.value.label;
  }

  if (status.value?.available) {
    const date = new Intl.DateTimeFormat(lang.value === "ru" ? "ru-RU" : "en-GB", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(status.value.cachedAt));
    return lang.value === "ru"
      ? `Путеводитель доступен офлайн: ${status.value.itemCount} карточек, ${status.value.mediaCount} медиа, ${date}`
      : `Guide available offline: ${status.value.itemCount} cards, ${status.value.mediaCount} media, ${date}`;
  }

  return lang.value === "ru" ? "Загрузить путеводитель для офлайн-доступа" : "Save guide for offline access";
});

async function saveOfflineGuide(): Promise<void> {
  if (saving.value) {
    return;
  }

  saving.value = true;
  lastError.value = "";
  progress.value = null;

  try {
    status.value = await cacheGuide({
      guestToken: guestToken.value,
      lang: lang.value,
      onProgress: (nextProgress) => {
        progress.value = nextProgress;
      },
    });
  } catch (err) {
    lastError.value = err instanceof Error ? err.message : lang.value === "ru" ? "Не удалось сохранить офлайн" : "Could not save offline";
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  status.value = getOfflineGuideStatus(lang.value);
});

watch(lang, () => {
  status.value = getOfflineGuideStatus(lang.value);
  lastError.value = "";
});
</script>

<style scoped>
.offline-button {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: 0;
  border-radius: 999px;
  background: #f4efe4;
  color: #5a3d12;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
}

.offline-button--ready {
  background: #e4f5ed;
  color: #17633d;
}

.offline-button:disabled {
  cursor: progress;
  opacity: 0.75;
}

.offline-button__spinner {
  width: 1.05em;
  height: 1.05em;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 999px;
  animation: offline-spin 0.8s linear infinite;
}

@keyframes offline-spin {
  to {
    transform: rotate(360deg);
  }
}

@media screen and (max-width: 430px) {
  .offline-button {
    width: 54px;
    min-width: 54px;
    min-height: 54px;
    padding: 0;
  }

  .offline-button__label {
    display: none;
  }

  .offline-button span:first-child {
    font-size: 26px;
    line-height: 1;
  }

  .offline-button__spinner {
    width: 24px;
    height: 24px;
  }
}
</style>
