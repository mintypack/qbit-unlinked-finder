FROM node:22-alpine AS webbuild
WORKDIR /src
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-dev
COPY backend/app ./backend/app
COPY --from=webbuild /src/dist ./frontend/dist
ENV QUF_CONFIG=/config/config.toml
EXPOSE 8000
CMD ["/app/backend/.venv/bin/uvicorn", "--factory", "app.main:build", \
     "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/backend"]
