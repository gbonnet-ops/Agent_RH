"""Client Google Drive via Service Account.

Permet de lire des fichiers (texte, docx) depuis un dossier Drive
dont l'ID est fourni par la variable d'environnement DRIVE_FOLDER_ID.
"""

from pathlib import Path


def authenticate() -> object:
    """Authentifie le client via le fichier JSON du Service Account.

    Le chemin du fichier est lu depuis la variable d'environnement
    GOOGLE_SERVICE_ACCOUNT_JSON.

    Returns:
        Objet service Google Drive authentifié.
    """
    ...


def list_files(folder_id: str) -> list[dict[str, str]]:
    """Liste les fichiers d'un dossier Drive.

    Args:
        folder_id: ID du dossier Google Drive.

    Returns:
        Liste de dicts avec 'id', 'name', et 'mimeType' de chaque fichier.
    """
    ...


def download_file(file_id: str, destination: Path) -> Path:
    """Télécharge un fichier Drive en local.

    Args:
        file_id: ID du fichier sur Google Drive.
        destination: Chemin local de destination.

    Returns:
        Chemin du fichier téléchargé.
    """
    ...


def read_text_file(file_id: str) -> str:
    """Lit le contenu texte d'un fichier Drive directement en mémoire.

    Args:
        file_id: ID du fichier texte sur Google Drive.

    Returns:
        Contenu du fichier sous forme de chaîne.
    """
    ...
