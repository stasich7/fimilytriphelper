<template>
  <section class="grid">
    <article class="card card--hero">
      <p class="card__label">Поездка</p>
      <template v-if="loading">
        <h2>Загружаем данные поездки...</h2>
      </template>
      <template v-else-if="error">
        <h2>Не удалось загрузить данные поездки</h2>
        <p>{{ error }}</p>
      </template>
      <template v-else-if="overview?.trip">
        <h2>{{ overview.trip.title }}</h2>
        <p v-if="guestName" class="guest-summary">Гостевая ссылка для {{ guestName }}</p>
        <img class="hero-image" src="/family-trip-v2.png" alt="Family Trip Helper" />
      </template>
      <template v-else>
        <h2>План поездки еще не загружен</h2>
        <p>Загрузите первую версию плана, чтобы заполнить это пространство.</p>
      </template>
    </article>

    <article class="card">
      <p class="card__label">Текущая версия</p>
      <template v-if="overview?.currentVersion">
        <h3>{{ overview.currentVersion.versionCode }} - {{ overview.currentVersion.title }}</h3>
        <p>{{ formatDate(overview.currentVersion.createdAt) }}</p>
        <RouterLink class="link" :to="buildVersionPath(overview.currentVersion.id, guestToken)">
          Открыть версию
        </RouterLink>
      </template>
      <p v-else>Пока нет загруженных версий.</p>
    </article>

    <article class="card">
      <p class="card__label">Сводка</p>
      <ul>
        <li>Пунктов в текущей версии: {{ overview?.stats.items || 0 }}</li>
        <li>Комментариев собрано: {{ overview?.stats.comments || 0 }}</li>
        <li>Открытых комментариев: {{ overview?.stats.openComments || 0 }}</li>
      </ul>
    </article>

    <article class="card">
      <p class="card__label">Загруженные версии</p>
      <ul v-if="versions.length > 0" class="version-list">
        <li v-for="version in versions" :key="version.id">
          <RouterLink class="link" :to="buildVersionPath(version.id, guestToken)">
            {{ version.versionCode }} - {{ version.title }}
          </RouterLink>
        </li>
      </ul>
      <p v-else>Пока нет загруженных версий.</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { getGuest, getOverview, getVersions } from "../api";
import { buildVersionPath } from "../paths";
import type { OverviewResponse, PlanVersion } from "../types/api";

const route = useRoute();
const loading = ref(true);
const error = ref("");
const overview = ref<OverviewResponse | null>(null);
const versions = ref<PlanVersion[]>([]);
const guestName = ref("");

const guestToken = computed(() => {
  const token = String(route.params.guestToken || "");
  return token || undefined;
});

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU");
}

async function loadPage(): Promise<void> {
  loading.value = true;
  error.value = "";

  try {
    const [overviewResponse, versionsResponse] = await Promise.all([getOverview(), getVersions()]);
    overview.value = overviewResponse;
    versions.value = versionsResponse.versions;

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

watch(
  () => String(route.params.guestToken || ""),
  () => {
    void loadPage();
  },
  { immediate: true },
);
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}

.card {
  padding: 24px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.04);
}

.card--hero {
  grid-column: 1 / -1;
}

.card__label {
  margin: 0 0 8px;
  color: #2c6f9e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h2,
h3 {
  margin-top: 0;
}

ul {
  margin: 0;
  padding-left: 20px;
}

.version-list {
  display: grid;
  gap: 10px;
}

.guest-summary {
  margin-top: 12px;
  color: #134c75;
  font-weight: 700;
}

.hero-image {
  display: block;
  width: 100%;
  margin-top: 18px;
  border-radius: 20px;
  box-shadow: 0 18px 40px rgba(31, 41, 55, 0.16);
}

.link {
  display: inline-block;
  margin-top: 12px;
  color: #134c75;
  font-weight: 700;
}
</style>
