FROM python:3.11-slim

WORKDIR /app

# Dépendances système nécessaires pour Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Installer dépendances Python
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium pour Playwright
RUN playwright install chromium

# Copier le code applicatif
COPY worker/ .

# Render utilise la variable PORT (10000 par défaut)
ENV PORT=10000
EXPOSE ${PORT}

# Lancer FastAPI sur le port dynamique de Render
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
