# Stage 1: Build the frontend React app
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the FastAPI backend
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies (needed for Pillow, ddddocr, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy the rest of the application code
COPY backend/ ./backend
COPY automation/ ./automation
COPY report_generator/ ./report_generator

# Install report_generator requirements
COPY report_generator/requirements.txt ./report_generator/requirements.txt
RUN pip install --no-cache-dir -r report_generator/requirements.txt

# Install Playwright chromium browser for the scraper
RUN playwright install chromium

# Create folders for data storage
RUN mkdir -p data/reports data/uploads

# Expose port and run server
ENV PORT=8000
CMD uvicorn backend.server:app --host 0.0.0.0 --port $PORT
