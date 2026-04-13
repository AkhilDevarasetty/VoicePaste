import { promises as fs } from "node:fs";
import path from "node:path";

import { NextResponse } from "next/server";

const CONFIG_PATH = path.resolve(process.cwd(), "..", "config.py");
const READABILITY_MODE_PATTERN =
  /READABILITY_MODE:\s*str\s*=\s*"(off|openai)"/;

type Mode = "off" | "openai";

export async function GET() {
  try {
    const configContents = await fs.readFile(CONFIG_PATH, "utf8");
    const match = configContents.match(READABILITY_MODE_PATTERN);

    if (!match) {
      return NextResponse.json(
        { error: "READABILITY_MODE was not found in config.py" },
        { status: 500 },
      );
    }

    return NextResponse.json({ mode: match[1] as Mode });
  } catch {
    return NextResponse.json(
      { error: "Unable to read config.py" },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { mode?: Mode };
    const nextMode = body.mode;

    if (nextMode !== "off" && nextMode !== "openai") {
      return NextResponse.json(
        { error: "Mode must be either 'off' or 'openai'" },
        { status: 400 },
      );
    }

    const configContents = await fs.readFile(CONFIG_PATH, "utf8");

    if (!READABILITY_MODE_PATTERN.test(configContents)) {
      return NextResponse.json(
        { error: "READABILITY_MODE was not found in config.py" },
        { status: 500 },
      );
    }

    const updatedConfig = configContents.replace(
      READABILITY_MODE_PATTERN,
      `READABILITY_MODE: str = "${nextMode}"`,
    );

    await fs.writeFile(CONFIG_PATH, updatedConfig, "utf8");

    return NextResponse.json({ mode: nextMode });
  } catch {
    return NextResponse.json(
      { error: "Unable to update config.py" },
      { status: 500 },
    );
  }
}
