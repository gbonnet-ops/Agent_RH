"""Module de notification par email.

Envoie les résultats du pipeline (offres trouvées, CV personnalisé,
lettre de motivation) au candidat par email via Resend ou SMTP.
"""

from pathlib import Path


def send_email(
    to: str,
    subject: str,
    body_html: str,
    attachments: list[Path] | None = None,
) -> bool:
    """Envoie un email avec pièces jointes optionnelles.

    Utilise l'API Resend (clé dans RESEND_API_KEY) ou un fallback SMTP.

    Args:
        to: Adresse email du destinataire.
        subject: Objet de l'email.
        body_html: Corps de l'email en HTML.
        attachments: Liste de chemins vers les fichiers à joindre.

    Returns:
        True si l'envoi a réussi, False sinon.
    """
    ...


def build_report_email(
    offers_summary: list[dict[str, str]],
    generated_files: list[Path],
) -> tuple[str, str]:
    """Construit le sujet et le corps HTML du rapport quotidien.

    Args:
        offers_summary: Liste de résumés d'offres
            (chaque dict contient 'title', 'company', 'score').
        generated_files: Liste des fichiers générés (CV, cover letters).

    Returns:
        Tuple (subject, body_html).
    """
    ...


def notify_candidate(
    email: str,
    offers_summary: list[dict[str, str]],
    generated_files: list[Path],
) -> bool:
    """Point d'entrée principal : construit et envoie le rapport.

    Args:
        email: Email du candidat.
        offers_summary: Résumés des offres traitées.
        generated_files: Fichiers générés à joindre.

    Returns:
        True si l'email a été envoyé avec succès.
    """
    ...
