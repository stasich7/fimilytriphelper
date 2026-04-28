<template>
  <section class="grid">
    <article class="card card--hero">
      <p class="card__label">{{ text.trip }}</p>
      <template v-if="loading">
        <h2>{{ text.loadingTrip }}</h2>
      </template>
      <template v-else-if="error">
        <h2>{{ text.tripLoadError }}</h2>
        <p>{{ error }}</p>
      </template>
      <template v-else-if="overview?.trip">
        <h2>{{ overview.trip.title }}</h2>
        <p v-if="guestName" class="guest-summary">{{ text.guestCommentsFrom }} {{ guestName }}</p>
        <RouterLink v-if="currentVersionPath" class="start-link" :to="currentVersionPath">{{ text.letsGo }}</RouterLink>
        <RouterLink v-if="currentVersionPath" class="hero-image-link" :to="currentVersionPath" :aria-label="text.openCurrentVersion">
          <img class="hero-image" src="/family-trip-v5.png" alt="Family Trip Helper" />
        </RouterLink>
        <img v-else class="hero-image" src="/family-trip-v5.png" alt="Family Trip Helper" />
      </template>
      <template v-else>
        <h2>{{ text.tripPlanNotLoaded }}</h2>
        <p>{{ text.loadFirstVersion }}</p>
      </template>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { getGuest, getOverview } from "../api";
import { getRouteLang, getUIText } from "../lang";
import { buildVersionPath } from "../paths";
import type { OverviewResponse } from "../types/api";

const route = useRoute();
const loading = ref(true);
const error = ref("");
const overview = ref<OverviewResponse | null>(null);
const guestName = ref("");
const lang = computed(() => getRouteLang(route));
const text = computed(() => getUIText(lang.value));

const guestToken = computed(() => {
  const token = String(route.params.guestToken || "");
  return token || undefined;
});

const currentVersionPath = computed(() => {
  if (!overview.value?.currentVersion) {
    return "";
  }

  return buildVersionPath(overview.value.currentVersion.id, guestToken.value, lang.value);
});

async function loadPage(): Promise<void> {
  loading.value = true;
  error.value = "";

  try {
    const overviewResponse = await getOverview(lang.value);
    overview.value = overviewResponse;

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
  () => `${String(route.params.guestToken || "")}:${String(route.query.lang || "")}`,
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

h2 {
  margin-top: 0;
}

.guest-summary {
  margin-top: 12px;
  color: #134c75;
  font-weight: 700;
}

.start-link {
  display: inline-block;
  margin-top: 18px;
  padding: 12px 18px;
  border-radius: 999px;
  background: #134c75;
  color: #fff;
  font-weight: 800;
  text-decoration: none;
}

.start-link:hover,
.start-link:focus-visible {
  background: #0f3d5f;
}

.hero-image-link {
  display: block;
  margin-top: 18px;
  border-radius: 20px;
}

.hero-image-link:focus-visible {
  outline: 3px solid rgba(19, 76, 117, 0.35);
  outline-offset: 4px;
}

.hero-image {
  display: block;
  width: 100%;
  border-radius: 20px;
  box-shadow: 0 18px 40px rgba(31, 41, 55, 0.16);
}

.card--hero > .hero-image {
  margin-top: 18px;
}

.link {
  display: inline-block;
  margin-top: 12px;
  color: #134c75;
  font-weight: 700;
}
</style>
