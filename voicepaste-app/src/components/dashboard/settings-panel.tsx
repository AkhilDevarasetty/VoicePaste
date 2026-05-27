"use client";

import { useEffect, useState, useTransition } from "react";

import {
  fetchSettings,
  updateSettings,
  type ReadabilityMode,
} from "@/lib/api-client";

export function SettingsPanel() {
  const [mode, setMode] = useState<ReadabilityMode>("off");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;

    async function loadMode() {
      try {
        const data = await fetchSettings();

        if (!cancelled) {
          setMode(data.readabilityMode);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Failed to load settings.",
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
    const nextMode: ReadabilityMode = mode === "openai" ? "off" : "openai";
    const previousMode = mode;

    setMode(nextMode);
    setError(null);

    startTransition(async () => {
      try {
        const data = await updateSettings({ readabilityMode: nextMode });
        setMode(data.readabilityMode);
      } catch (updateError) {
        setMode(previousMode);
        setError(
          updateError instanceof Error
            ? updateError.message
            : "Failed to update settings.",
        );
      }
    });
  }

  return (
    <section id="settings" className="fig-panel px-6 py-6 lg:px-8 lg:py-7">
      <div className="rounded-[8px] border border-black/10 px-5 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-[16px] font-medium tracking-[-0.14px] text-black">Cloud enhancement</h3>
            <p className="mt-2 text-sm leading-[1.45] tracking-[-0.12px] text-muted">
              Stored in local VoicePaste settings and applied on the next transcript.
            </p>
          </div>
          <button
            aria-label="Toggle cloud enhancement"
            aria-pressed={mode === "openai"}
            className={`fig-pill relative inline-flex h-10 w-18 shrink-0 border border-black transition ${
              mode === "openai"
                ? "bg-black text-white"
                : "bg-white text-black"
            } ${loading || isPending ? "cursor-wait opacity-70" : ""}`}
            disabled={loading || isPending}
            onClick={handleToggle}
            type="button"
          >
            <span
              className={`fig-circle absolute top-1 h-8 w-8 bg-white transition ${
                mode === "openai" ? "left-9" : "left-1 border border-black"
              }`}
            />
          </button>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <span className={`fig-pill border px-3.5 py-2 text-[11px] font-medium uppercase tracking-[0.22em] ${
            mode === "openai" ? "border-black bg-black text-white" : "border-black/10 bg-white text-black"
          }`}>
            {loading ? "Loading" : mode === "openai" ? "Enabled" : "Disabled"}
          </span>
          {isPending ? (
            <span className="text-xs tracking-[-0.08px] text-soft">Saving…</span>
          ) : null}
        </div>

        {error ? <p className="mt-4 text-sm tracking-[-0.12px] text-black">{error}</p> : null}
      </div>
    </section>
  );
}
