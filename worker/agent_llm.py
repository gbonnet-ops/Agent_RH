"""Module d'orchestration LLM pour l'Agent RH.

Gère les appels au modèle de langage pour :
- Analyser la pertinence d'une offre par rapport au profil candidat.
- Rédiger une lettre de motivation personnalisée.
- Répondre aux questions du funnel de candidature.
"""

import json
import logging
import os
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from scraper import JobOffer

logger = logging.getLogger("agent_rh.llm")

# Modèle par défaut — GPT-4o mini pour le rapport coût/qualité
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@dataclass
class CandidateProfile:
    """Profil candidat récupéré depuis le frontend."""

    job_title: str
    skills: list[str]
    linkedin_url: str
    achievements: str  # Texte brut lu depuis Google Drive
    cv_text: str = ""  # CV complet en texte
    years_experience: int = 0  # Années d'expérience professionnelle
    personal_note: str = ""  # Note personnelle pour humaniser la lettre


@dataclass
class LLMOutput:
    """Résultat structuré de l'analyse LLM."""

    relevance_score: float  # 0.0 à 1.0
    cover_letter: str
    funnel_answers: dict[str, str]  # question -> réponse


def _get_llm() -> ChatOpenAI:
    """Instancie le client LLM."""
    return ChatOpenAI(model=MODEL_NAME, temperature=0.7)


async def analyze_offer(
    profile: CandidateProfile,
    offer: JobOffer,
) -> float:
    """Évalue la pertinence d'une offre par rapport au profil candidat.

    Returns:
        Score de pertinence entre 0.0 et 1.0.
    """
    llm = _get_llm()

    system = SystemMessage(content=(
        "Tu es un expert en recrutement. Évalue la pertinence d'une offre "
        "d'emploi par rapport au profil d'un candidat. "
        "Réponds UNIQUEMENT avec un nombre décimal entre 0.0 et 1.0."
    ))
    cv_info = f"\n- CV :\n{profile.cv_text}" if profile.cv_text else ""
    xp_info = f"\n- Années d'expérience : {profile.years_experience}" if profile.years_experience else ""
    human = HumanMessage(content=(
        f"## Profil candidat\n"
        f"- Poste recherché : {profile.job_title}\n"
        f"- Compétences : {', '.join(profile.skills)}\n"
        f"- Réalisations : {profile.achievements}\n"
        f"{xp_info}"
        f"{cv_info}\n\n"
        f"## Offre d'emploi\n"
        f"- Titre : {offer.title}\n"
        f"- Entreprise : {offer.company}\n"
        f"- Description : {offer.description}\n\n"
        f"Score de pertinence (0.0 à 1.0) :"
    ))

    response = await llm.ainvoke([system, human])
    try:
        score = float(response.content.strip())
        return max(0.0, min(1.0, score))
    except ValueError:
        logger.warning("Score LLM invalide: %s, fallback 0.5", response.content)
        return 0.5


