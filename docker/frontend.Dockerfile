# WebSentinel frontend (React + Vite dev server).
# Build context is ./frontend.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Vite dev server with HMR; proxies /api to the backend (see vite.config.ts).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
