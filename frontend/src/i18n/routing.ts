import { defineRouting } from "next-intl/routing";

// Add a language: create messages/<code>.json and append the code here.
export const routing = defineRouting({
  locales: ["es", "en"],
  defaultLocale: "es",
  // First visit follows the browser language (Accept-Language); es is only the fallback.
  // No cookie: the locale lives in the URL, so a stale choice never overrides the browser.
  localeCookie: false,
});

export type Locale = (typeof routing.locales)[number];
