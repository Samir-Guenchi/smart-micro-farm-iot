/// <reference lib="webworker" />
// Service worker: offline app shell (precache) and push notifications.
import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";

declare const self: ServiceWorkerGlobalScope;

self.skipWaiting();
self.addEventListener("activate", () => self.clients.claim());
cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST);

// Payload from the backend: {"title": "...", "body": "...", "url": "#/bed"}
self.addEventListener("push", (event) => {
  let data: { title?: string; body?: string; url?: string } = {};
  try {
    data = event.data?.json() ?? {};
  } catch {
    data = { body: event.data?.text() };
  }
  event.waitUntil(
    self.registration.showNotification(data.title ?? "GreenLoop Farm", {
      body: data.body ?? "",
      icon: "icons/icon-192.png",
      badge: "icons/icon-192.png",
      data: { url: data.url ?? "./" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url ?? "./", self.registration.scope).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const open = clients.find((c) => c.url.startsWith(self.registration.scope));
      if (open) {
        open.navigate(url);
        return open.focus();
      }
      return self.clients.openWindow(url);
    }),
  );
});
