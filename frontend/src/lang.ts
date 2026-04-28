import type { RouteLocationNormalizedLoaded, LocationQueryRaw } from "vue-router";

export type AppLang = "ru" | "en";

export interface UIText {
  home: string;
  back: string;
  tools: string;
  langToggle: string;
  cardNavigation: string;
  trip: string;
  loadingTrip: string;
  tripLoadError: string;
  guestCommentsFrom: string;
  letsGo: string;
  openCurrentVersion: string;
  tripPlanNotLoaded: string;
  loadFirstVersion: string;
  currentVersion: string;
  openVersion: string;
  uploadedVersions: string;
  noVersions: string;
  versionLabel: string;
  versionLoading: string;
  versionLoadError: string;
  viewItem: string;
  generalVersionComments: string;
  noVersionComments: string;
  commentFrom: string;
  versionGuestHint: string;
  versionCommentPlaceholder: string;
  sending: string;
  leaveComment: string;
  cardLabel: string;
  itemLoading: string;
  itemLoadError: string;
  likesTitle: string;
  likesGuestHint: string;
  comments: string;
  noItemComments: string;
  itemGuestHint: string;
  itemCommentPlaceholder: string;
  navBack: string;
  previous: string;
  next: string;
  arrivalSection: string;
  staySection: string;
  planSection: string;
  daySection: string;
  departureSection: string;
  detailsSection: string;
}

const texts: Record<AppLang, UIText> = {
  ru: {
    home: "В начало",
    back: "Назад",
    tools: "Инструменты",
    langToggle: "Рус/Eng",
    cardNavigation: "Навигация по карточкам",
    trip: "Поездка",
    loadingTrip: "Загружаем данные поездки...",
    tripLoadError: "Не удалось загрузить данные поездки",
    guestCommentsFrom: "Комментарии от имени",
    letsGo: "Поехали",
    openCurrentVersion: "Открыть текущую версию плана",
    tripPlanNotLoaded: "План поездки еще не загружен",
    loadFirstVersion: "Загрузите первую версию плана, чтобы заполнить это пространство.",
    currentVersion: "Текущая версия",
    openVersion: "Открыть версию",
    uploadedVersions: "Загруженные версии",
    noVersions: "Пока нет загруженных версий.",
    versionLabel: "Версия",
    versionLoading: "Загружаем версию...",
    versionLoadError: "Не удалось загрузить версию",
    viewItem: "Смотреть",
    generalVersionComments: "Общие комментарии к версии",
    noVersionComments: "Пока нет общих комментариев к этой версии.",
    commentFrom: "Комментарий будет отправлен от имени",
    versionGuestHint: "Чтобы оставить общий комментарий к версии, откройте ее по персональной гостевой ссылке.",
    versionCommentPlaceholder: "Напишите общий комментарий к этой версии поездки.",
    sending: "Отправляем...",
    leaveComment: "Оставить комментарий",
    cardLabel: "Карточка",
    itemLoading: "Загружаем карточку...",
    itemLoadError: "Не удалось загрузить карточку",
    likesTitle: "Нравится",
    likesGuestHint: "Откройте по гостевой ссылке, чтобы поставить лайк",
    comments: "Комментарии",
    noItemComments: "Пока нет комментариев.",
    itemGuestHint: "Чтобы оставить комментарий к карточке, откройте ее по персональной гостевой ссылке.",
    itemCommentPlaceholder: "Напишите комментарий к этому пункту плана.",
    navBack: "Назад",
    previous: "Предыдущий",
    next: "Следующий",
    arrivalSection: "Прилет и трансфер",
    staySection: "Районы для выбора проживания",
    planSection: "План поездки",
    daySection: "Ритм по дням",
    departureSection: "Отъезд",
    detailsSection: "Подробности",
  },
  en: {
    home: "Home",
    back: "Back",
    tools: "Tools",
    langToggle: "Рус/Eng",
    cardNavigation: "Card navigation",
    trip: "Trip",
    loadingTrip: "Loading trip details...",
    tripLoadError: "Could not load trip details",
    guestCommentsFrom: "Comments as",
    letsGo: "Get started",
    openCurrentVersion: "Open the current plan version",
    tripPlanNotLoaded: "The trip plan has not been loaded yet",
    loadFirstVersion: "Import the first plan version to bring this page to life.",
    currentVersion: "Current version",
    openVersion: "Open version",
    uploadedVersions: "Imported versions",
    noVersions: "No versions have been imported yet.",
    versionLabel: "Version",
    versionLoading: "Loading version...",
    versionLoadError: "Could not load version",
    viewItem: "Open",
    generalVersionComments: "General comments for this version",
    noVersionComments: "There are no general comments for this version yet.",
    commentFrom: "Your comment will be posted as",
    versionGuestHint: "Open this version through a personal guest link to leave a general comment.",
    versionCommentPlaceholder: "Write a general comment about this version of the trip plan.",
    sending: "Sending...",
    leaveComment: "Leave a comment",
    cardLabel: "Card",
    itemLoading: "Loading card...",
    itemLoadError: "Could not load card",
    likesTitle: "Like",
    likesGuestHint: "Open this page through a guest link to leave a like",
    comments: "Comments",
    noItemComments: "There are no comments yet.",
    itemGuestHint: "Open this card through a personal guest link to leave a comment.",
    itemCommentPlaceholder: "Write a comment about this plan item.",
    navBack: "Back",
    previous: "Previous",
    next: "Next",
    arrivalSection: "Arrival and transfer",
    staySection: "Areas to consider for staying",
    planSection: "Trip plan",
    daySection: "Day-by-day rhythm",
    departureSection: "Departure",
    detailsSection: "Details",
  },
};

export function normalizeLang(value: unknown): AppLang {
  return value === "en" ? "en" : "ru";
}

export function getRouteLang(route: RouteLocationNormalizedLoaded): AppLang {
  const rawValue = Array.isArray(route.query.lang) ? route.query.lang[0] : route.query.lang;
  return normalizeLang(rawValue);
}

export function buildLangQuery(lang: AppLang, query: LocationQueryRaw = {}): LocationQueryRaw {
  if (lang === "ru") {
    const { lang: _lang, ...rest } = query;
    return rest;
  }

  return { ...query, lang };
}

export function getUIText(lang: AppLang): UIText {
  return texts[lang];
}

export function getNextLang(lang: AppLang): AppLang {
  return lang === "ru" ? "en" : "ru";
}

export function getDateLocale(lang: AppLang): string {
  return lang === "en" ? "en-GB" : "ru-RU";
}
