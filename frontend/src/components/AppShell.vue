<template>
  <div class="shell">
    <header :class="['shell__header', { 'shell__header--with-image': showHeaderImage }]">
      <div>
        <p class="shell__eyebrow">FamilyTripHelper</p>
        <h1>Family Trip Helper</h1>
        <p class="shell__subtitle">Совместно планируем, комментируем, рассматриваем варианты общей части поездки</p>
        <p class="shell__subtitle">Пока <b>БЕЗ вариантов проживания</b>, но с предложениями по районам.</p>
        <p v-if="guestSummary" class="shell__guest-mode">{{ guestSummary }}</p>
      </div>

      <nav class="shell__nav">
        <RouterLink :to="overviewPath">В начало</RouterLink>
        <RouterLink :to="toolsPath">Инструменты</RouterLink>
      </nav>
    </header>

    <main class="shell__content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { getGuest } from "../api";
import { buildOverviewPath, buildToolsPath } from "../paths";

const route = useRoute();

const guestToken = computed(() => String(route.params.guestToken || ""));
const overviewPath = computed(() => buildOverviewPath(guestToken.value || undefined));
const toolsPath = buildToolsPath();
const guestName = ref("");

const showHeaderImage = computed(() => {
  const routeName = String(route.name || "");
  return routeName !== "overview" && routeName !== "guest";
});

const guestSummary = computed(() => {
  if (!guestName.value) {
    return "";
  }

  return `Комментарии от имени ${guestName.value}`;
});

watch(
  () => guestToken.value,
  async (token) => {
    if (!token) {
      guestName.value = "";
      return;
    }

    try {
      const guest = await getGuest(token);
      guestName.value = guest.participant.displayName;
    } catch {
      guestName.value = "";
    }
  },
  { immediate: true },
);
</script>

<style scoped>
.shell {
  max-width: 1160px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}

.shell__header {
  display: grid;
  gap: 20px;
  margin-bottom: 28px;
  padding: 24px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.06);
}

.shell__header--with-image {
  background-color: rgba(255, 255, 255, 0.9);
  background-image: linear-gradient(to right, rgba(255, 255, 255, 0.96) 0%, rgba(255, 255, 255, 0.94) 46%, rgba(255, 255, 255, 0.78) 64%, rgba(255, 255, 255, 0.2) 100%), url("/family-trip-v4.png");
  background-position: left top, right bottom;
  background-repeat: no-repeat, no-repeat;
  background-size: auto, 39%;
}

.shell__eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #2c6f9e;
}

.shell__header h1 {
  margin: 0;
  font-size: 32px;
}

.shell__subtitle {
  margin: 8px 0 0;
  max-width: 720px;
  color: #4b5563;
}

.shell__guest-mode {
  margin: 10px 0 0;
  color: #134c75;
  font-weight: 700;
}

.shell__nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.shell__nav a {
  padding: 10px 14px;
  border-radius: 999px;
  background: #e9f4fb;
  color: #134c75;
  font-weight: 600;
}

.shell__nav a.router-link-active {
  background: #134c75;
  color: #fff;
}

.shell__content {
  display: grid;
  gap: 20px;
}

@media (max-width: 900px) {
  .shell__header--with-image {
    background-position: left top, right bottom;
    background-size: auto, 48% auto;
  }
}

@media (max-width: 640px) {
  .shell__header--with-image {
    background-image: linear-gradient(to bottom, rgba(255, 255, 255, 0.97) 0%, rgba(255, 255, 255, 0.94) 52%, rgba(255, 255, 255, 0.88) 100%), url("/family-trip-v4.png");
    background-position: left top, right bottom;
    background-size: auto, 240px auto;
  }
}
</style>
