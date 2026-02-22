"""Client Google Drive via Service Account.

Permet de lire des fichiers (texte, docx) depuis un dossier Drive
dont l'ID est fourni par la variable d'environnement DRIVE_FOLDER_ID.
"""

import io
import json
import logging
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger("agent_rh.drive")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authenticate():
    """Authentifie le client via le fichier JSON du Service Account.

    Le chemin du fichier est lu depuis la variable d'environnement
    GOOGLE_SERVICE_ACCOUNT_JSON. Supporte aussi un JSON inline
    (utile pour les variables d'env sur Render/Vercel).

    Returns:
        Objet service Google Drive authentifié.
    """
    creds_source = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not creds_source:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON non défini")

    # Si c'est un JSON inline (commence par {), on le parse directement
    if creds_source.strip().startswith("{"):
        info = json.loads(creds_source)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    else:
        # Sinon c'est un chemin vers un fichier
        credentials = service_account.Credentials.from_service_account_file(
            creds_source, scopes=SCOPES
        )

    service = build("drive", "v3", credentials=credentials)
    logger.info("Client Google Drive authentifié")
    return service


def list_files(folder_id: str) -> list[dict[str, str]]:
    """Liste les fichiers d'un dossier Drive.

    Args:
        folder_id: ID du dossier Google Drive.

    Returns:
        Liste de dicts avec 'id', 'name', et 'mimeType' de chaque fichier.
    """
    service = authenticate()
    query = f"'{folder_id}' in parents and trashed = false"

    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        pageSize=100,
    ).execute()

    files = results.get("files", [])
    logger.info("%d fichiers trouvés dans le dossier %s", len(files), folder_id)
    return files


def download_file(file_id: str, destination: Path) -> Path:
    """Télécharge un fichier Drive en local.

    Args:
        file_id: ID du fichier sur Google Drive.
        destination: Chemin local de destination.

    Returns:
        Chemin du fichier téléchargé.
    """
    service = authenticate()
    request = service.files().get_media(fileId=file_id)

    destination.parent.mkdir(parents=True, exist_ok=True)

    with open(destination, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    logger.info("Fichier téléchargé : %s", destination)
    return destination


def read_text_file(file_id: str) -> str:
    """Lit le contenu texte d'un fichier Drive directement en mémoire.

    Args:
        file_id: ID du fichier texte sur Google Drive.

    Returns:
        Contenu du fichier sous forme de chaîne.
    """
    service = authenticate()
    request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    content = buffer.getvalue().decode("utf-8")
    logger.info("Fichier texte lu (%d caractères)", len(content))
    return content
