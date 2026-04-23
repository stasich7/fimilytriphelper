<template>
  <section class="layout">
    <article class="card">
      <p class="card__label">Инструменты</p>
      <h2>Импорт и экспорт</h2>
      <p>Здесь можно загрузить новую версию плана и получить готовый экспорт комментариев для Codex.</p>
    </article>

    <article class="card">
      <p class="card__label">Импорт новой версии</p>
      <p class="hint">Вставьте полный markdown новой версии в согласованном формате.</p>
      <p v-if="importError" class="error">{{ importError }}</p>
      <p v-if="importSuccess" class="success">{{ importSuccess }}</p>
      <textarea
        v-model="importSource"
        rows="16"
        placeholder="Вставьте сюда markdown новой версии."
        :disabled="importing"
      />
      <button type="button" :disabled="importing || !importSource.trim()" @click="submitImport">
        {{ importing ? "Импортируем..." : "Импортировать" }}
      </button>
    </article>

    <article class="card">
      <p class="card__label">Экспорт комментариев</p>
      <p class="hint">Выберите версию и получите markdown-пакет, который можно сразу отправить в Codex.</p>
      <label class="field">
        <span>Версия</span>
        <select v-model="selectedVersionId" :disabled="loadingVersions || exporting || versions.length === 0">
          <option value="" disabled>Выберите версию</option>
          <option v-for="version in versions" :key="version.id" :value="String(version.id)">
            {{ version.versionCode }} - {{ version.title }}
          </option>
        </select>
      </label>
      <p v-if="exportError" class="error">{{ exportError }}</p>
      <p v-if="copySuccess" class="success">{{ copySuccess }}</p>
      <div class="actions">
        <button type="button" :disabled="exporting || !selectedVersionId" @click="loadExport">
          {{ exporting ? "Формируем..." : "Сформировать экспорт" }}
        </button>
        <button type="button" :disabled="!exportMarkdown" @click="copyExport">Скопировать</button>
      </div>
      <textarea
        v-model="exportMarkdown"
        rows="16"
        placeholder="Здесь появится готовый экспорт комментариев."
        readonly
      />
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import { getCodexExport, getVersions, importMarkdown } from "../api";
import type { PlanVersion } from "../types/api";

const versions = ref<PlanVersion[]>([]);
const loadingVersions = ref(false);
const importing = ref(false);
const exporting = ref(false);
const importSource = ref("");
const importError = ref("");
const importSuccess = ref("");
const selectedVersionId = ref("");
const exportMarkdown = ref("");
const exportError = ref("");
const copySuccess = ref("");

async function loadVersions(): Promise<void> {
  loadingVersions.value = true;
  exportError.value = "";

  try {
    const response = await getVersions();
    versions.value = response.versions ?? [];

    if (!selectedVersionId.value && versions.value.length > 0) {
      selectedVersionId.value = String(versions.value[0].id);
    }
  } catch (err) {
    exportError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    loadingVersions.value = false;
  }
}

async function submitImport(): Promise<void> {
  if (!importSource.value.trim()) {
    return;
  }

  importing.value = true;
  importError.value = "";
  importSuccess.value = "";

  try {
    const response = await importMarkdown(importSource.value);
    importSuccess.value = `Версия ${response.versionCode} импортирована, карточек: ${response.importedItems}.`;
    importSource.value = "";
    await loadVersions();
    selectedVersionId.value = String(response.versionID);
  } catch (err) {
    importError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    importing.value = false;
  }
}

async function loadExport(): Promise<void> {
  if (!selectedVersionId.value) {
    return;
  }

  exporting.value = true;
  exportError.value = "";
  copySuccess.value = "";

  try {
    const response = await getCodexExport(selectedVersionId.value);
    exportMarkdown.value = response.markdown;
  } catch (err) {
    exportError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    exporting.value = false;
  }
}

async function copyExport(): Promise<void> {
  if (!exportMarkdown.value) {
    return;
  }

  await navigator.clipboard.writeText(exportMarkdown.value);
  copySuccess.value = "Экспорт скопирован.";
}

onMounted(() => {
  void loadVersions();
});
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

.hint {
  color: #4b5563;
}

.field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

textarea,
select {
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  font: inherit;
}

textarea {
  resize: vertical;
  margin-bottom: 16px;
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
textarea:disabled,
select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #b42318;
  font-weight: 700;
}

.success {
  color: #134c75;
  font-weight: 700;
}
</style>
