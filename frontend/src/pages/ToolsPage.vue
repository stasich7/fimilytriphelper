<template>
  <section class="layout">
    <article v-if="!isUnlocked" class="card">
      <p class="card__label">Инструменты</p>
      <h2>Вход по пин-коду</h2>
      <p class="hint">Введите пин-код, чтобы открыть раздел инструментов.</p>
      <label class="field">
        <span>Пин-код</span>
        <input
          v-model="pin"
          type="password"
          inputmode="numeric"
          autocomplete="current-password"
          placeholder="Введите пин-код"
          :disabled="unlocking"
          @keydown.enter.prevent="submitPIN"
        />
      </label>
      <p v-if="unlockError" class="error">{{ unlockError }}</p>
      <button type="button" :disabled="unlocking || !pin.trim()" @click="submitPIN">
        {{ unlocking ? "Проверяем..." : "Открыть инструменты" }}
      </button>
    </article>

    <template v-else>
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
          <button type="button" class="button-secondary" :disabled="!exportMarkdown" @click="copyExport">
            Скопировать
          </button>
        </div>
        <textarea
          v-model="exportMarkdown"
          rows="16"
          placeholder="Здесь появится готовый экспорт комментариев."
          readonly
        />
      </article>

      <article class="card">
        <div class="section-header">
          <p class="card__label">Гости</p>
          <h2>Гостевые ссылки</h2>
          <p class="hint">Создавайте гостевые ссылки, копируйте их и удаляйте гостей без комментариев.</p>
        </div>

        <div class="guest-create">
          <label class="field guest-create__field">
            <span>Имя гостя</span>
            <input
              v-model="newGuestName"
              type="text"
              placeholder="Например, Гэндальф"
              :disabled="creatingGuest"
              @keydown.enter.prevent="submitGuest"
            />
          </label>
          <button type="button" :disabled="creatingGuest || !newGuestName.trim()" @click="submitGuest">
            {{ creatingGuest ? "Создаем..." : "Создать гостя" }}
          </button>
        </div>

        <p v-if="guestError" class="error">{{ guestError }}</p>
        <p v-if="guestSuccess" class="success">{{ guestSuccess }}</p>
        <p v-if="loadingGuests" class="hint">Загружаем гостей...</p>
        <p v-else-if="guests.length === 0">Пока нет созданных гостей.</p>

        <div v-else class="guest-list">
          <section v-for="guest in guests" :key="guest.id" class="guest-row">
            <div class="guest-row__main">
              <h3>{{ guest.displayName }}</h3>
              <p class="guest-meta">Создан: {{ formatDate(guest.createdAt) }}</p>
              <p class="guest-meta">
                Последняя активность:
                {{ guest.lastSeenAt ? formatDate(guest.lastSeenAt) : "еще не заходил" }}
              </p>
              <p class="guest-meta">Комментариев: {{ guest.commentsCount }}</p>
              <input class="guest-link" :value="buildGuestLink(guest.guestToken)" readonly />
            </div>

            <div class="guest-row__actions">
              <button type="button" class="button-secondary" @click="copyGuestLink(guest)">Скопировать ссылку</button>
              <button
                type="button"
                class="button-danger"
                :disabled="deletingGuestId === guest.id || guest.commentsCount > 0"
                @click="removeGuest(guest)"
              >
                {{ deletingGuestId === guest.id ? "Удаляем..." : "Удалить" }}
              </button>
            </div>
          </section>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  createManagedGuest,
  deleteManagedGuest,
  getCodexExport,
  getManagedGuests,
  getVersions,
  importMarkdown,
  unlockTools,
} from "../api";
import type { ManagedGuest, PlanVersion } from "../types/api";

const TOOLS_UNLOCK_KEY = "family-trip-helper:tools-unlocked";

