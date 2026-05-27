import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/ui/status-badge";

describe("StatusBadge", () => {
  it("renders the provided label text", () => {
    render(<StatusBadge label="Completed" tone="success" />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("applies the success tone classes", () => {
    render(<StatusBadge label="Completed" tone="success" />);
    const node = screen.getByText("Completed");
    expect(node.className).toContain("bg-black");
    expect(node.className).toContain("text-white");
  });

  it("applies the warning tone classes", () => {
    render(<StatusBadge label="Paste failed" tone="warning" />);
    const node = screen.getByText("Paste failed");
    expect(node.className).toContain("bg-white");
    expect(node.className).toContain("text-black");
  });

  it("applies the danger tone classes", () => {
    render(<StatusBadge label="Failed" tone="danger" />);
    const node = screen.getByText("Failed");
    expect(node.className).toContain("bg-white");
    expect(node.className).toContain("text-black");
  });

  it("applies the accent tone classes", () => {
    render(<StatusBadge label="Active" tone="accent" />);
    const node = screen.getByText("Active");
    expect(node.className).toContain("bg-black");
    expect(node.className).toContain("text-white");
  });

  it("renders a leading status dot", () => {
    const { container } = render(
      <StatusBadge label="Completed" tone="success" />,
    );
    const badge = container.querySelector("span");
    expect(badge).not.toBeNull();
    expect(badge?.querySelector("span")).not.toBeNull();
  });

  it("renders an empty label without crashing", () => {
    const { container } = render(<StatusBadge label="" tone="success" />);
    expect(container.querySelectorAll("span").length).toBeGreaterThanOrEqual(2);
  });
});
