# Stage 1 — build
FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
# npm ci (not npm install) — installs exactly what's in the lockfile for reproducible builds.
RUN npm ci

COPY . .
RUN node node_modules/vite/bin/vite.js build

# Stage 2 — serve
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
