// Web push: asks permission, subscribes this device and hands the subscription to the API.
// The service worker (sw.ts) shows the notifications. Sending them needs the backend side,
// which stores subscriptions and sends alerts with the VAPID private key.
import { getToken } from "./api";

export type PushState = "default" | "enabled" | "denied" | "unsupported" | "notConfigured";

const VAPID_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY ?? "";
const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

function supported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export async function pushState(): Promise<PushState> {
  if (!supported()) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  if (Notification.permission !== "granted") return "default";
  const reg = await navigator.serviceWorker.getRegistration();
  return (await reg?.pushManager.getSubscription()) ? "enabled" : "default";
}

function urlBase64ToUint8Array(base64: string) {
  const padded = (base64 + "=".repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

export async function enablePush(): Promise<PushState> {
  if (!supported()) return "unsupported";
  if (!VAPID_KEY) return "notConfigured";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return permission === "denied" ? "denied" : "default";
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(VAPID_KEY) });
  await fetch(`${BASE}/api/push/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(sub),
  });
  return "enabled";
}
