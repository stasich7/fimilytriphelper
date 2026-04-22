import { createRouter, createWebHistory } from "vue-router";

import OverviewPage from "../pages/OverviewPage.vue";
import PlanItemPage from "../pages/PlanItemPage.vue";
import PlanVersionPage from "../pages/PlanVersionPage.vue";
import ToolsPage from "../pages/ToolsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }

    return { top: 0 };
  },
  routes: [
    {
      path: "/",
      name: "overview",
      component: OverviewPage,
    },
    {
      path: "/versions/:versionId",
      name: "version",
      component: PlanVersionPage,
    },
    {
      path: "/items/:itemId",
      name: "item",
      component: PlanItemPage,
    },
    {
      path: "/tools",
      name: "tools",
      component: ToolsPage,
    },
    {
      path: "/guest/:guestToken",
      name: "guest",
      component: OverviewPage,
    },
    {
      path: "/guest/:guestToken/versions/:versionId",
      name: "guest-version",
      component: PlanVersionPage,
    },
    {
      path: "/guest/:guestToken/items/:itemId",
      name: "guest-item",
      component: PlanItemPage,
    },
  ],
});

export default router;
