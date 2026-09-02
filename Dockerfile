FROM node:22-alpine AS fe
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=fe /fe/dist ./frontend/dist
ENV PYTHONPATH=/app
ENV COOKIE_SECURE=1
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "backend.wsgi:app"]
