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

    url = f"{ADZUNA_BASE_URL}/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": job_title,
        "where": location,
        "results_per_page": max_results,
        "content-type": "application/json",
    }

    logger.info("Recherche Adzuna : %s à %s (pays=%s)", job_title, location, country)

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
