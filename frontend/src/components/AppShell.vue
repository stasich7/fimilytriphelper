<template>
  <div class="shell">
    <header class="shell__header">
      <nav class="shell__nav">
        <RouterLink :to="overviewPath">В начало</RouterLink>
        <button v-if="showBack" type="button" class="shell__nav-button" @click="goBack">Назад</button>
        <RouterLink class="shell__tools" :to="toolsPath" aria-label="Инструменты" title="Инструменты">⚙</RouterLink>
      </nav>
    </header>

    <main class="shell__content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { buildOverviewPath, buildToolsPath } from "../paths";

const RETURN_PATH_KEY = "family-trip-helper:return-path";

const route = useRoute();
const router = useRouter();

const guestToken = computed(() => String(route.params.guestToken || ""));
const overviewPath = computed(() => buildOverviewPath(guestToken.value || undefined));
const toolsPath = buildToolsPath();

const showBack = computed(() => {
  const routeName = String(route.name || "");
  return routeName !== "overview" && routeName !== "guest";
});

async function goBack(): Promise<void> {
  const returnPath = sessionStorage.getItem(RETURN_PATH_KEY);

  if (returnPath) {
    sessionStorage.removeItem(RETURN_PATH_KEY);
    await router.push(returnPath);
    return;
  }

  await router.push(overviewPath.value);
}
</script>

<style scoped>
.shell {
  max-width: 1160px;
  margin: 0 auto;
  padding: 10px 12px 40px;
}

.shell__header {
  margin-bottom: 12px;
  padding: 8px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.06);
}

.shell__nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shell__nav a,
.shell__nav-button {
  min-height: 38px;
  padding: 8px 12px;
  border: 0;
  border-radius: 999px;
  background: #e9f4fb;
  color: #134c75;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}

.shell__tools {
  width: 38px;
  margin-left: auto;
  padding: 8px 0;
  text-align: center;
}

.shell__nav a.router-link-active {
  background: #134c75;
  color: #fff;
}

.shell__content {
  display: grid;
  gap: 12px;
}
</style>
