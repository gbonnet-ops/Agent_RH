"""Générateur de documents Word pour l'Agent RH.

Utilise python-docx pour prendre un template Word (issu de Google Drive)
et le remplir avec les données générées par le LLM (CV personnalisé,
lettre de motivation, etc.).
"""

from pathlib import Path


def load_template(template_path: Path) -> object:
    """Charge un template Word (.docx) depuis le disque.

    Args:
        template_path: Chemin vers le fichier template .docx.

    Returns:
        Objet Document python-docx.
    """
    ...


def fill_template(
    template_path: Path,
    placeholders: dict[str, str],
    output_path: Path,
) -> Path:
    """Remplit un template Word en remplaçant les placeholders.

    Les placeholders dans le document sont au format {{NOM_VARIABLE}}.

    Args:
        template_path: Chemin du template source.
        placeholders: Dictionnaire {placeholder: valeur de remplacement}.
        output_path: Chemin de sortie du document généré.

    Returns:
        Chemin du document généré.
    """
    ...


def generate_cover_letter_docx(
    cover_letter_text: str,
    candidate_name: str,
    company_name: str,
    output_path: Path,
) -> Path:
    """Génère un document Word contenant la lettre de motivation.

    Crée un document formaté de zéro (sans template) avec en-tête,
    corps de lettre et signature.

    Args:
        cover_letter_text: Texte de la lettre de motivation.
        candidate_name: Nom complet du candidat.
        company_name: Nom de l'entreprise destinataire.
        output_path: Chemin de sortie du fichier .docx.

    Returns:
        Chemin du document généré.
    """
    ...
