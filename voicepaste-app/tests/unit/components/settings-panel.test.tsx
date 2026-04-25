import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPanel } from "@/components/dashboard/settings-panel";

describe("SettingsPanel", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  function mockSettingsResponse(payload: unknown, init: { ok?: boolean; status?: number } = {}) {
    fetchMock.mockResolvedValueOnce({
      ok: init.ok ?? true,
      status: init.status ?? 200,
      json: vi.fn(async () => payload),
    });
  }

  it("starts in a loading state and shows the Loading pill", () => {
    fetchMock.mockReturnValueOnce(new Promise(() => {}));
    render(<SettingsPanel />);
    expect(screen.getByText("Loading")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Toggle cloud enhancement" }),
    ).toBeDisabled();
  });

  it("renders the Disabled pill when the server returns mode=off", async () => {
    mockSettingsResponse({ readabilityMode: "off" });
    render(<SettingsPanel />);
    expect(await screen.findByText("Disabled")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Toggle cloud enhancement" }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("renders the Enabled pill when the server returns mode=openai", async () => {
    mockSettingsResponse({ readabilityMode: "openai" });
    render(<SettingsPanel />);
    expect(await screen.findByText("Enabled")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Toggle cloud enhancement" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("renders an inline error if loading fails", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: vi.fn(async () => ({ error: "VoicePaste database is not available yet." })),
    });
    render(<SettingsPanel />);
    expect(
      await screen.findByText("VoicePaste database is not available yet."),
    ).toBeInTheDocument();
  });

  it("toggles to enabled and POSTs the new value", async () => {
    mockSettingsResponse({ readabilityMode: "off" });
    mockSettingsResponse({ readabilityMode: "openai" });

    render(<SettingsPanel />);
    const toggle = await screen.findByRole("button", {
      name: "Toggle cloud enhancement",
    });

    await userEvent.click(toggle);

    await waitFor(() =>
      expect(toggle).toHaveAttribute("aria-pressed", "true"),
    );

    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ readabilityMode: "openai" }),
    });
  });

  it("reverts the toggle and surfaces an error when update fails", async () => {
    mockSettingsResponse({ readabilityMode: "off" });
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: vi.fn(async () => ({ error: "boom" })),
    });

    render(<SettingsPanel />);
    const toggle = await screen.findByRole("button", {
      name: "Toggle cloud enhancement",
    });

    await userEvent.click(toggle);

    expect(await screen.findByText("boom")).toBeInTheDocument();
    await waitFor(() =>
      expect(toggle).toHaveAttribute("aria-pressed", "false"),
    );
  });

  it("clears any prior error when toggling again", async () => {
    mockSettingsResponse({ readabilityMode: "off" });
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: vi.fn(async () => ({ error: "first failure" })),
    });
    mockSettingsResponse({ readabilityMode: "openai" });

    render(<SettingsPanel />);
    const toggle = await screen.findByRole("button", {
      name: "Toggle cloud enhancement",
    });

    await userEvent.click(toggle);
    expect(await screen.findByText("first failure")).toBeInTheDocument();

    await userEvent.click(toggle);
    await waitFor(() =>
      expect(screen.queryByText("first failure")).not.toBeInTheDocument(),
    );
  });
});
