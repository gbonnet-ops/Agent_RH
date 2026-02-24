"""Point d'entrée FastAPI pour l'Agent RH.

Expose deux routes principales :
  POST /search-offers     → recherche d'offres (rapide, sans LLM)
  POST /generate-documents → génère cover letters pour les offres sélectionnées
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
from job_search_api import search_offers_adzuna, is_excluded_offer
from scraper import JobOffer, search_offers

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_rh")

app = FastAPI(title="Agent RH Worker", version="0.2.0")


@app.on_event("startup")
async def startup_event() -> None:
    """Log au démarrage pour confirmer que le service est opérationnel."""
    logger.info("Agent RH Worker démarré sur le port %s", os.getenv("PORT", "10000"))


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


# Middleware pour logger les requêtes entrantes
@app.middleware("http")
async def log_requests(request, call_next):
    """Log toute requête entrante pour débugger."""
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"← {response.status_code} {request.url.path}")
    return response

# ---------------------------------------------------------------------------
# Dossier de sortie pour les documents générés
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(tempfile.gettempdir()) / "agent_rh_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

# --- Phase 1 : Recherche ---

class SearchRequest(BaseModel):
    """Paramètres pour la recherche d'offres."""
    job_title: str = "Développeur Full-Stack Senior"
    location: str = "Paris"
    max_results: int = 30
    dismissed_urls: list[str] = []  # URLs déjà refusées par l'utilisateur


class RawOffer(BaseModel):
    """Offre brute retournée par la recherche (avant traitement LLM)."""
    title: str
    company: str
    url: str = ""
    description: str = ""


class SearchResponse(BaseModel):
    """Réponse de la recherche d'offres."""
    status: str
    offers: list[RawOffer]
    country_detected: str = "fr"


# --- Phase 2 : Génération ---

class GenerateRequest(BaseModel):
    """Paramètres pour la génération de cover letters."""
    candidate_name: str = "Jean Dupont"
    candidate_email: str = "jean.dupont@example.com"
    job_title: str = "Développeur Full-Stack Senior"
    skills: list[str] = []
    linkedin_url: str = ""
    cv_text: str = ""
    personal_note: str = ""
    years_experience: int = 0
    selected_offers: list[RawOffer]
    min_score: float = 0.0


class ProcessedOffer(BaseModel):
    """Résumé d'une offre traitée par le pipeline."""
    title: str
    company: str
    url: str = ""
    relevance_score: float
    cover_letter_path: str
    cv_path: str | None = None


class GenerateResponse(BaseModel):
    """Réponse de la génération de documents."""
    status: str
    processed_at: str
    offers_count: int
    results: list[ProcessedOffer]


# --- Legacy (backward compat) ---

class JobSearchRequest(BaseModel):
    """Paramètres optionnels pour déclencher la recherche (legacy)."""
    job_title: str = "Développeur Full-Stack Senior"
    location: str = "Paris"
    candidate_name: str = "Jean Dupont"
    candidate_email: str = "jean.dupont@example.com"
    skills: list[str] = []
    years_experience: int = 0
    linkedin_url: str = ""
    cv_text: str = ""
    personal_note: str = ""


