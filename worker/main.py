"""Point d'entrée FastAPI pour l'Agent RH.

Expose une route POST /trigger-job-search déclenchée par le Cron Vercel
pour lancer le pipeline de recherche d'emploi automatisée.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from document_builder import fill_template, generate_cover_letter_docx
from scraper import JobOffer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_rh")

app = FastAPI(title="Agent RH Worker", version="0.1.0")

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

MOCK_COVER_LETTER = """\
Madame, Monsieur,

Votre offre de {job_title} chez {company} a immédiatement retenu mon attention. \
Fort de plusieurs années d'expérience en développement logiciel, je suis convaincu \
que mon profil correspond aux attentes de votre équipe.

Au cours de ma carrière, j'ai eu l'opportunité de travailler sur des projets \
ambitieux mêlant développement backend (Python, FastAPI), frontend (React, \
TypeScript) et infrastructure cloud (AWS, Docker). J'ai notamment contribué à la \
mise en place de pipelines CI/CD robustes et à l'amélioration des pratiques DevOps \
au sein de mes équipes.

Ce qui me motive particulièrement dans cette opportunité, c'est la possibilité \
de contribuer à un projet à fort impact tout en évoluant dans un environnement \
technique stimulant. Je serais ravi d'échanger avec vous sur la valeur que je \
pourrais apporter à {company}.

Dans l'attente de votre retour, je vous prie d'agréer, Madame, Monsieur, \
l'expression de mes salutations distinguées.\
"""


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

    Étapes orchestrées (mode mock pour le moment) :
    1. Récupérer les offres (mockées).
    2. Pour chaque offre : générer la cover letter en .docx.
    3. Si un template CV est disponible, le remplir via fill_template.
    4. Retourner le récapitulatif.
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

    results: list[ProcessedOffer] = []

    for i, offer in enumerate(offers):
        # -- Étape 2 : score de pertinence simulé --
        mock_score = round(0.9 - i * 0.15, 2)

        # -- Étape 3 : générer la cover letter --
        cover_text = MOCK_COVER_LETTER.format(
            job_title=offer.title,
            company=offer.company,
        )

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
            logger.info("Cover letter générée : %s", cl_path)
        except Exception:
            logger.exception("Erreur génération cover letter pour %s", offer.company)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur génération document pour {offer.company}",
            )

        # -- Étape 4 : remplir le template CV si disponible --
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
                logger.info("CV généré : %s", cv_out)
            except Exception:
                logger.exception("Erreur remplissage CV pour %s", offer.company)

        results.append(
            ProcessedOffer(
                title=offer.title,
                company=offer.company,
                relevance_score=mock_score,
                cover_letter_path=str(cl_path),
                cv_path=cv_path_str,
            ),
        )

    logger.info("Pipeline terminé : %d offres traitées", len(results))

    return JobSearchResponse(
        status="completed",
        processed_at=datetime.now().isoformat(),
        offers_count=len(results),
        results=results,
    )
