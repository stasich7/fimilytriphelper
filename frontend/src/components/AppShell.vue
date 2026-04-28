<template>
  <div class="shell">
    <header class="shell__header">
      <nav class="shell__nav">
        <button
          type="button"
          class="shell__nav-button shell__nav-button--icon"
          :aria-label="text.home"
          :title="text.home"
          @click="goHome"
        >
          <span aria-hidden="true" class="shell__home-icon">⌂</span>
        </button>
        <button type="button" class="shell__nav-button shell__lang-button" @click="toggleLanguage">
          {{ text.langToggle }}
        </button>
        <button v-if="showBack" type="button" class="shell__nav-button" @click="goBack">{{ text.back }}</button>
        <RouterLink class="shell__tools" :to="toolsPath" :aria-label="text.tools" :title="text.tools">⚙</RouterLink>
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

import { getOverview } from "../api";
import { buildLangQuery, getNextLang, getRouteLang, getUIText } from "../lang";
import { buildOverviewPath, buildToolsPath, buildVersionPath } from "../paths";

const RETURN_PATH_KEY = "family-trip-helper:return-path";

const route = useRoute();
const router = useRouter();

const lang = computed(() => getRouteLang(route));
const text = computed(() => getUIText(lang.value));
const guestToken = computed(() => String(route.params.guestToken || ""));
const overviewPath = computed(() => buildOverviewPath(guestToken.value || undefined, lang.value));
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

async function openCurrentVersion(): Promise<void> {
  try {
    const overview = await getOverview(lang.value);
    if (overview.currentVersion) {
      await router.push(buildVersionPath(overview.currentVersion.id, guestToken.value || undefined, lang.value));
      return;
    }
  } catch {
    // Fall back to the public overview when the current version cannot be loaded.
  }

  await router.push(overviewPath.value);
}

async function goHome(): Promise<void> {
  await router.push(overviewPath.value);
}

async function toggleLanguage(): Promise<void> {
  const nextLang = getNextLang(lang.value);
  await router.push({
    name: route.name || undefined,
    params: route.params,
    query: buildLangQuery(nextLang, route.query),
    hash: route.hash,
  });
}
</script>

<style scoped>
.shell {
  max-width: 1160px;
  margin: 0 auto;
  padding: 10px 12px 40px;
}

@media screen and (max-width: 767px) {
  .shell__tools {
    display: none !important;
  }
  .shell__header::after {
    width: min(48%, 160px);
  }
}

.shell__header {
  position: relative;
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 16px;
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.06);
  background-color: white;
}

.shell__header::after {
  content: "";
  position: absolute;
  right: 8px;
  bottom: 0px;
  top: 8px;
  width: min(40%, 220px);
  background: url(/family-trip-v4.png);
  background-position: right bottom;
  background-size: contain;
  background-repeat: no-repeat;
  pointer-events: none;
}

.shell__image {
  display: block;
  width: 100%;
  height: 92px;
  border-radius: 12px;
  background: #f7fbfe;
  object-fit: contain;
  object-position: right bottom;
}

.shell__nav {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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

.shell__nav-button--icon {
  width: 54px;
  min-height: 54px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.shell__home-icon {
  font-size: 34px;
  line-height: 1;
}

.shell__lang-button {
  min-width: 84px;
}

.shell__tools {
  display: inline-flex;
  width: 54px;
  min-height: 54px;
  padding: 0;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  line-height: 1;
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
