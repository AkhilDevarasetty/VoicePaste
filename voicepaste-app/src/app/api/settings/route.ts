import { NextResponse } from "next/server";

import {
  assertSchemaCompatible,
  databaseExists,
  openVoicePasteDatabase,
} from "@/lib/db";

export const runtime = "nodejs";

const VALID_READABILITY_MODES = new Set(["off", "openai"]);

export async function GET() {
  if (!databaseExists()) {
    return NextResponse.json(
      { error: "VoicePaste database is not available yet." },
      { status: 503 },
    );
  }

  const db = openVoicePasteDatabase({ readonly: true, fileMustExist: true });

  try {
    assertSchemaCompatible(db);
    const row = db
      .prepare("SELECT value FROM settings WHERE key = ?")
      .get("readability_mode") as { value?: string } | undefined;

    if (!row?.value || !VALID_READABILITY_MODES.has(row.value)) {
      return NextResponse.json(
        { error: "readability_mode is missing from settings." },
        { status: 500 },
      );
    }

    return NextResponse.json({ readabilityMode: row.value });
  } catch (error) {
    console.error("Unable to load settings from SQLite.", error);
    return NextResponse.json(
      { error: "Unable to load settings from SQLite." },
      { status: 500 },
    );
  } finally {
    db.close();
  }
}

export async function POST(request: Request) {
  if (!databaseExists()) {
    return NextResponse.json(
      { error: "VoicePaste database is not available yet." },
      { status: 503 },
    );
  }

  const body = (await request.json()) as { readabilityMode?: string };
  const readabilityMode = body.readabilityMode;

  if (!readabilityMode || !VALID_READABILITY_MODES.has(readabilityMode)) {
    return NextResponse.json(
      { error: "readabilityMode must be either 'off' or 'openai'." },
      { status: 400 },
    );
  }

  const db = openVoicePasteDatabase();

  try {
    assertSchemaCompatible(db);
    db.prepare(
      `
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = excluded.updated_at
      `,
    ).run("readability_mode", readabilityMode, new Date().toISOString());

    return NextResponse.json({ readabilityMode });
  } catch (error) {
    console.error("Unable to update SQLite settings.", error);
    return NextResponse.json(
      { error: "Unable to update SQLite settings." },
      { status: 500 },
    );
  } finally {
    db.close();
  }
}
