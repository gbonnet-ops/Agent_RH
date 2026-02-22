"""Point d'entrée FastAPI pour l'Agent RH.

Expose une route POST /trigger-job-search déclenchée par le Cron Vercel
pour lancer le pipeline de recherche d'emploi automatisée.
"""

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_llm import CandidateProfile, process_offer
from document_builder import fill_template, generate_cover_letter_docx
from drive_client import list_files, read_text_file
from notifier import notify_candidate
from scraper import JobOffer

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_rh")

app = FastAPI(title="Agent RH Worker", version="0.1.0")

# CORS pour permettre au frontend Vercel d'appeler le worker
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://agent-rh.vercel.app",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dossier de sortie pour les documents générés
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(tempfile.gettempdir()) / "agent_rh_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Modèles Pydantic pour les requêtes / réponses
# ---------------------------------------------------------------------------
class JobSearchRequest(BaseModel):
    """Paramètres optionnels pour déclencher la recherche."""

    job_title: str = "Développeur Full-Stack Senior"
    location: str = "Paris"
    candidate_name: str = "Jean Dupont"
    candidate_email: str = "jean.dupont@example.com"


class ProcessedOffer(BaseModel):
    """Résumé d'une offre traitée par le pipeline."""

    title: str
    company: str
    relevance_score: float
    cover_letter_path: str
    cv_path: str | None = None


class JobSearchResponse(BaseModel):
    """Réponse du pipeline de recherche."""

    status: str
    processed_at: str
    offers_count: int
    results: list[ProcessedOffer]


