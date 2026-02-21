"""Point d'entrée FastAPI pour l'Agent RH.

Expose une route POST /trigger-job-search déclenchée par le Cron Vercel
pour lancer le pipeline de recherche d'emploi automatisée.
"""

from fastapi import FastAPI

app = FastAPI(title="Agent RH Worker", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health-check basique pour le monitoring."""
    ...


@app.post("/trigger-job-search")
async def trigger_job_search() -> dict[str, str]:
    """Déclenche le pipeline complet de recherche d'emploi.

    Étapes orchestrées :
    1. Récupérer le profil candidat (depuis l'API frontend ou le store).
    2. Scraper les offres correspondantes sur Welcome to the Jungle.
    3. Pour chaque offre pertinente :
       a. Lire le template CV et les achievements depuis Google Drive.
       b. Appeler le LLM pour analyser l'offre, rédiger la cover letter
          et répondre aux questions du funnel.
       c. Générer le document Word personnalisé.
       d. Envoyer le package par email.
    """
    ...
