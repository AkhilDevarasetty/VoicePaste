import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsScreen } from "@/components/settings/settings-screen";

describe("SettingsScreen", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReturnValue(new Promise(() => {}));
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("renders the Settings page header and description", () => {
    render(<SettingsScreen />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Settings" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Manage VoicePaste behavior here. More settings will be added over time.",
      ),
    ).toBeInTheDocument();
  });

  it("embeds the cloud-enhancement settings panel", () => {
    render(<SettingsScreen />);
    expect(screen.getByText("Cloud enhancement")).toBeInTheDocument();
  });
});
