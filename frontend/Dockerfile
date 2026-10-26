# Imagen del frontend (Next.js, pnpm). La URL del backend se fija al construir porque next.config.ts la usa en las rewrites.
# El contexto nombrado "certs" aporta CAs extra (antivirus/proxy que intercepta HTTPS) para npm/pnpm durante la construccion.
FROM node:22-alpine AS build
COPY --from=certs . /extra-certs
RUN cat /etc/ssl/certs/ca-certificates.crt /extra-certs/*.crt > /extra-ca.pem 2>/dev/null || cp /etc/ssl/certs/ca-certificates.crt /extra-ca.pem
ENV NODE_EXTRA_CA_CERTS=/extra-ca.pem
RUN npm install -g pnpm@12.14.0
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=${BACKEND_URL}
RUN pnpm build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/messages ./messages
COPY --from=build /app/next.config.ts ./next.config.ts
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/ >/dev/null || exit 1
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
