import { NextResponse } from "next/server";

import {
  assertSchemaCompatible,
  databaseExists,
  openVoicePasteDatabase,
} from "@/lib/db";

export const runtime = "nodejs";

type StatsRow = {
  average_duration_seconds: number | null;
  completed_transcripts: number | null;
  total_transcripts: number | null;
};

export async function GET() {
  if (!databaseExists()) {
    return NextResponse.json({
      totalTranscripts: 0,
      completedTranscripts: 0,
      successRate: 0,
      averageDurationSeconds: 0,
    });
  }

  const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });

  try {
    assertSchemaCompatible(db);
    const row = db
      .prepare(
        `
          SELECT
            COUNT(*) AS total_transcripts,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_transcripts,
            AVG(CASE WHEN status = 'completed' THEN duration_seconds END) AS average_duration_seconds
          FROM transcripts
        `,
      )
      .get() as StatsRow;

    const totalTranscripts = Number(row.total_transcripts ?? 0);
    const completedTranscripts = Number(row.completed_transcripts ?? 0);
    const averageDurationSeconds = Number(row.average_duration_seconds ?? 0);
    const successRate =
      totalTranscripts > 0 ? (completedTranscripts / totalTranscripts) * 100 : 0;

    return NextResponse.json({
      totalTranscripts,
      completedTranscripts,
      successRate,
      averageDurationSeconds,
    });
  } catch (error) {
    console.error("Unable to load dashboard stats from SQLite.", error);
    return NextResponse.json(
      { error: "Unable to load dashboard stats from SQLite." },
      { status: 500 },
    );
  } finally {
    db.close();
  }
}
