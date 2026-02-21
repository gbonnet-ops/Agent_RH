"""Module de scraping pour Welcome to the Jungle.

Utilise Playwright pour naviguer sur le site et BeautifulSoup
pour parser le HTML et extraire les informations des offres d'emploi.
"""

from dataclasses import dataclass


@dataclass
class JobOffer:
    """Représente une offre d'emploi scrapée."""

    title: str
    company: str
    url: str
    description: str
    funnel_questions: list[str]


async def search_offers(job_title: str, location: str = "Paris") -> list[JobOffer]:
    """Recherche des offres sur Welcome to the Jungle.

    Args:
        job_title: Intitulé du poste à rechercher.
        location: Localisation souhaitée (défaut : Paris).

    Returns:
        Liste d'offres d'emploi correspondantes.
    """
    ...


async def scrape_offer_details(offer_url: str) -> JobOffer:
    """Scrape les détails complets d'une offre individuelle.

    Récupère la description longue et les éventuelles questions
    du funnel de candidature.

    Args:
        offer_url: URL complète de l'offre sur WttJ.

    Returns:
        Objet JobOffer rempli avec tous les détails.
    """
    ...
