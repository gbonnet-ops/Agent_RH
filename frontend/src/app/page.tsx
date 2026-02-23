"use client";

import { useState, useEffect, useMemo, type FormEvent } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

interface RawOffer {
  title: string;
  company: string;
  url: string;
  description: string;
}

interface ProcessedOffer {
  title: string;
  company: string;
  url: string;
  relevance_score: number;
  cover_letter_path: string;
  cv_path: string | null;
}

interface SearchResponse {
  status: string;
  offers: RawOffer[];
  country_detected: string;
}

interface GenerateResponse {
  status: string;
  processed_at: string;
  offers_count: number;
  results: ProcessedOffer[];
}

// ---------------------------------------------------------------------------
// History data model
// ---------------------------------------------------------------------------

interface HistoryEntry {
  id: string; // URL or title__company
  title: string;
  company: string;
  url: string;
  status: "rejected" | "generated";
  date: string; // ISO string
  relevanceScore?: number;
  searchQuery?: string;
  location?: string;
}

type HistoryFilter = "all" | "generated" | "rejected";
type TabId = "profil" | "sources" | "resultats" | "historique";

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const HISTORY_KEY = "agent_rh_history";
const CUSTOM_URLS_KEY = "agent_rh_custom_urls";

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
}

function loadCustomUrls(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(CUSTOM_URLS_KEY) || "";
}

function saveCustomUrls(urls: string) {
  localStorage.setItem(CUSTOM_URLS_KEY, urls);
}

// ---------------------------------------------------------------------------
// Shared Tailwind class strings
// ---------------------------------------------------------------------------

const inputClass =
  "rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700";

const btnPrimary =
  "rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200";

