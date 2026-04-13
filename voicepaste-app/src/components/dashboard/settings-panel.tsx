"use client";

import { useEffect, useState, useTransition } from "react";

type CloudEnhancementResponse = {
  mode: "off" | "openai";
};

export function SettingsPanel() {
  const [mode, setMode] = useState<"off" | "openai">("off");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;

    async function loadMode() {
      try {
        const response = await fetch("/api/cloud-enhancement", {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Failed to load cloud enhancement setting.");
        }

        const data = (await response.json()) as CloudEnhancementResponse;

        if (!cancelled) {
          setMode(data.mode);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Failed to load cloud enhancement setting.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadMode();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleToggle() {
    const nextMode = mode === "openai" ? "off" : "openai";
    const previousMode = mode;

    setMode(nextMode);
    setError(null);

    startTransition(async () => {
      try {
        const response = await fetch("/api/cloud-enhancement", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ mode: nextMode }),
        });

        if (!response.ok) {
          throw new Error("Failed to update config.py");
        }

        const data = (await response.json()) as CloudEnhancementResponse;
        setMode(data.mode);
      } catch (updateError) {
        setMode(previousMode);
        setError(
          updateError instanceof Error
            ? updateError.message
            : "Failed to update config.py",
        );
      }
    });
  }

  return (
    <section id="settings" className="border-y border-[var(--border-soft)] py-5 lg:py-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-soft)]">
          Settings
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em]">
          Transcript enhancement
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          Toggle cloud enhancement to send transcript text to OpenAI for readability cleanup. Audio stays local.
        </p>
      </div>

      <div className="mt-5 border border-[var(--border-soft)] bg-white/82 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold">Cloud enhancement</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
              Mirrors `READABILITY_MODE` in `config.py`.
            </p>
          </div>
          <button
            aria-label="Toggle cloud enhancement"
            aria-pressed={mode === "openai"}
            className={`relative inline-flex h-8 w-14 shrink-0 rounded-full transition ${
              mode === "openai"
                ? "bg-[var(--accent)]"
                : "bg-[rgba(128,144,157,0.35)]"
            } ${loading || isPending ? "cursor-wait opacity-70" : ""}`}
            disabled={loading || isPending}
            onClick={handleToggle}
            type="button"
          >
            <span
              className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow-sm transition ${
                mode === "openai" ? "left-7" : "left-1"
              }`}
            />
          </button>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.12em] ${
              mode === "openai"
                ? "bg-[rgba(221,232,238,0.72)] text-[var(--accent)]"
                : "bg-[rgba(242,245,246,0.88)] text-[var(--text-muted)]"
            }`}
          >
            {loading ? "Loading" : mode === "openai" ? "Enabled" : "Disabled"}
          </span>
          {isPending ? (
            <span className="text-xs text-[var(--text-soft)]">Saving to config.py…</span>
          ) : null}
        </div>

        {error ? (
          <p className="mt-4 text-sm text-[var(--danger)]">{error}</p>
        ) : null}
      </div>
    </section>
  );
}
