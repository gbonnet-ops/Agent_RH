"""Recherche d'offres via l'API Adzuna (gratuite, sans scraping).

Adzuna agrège les offres de multiples job boards (Indeed, LinkedIn, etc.).
Inscription gratuite : https://developer.adzuna.com/
Variables d'environnement nécessaires :
  ADZUNA_APP_ID   – identifiant d'application
  ADZUNA_APP_KEY  – clé d'API
"""

import logging
import os

import httpx

from scraper import JobOffer

logger = logging.getLogger("agent_rh.job_search_api")

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# ---------------------------------------------------------------------------
# Détection automatique du pays à partir de la localisation
# ---------------------------------------------------------------------------
CITY_TO_COUNTRY: dict[str, str] = {
    # France
    "paris": "fr", "lyon": "fr", "marseille": "fr", "toulouse": "fr",
    "nice": "fr", "nantes": "fr", "strasbourg": "fr", "montpellier": "fr",
    "bordeaux": "fr", "lille": "fr", "rennes": "fr", "grenoble": "fr",
    "rouen": "fr", "toulon": "fr", "clermont-ferrand": "fr", "aix-en-provence": "fr",
    "la defense": "fr", "la défense": "fr", "saint-denis": "fr",
    # UK
    "london": "gb", "londres": "gb", "manchester": "gb", "birmingham": "gb",
    "leeds": "gb", "glasgow": "gb", "liverpool": "gb", "edinburgh": "gb",
    "edimbourg": "gb", "bristol": "gb", "cambridge": "gb", "oxford": "gb",
    # Germany
    "berlin": "de", "munich": "de", "münchen": "de", "frankfurt": "de",
    "francfort": "de", "hamburg": "de", "hambourg": "de", "cologne": "de",
    "köln": "de", "düsseldorf": "de", "stuttgart": "de",
    # Netherlands
    "amsterdam": "nl", "rotterdam": "nl", "la haye": "nl", "the hague": "nl",
    "utrecht": "nl", "eindhoven": "nl",
    # Belgium
    "bruxelles": "be", "brussels": "be", "anvers": "be", "antwerp": "be",
    "gand": "be", "ghent": "be", "liège": "be",
    # Spain
    "madrid": "es", "barcelona": "es", "barcelone": "es", "valencia": "es",
    "valence": "es", "seville": "es", "séville": "es",
    # Italy
    "rome": "it", "roma": "it", "milan": "it", "milano": "it",
    "turin": "it", "torino": "it", "florence": "it", "firenze": "it",
    # Switzerland
    "zurich": "ch", "zürich": "ch", "genève": "ch", "geneva": "ch",
    "berne": "ch", "bern": "ch", "lausanne": "ch", "bâle": "ch", "basel": "ch",
    # Luxembourg
    "luxembourg": "lu",
    # USA
    "new york": "us", "san francisco": "us", "los angeles": "us",
    "chicago": "us", "boston": "us", "seattle": "us", "austin": "us",
    "washington": "us", "miami": "us", "denver": "us", "atlanta": "us",
    # Canada
    "toronto": "ca", "montreal": "ca", "montréal": "ca", "vancouver": "ca",
    "ottawa": "ca",
    # Australia
    "sydney": "au", "melbourne": "au", "brisbane": "au", "perth": "au",
    # Singapore
    "singapore": "sg", "singapour": "sg",
    # Poland
    "warsaw": "pl", "varsovie": "pl", "cracow": "pl", "cracovie": "pl",
    # Austria
    "vienna": "at", "vienne": "at",
    # India
    "mumbai": "in", "bangalore": "in", "delhi": "in", "new delhi": "in",
    # Brazil
    "são paulo": "br", "sao paulo": "br", "rio de janeiro": "br",
    # South Africa
    "johannesburg": "za", "cape town": "za",
    # New Zealand
    "auckland": "nz", "wellington": "nz",
}


def detect_country(location: str) -> str:
    """Détecte le code pays ISO à partir du nom de la ville/localisation.

    Cherche d'abord une correspondance exacte, puis partielle.
    Retourne 'fr' par défaut si aucune correspondance n'est trouvée.
    """
    loc_lower = location.lower().strip()

    # Correspondance exacte
    if loc_lower in CITY_TO_COUNTRY:
        return CITY_TO_COUNTRY[loc_lower]

    # Correspondance partielle (ex: "London, UK" → "london")
    for city, country in CITY_TO_COUNTRY.items():
        if city in loc_lower or loc_lower in city:
            return country

    return "fr"


# ---------------------------------------------------------------------------
# Filtrage des offres indésirables (stages, alternances)
# ---------------------------------------------------------------------------
EXCLUDED_TITLE_KEYWORDS = [
    "intern", "internship", "stagiaire", "stage",
    "alternance", "alternant", "apprenti", "apprentissage",
    "werkstudent", "praktikum",
]


