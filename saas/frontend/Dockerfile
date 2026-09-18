FROM node:22-alpine AS build

WORKDIR /app

# `npm ci` suit package-lock.json : les versions installées sont celles qui ont été testées.
# (Avec `npm install` et le seul package.json, chaque build resolvait a neuf les dependances
# indirectes ; une version publiee le 2026-09-18 cassait la resolution — build en echec.)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