const btnSecondary =
  "rounded-lg border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Home() {
  // --- State: Profile ---
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

  // --- State: Sources ---
  const [customUrls, setCustomUrls] = useState<string>("");

  // --- State: Tabs ---
  const [activeTab, setActiveTab] = useState<TabId>("profil");

  // --- State: Search ---
  const [searching, setSearching] = useState(false);
  const [offers, setOffers] = useState<RawOffer[]>([]);
  const [countryDetected, setCountryDetected] = useState("fr");

  // --- State: Selection ---
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  // --- State: Generation ---
  const [generating, setGenerating] = useState(false);
  const [generatedResults, setGeneratedResults] = useState<ProcessedOffer[]>(
    []
  );

  // --- State: Feedback ---
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // --- State: Minimum score filter ---
  const [minScore, setMinScore] = useState(0.4);

  // --- State: History ---
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyFilter, setHistoryFilter] = useState<HistoryFilter>("all");

  // Load persisted data on mount
  useEffect(() => {
    setHistory(loadHistory());
    setCustomUrls(loadCustomUrls());
  }, []);

  // Persist custom URLs when changed
  useEffect(() => {
    if (typeof window !== "undefined") {
      saveCustomUrls(customUrls);
    }
  }, [customUrls]);

  // Derive excluded URLs from history (both rejected + generated)
  const excludedUrls = useMemo(
    () => new Set(history.map((h) => h.id)),
    [history]
  );

  // Key for offer selection
  function offerKey(offer: RawOffer): string {
    return offer.url || `${offer.title}__${offer.company}`;
  }

  // -----------------------------------------------------------------------
  // History helpers
  // -----------------------------------------------------------------------
  function addToHistory(entries: HistoryEntry[]) {
    setHistory((prev) => {
      const existingIds = new Set(prev.map((h) => h.id));
      const newEntries = entries.filter((e) => !existingIds.has(e.id));
      const updated = [...newEntries, ...prev];
      saveHistory(updated);
      return updated;
    });
  }

  function clearHistory() {
    setHistory([]);
    saveHistory([]);
  }

  // -----------------------------------------------------------------------
  // Phase 1 : Search
  // -----------------------------------------------------------------------
  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    setSearching(true);
    setError(null);
    setSuccess(null);
    setOffers([]);
    setGeneratedResults([]);
    setSelected({});

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_title: profile.jobTitle,
          location: profile.location,
          max_results: 30,
          dismissed_urls: Array.from(excludedUrls),
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Erreur serveur");
      }

      const data: SearchResponse = await res.json();

      // Client-side filter: remove any offers already in history
      const freshOffers = data.offers.filter(
        (o) => !excludedUrls.has(offerKey(o))
      );

      setOffers(freshOffers);
      setCountryDetected(data.country_detected);

      // Pre-select all offers
      const sel: Record<string, boolean> = {};
      freshOffers.forEach((o) => {
        sel[offerKey(o)] = true;
      });
      setSelected(sel);

      setActiveTab("resultats");
      setSuccess(
        `${freshOffers.length} offre(s) trouvée(s) (pays: ${data.country_detected.toUpperCase()})`
      );
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setSearching(false);
    }
  }

  // -----------------------------------------------------------------------
  // Phase 2 : Generate cover letters for selected offers
  // -----------------------------------------------------------------------
  async function handleGenerate() {
    const selectedOffers = offers.filter((o) => selected[offerKey(o)]);
    if (selectedOffers.length === 0) {
      setError("Sélectionnez au moins une offre.");
      return;
    }

    // Record dismissed (deselected) offers in history
    const dismissedOffers = offers.filter((o) => !selected[offerKey(o)]);
    if (dismissedOffers.length > 0) {
      const now = new Date().toISOString();
      addToHistory(
        dismissedOffers.map((o) => ({
          id: offerKey(o),
          title: o.title,
          company: o.company,
          url: o.url,
          status: "rejected" as const,
          date: now,
          searchQuery: profile.jobTitle,
          location: profile.location,
        }))
      );
    }

    setGenerating(true);
    setError(null);
    setSuccess(null);
    setGeneratedResults([]);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_name: profile.candidateName,
          candidate_email: profile.candidateEmail,
          job_title: profile.jobTitle,
          skills: profile.skills
            .split(",")
            .map((s: string) => s.trim())
            .filter(Boolean),
          linkedin_url: profile.linkedinUrl,
          cv_text: profile.cvText,
          cover_letter_example: profile.coverLetterExample,
          selected_offers: selectedOffers,
          min_score: minScore,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Erreur serveur");
      }

      const data: GenerateResponse = await res.json();
      setGeneratedResults(data.results);

      // Record generated offers in history
      if (data.results.length > 0) {
        const now = new Date().toISOString();
        addToHistory(
          data.results.map((r) => ({
            id: r.url || `${r.title}__${r.company}`,
            title: r.title,
            company: r.company,
            url: r.url,
            status: "generated" as const,
            date: now,
            relevanceScore: r.relevance_score,
            searchQuery: profile.jobTitle,
            location: profile.location,
          }))
        );
      }

      setSuccess(
        `${data.offers_count} lettre(s) de motivation générée(s) !`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setGenerating(false);
    }
  }

  // -----------------------------------------------------------------------
  // Selection helpers
  // -----------------------------------------------------------------------
  function toggleOffer(offer: RawOffer) {
    const key = offerKey(offer);
    setSelected((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function selectAll() {
    const sel: Record<string, boolean> = {};
    offers.forEach((o) => {
      sel[offerKey(o)] = true;
    });
    setSelected(sel);
  }

  function deselectAll() {
    setSelected({});
  }

  const selectedCount = Object.values(selected).filter(Boolean).length;

  // -----------------------------------------------------------------------
  // Filtered history
  // -----------------------------------------------------------------------
  const filteredHistory = useMemo(() => {
    if (historyFilter === "all") return history;
    return history.filter((h) => h.status === historyFilter);
  }, [history, historyFilter]);

  const generatedCount = history.filter((h) => h.status === "generated").length;
  const rejectedCount = history.filter((h) => h.status === "rejected").length;

  // -----------------------------------------------------------------------
  // Tabs
  // -----------------------------------------------------------------------
  const tabs: { id: TabId; label: string }[] = [
    { id: "profil", label: "Profil" },
    { id: "sources", label: "Sources" },
    {
      id: "resultats",
      label: `Résultats${offers.length > 0 ? ` (${offers.length})` : ""}`,
    },
    {
      id: "historique",
      label: `Historique${history.length > 0 ? ` (${history.length})` : ""}`,
    },
  ];

  return (
    <div className="flex min-h-screen items-start justify-center bg-zinc-50 py-8 dark:bg-zinc-950">
      <main className="w-full max-w-2xl rounded-2xl bg-white p-8 shadow-sm dark:bg-zinc-900">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Agent RH
        </h1>
        <p className="mb-6 text-sm text-zinc-500 dark:text-zinc-400">
          Recherche automatisée d&apos;emploi avec lettres de motivation
          personnalisées.
        </p>

        {/* Tab navigation */}
        <div className="mb-6 flex gap-1 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition ${
                activeTab === tab.id
                  ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Feedback messages */}
        {success && (
          <p className="mb-4 rounded-lg bg-green-50 p-3 text-center text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            {success}
          </p>
        )}
        {error && (
          <p className="mb-4 rounded-lg bg-red-50 p-3 text-center text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {error}
          </p>
        )}

        {/* ============================================================= */}
        {/* TAB: Profil                                                    */}
        {/* ============================================================= */}
        {activeTab === "profil" && (
          <form onSubmit={handleSearch} className="flex flex-col gap-5">
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
                  className={inputClass}
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
                    setProfile({
                      ...profile,
                      candidateEmail: e.target.value,
                    })
                  }
                  className={inputClass}
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
                  className={inputClass}
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Localisation
                </span>
                <input
                  type="text"
                  required
                  placeholder="Paris, London, Berlin..."
                  value={profile.location}
                  onChange={(e) =>
                    setProfile({ ...profile, location: e.target.value })
                  }
                  className={inputClass}
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
                className={inputClass}
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
                className={inputClass}
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
                className={inputClass}
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Exemple de lettre de motivation (pour le style)
              </span>
              <textarea
                rows={6}
                placeholder="Collez ici un exemple de cover letter dont vous aimez le style."
                value={profile.coverLetterExample}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    coverLetterExample: e.target.value,
                  })
                }
                className={inputClass}
              />
            </label>

            <button type="submit" disabled={searching} className={btnPrimary}>
              {searching ? "Recherche en cours..." : "Rechercher des offres"}
            </button>
          </form>
        )}

        {/* ============================================================= */}
        {/* TAB: Sources                                                   */}
        {/* ============================================================= */}
        {activeTab === "sources" && (
          <div className="flex flex-col gap-5">
            <div>
              <h2 className="mb-2 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                Sites ciblés
              </h2>
              <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
                Ajoutez les URLs de pages carrières d&apos;entreprises ou de
                chasseurs de tête que vous souhaitez cibler. Une URL par ligne.
              </p>
              <textarea
                rows={8}
                placeholder={
                  "https://careers.airliquide.com/\nhttps://jobs.michael-page.fr/\nhttps://www.hays.fr/\nhttps://www.robertwalters.fr/"
                }
                value={customUrls}
                onChange={(e) => setCustomUrls(e.target.value)}
                className={inputClass + " w-full"}
              />
              <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">
                Ces sites seront utilisés comme sources complémentaires lors de
                la recherche. (Fonctionnalité en cours de développement)
              </p>
            </div>
          </div>
        )}

        {/* ============================================================= */}
        {/* TAB: Résultats                                                 */}
        {/* ============================================================= */}
        {activeTab === "resultats" && (
          <div className="flex flex-col gap-5">
            {offers.length === 0 && generatedResults.length === 0 && (
              <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
                Aucune offre pour le moment. Lancez une recherche depuis
                l&apos;onglet Profil.
              </p>
            )}

            {/* Search results with checkboxes */}
            {offers.length > 0 && (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                    {offers.length} offre(s) trouvée(s)
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={selectAll}
                      className="text-xs font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
                    >
                      Tout cocher
                    </button>
                    <span className="text-zinc-300 dark:text-zinc-600">|</span>
                    <button
                      onClick={deselectAll}
                      className="text-xs font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
                    >
                      Tout décocher
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  {offers.map((offer, i) => {
                    const key = offerKey(offer);
                    const isSelected = !!selected[key];
                    return (
                      <div
                        key={i}
                        onClick={() => toggleOffer(offer)}
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition ${
                          isSelected
                            ? "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20"
                            : "border-zinc-200 bg-zinc-50 opacity-60 dark:border-zinc-700 dark:bg-zinc-800"
                        }`}
                      >
                        {/* Checkbox */}
                        <div
                          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition ${
                            isSelected
                              ? "border-blue-500 bg-blue-500 dark:border-blue-400 dark:bg-blue-400"
                              : "border-zinc-300 dark:border-zinc-600"
                          }`}
                        >
                          {isSelected && (
                            <svg
                              className="h-3 w-3 text-white"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={3}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          )}
                        </div>

                        {/* Offer info */}
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-zinc-900 dark:text-zinc-100">
                            {offer.title}
                          </p>
                          <p className="truncate text-sm text-zinc-500 dark:text-zinc-400">
                            {offer.company}
                          </p>
                        </div>

                        {/* Link */}
                        {offer.url && (
                          <a
                            href={offer.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="shrink-0 text-xs font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
                          >
                            Voir &rarr;
                          </a>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Score threshold + Generate button */}
                <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800">
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                      <span className="whitespace-nowrap">
                        Score minimum :
                      </span>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        step={5}
                        value={minScore * 100}
                        onChange={(e) =>
                          setMinScore(Number(e.target.value) / 100)
                        }
                        className="w-24"
                      />
                      <span className="w-10 text-center font-mono text-sm font-semibold">
                        {Math.round(minScore * 100)}%
                      </span>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">
                      {selectedCount} offre(s) sélectionnée(s)
                    </p>
                    <button
                      onClick={handleGenerate}
                      disabled={generating || selectedCount === 0}
                      className={btnPrimary}
                    >
                      {generating
                        ? "Génération en cours..."
                        : `Générer ${selectedCount} lettre(s)`}
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* Generated results */}
            {generatedResults.length > 0 && (
              <div className="border-t border-zinc-200 pt-4 dark:border-zinc-700">
                <h2 className="mb-3 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  Lettres générées
                </h2>
                <div className="flex flex-col gap-3">
                  {generatedResults.map((result, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-zinc-900 dark:text-zinc-100">
                            {result.title}
                          </p>
                          <p className="text-sm text-zinc-500 dark:text-zinc-400">
                            {result.company}
                          </p>
                        </div>
                        <span
                          className={`rounded-full px-3 py-1 text-sm font-medium ${
                            result.relevance_score >= 0.7
                              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                              : result.relevance_score >= 0.4
                              ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                              : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                          }`}
                        >
                          {Math.round(result.relevance_score * 100)}%
                        </span>
                      </div>
                      {result.url && (
                        <a
                          href={result.url}
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
          </div>
        )}

        {/* ============================================================= */}
        {/* TAB: Historique                                                 */}
        {/* ============================================================= */}
        {activeTab === "historique" && (
          <div className="flex flex-col gap-5">
            {/* Filter buttons */}
            <div className="flex items-center justify-between">
              <div className="flex gap-1 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
                {(
                  [
                    { id: "all", label: `Tout (${history.length})` },
                    { id: "generated", label: `Postulé (${generatedCount})` },
                    { id: "rejected", label: `Rejeté (${rejectedCount})` },
                  ] as const
                ).map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setHistoryFilter(f.id)}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                      historyFilter === f.id
                        ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-100"
                        : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {history.length > 0 && (
                <button
                  onClick={clearHistory}
                  className="text-xs font-medium text-red-500 hover:text-red-400"
                >
                  Tout effacer
                </button>
              )}
            </div>

            {/* History list */}
            {filteredHistory.length === 0 && (
              <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
                {history.length === 0
                  ? "Aucun historique. Lancez une recherche pour commencer."
                  : "Aucune offre dans cette catégorie."}
              </p>
            )}

            <div className="flex flex-col gap-2">
              {filteredHistory.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800"
                >
                  {/* Status badge */}
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                      entry.status === "generated"
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        : "bg-zinc-200 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400"
                    }`}
                  >
                    {entry.status === "generated" ? "Postulé" : "Rejeté"}
                  </span>

                  {/* Offer info */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                      {entry.title}
                    </p>
                    <p className="truncate text-xs text-zinc-500 dark:text-zinc-400">
                      {entry.company}
                      {entry.searchQuery && (
                        <span>
                          {" "}
                          &middot; Recherche : {entry.searchQuery}
                        </span>
                      )}
                    </p>
                  </div>

                  {/* Score (if generated) */}
                  {entry.relevanceScore !== undefined && (
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                        entry.relevanceScore >= 0.7
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                          : entry.relevanceScore >= 0.4
                          ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                          : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      }`}
                    >
                      {Math.round(entry.relevanceScore * 100)}%
                    </span>
                  )}

                  {/* Date */}
                  <span className="shrink-0 text-xs text-zinc-400 dark:text-zinc-500">
                    {new Date(entry.date).toLocaleDateString("fr-FR", {
                      day: "numeric",
                      month: "short",
                    })}
                  </span>

                  {/* Link */}
                  {entry.url && (
                    <a
                      href={entry.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 text-xs font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
                    >
                      Voir
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
