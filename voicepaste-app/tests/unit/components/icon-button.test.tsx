import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IconButton } from "@/components/ui/icon-button";

describe("IconButton", () => {
  it("uses the label as accessible name", () => {
    render(<IconButton label="Open settings" icon={<span>icon</span>} />);
    expect(screen.getByRole("button", { name: "Open settings" })).toBeInTheDocument();
  });

  it("renders the provided icon node as a child", () => {
    render(
      <IconButton
        label="Search"
        icon={<svg data-testid="custom-icon" aria-hidden="true" />}
      />,
    );
    expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
  });

  it("renders as a button element with type=button", () => {
    render(<IconButton label="Refresh" icon={<span>r</span>} />);
    const button = screen.getByRole("button", { name: "Refresh" });
    expect(button.tagName).toBe("BUTTON");
    expect(button).toHaveAttribute("type", "button");
  });
});
