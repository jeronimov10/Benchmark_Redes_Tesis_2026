// Idiomas disponibles y su ruta.
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["es", "en"],
  defaultLocale: "es",
  localeCookie: false,
});

export type Locale = (typeof routing.locales)[number];
