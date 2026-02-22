FROM python:3.11-slim

WORKDIR /app

# Installer dépendances Python d'abord (layer caching)
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium + toutes ses dépendances système automatiquement
RUN playwright install --with-deps chromium

# Copier le code applicatif
COPY worker/ .

# Render utilise la variable PORT (10000 par défaut)
ENV PORT=10000
EXPOSE ${PORT}

# Lancer FastAPI sur le port dynamique de Render
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
