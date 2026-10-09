# Two stages: Node builds the app, then only the built files are copied into
# a small web server image. Node, node_modules and the source never reach the
# final image -- the browser only needs static HTML, JS and CSS.

# --- Stage 1: build ---
FROM node:24-slim AS build
WORKDIR /app

# Lockfile first, same layer-cache idea as the API image: npm ci reruns only
# when the dependencies change, not on every source edit.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The API URL is written into the JavaScript at build time; the built files
# can't read environment variables later. It must be a URL the *browser* can
# reach (a host port), not the Docker-network name "api".
ARG VITE_API_URL=http://127.0.0.1:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# --- Stage 2: serve ---
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
