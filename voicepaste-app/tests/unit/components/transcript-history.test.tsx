import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TranscriptHistory } from "@/components/dashboard/transcript-history";
import type { Transcript } from "@/lib/api-client";

function makeTranscript(overrides: Partial<Transcript> = {}): Transcript {
  const defaults: Transcript = {
    id: "id-1",
    createdAt: "2026-04-24T15:00:00Z",
    status: "completed",
    rawText: "raw text",
    finalText: "final text",
    durationSeconds: 12,
    transcriptionLatencyMs: 800,
    enhancementLatencyMs: 200,
    targetApp: "Notes",
    errorMessage: null,
  };
  return { ...defaults, ...overrides };
}

describe("TranscriptHistory", () => {
  it("renders the section heading", () => {
    render(<TranscriptHistory error={null} loading={false} rows={[]} />);
    expect(
      screen.getByRole("heading", { level: 2, name: "Recent voice events" }),
    ).toBeInTheDocument();
  });

  it("renders three filter pills with All active by default", () => {
    render(<TranscriptHistory error={null} loading={false} rows={[]} />);
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Completed" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Failed" })).toBeInTheDocument();
  });

  it("shows skeleton loading rows when loading is true", () => {
    const { container } = render(
      <TranscriptHistory error={null} loading={true} rows={[]} />,
    );
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("shows empty-state copy for the All filter", () => {
    render(<TranscriptHistory error={null} loading={false} rows={[]} />);
    expect(
      screen.getByText("No transcriptions yet. Hold Right Option to record."),
    ).toBeInTheDocument();
  });

  it("shows the completed empty-state when filter is Completed", async () => {
    render(<TranscriptHistory error={null} loading={false} rows={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Completed" }));
    expect(screen.getByText("No completed transcriptions yet.")).toBeInTheDocument();
  });

  it("shows the failed empty-state when filter is Failed", async () => {
    render(<TranscriptHistory error={null} loading={false} rows={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Failed" }));
    expect(screen.getByText("No failed transcriptions yet.")).toBeInTheDocument();
  });

  it("renders an error row when there are no rows and an error", () => {
    render(
      <TranscriptHistory error="Connection lost." loading={false} rows={[]} />,
    );
    expect(screen.getByText("Connection lost.")).toBeInTheDocument();
  });

  it("renders an inline error banner above rows when both are present", () => {
    const rows = [makeTranscript()];
    render(
      <TranscriptHistory error="Stale data." loading={false} rows={rows} />,
    );
    expect(screen.getByText("Stale data.")).toBeInTheDocument();
    expect(screen.getByText("final text")).toBeInTheDocument();
  });

  it("renders one row per transcript with text preview and duration", () => {
    const rows = [
      makeTranscript({ id: "a", finalText: "first" }),
      makeTranscript({ id: "b", finalText: "second" }),
    ];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(screen.getByText("first")).toBeInTheDocument();
    expect(screen.getByText("second")).toBeInTheDocument();
    expect(screen.getAllByText("00:12")).toHaveLength(2);
  });

  it("falls back to raw text when finalText is null", () => {
    const rows = [makeTranscript({ finalText: null, rawText: "raw only" })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(screen.getByText("raw only")).toBeInTheDocument();
  });

  it("falls back to placeholder when both texts are null", () => {
    const rows = [makeTranscript({ finalText: null, rawText: null })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(screen.getByText("Transcript unavailable.")).toBeInTheDocument();
  });

  it("filters to completed rows when Completed pill is active", async () => {
    const rows = [
      makeTranscript({ id: "ok", finalText: "good", status: "completed" }),
      makeTranscript({ id: "bad", finalText: "bad", status: "failed", errorMessage: "x" }),
    ];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    await userEvent.click(screen.getByRole("button", { name: "Completed" }));
    expect(screen.getByText("good")).toBeInTheDocument();
    expect(screen.queryByText("bad")).not.toBeInTheDocument();
  });

  it("filters to failed and paste_failed rows when Failed pill is active", async () => {
    const rows = [
      makeTranscript({ id: "ok", finalText: "good", status: "completed" }),
      makeTranscript({ id: "bad", finalText: "bad", status: "failed", errorMessage: "x" }),
      makeTranscript({
        id: "paste",
        finalText: "paste-text",
        status: "paste_failed",
        errorMessage: "y",
      }),
    ];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    await userEvent.click(screen.getByRole("button", { name: "Failed" }));
    expect(screen.queryByText("good")).not.toBeInTheDocument();
    expect(screen.getByText("bad")).toBeInTheDocument();
    expect(screen.getByText("paste-text")).toBeInTheDocument();
  });

  it("renders a status badge per row using the right label", () => {
    const rows = [
      makeTranscript({ id: "1", status: "completed" }),
      makeTranscript({ id: "2", status: "failed", errorMessage: "boom" }),
      makeTranscript({ id: "3", status: "paste_failed", errorMessage: "no perms" }),
    ];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    // "Completed" appears once as a status badge and once as a filter pill, so query within the table body.
    const tableRows = screen.getAllByRole("row");
    expect(within(tableRows[1]).getByText("Completed")).toBeInTheDocument();
    expect(within(tableRows[2]).getByText("Failed")).toBeInTheDocument();
    expect(within(tableRows[3]).getByText("Paste failed")).toBeInTheDocument();
  });

  it("uses targetApp in the context line for completed rows", () => {
    const rows = [makeTranscript({ targetApp: "Slack" })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(screen.getByText("Target app: Slack")).toBeInTheDocument();
  });

  it("falls back to a generic completed message when targetApp is null", () => {
    const rows = [makeTranscript({ targetApp: null })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(screen.getByText("Completed and stored locally.")).toBeInTheDocument();
  });

  it("describes paste failures with the error message", () => {
    const rows = [
      makeTranscript({
        status: "paste_failed",
        errorMessage: "no accessibility permission",
      }),
    ];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(
      screen.getByText("Paste failed: no accessibility permission"),
    ).toBeInTheDocument();
  });

  it("describes failed status with a fallback message when no errorMessage", () => {
    const rows = [makeTranscript({ status: "failed", errorMessage: null })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    expect(
      screen.getByText("Transcript could not be completed."),
    ).toBeInTheDocument();
  });

  it("disables the copy button when no copy text is available", () => {
    const rows = [
      makeTranscript({ id: "x", finalText: null, rawText: null }),
    ];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    const button = screen.getByRole("button", { name: "Copy transcript" });
    expect(button).toBeDisabled();
  });

  it("copies the final text to the clipboard and flips the icon to the check state", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    const rows = [makeTranscript({ finalText: "hello world" })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);

    await userEvent.click(
      screen.getByRole("button", { name: "Copy transcript" }),
    );

    expect(writeText).toHaveBeenCalledWith("hello world");
    expect(
      await screen.findByRole("button", { name: "Transcript copied" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Copied")).toBeInTheDocument();
  });

  it("logs an error and does not flip state when clipboard write fails", async () => {
    const writeText = vi
      .fn()
      .mockRejectedValue(new Error("clipboard denied"));
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const rows = [makeTranscript({ finalText: "denied" })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);

    await userEvent.click(
      screen.getByRole("button", { name: "Copy transcript" }),
    );

    expect(writeText).toHaveBeenCalled();
    expect(consoleError).toHaveBeenCalled();
    expect(
      screen.queryByRole("button", { name: "Transcript copied" }),
    ).not.toBeInTheDocument();
  });

  it("renders the duration as an em-dash when duration is null", () => {
    const rows = [makeTranscript({ durationSeconds: null })];
    render(<TranscriptHistory error={null} loading={false} rows={rows} />);
    const tableRows = screen.getAllByRole("row");
    expect(within(tableRows[1]).getByText("—")).toBeInTheDocument();
  });
});