class JobSearchResponse(BaseModel):
    """Réponse du pipeline de recherche (legacy)."""
    status: str
    processed_at: str
    offers_count: int
    results: list[ProcessedOffer]


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
@app.get("/")
async def root() -> dict[str, str]:
    """Route racine — utilisée par Render comme health-check par défaut."""
    return {"status": "ok", "service": "agent-rh-worker"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health-check basique pour le monitoring."""
    return {"status": "ok", "service": "agent-rh-worker"}


# ---------------------------------------------------------------------------
# Phase 1 : Recherche d'offres (rapide, sans LLM)
# ---------------------------------------------------------------------------
@app.post("/search-offers", response_model=SearchResponse)
async def search_offers_endpoint(request: SearchRequest) -> SearchResponse:
    """Recherche des offres d'emploi.

    Retourne les offres brutes filtrées (sans stages/alternances,
    sans les offres déjà refusées par l'utilisateur).
    """
    logger.info(
        "Recherche pour '%s' à '%s' (max=%d)",
        request.job_title,
        request.location,
        request.max_results,
    )

    offers: list[JobOffer] = []
    from job_search_api import detect_country
    country = detect_country(request.location)

    # Tentative 1 : API Adzuna
    try:
        offers = await search_offers_adzuna(
            request.job_title,
            request.location,
            max_results=request.max_results,
            country=country,
        )
        if offers:
            logger.info("%d offres trouvées via Adzuna API", len(offers))
    except Exception:
        logger.warning("Adzuna API échouée, fallback vers WttJ", exc_info=True)

    # Tentative 2 : scraping WttJ si Adzuna n'a rien trouvé
    if not offers:
        try:
            offers = await search_offers(
                request.job_title,
                request.location,
                max_results=request.max_results,
            )
            logger.info("%d offres trouvées via scraping WttJ", len(offers))
        except Exception:
            logger.exception("Scraping WttJ échoué également")

    if not offers:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucune offre trouvée pour '{request.job_title}' à '{request.location}'. "
                "Vérifiez que ADZUNA_APP_ID/ADZUNA_APP_KEY sont configurés, "
                "ou essayez avec des termes différents."
            ),
        )

    # Filtrer les offres déjà refusées
    dismissed = set(request.dismissed_urls)
    raw_offers = [
        RawOffer(
            title=o.title,
            company=o.company,
            url=o.url,
            description=o.description[:500],  # Résumé court pour le frontend
        )
        for o in offers
        if o.url not in dismissed and not is_excluded_offer(o.title)
    ]

    logger.info("%d offres retournées après filtrage", len(raw_offers))

    return SearchResponse(
        status="ok",
        offers=raw_offers,
        country_detected=country,
    )


# ---------------------------------------------------------------------------
# Phase 2 : Génération de documents pour les offres sélectionnées
# ---------------------------------------------------------------------------
@app.post("/generate-documents", response_model=GenerateResponse)
async def generate_documents(request: GenerateRequest) -> GenerateResponse:
    """Génère les cover letters et CV pour les offres sélectionnées.

    Étapes :
    1. Charger le profil candidat.
    2. Pour chaque offre sélectionnée : analyser avec LLM + générer la cover letter.
    3. Envoyer le rapport par email.
    4. Retourner le récapitulatif.
    """
    if not request.selected_offers:
        raise HTTPException(
            status_code=400,
            detail="Aucune offre sélectionnée.",
        )

    logger.info(
        "Génération pour %d offres sélectionnées (candidat: %s)",
        len(request.selected_offers),
        request.candidate_name,
    )

    # Charger le profil candidat
    achievements = _load_achievements_from_drive()
    skills = request.skills if request.skills else [
        s.strip() for s in request.job_title.split(",")
    ]
    candidate = CandidateProfile(
        job_title=request.job_title,
        skills=skills,
        linkedin_url=request.linkedin_url,
        achievements=achievements or "Profil professionnel expérimenté",
        cv_text=request.cv_text,
        years_experience=request.years_experience,
        personal_note=request.personal_note,
    )

    results: list[ProcessedOffer] = []
    generated_files: list[Path] = []

    for i, offer_data in enumerate(request.selected_offers):
        # Convertir RawOffer → JobOffer pour le LLM
        offer = JobOffer(
            title=offer_data.title,
            company=offer_data.company,
            url=offer_data.url,
            description=offer_data.description,
            funnel_questions=[],
        )

        # Analyse LLM
        llm_output = None
        use_llm = bool(os.getenv("OPENAI_API_KEY"))

        if use_llm:
            try:
                llm_output = await process_offer(candidate, offer)
            except Exception:
                logger.warning(
                    "Erreur LLM pour %s, fallback mock",
                    offer.company,
                    exc_info=True,
                )

        if llm_output:
            score = llm_output.relevance_score
            cover_text = llm_output.cover_letter
        else:
            # Fallback mock
            score = round(0.9 - i * 0.05, 2)
            cover_text = (
                f"Madame, Monsieur,\n\n"
                f"Votre offre de {offer.title} chez {offer.company} a retenu "
                f"mon attention. Fort de mon expérience, je suis convaincu que "
                f"mon profil correspond à vos attentes.\n\n"
                f"Cordialement"
            )

        # Vérifier le score minimum
        if score < request.min_score:
            logger.info(
                "Offre '%s' @ %s — score %.2f < seuil %.2f, ignorée",
                offer.title, offer.company, score, request.min_score,
            )
            continue

        # Générer la cover letter en .docx
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

        # Remplir le template CV si disponible
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
                url=offer.url,
                relevance_score=score,
                cover_letter_path=str(cl_path),
                cv_path=cv_path_str,
            ),
        )

    # Envoyer le rapport par email
    if os.getenv("RESEND_API_KEY") and results:
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

    logger.info("Génération terminée : %d offres traitées", len(results))

    return GenerateResponse(
        status="completed",
        processed_at=datetime.now().isoformat(),
        offers_count=len(results),
        results=results,
    )


# ---------------------------------------------------------------------------
# Legacy : pipeline complet en un seul appel (backward compat)
# ---------------------------------------------------------------------------
@app.post("/trigger-job-search", response_model=JobSearchResponse)
async def trigger_job_search(
    request: JobSearchRequest | None = None,
) -> JobSearchResponse:
    """Pipeline complet de recherche d'emploi (legacy, conservé pour compatibilité)."""
    if request is None:
        request = JobSearchRequest()

    # Phase 1 : recherche
    search_req = SearchRequest(
        job_title=request.job_title,
        location=request.location,
        max_results=30,
    )
    search_result = await search_offers_endpoint(search_req)

    # Phase 2 : génération pour toutes les offres trouvées
    gen_req = GenerateRequest(
        candidate_name=request.candidate_name,
        candidate_email=request.candidate_email,
        job_title=request.job_title,
        skills=request.skills,
        linkedin_url=request.linkedin_url,
        cv_text=request.cv_text,
        cover_letter_example=request.cover_letter_example,
        selected_offers=search_result.offers,
    )
    gen_result = await generate_documents(gen_req)

    return JobSearchResponse(
        status=gen_result.status,
        processed_at=gen_result.processed_at,
        offers_count=gen_result.offers_count,
        results=gen_result.results,
    )
