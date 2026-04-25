import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ShortcutLibraryScreen } from "@/components/shortcuts/shortcut-library-screen";

describe("ShortcutLibraryScreen", () => {
  it("renders the Voice Shortcuts heading", () => {
    render(<ShortcutLibraryScreen />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Voice Shortcuts" }),
    ).toBeInTheDocument();
  });

  it("renders the placeholder coming-soon message", () => {
    render(<ShortcutLibraryScreen />);
    expect(
      screen.getByText("Coming as part of future enhancements"),
    ).toBeInTheDocument();
  });
});
