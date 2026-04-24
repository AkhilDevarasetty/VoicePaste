import { NextResponse } from "next/server";

import { databaseExists, openVoicePasteDatabase } from "@/lib/db";

export const runtime = "nodejs";

type TranscriptRow = {
  id: string;
  created_at: string;
  status: "completed" | "failed" | "paste_failed";
  raw_text: string | null;
  final_text: string | null;
  duration_seconds: number | null;
  transcription_latency_ms: number | null;
  enhancement_latency_ms: number | null;
  target_app: string | null;
  error_message: string | null;
};

export async function GET(request: Request) {
  if (!databaseExists()) {
    return NextResponse.json([]);
  }

  const { searchParams } = new URL(request.url);
  const limit = clampNumber(searchParams.get("limit"), 50, 1, 500);
  const offset = clampNumber(searchParams.get("offset"), 0, 0, 5000);
  const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });

  try {
    const rows = db
      .prepare(
        `
          SELECT
            id,
            created_at,
            status,
            raw_text,
            final_text,
            duration_seconds,
            transcription_latency_ms,
            enhancement_latency_ms,
            target_app,
            error_message
          FROM transcripts
          ORDER BY created_at DESC
          LIMIT ? OFFSET ?
        `,
      )
      .all(limit, offset) as TranscriptRow[];

    return NextResponse.json(
      rows.map((row) => ({
        id: row.id,
        createdAt: row.created_at,
        status: row.status,
        rawText: row.raw_text,
        finalText: row.final_text,
        durationSeconds: row.duration_seconds,
        transcriptionLatencyMs: row.transcription_latency_ms,
        enhancementLatencyMs: row.enhancement_latency_ms,
        targetApp: row.target_app,
        errorMessage: row.error_message,
      })),
    );
  } catch {
    return NextResponse.json(
      { error: "Unable to load transcripts from SQLite." },
      { status: 500 },
    );
  } finally {
    db.close();
  }
}

function clampNumber(
  value: string | null,
  fallback: number,
  min: number,
  max: number,
) {
  const parsed = Number.parseInt(value ?? "", 10);
  if (Number.isNaN(parsed)) {
    return fallback;
  }
  return Math.min(Math.max(parsed, min), max);
}
