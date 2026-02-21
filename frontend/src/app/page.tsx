"use client";

import { useState, type FormEvent } from "react";

interface CandidateProfile {
  jobTitle: string;
  skills: string;
  linkedinUrl: string;
}

export default function Home() {
  const [profile, setProfile] = useState<CandidateProfile>({
    jobTitle: "",
    skills: "",
    linkedinUrl: "",
  });
  const [saved, setSaved] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // TODO: persist to Vercel KV or API route
    console.log("Profile saved:", profile);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
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
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Titre du poste recherché
            </span>
            <input
              type="text"
              required
              placeholder="ex: Développeur Full-Stack Senior"
              value={profile.jobTitle}
              onChange={(e) =>
                setProfile({ ...profile, jobTitle: e.target.value })
              }
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-700"
            />
          </label>

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

          <button
            type="submit"
            className="mt-2 rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Sauvegarder
          </button>

          {saved && (
            <p className="text-center text-sm text-green-600 dark:text-green-400">
              Profil sauvegardé avec succès.
            </p>
          )}
        </form>
      </main>
    </div>
  );
}