const versions = ref<PlanVersion[]>([]);
const guests = ref<ManagedGuest[]>([]);
const isUnlocked = ref(false);
const pin = ref("");
const unlocking = ref(false);
const unlockError = ref("");
const loadingVersions = ref(false);
const loadingGuests = ref(false);
const importing = ref(false);
const exporting = ref(false);
const creatingGuest = ref(false);
const deletingGuestId = ref<number | null>(null);
const importSource = ref("");
const importError = ref("");
const importSuccess = ref("");
const selectedVersionId = ref("");
const exportMarkdown = ref("");
const exportError = ref("");
const copySuccess = ref("");
const newGuestName = ref("");
const guestError = ref("");
const guestSuccess = ref("");

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU");
}

function buildGuestLink(guestToken: string): string {
  return `${window.location.origin}/guest/${guestToken}`;
}

async function submitPIN(): Promise<void> {
  if (!pin.value.trim()) {
    return;
  }

  unlocking.value = true;
  unlockError.value = "";

  try {
    await unlockTools(pin.value);
    isUnlocked.value = true;
    sessionStorage.setItem(TOOLS_UNLOCK_KEY, "true");
    pin.value = "";
    await Promise.all([loadVersions(), loadGuests()]);
  } catch (err) {
    unlockError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    unlocking.value = false;
  }
}

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

async function loadGuests(): Promise<void> {
  loadingGuests.value = true;
  guestError.value = "";

  try {
    const response = await getManagedGuests();
    guests.value = response.guests ?? [];
  } catch (err) {
    guestError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    loadingGuests.value = false;
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

async function copyGuestLink(guest: ManagedGuest): Promise<void> {
  await navigator.clipboard.writeText(buildGuestLink(guest.guestToken));
  guestSuccess.value = `Ссылка для ${guest.displayName} скопирована.`;
  guestError.value = "";
}

async function submitGuest(): Promise<void> {
  if (!newGuestName.value.trim()) {
    return;
  }

  creatingGuest.value = true;
  guestError.value = "";
  guestSuccess.value = "";

  try {
    const response = await createManagedGuest(newGuestName.value);
    guests.value = [response.guest, ...guests.value];
    guestSuccess.value = `Гость ${response.guest.displayName} создан.`;
    newGuestName.value = "";
  } catch (err) {
    guestError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    creatingGuest.value = false;
  }
}

async function removeGuest(guest: ManagedGuest): Promise<void> {
  deletingGuestId.value = guest.id;
  guestError.value = "";
  guestSuccess.value = "";

  try {
    await deleteManagedGuest(guest.id);
    guests.value = guests.value.filter((item) => item.id !== guest.id);
    guestSuccess.value = `Гость ${guest.displayName} удален.`;
  } catch (err) {
    guestError.value = err instanceof Error ? err.message : "Неизвестная ошибка";
  } finally {
    deletingGuestId.value = null;
  }
}

onMounted(() => {
  isUnlocked.value = sessionStorage.getItem(TOOLS_UNLOCK_KEY) === "true";

  if (isUnlocked.value) {
    void Promise.all([loadVersions(), loadGuests()]);
  }
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

.section-header {
  margin-bottom: 16px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

textarea,
select,
input {
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

.button-secondary {
  background: #e9f4fb;
  color: #134c75;
}

.button-danger {
  background: #b42318;
}

button:disabled,
textarea:disabled,
select:disabled,
input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.guest-create {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: end;
  margin-bottom: 20px;
}

.guest-create__field {
  flex: 1 1 280px;
  margin-bottom: 0;
}

.guest-list {
  display: grid;
  gap: 12px;
}

.guest-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 18px;
  background: #f8fbfd;
}

.guest-row__main {
  flex: 1 1 auto;
  min-width: 0;
}

.guest-row__main h3 {
  margin: 0 0 8px;
}

.guest-meta {
  margin: 0;
  color: #4b5563;
}

.guest-meta + .guest-meta {
  margin-top: 4px;
}

.guest-link {
  margin-top: 12px;
  background: #fff;
}

.guest-row__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-content: start;
  justify-content: flex-end;
}

.error {
  color: #b42318;
  font-weight: 700;
}

.success {
  color: #134c75;
  font-weight: 700;
}

@media (max-width: 720px) {
  .guest-row {
    flex-direction: column;
  }

  .guest-row__actions {
    justify-content: flex-start;
  }
}
</style>
