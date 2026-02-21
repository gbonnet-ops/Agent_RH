"""Module d'orchestration LLM pour l'Agent RH.

Gère les appels au modèle de langage pour :
- Analyser la pertinence d'une offre par rapport au profil candidat.
- Rédiger une lettre de motivation personnalisée.
- Répondre aux questions du funnel de candidature.
"""

from dataclasses import dataclass

from scraper import JobOffer


@dataclass
class CandidateProfile:
    """Profil candidat récupéré depuis le frontend."""

    job_title: str
    skills: list[str]
    linkedin_url: str
    achievements: str  # Texte brut lu depuis Google Drive


@dataclass
class LLMOutput:
    """Résultat structuré de l'analyse LLM."""

    relevance_score: float  # 0.0 à 1.0
    cover_letter: str
    funnel_answers: dict[str, str]  # question -> réponse


async def analyze_offer(
    profile: CandidateProfile,
    offer: JobOffer,
) -> float:
    """Évalue la pertinence d'une offre par rapport au profil candidat.

    Args:
        profile: Profil du candidat.
        offer: Offre d'emploi à évaluer.

    Returns:
        Score de pertinence entre 0.0 (aucun match) et 1.0 (match parfait).
    """
    ...


async def generate_cover_letter(
    profile: CandidateProfile,
    offer: JobOffer,
) -> str:
    """Rédige une lettre de motivation personnalisée.

    La lettre est adaptée au poste, à l'entreprise, et met en avant
    les compétences et achievements pertinents du candidat.

    Args:
        profile: Profil du candidat.
        offer: Offre d'emploi ciblée.

    Returns:
        Texte de la lettre de motivation.
    """
    ...


async def answer_funnel_questions(
    profile: CandidateProfile,
    offer: JobOffer,
) -> dict[str, str]:
    """Génère des réponses aux questions du funnel de candidature.

    Args:
        profile: Profil du candidat.
        offer: Offre contenant les questions du funnel.

    Returns:
        Dictionnaire {question: réponse}.
    """
    ...


async def process_offer(
    profile: CandidateProfile,
    offer: JobOffer,
    relevance_threshold: float = 0.6,
) -> LLMOutput | None:
    """Pipeline complet d'analyse et de génération pour une offre.

    Évalue d'abord la pertinence. Si le score est au-dessus du seuil,
    génère la cover letter et les réponses au funnel.

    Args:
        profile: Profil du candidat.
        offer: Offre d'emploi à traiter.
        relevance_threshold: Score minimum pour poursuivre (défaut : 0.6).

    Returns:
        LLMOutput si l'offre est pertinente, None sinon.
    """
    ...