def is_excluded_offer(title: str) -> bool:
    """Vérifie si une offre correspond à un stage/alternance/internship."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in EXCLUDED_TITLE_KEYWORDS)


# ---------------------------------------------------------------------------
# Élargissement de la requête de recherche
# ---------------------------------------------------------------------------

# Synonymes de niveaux hiérarchiques (bidirectionnels)
TITLE_SYNONYMS: list[set[str]] = [
    {"head of", "vp", "vice president", "director", "directeur", "directrice"},
    {"cfo", "chief financial officer", "head of finance", "vp finance", "directeur financier"},
    {"cto", "chief technology officer", "head of engineering", "vp engineering", "directeur technique"},
    {"coo", "chief operating officer", "head of operations", "vp operations", "directeur des opérations"},
    {"cmo", "chief marketing officer", "head of marketing", "vp marketing", "directeur marketing"},
    {"ceo", "chief executive officer", "managing director", "directeur général", "general manager"},
    {"manager", "responsable", "lead", "team lead", "chef de"},
    {"senior", "sr", "sr.", "principal", "staff"},
    {"développeur", "developer", "engineer", "ingénieur", "dev"},
    {"analyste", "analyst", "data analyst", "business analyst"},
    {"consultant", "conseiller", "advisor"},
    {"commercial", "sales", "business development", "account executive", "chargé d'affaires"},
    {"product manager", "chef de produit", "product owner", "po"},
    {"project manager", "chef de projet", "program manager"},
    {"full-stack", "fullstack", "full stack"},
    {"front-end", "frontend", "front end"},
    {"back-end", "backend", "back end"},
]

# Mots non significatifs à ignorer lors de l'extraction des mots-clés
STOP_WORDS = {
    "de", "du", "des", "le", "la", "les", "un", "une", "et", "en", "au",
    "aux", "à", "of", "the", "a", "an", "and", "in", "at", "for", "with",
    "on", "is", "are", "to", "from", "by",
}


def expand_job_title(job_title: str) -> str:
    """Élargit un intitulé de poste en ajoutant des variantes/synonymes.

    Ex: "Head of Finance" → "Head of Finance OR VP Finance OR Director Finance OR CFO"
    """
    title_lower = job_title.lower().strip()

    # Trouver les groupes de synonymes correspondants
    matched_synonyms: list[str] = []
    for group in TITLE_SYNONYMS:
        for synonym in group:
            if synonym in title_lower:
                # Ajouter les autres synonymes du groupe
                for alt in group:
                    if alt != synonym and alt not in title_lower:
                        matched_synonyms.append(alt)
                break

    if not matched_synonyms:
        return job_title

    # Extraire les mots-clés métier (pas les niveaux hiérarchiques)
    # Ex: "Head of Finance" → "Finance"
    all_level_words: set[str] = set()
    for group in TITLE_SYNONYMS:
        for synonym in group:
            all_level_words.update(synonym.lower().split())

    domain_words = [
        w for w in job_title.split()
        if w.lower() not in STOP_WORDS and w.lower() not in all_level_words
    ]
    domain = " ".join(domain_words) if domain_words else ""

    # Construire la requête élargie
    variants = [job_title]
    for syn in matched_synonyms[:4]:  # Limiter à 4 variantes
        if domain:
            variants.append(f"{syn} {domain}")
        else:
            variants.append(syn)

    expanded = " OR ".join(variants)
    logger.info("Requête élargie : '%s' → '%s'", job_title, expanded)
    return expanded


async def search_offers_adzuna(
    job_title: str,
    location: str = "Paris",
    max_results: int = 30,
    country: str | None = None,
) -> list[JobOffer]:
    """Recherche d'offres via l'API Adzuna.

    Args:
        job_title: Intitulé du poste.
        location: Ville ou région.
        max_results: Nombre max de résultats.
        country: Code pays ISO (fr, gb, us, de...). Auto-détecté si None.

    Returns:
        Liste de JobOffer (filtrée, sans stages/alternances).
    """
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")

    if not app_id or not app_key:
        logger.warning(
            "ADZUNA_APP_ID / ADZUNA_APP_KEY non configurés – recherche Adzuna désactivée"
        )
        return []

    # Auto-détection du pays si non spécifié
    if country is None:
        country = detect_country(location)

    # Élargir la requête pour capturer des variantes du titre
    expanded_title = expand_job_title(job_title)

    url = f"{ADZUNA_BASE_URL}/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": expanded_title,
        "where": location,
        "results_per_page": max_results,
        "content-type": "application/json",
    }

    logger.info("Recherche Adzuna : '%s' (élargi: '%s') à %s (pays=%s)",
                job_title, expanded_title, location, country)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    logger.info("Adzuna : %d résultats bruts", len(results))

    offers: list[JobOffer] = []
    for item in results:
        title = item.get("title", "Poste non spécifié")

        # Filtrer les stages/alternances
        if is_excluded_offer(title):
            logger.debug("Offre filtrée (stage/alternance) : %s", title)
            continue

        company = item.get("company", {}).get("display_name", "Entreprise")
        offer_url = item.get("redirect_url", "")
        description = item.get("description", "")

        offers.append(
            JobOffer(
                title=title,
                company=company,
                url=offer_url,
                description=description[:3000],
                funnel_questions=[],
            )
        )

    logger.info("Adzuna : %d offres après filtrage", len(offers))
    return offers
