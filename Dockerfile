# Stage 1: Build Vue UI
FROM node:20-alpine AS ui-builder
WORKDIR /app
# Copy workspace manifests so npm ci resolves all workspaces
COPY package.json package-lock.json ./
COPY api/package.json ./api/
COPY ui/package.json ./ui/
RUN npm ci
COPY ui/ ./ui/
ENV VITE_API_URL=/api
RUN npm run build:ui

# Stage 2: Build NestJS API
FROM node:20-alpine AS api-builder
WORKDIR /app
COPY package.json package-lock.json ./
COPY api/package.json ./api/
COPY ui/package.json ./ui/
RUN npm ci
COPY api/ ./api/
RUN npm run build:api

# Stage 3: Production runtime
FROM node:20-alpine
WORKDIR /app
# node_modules are hoisted to the root in a workspace install
COPY --from=api-builder /app/node_modules ./node_modules
COPY --from=api-builder /app/api/dist ./api/dist
COPY --from=api-builder /app/api/package.json ./api/package.json
COPY --from=ui-builder /app/ui/dist ./ui/dist
ENV API_PORT=7860
EXPOSE 7860
WORKDIR /app/api
CMD ["node", "dist/main.js"]
