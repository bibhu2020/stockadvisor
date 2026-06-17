# Stage 0: Install all dependencies once (build tools needed for better-sqlite3 native module)
FROM node:20-alpine AS deps
WORKDIR /app
RUN apk add --no-cache python3 make g++
COPY package.json package-lock.json ./
COPY api/package.json ./api/
COPY ui/package.json ./ui/
RUN npm ci

# Stage 1: Build Vue UI
FROM node:20-alpine AS ui-builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/ui/node_modules ./ui/node_modules
COPY ui/ ./ui/
WORKDIR /app/ui
ENV VITE_API_URL=/api
RUN PATH="/app/node_modules/.bin:/app/ui/node_modules/.bin:$PATH" vite build

# Stage 2: Build NestJS API
FROM node:20-alpine AS api-builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/api/node_modules ./api/node_modules
COPY api/ ./api/
WORKDIR /app/api
RUN node_modules/.bin/nest build

# Stage 3: Production runtime
FROM node:20-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/api/node_modules ./api/node_modules
COPY --from=api-builder /app/api/dist ./api/dist
COPY --from=api-builder /app/api/package.json ./api/package.json
COPY --from=ui-builder /app/ui/dist ./ui/dist
ENV API_PORT=7860
EXPOSE 7860
WORKDIR /app/api
CMD ["node", "dist/main.js"]
