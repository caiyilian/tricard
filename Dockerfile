FROM python:3.11-slim

WORKDIR /app

# Install Node.js (for frontend build)
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY backend/requirements.txt backend/
COPY frontend/package.json frontend/package-lock.json frontend/

# Install Python deps
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install frontend deps and build
WORKDIR /app/frontend
RUN npm install
COPY frontend/ .
RUN npm run build

# Copy backend
WORKDIR /app
COPY backend/ backend/

# Seed AI accounts
RUN python backend/scripts/seed_ai.py --ensure

EXPOSE 8000

CMD ["uvicorn", "app.main:sio_app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]