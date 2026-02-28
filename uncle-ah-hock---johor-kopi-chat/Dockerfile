FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Build args become VITE_ env vars at build time
ARG VITE_BACKEND_URL=http://localhost:5000/api
ARG VITE_CALL_AUDIO_RELAY_ENABLED=true
ARG VITE_CALL_AUDIO_WS_PORT=8765

ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_CALL_AUDIO_RELAY_ENABLED=$VITE_CALL_AUDIO_RELAY_ENABLED
ENV VITE_CALL_AUDIO_WS_PORT=$VITE_CALL_AUDIO_WS_PORT

RUN npm run build

# Serve with lightweight nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
