export type TranscriptStatus = "completed" | "failed" | "paste_failed";
export type ReadabilityMode = "off" | "openai";

export type Transcript = {
  id: string;
  createdAt: string;
  status: TranscriptStatus;
  rawText: string | null;
  finalText: string | null;
  durationSeconds: number | null;
  transcriptionLatencyMs: number | null;
  enhancementLatencyMs: number | null;
  targetApp: string | null;
  errorMessage: string | null;
};

export type DashboardStats = {
  totalTranscripts: number;
  completedTranscripts: number;
  successRate: number;
  averageDurationSeconds: number;
};

export type Settings = {
  readabilityMode: ReadabilityMode;
};

async function parseResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    let message = fallbackMessage;
    try {
      const body = (await response.json()) as { error?: string };
      if (body.error) {
        message = body.error;
      }
    } catch {}
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function fetchTranscripts(limit = 50, offset = 0): Promise<Transcript[]> {
  const response = await fetch(`/api/transcripts?limit=${limit}&offset=${offset}`, {
    cache: "no-store",
  });

  return parseResponse<Transcript[]>(response, "Failed to load transcripts.");
}

export async function fetchStats(): Promise<DashboardStats> {
  const response = await fetch("/api/stats", {
    cache: "no-store",
  });

  return parseResponse<DashboardStats>(response, "Failed to load dashboard stats.");
}

export async function fetchSettings(): Promise<Settings> {
  const response = await fetch("/api/settings", {
    cache: "no-store",
  });

  return parseResponse<Settings>(response, "Failed to load settings.");
}

export async function updateSettings(patch: Partial<Settings>): Promise<Settings> {
  const response = await fetch("/api/settings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(patch),
  });

  return parseResponse<Settings>(response, "Failed to update settings.");
}
