"""Module de notification par email.

Envoie les résultats du pipeline (offres trouvées, CV personnalisé,
lettre de motivation) au candidat par email via Resend.
"""

import base64
import logging
import os
from pathlib import Path

import resend

logger = logging.getLogger("agent_rh.notifier")


def _init_resend() -> None:
    """Configure la clé API Resend."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        raise ValueError("RESEND_API_KEY non défini")
    resend.api_key = api_key


def send_email(
    to: str,
    subject: str,
    body_html: str,
    attachments: list[Path] | None = None,
) -> bool:
    """Envoie un email avec pièces jointes optionnelles.

    Args:
        to: Adresse email du destinataire.
        subject: Objet de l'email.
        body_html: Corps de l'email en HTML.
        attachments: Liste de chemins vers les fichiers à joindre.

    Returns:
        True si l'envoi a réussi, False sinon.
    """
    _init_resend()

    # Préparer les pièces jointes
    resend_attachments = []
    if attachments:
        for file_path in attachments:
            if file_path.exists():
                with open(file_path, "rb") as f:
                    content = base64.b64encode(f.read()).decode("utf-8")
                resend_attachments.append({
                    "filename": file_path.name,
                    "content": content,
                })

    params = {
        "from": "Agent RH <onboarding@resend.dev>",
        "to": [to],
        "subject": subject,
        "html": body_html,
    }
    if resend_attachments:
        params["attachments"] = resend_attachments

    try:
        result = resend.Emails.send(params)
        logger.info("Email envoyé à %s (id: %s)", to, result.get("id", "?"))
        return True
    except Exception:
        logger.exception("Erreur envoi email à %s", to)
        return False


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
    count = len(offers_summary)
    subject = f"Agent RH — {count} offre{'s' if count > 1 else ''} trouvée{'s' if count > 1 else ''}"

    rows = ""
    for offer in offers_summary:
        score_pct = int(float(offer.get("score", 0)) * 100)
        rows += (
            f"<tr>"
            f"<td style='padding:8px;border-bottom:1px solid #eee'>{offer.get('title', '')}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee'>{offer.get('company', '')}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee;text-align:center'>{score_pct}%</td>"
            f"</tr>"
        )

    files_list = ""
    if generated_files:
        files_list = "<h3>Documents générés :</h3><ul>"
        for f in generated_files:
            files_list += f"<li>{f.name}</li>"
        files_list += "</ul>"

    body_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#1a1a2e">Rapport Agent RH</h2>
        <p>Bonjour,</p>
        <p>Voici les offres correspondant à votre profil :</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0">
            <thead>
                <tr style="background:#f5f5f5">
                    <th style="padding:8px;text-align:left">Poste</th>
                    <th style="padding:8px;text-align:left">Entreprise</th>
                    <th style="padding:8px;text-align:center">Match</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        {files_list}
        <p style="color:#666;font-size:12px;margin-top:24px">
            Envoyé automatiquement par Agent RH
        </p>
    </div>
    """

    return subject, body_html


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
    subject, body_html = build_report_email(offers_summary, generated_files)
    return send_email(
        to=email,
        subject=subject,
        body_html=body_html,
        attachments=generated_files,
    )
