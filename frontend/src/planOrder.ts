import type { PlanItem } from "./types/api";
import type { AppLang } from "./lang";
import { getUIText } from "./lang";

export interface ReadingSection {
  key: string;
  label: string;
  items: PlanItem[];
}

const planStableKeys = ["note.plan.update-scope", "route.option.a"];
const stayStableKeys = [
  "stay.tbilisi.area.sololaki",
  "stay.tbilisi.area.mtatsminda",
  "stay.batumi.area.old-batumi",
  "stay.batumi.area.chakvi",
];
const arrivalStableKeys = ["transport.arrival.tbilisi-airport"];
const departureStableKeys = ["transport.departure.batumi-airport"];
const detailStableKeys = [
  "transport.train.tbilisi-batumi",
  "note.transport.cableways",
  "activity.tbilisi.old-town",
  "activity.mtskheta.daytrip",
  "activity.kakheti.sighnaghi",
  "activity.kazbegi.daytrip",
  "activity.borjomi.daytrip",
  "activity.batumi.sea-days",
  "activity.batumi.botanical-garden",
  "activity.adjara.makhuntseti",
  "note.food.cuisine",
  "note.wine.guide",
];

function extractDateSortKey(item: PlanItem): string {
  const match = item.stableKey.match(/\d{4}-\d{2}-\d{2}/);
  if (match) {
    return match[0];
  }

  return item.stableKey;
}

function collectByStableKeys(
  itemsByStableKey: Map<string, PlanItem>,
  stableKeys: string[],
  usedStableKeys: Set<string>,
): PlanItem[] {
  const result: PlanItem[] = [];

  for (const stableKey of stableKeys) {
    const item = itemsByStableKey.get(stableKey);
    if (!item || usedStableKeys.has(stableKey)) {
      continue;
    }

    result.push(item);
    usedStableKeys.add(stableKey);
  }

  return result;
}

export function buildReadingSections(items: PlanItem[], lang: AppLang = "ru"): ReadingSection[] {
  const itemsByStableKey = new Map(items.map((item) => [item.stableKey, item]));
  const usedStableKeys = new Set<string>();
  const text = getUIText(lang);

  const planItems = collectByStableKeys(itemsByStableKey, planStableKeys, usedStableKeys);
  const stayItems = collectByStableKeys(itemsByStableKey, stayStableKeys, usedStableKeys);
  const arrivalItems = collectByStableKeys(itemsByStableKey, arrivalStableKeys, usedStableKeys);

  const dayItems = items
    .filter((item) => item.type === "day_plan")
    .sort((left, right) => {
      const leftDate = extractDateSortKey(left);
      const rightDate = extractDateSortKey(right);

      if (leftDate !== rightDate) {
        return leftDate.localeCompare(rightDate, "en");
      }

      return left.stableKey.localeCompare(right.stableKey, "ru");
    });

  for (const item of dayItems) {
    usedStableKeys.add(item.stableKey);
  }

  const departureItems = collectByStableKeys(itemsByStableKey, departureStableKeys, usedStableKeys);
  const detailItems = collectByStableKeys(itemsByStableKey, detailStableKeys, usedStableKeys);

  const remainingItems = items
    .filter((item) => !usedStableKeys.has(item.stableKey))
    .sort((left, right) => left.stableKey.localeCompare(right.stableKey, "ru"));

  const sections: ReadingSection[] = [
    { key: "plan", label: text.planSection, items: planItems },
    { key: "stay", label: text.staySection, items: stayItems },
    { key: "arrival", label: text.arrivalSection, items: arrivalItems },
    { key: "days", label: text.daySection, items: dayItems },
    { key: "departure", label: text.departureSection, items: departureItems },
    { key: "details", label: text.detailsSection, items: [...detailItems, ...remainingItems] },
  ];

  return sections.filter((section) => section.items.length > 0);
}

export function buildReadingOrder(items: PlanItem[], lang: AppLang = "ru"): PlanItem[] {
  return buildReadingSections(items, lang).flatMap((section) => section.items);
}
