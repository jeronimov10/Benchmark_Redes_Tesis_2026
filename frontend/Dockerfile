# Imagen del frontend (Next.js). La URL del backend se fija al construir porque next.config.ts la usa en las rewrites.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=${BACKEND_URL}
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/messages ./messages
COPY --from=build /app/next.config.ts ./next.config.ts
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
