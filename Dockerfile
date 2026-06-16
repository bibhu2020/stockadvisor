# Stage 1: Build Vue UI
FROM node:20-alpine AS ui-builder
WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ .
ENV VITE_API_URL=/api
RUN npm run build

# Stage 2: Build NestJS API
FROM node:20-alpine AS api-builder
WORKDIR /app/api
COPY api/package*.json ./
RUN npm ci
COPY api/ .
RUN npm run build

# Stage 3: Production runtime
FROM node:20-alpine
WORKDIR /app
COPY --from=api-builder /app/api/dist ./api/dist
COPY --from=api-builder /app/api/node_modules ./api/node_modules
COPY --from=api-builder /app/api/package.json ./api/package.json
COPY --from=ui-builder /app/ui/dist ./ui/dist
ENV API_PORT=7860
EXPOSE 7860
WORKDIR /app/api
CMD ["node", "dist/main.js"]
