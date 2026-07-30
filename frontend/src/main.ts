import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import "./style.css";

createApp(App).use(router).mount("#app");

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/offline-sw.js");
  });
}
