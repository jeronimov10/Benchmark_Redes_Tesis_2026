// Proxy de Next.js que aplica el prefijo de idioma a las rutas.
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: "/((?!api|_next|_vercel|.*\..*).*)",
};
