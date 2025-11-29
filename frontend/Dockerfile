# --- Stage 1: build the static React bundle ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# VITE_API_BASE is left empty so the app uses relative /api URLs, which nginx
# proxies to the backend (single origin -> no CORS needed in production).
RUN npm run build

# --- Stage 2: serve the bundle with nginx ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
