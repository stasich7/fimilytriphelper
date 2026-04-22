FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM golang:1.25-alpine AS backend-build

WORKDIR /app/backend

COPY backend/go.mod backend/go.sum ./
RUN go mod download

COPY backend/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /family-trip-helper ./cmd/server

FROM alpine:3.20

WORKDIR /app

COPY --from=backend-build /family-trip-helper /usr/local/bin/family-trip-helper
COPY --from=frontend-build /app/frontend/dist /app/web

EXPOSE 80

CMD ["family-trip-helper"]
