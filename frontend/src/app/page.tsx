"use client";

import { useState, type FormEvent } from "react";

interface CandidateProfile {
  jobTitle: string;
  skills: string;
  linkedinUrl: string;
  candidateName: string;
  candidateEmail: string;
  location: string;
  cvText: string;
  coverLetterExample: string;
}

interface ProcessedOffer {
  title: string;
  company: string;
  url: string;
  relevance_score: number;
  cover_letter_path: string;
  cv_path: string | null;
}

interface JobSearchResponse {
  status: string;
  processed_at: string;
  offers_count: number;
  results: ProcessedOffer[];
}

export default function Home() {
  const [profile, setProfile] = useState<CandidateProfile>({
    jobTitle: "",
    skills: "",
    linkedinUrl: "",
    candidateName: "",
    candidateEmail: "",
    location: "Paris",
    cvText: "",
    coverLetterExample: "",
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<JobSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const res = await fetch("/api/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_title: profile.jobTitle,
          location: profile.location,
          candidate_name: profile.candidateName,
          candidate_email: profile.candidateEmail,
          skills: profile.skills.split(",").map((s: string) => s.trim()).filter(Boolean),
          linkedin_url: profile.linkedinUrl,
          cv_text: profile.cvText,
          cover_letter_example: profile.coverLetterExample,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Erreur serveur");
      }

      const data: JobSearchResponse = await res.json();
      setResults(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950">
      <main className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-sm dark:bg-zinc-900">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Agent RH
        </h1>
        <p className="mb-8 text-sm text-zinc-500 dark:text-zinc-400">
          Configurez votre profil candidat pour la recherche automatisée.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="grid grid-cols-2 gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Nom complet
              </span>
              <input
                type="text"
                required
                placeholder="Jean Dupont"
                value={profile.candidateName}
                onChange={(e) =>
                  setProfile({ ...profile, candidateName: e.target.value })
                }
                className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Email
              </span>
              <input
                type="email"
                required
                placeholder="jean@exemple.com"
                value={profile.candidateEmail}
                onChange={(e) =>
                  setProfile({ ...profile, candidateEmail: e.target.value })
                }
                className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Poste recherché
              </span>
              <input
                type="text"
                required
                placeholder="Développeur Full-Stack"
                value={profile.jobTitle}
                onChange={(e) =>
                  setProfile({ ...profile, jobTitle: e.target.value })
                }
                className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Localisation
              </span>
              <input
                type="text"
                required
                placeholder="Paris"
                value={profile.location}
                onChange={(e) =>
                  setProfile({ ...profile, location: e.target.value })
                }
                className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Compétences clés
            </span>
            <textarea
              required
              rows={3}
              placeholder="ex: Python, React, AWS, Machine Learning..."
              value={profile.skills}
              onChange={(e) =>
                setProfile({ ...profile, skills: e.target.value })
              }
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              URL LinkedIn
            </span>
            <input
              type="url"
              required
              placeholder="https://linkedin.com/in/votre-profil"
              value={profile.linkedinUrl}
              onChange={(e) =>
                setProfile({ ...profile, linkedinUrl: e.target.value })
              }
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Votre CV (copier-coller le texte)
            </span>
            <textarea
              rows={6}
              placeholder="Collez ici le contenu de votre CV : expériences, formations, réalisations..."
              value={profile.cvText}
              onChange={(e) =>
                setProfile({ ...profile, cvText: e.target.value })
              }
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Exemple de lettre de motivation (pour le style)
            </span>
            <textarea
              rows={6}
              placeholder="Collez ici un exemple de cover letter dont vous aimez le style. Le modèle reproduira ce ton."
              value={profile.coverLetterExample}
              onChange={(e) =>
                setProfile({ ...profile, coverLetterExample: e.target.value })
              }
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {loading ? "Recherche en cours..." : "Lancer la recherche"}
          </button>

          {saved && (
            <p className="text-center text-sm text-green-600 dark:text-green-400">
              Recherche terminée avec succès.
            </p>
          )}

          {error && (
            <p className="text-center text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
        </form>

        {results && (
          <div className="mt-8 border-t border-zinc-200 pt-6 dark:border-zinc-700">
            <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {results.offers_count} offre{results.offers_count > 1 ? "s" : ""} trouvée{results.offers_count > 1 ? "s" : ""}
            </h2>
            <div className="flex flex-col gap-3">
              {results.results.map((offer, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-zinc-900 dark:text-zinc-100">
                        {offer.title}
                      </p>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">
                        {offer.company}
                      </p>
                    </div>
                    <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                      {Math.round(offer.relevance_score * 100)}%
                    </span>
                  </div>
                  {offer.url && (
                    <a
                      href={offer.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-block text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Postuler &rarr;
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
