import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppSidebar } from "@/components/layout/app-sidebar";

describe("AppSidebar", () => {
  it("renders all three nav items with descriptions when expanded", () => {
    render(<AppSidebar collapsed={false} currentPath="/" onToggle={() => {}} />);
    expect(screen.getByRole("link", { name: /Dashboard/ })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Voice Shortcuts/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Settings/ })).toBeInTheDocument();
    expect(screen.getByText("Overview and activity")).toBeInTheDocument();
    expect(screen.getByText("Future shortcut library")).toBeInTheDocument();
    expect(screen.getByText("Preferences and devices")).toBeInTheDocument();
  });

  it("marks the active nav item with aria-current=page", () => {
    render(
      <AppSidebar
        collapsed={false}
        currentPath="/settings"
        onToggle={() => {}}
      />,
    );
    const settingsLink = screen.getByRole("link", { name: /Settings/ });
    expect(settingsLink).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /Dashboard/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("renders the collapse toggle with the right aria-label when expanded", () => {
    render(<AppSidebar collapsed={false} currentPath="/" onToggle={() => {}} />);
    expect(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    ).toBeInTheDocument();
  });

  it("renders the collapse toggle with the right aria-label when collapsed", () => {
    render(<AppSidebar collapsed={true} currentPath="/" onToggle={() => {}} />);
    expect(
      screen.getByRole("button", { name: "Expand sidebar" }),
    ).toBeInTheDocument();
  });

  it("invokes onToggle when the chevron button is clicked", async () => {
    const onToggle = vi.fn();
    render(
      <AppSidebar collapsed={false} currentPath="/" onToggle={onToggle} />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    );
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("hides nav descriptions inside a hidden wrapper when collapsed", () => {
    render(<AppSidebar collapsed={true} currentPath="/" onToggle={() => {}} />);
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    // The text remains in the DOM but the wrapper carries the Tailwind `hidden` class.
    const description = screen.getByText("Overview and activity");
    expect(description.parentElement).toHaveClass("hidden");
  });

  it("links to the correct hrefs", () => {
    render(<AppSidebar collapsed={false} currentPath="/" onToggle={() => {}} />);
    expect(screen.getByRole("link", { name: /Dashboard/ })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /Voice Shortcuts/ })).toHaveAttribute(
      "href",
      "/voice-shortcuts",
    );
    expect(screen.getByRole("link", { name: /Settings/ })).toHaveAttribute(
      "href",
      "/settings",
    );
  });
});