# ---------------------------------------------------------------------------
# Données mockées pour tester le pipeline sans scraping réel
# ---------------------------------------------------------------------------
MOCK_OFFERS: list[JobOffer] = [
    JobOffer(
        title="Développeur Full-Stack Python/React",
        company="TechStartup SAS",
        url="https://www.welcometothejungle.com/fr/companies/techstartup/jobs/dev-fullstack",
        description=(
            "Nous recherchons un développeur Full-Stack pour rejoindre notre "
            "équipe produit. Vous travaillerez sur notre plateforme SaaS B2B "
            "avec une stack Python (FastAPI) / React / PostgreSQL / AWS. "
            "Expérience requise : 5 ans minimum, maîtrise de CI/CD, "
            "sensibilité UX."
        ),
        funnel_questions=[
            "Pourquoi souhaitez-vous rejoindre TechStartup ?",
            "Décrivez un projet technique dont vous êtes fier.",
        ],
    ),
    JobOffer(
        title="Lead Developer Python",
        company="DataCorp",
        url="https://www.welcometothejungle.com/fr/companies/datacorp/jobs/lead-dev",
        description=(
            "DataCorp recrute un Lead Developer Python pour piloter une "
            "équipe de 4 développeurs. Mission : refonte de notre pipeline "
            "data (Airflow, dbt, BigQuery) et développement d'APIs internes. "
            "Poste basé à Paris, 3j de télétravail."
        ),
        funnel_questions=[
            "Quelle est votre expérience en management d'équipe technique ?",
        ],
    ),
    JobOffer(
        title="Ingénieur MLOps",
        company="AI Factory",
        url="https://www.welcometothejungle.com/fr/companies/aifactory/jobs/mlops",
        description=(
            "Rejoignez AI Factory en tant qu'Ingénieur MLOps. Vous mettrez "
            "en production des modèles ML, gérerez l'infra Kubernetes, et "
            "développerez les pipelines de feature engineering. "
            "Stack : Python, Docker, K8s, MLflow, Terraform."
        ),
        funnel_questions=[
            "Avez-vous déjà déployé un modèle ML en production ?",
            "Quelle est votre expérience avec Kubernetes ?",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_achievements_from_drive() -> str:
    """Tente de charger les réalisations du candidat depuis Google Drive."""
    folder_id = os.getenv("DRIVE_FOLDER_ID", "")
    if not folder_id:
        return ""

    try:
        files = list_files(folder_id)
        for f in files:
            if "achievement" in f["name"].lower() or "realisation" in f["name"].lower():
                return read_text_file(f["id"])
    except Exception:
        logger.warning("Impossible de lire les achievements depuis Drive", exc_info=True)

    return ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    """Health-check basique pour le monitoring."""
    return {"status": "ok", "service": "agent-rh-worker"}


@app.post("/trigger-job-search", response_model=JobSearchResponse)
async def trigger_job_search(
    request: JobSearchRequest | None = None,
) -> JobSearchResponse:
    """Déclenche le pipeline complet de recherche d'emploi.

    Étapes orchestrées :
    1. Récupérer les offres (mockées pour le moment).
    2. Charger les achievements depuis Google Drive.
    3. Pour chaque offre : analyser avec le LLM, générer la cover letter.
    4. Envoyer le rapport par email via Resend.
    5. Retourner le récapitulatif.
    """
    if request is None:
        request = JobSearchRequest()

    logger.info(
        "Pipeline déclenché pour '%s' à '%s'",
        request.job_title,
        request.location,
    )

    # -- Étape 1 : récupérer les offres (mock) --
    offers = MOCK_OFFERS
    logger.info("%d offres trouvées (mockées)", len(offers))

    # -- Étape 2 : charger le profil candidat --
    achievements = _load_achievements_from_drive()
    candidate = CandidateProfile(
        job_title=request.job_title,
        skills=[s.strip() for s in request.job_title.split(",")],
        linkedin_url="",
        achievements=achievements or "Profil professionnel expérimenté",
    )

    results: list[ProcessedOffer] = []
    generated_files: list[Path] = []

    for i, offer in enumerate(offers):
        # -- Étape 3 : analyse LLM --
        llm_output = None
        use_llm = bool(os.getenv("OPENAI_API_KEY"))

        if use_llm:
            try:
                llm_output = await process_offer(candidate, offer)
            except Exception:
                logger.warning("Erreur LLM pour %s, fallback mock", offer.company, exc_info=True)

        if llm_output:
            score = llm_output.relevance_score
            cover_text = llm_output.cover_letter
        else:
            # Fallback mock
            score = round(0.9 - i * 0.15, 2)
            cover_text = (
                f"Madame, Monsieur,\n\n"
                f"Votre offre de {offer.title} chez {offer.company} a retenu "
                f"mon attention. Fort de mon expérience, je suis convaincu que "
                f"mon profil correspond à vos attentes.\n\n"
                f"Cordialement"
            )

        # -- Étape 4 : générer la cover letter en .docx --
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company = offer.company.replace(" ", "_").lower()
        cl_filename = f"cover_letter_{safe_company}_{timestamp}_{i}.docx"
        cl_path = OUTPUT_DIR / cl_filename

        try:
            generate_cover_letter_docx(
                cover_letter_text=cover_text,
                candidate_name=request.candidate_name,
                company_name=offer.company,
                output_path=cl_path,
            )
            generated_files.append(cl_path)
            logger.info("Cover letter générée : %s", cl_path)
        except Exception:
            logger.exception("Erreur génération cover letter pour %s", offer.company)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur génération document pour {offer.company}",
            )

        # -- Étape 5 : remplir le template CV si disponible --
        cv_path_str: str | None = None
        cv_template = OUTPUT_DIR / "cv_template.docx"
        if cv_template.exists():
            cv_filename = f"cv_{safe_company}_{timestamp}_{i}.docx"
            cv_out = OUTPUT_DIR / cv_filename
            try:
                fill_template(
                    template_path=cv_template,
                    placeholders={
                        "NOM": request.candidate_name,
                        "POSTE": offer.title,
                        "ENTREPRISE": offer.company,
                    },
                    output_path=cv_out,
                )
                cv_path_str = str(cv_out)
                generated_files.append(cv_out)
                logger.info("CV généré : %s", cv_out)
            except Exception:
                logger.exception("Erreur remplissage CV pour %s", offer.company)

        results.append(
            ProcessedOffer(
                title=offer.title,
                company=offer.company,
                relevance_score=score,
                cover_letter_path=str(cl_path),
                cv_path=cv_path_str,
            ),
        )

    # -- Étape 6 : envoyer le rapport par email --
    if os.getenv("RESEND_API_KEY"):
        offers_summary = [
            {"title": r.title, "company": r.company, "score": str(r.relevance_score)}
            for r in results
        ]
        try:
            notify_candidate(
                email=request.candidate_email,
                offers_summary=offers_summary,
                generated_files=generated_files,
            )
            logger.info("Rapport envoyé à %s", request.candidate_email)
        except Exception:
            logger.warning("Erreur envoi email", exc_info=True)

    logger.info("Pipeline terminé : %d offres traitées", len(results))

    return JobSearchResponse(
        status="completed",
        processed_at=datetime.now().isoformat(),
        offers_count=len(results),
        results=results,
    )
