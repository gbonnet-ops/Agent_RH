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


async def search_offers_adzuna(
    job_title: str,
    location: str = "Paris",
    max_results: int = 10,
    country: str = "fr",
) -> list[JobOffer]:
    """Recherche d'offres via l'API Adzuna.

    Args:
        job_title: Intitulé du poste.
        location: Ville ou région.
        max_results: Nombre max de résultats.
        country: Code pays ISO (fr, gb, us, de...).

    Returns:
        Liste de JobOffer.
    """
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")

    if not app_id or not app_key:
        logger.warning(
            "ADZUNA_APP_ID / ADZUNA_APP_KEY non configurés – recherche Adzuna désactivée"
        )
        return []

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

    return offers