async def generate_cover_letter(
    profile: CandidateProfile,
    offer: JobOffer,
) -> str:
    """Rédige une lettre de motivation personnalisée.

    Se base sur le CV, la note personnelle et la description du poste.
    """
    llm = _get_llm()

    # Construire le bloc CV si fourni
    cv_block = ""
    if profile.cv_text:
        cv_block = (
            f"\n\n## CV COMPLET DU CANDIDAT\n"
            f"Utilise ces informations concrètes (expériences, chiffres, "
            f"résultats, entreprises) pour personnaliser la lettre :\n\n"
            f"{profile.cv_text}\n"
        )

    # Construire le bloc note personnelle si fourni
    personal_block = ""
    if profile.personal_note:
        personal_block = (
            "\n\n## NOTE PERSONNELLE DU CANDIDAT\n"
            "Voici des éléments personnels que le candidat souhaite voir "
            "intégrés dans sa lettre de motivation. Utilise-les de manière "
            "naturelle pour rendre la lettre authentique et humaine. "
            "Intègre ces éléments là où ils sont pertinents par rapport "
            "à l'offre ciblée :\n\n"
            f"{profile.personal_note}\n"
        )

    system = SystemMessage(content=(
        "Tu es un coach carrière senior spécialisé dans la rédaction de "
        "candidatures percutantes en français.\n\n"
        "Ta méthode : tu analyses en profondeur le CV du candidat, sa note "
        "personnelle et la description du poste pour créer une lettre de "
        "motivation sur-mesure qui fait le pont entre le parcours du candidat "
        "et les besoins spécifiques de l'entreprise.\n\n"
        "Règles strictes :\n"
        "1. ACCROCHE (2 phrases max) : Mentionne le nom de l'entreprise et "
        "pourquoi elle attire le candidat spécifiquement (culture, produit, "
        "mission). Déduis-le de la description de poste.\n"
        "2. VALEUR AJOUTÉE (1-2 paragraphes) : Relie les expériences et "
        "compétences concrètes du CV aux besoins du poste. Cite des chiffres, "
        "des projets réels, des résultats mesurables tirés du CV. Si la note "
        "personnelle contient des éléments pertinents pour ce poste, "
        "intègre-les naturellement.\n"
        "3. MOTIVATION (2-3 phrases) : Explique ce que le candidat apportera "
        "à l'équipe, pas juste ce qu'il veut. Utilise la note personnelle "
        "pour donner de la profondeur humaine.\n"
        "4. CONCLUSION : Appel à l'action naturel.\n\n"
        "Style :\n"
        "- Ton professionnel mais humain (pas de jargon creux type "
        "'fort de mon expérience', 'dynamique et motivé', "
        "'passionné', 'force de proposition')\n"
        "- Maximum 300 mots\n"
        "- Personnalise au maximum : cite le nom de l'entreprise, le poste exact, "
        "des éléments concrets du CV du candidat\n"
        "- JAMAIS de phrases génériques utilisables pour n'importe quelle entreprise\n"
        "- Utilise des données concrètes du CV : noms d'entreprises, chiffres, projets\n\n"
        "Format : Commence par 'Madame, Monsieur,' et termine par 'Cordialement,'. "
        "Pas d'en-tête, pas de date, pas de signature."
        + personal_block
    ))
    xp_block = (
        f"\n- Années d'expérience : {profile.years_experience} ans\n"
        if profile.years_experience
        else ""
    )

    human = HumanMessage(content=(
        f"## Profil du candidat\n"
        f"- Poste recherché : {profile.job_title}\n"
        f"- Compétences techniques : {', '.join(profile.skills)}\n"
        f"{xp_block}"
        f"- Réalisations et expérience :\n{profile.achievements}\n"
        f"{cv_block}\n"
        f"## Offre ciblée\n"
        f"- Poste : {offer.title}\n"
        f"- Entreprise : {offer.company}\n"
        f"- Description complète de l'offre :\n{offer.description}\n\n"
        f"Rédige une lettre de motivation unique et spécifique à cette offre. "
        f"Chaque phrase doit montrer que le candidat a lu et compris l'offre. "
        f"Utilise des éléments concrets du CV pour appuyer chaque argument :"
    ))

    response = await llm.ainvoke([system, human])
    return response.content.strip()


async def answer_funnel_questions(
    profile: CandidateProfile,
    offer: JobOffer,
) -> dict[str, str]:
    """Génère des réponses aux questions du funnel de candidature."""
    if not offer.funnel_questions:
        return {}

    llm = _get_llm()

    questions_text = "\n".join(
        f"{i+1}. {q}" for i, q in enumerate(offer.funnel_questions)
    )

    system = SystemMessage(content=(
        "Tu es un candidat qui répond aux questions d'un formulaire de "
        "candidature. Réponds de façon professionnelle, concise (3-5 phrases "
        "par réponse) et personnalisée avec le profil fourni. "
        "Réponds au format JSON : {\"question\": \"réponse\", ...}"
    ))
    human = HumanMessage(content=(
        f"## Mon profil\n"
        f"- Poste recherché : {profile.job_title}\n"
        f"- Compétences : {', '.join(profile.skills)}\n"
        f"- Réalisations : {profile.achievements}\n\n"
        f"## Offre : {offer.title} chez {offer.company}\n\n"
        f"## Questions du formulaire :\n{questions_text}\n\n"
        f"Réponses en JSON :"
    ))

    response = await llm.ainvoke([system, human])

    try:
        # Extraire le JSON de la réponse (peut être entouré de ```json)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        answers = json.loads(content)
        return answers
    except (json.JSONDecodeError, IndexError):
        logger.warning("Réponse funnel non-JSON, fallback texte brut")
        return {q: response.content for q in offer.funnel_questions}


async def process_offer(
    profile: CandidateProfile,
    offer: JobOffer,
    relevance_threshold: float = 0.6,
) -> LLMOutput | None:
    """Pipeline complet d'analyse et de génération pour une offre.

    Évalue d'abord la pertinence. Si le score est au-dessus du seuil,
    génère la cover letter et les réponses au funnel.

    Returns:
        LLMOutput si l'offre est pertinente, None sinon.
    """
    score = await analyze_offer(profile, offer)
    logger.info("Offre '%s' @ %s — score: %.2f", offer.title, offer.company, score)

    if score < relevance_threshold:
        logger.info("Score trop bas (< %.2f), offre ignorée", relevance_threshold)
        return None

    cover_letter = await generate_cover_letter(profile, offer)
    funnel_answers = await answer_funnel_questions(profile, offer)

    return LLMOutput(
        relevance_score=score,
        cover_letter=cover_letter,
        funnel_answers=funnel_answers,
    )
