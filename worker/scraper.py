"""Module de scraping pour Welcome to the Jungle.

Utilise Playwright pour naviguer sur le site et BeautifulSoup
pour parser le HTML et extraire les informations des offres d'emploi.
"""

import logging
import urllib.parse
from dataclasses import dataclass

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

logger = logging.getLogger("agent_rh.scraper")


@dataclass
class JobOffer:
    """Représente une offre d'emploi scrapée."""

    title: str
    company: str
    url: str
    description: str
    funnel_questions: list[str]


def _company_from_url(url: str) -> str:
    """Extrait le nom de l'entreprise depuis l'URL WttJ."""
    try:
        slug = url.split("/companies/")[1].split("/")[0]
        return slug.replace("-", " ").title()
    except (IndexError, AttributeError):
        return ""


def _parse_search_results(soup: BeautifulSoup, max_results: int) -> list[JobOffer]:
    """Extrait les offres depuis le HTML de la page de résultats WttJ."""
    offers: list[JobOffer] = []
    seen_urls: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]

        # Les URLs d'offres WttJ suivent le pattern /fr/companies/{slug}/jobs/{slug}
        if "/companies/" not in href or "/jobs/" not in href:
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)

        full_url = (
            f"https://www.welcometothejungle.com{href}"
            if href.startswith("/")
            else href
        )

        # Extraire le texte de la carte
        card_text = a_tag.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in card_text.split("\n") if line.strip()]

        title = lines[0] if lines else "Poste non spécifié"
        company = lines[1] if len(lines) > 1 else _company_from_url(full_url)

        offers.append(
            JobOffer(
                title=title,
                company=company,
                url=full_url,
                description="",
                funnel_questions=[],
            )
        )

        if len(offers) >= max_results:
            break

    return offers


def _parse_offer_details(soup: BeautifulSoup) -> tuple[str, list[str]]:
    """Extrait la description et les questions depuis la page d'une offre."""
    description_parts: list[str] = []

    main_content = soup.find("main") or soup.find("article") or soup

    for el in main_content.find_all(["p", "li", "h3", "h4"]):
        text = el.get_text(strip=True)
        if text and len(text) > 10:
            description_parts.append(text)

    description = "\n".join(description_parts[:30])
    if len(description) > 3000:
        description = description[:3000] + "..."

    funnel_questions: list[str] = []

    return description, funnel_questions


async def search_offers(
    job_title: str,
    location: str = "Paris",
    max_results: int = 10,
) -> list[JobOffer]:
    """Recherche des offres sur Welcome to the Jungle.

    Args:
        job_title: Intitulé du poste à rechercher.
        location: Localisation souhaitée (défaut : Paris).
        max_results: Nombre maximum d'offres à retourner.

    Returns:
        Liste d'offres d'emploi correspondantes.
    """
    query = urllib.parse.quote_plus(job_title)
    loc = urllib.parse.quote_plus(location)
    search_url = (
        f"https://www.welcometothejungle.com/fr/jobs"
        f"?query={query}&aroundQuery={loc}"
    )

    logger.info("Recherche WttJ : %s", search_url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({"Accept-Language": "fr-FR,fr;q=0.9"})

            # Page de résultats
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            search_html = await page.content()
            soup = BeautifulSoup(search_html, "html.parser")
            offers = _parse_search_results(soup, max_results)

            logger.info("%d offres trouvées dans les résultats", len(offers))

            # Scraper les détails de chaque offre (même browser)
            for offer in offers:
                try:
                    await page.goto(
                        offer.url, wait_until="networkidle", timeout=30000
                    )
                    await page.wait_for_timeout(2000)
                    detail_html = await page.content()
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    offer.description, offer.funnel_questions = _parse_offer_details(
                        detail_soup
                    )
                except Exception:
                    logger.warning(
                        "Impossible de scraper les détails : %s",
                        offer.url,
                        exc_info=True,
                    )
        finally:
            await browser.close()

    return offers


async def scrape_offer_details(offer_url: str) -> JobOffer:
    """Scrape les détails complets d'une offre individuelle.

    Récupère la description longue et les éventuelles questions
    du funnel de candidature.

    Args:
        offer_url: URL complète de l'offre sur WttJ.

    Returns:
        Objet JobOffer rempli avec tous les détails.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(offer_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            html = await page.content()
        finally:
            await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h2") or soup.find("h1")
    title = title_el.get_text(strip=True) if title_el else "Poste"

    company = _company_from_url(offer_url)
    description, funnel_questions = _parse_offer_details(soup)

    return JobOffer(
        title=title,
        company=company,
        url=offer_url,
        description=description,
        funnel_questions=funnel_questions,
    )
