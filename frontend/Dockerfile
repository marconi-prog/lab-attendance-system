# Etapa 1: build estático da versão web (React Native Web)
FROM node:22-alpine AS build
WORKDIR /app
ARG EXPO_PUBLIC_API_URL=http://localhost:5000
ENV EXPO_PUBLIC_API_URL=$EXPO_PUBLIC_API_URL CI=1
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx expo export --platform web

# Etapa 2: servidor estático
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
