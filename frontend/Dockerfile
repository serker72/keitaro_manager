# syntax=docker/dockerfile:1
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Адрес бэкенда внутри docker-сети (используется routeRules-прокси)
ARG NUXT_BACKEND_URL=http://backend:8000
ENV NUXT_BACKEND_URL=${NUXT_BACKEND_URL}

RUN npm run build


FROM node:22-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NITRO_HOST=0.0.0.0 \
    NITRO_PORT=3000

COPY --from=build /app/.output ./.output

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
