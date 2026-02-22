FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système pour Playwright
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer dépendances Python
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright
RUN playwright install chromium --with-deps

# Copier le code
COPY worker/ .

# Exposer le port
EXPOSE 8000

# Lancer FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
