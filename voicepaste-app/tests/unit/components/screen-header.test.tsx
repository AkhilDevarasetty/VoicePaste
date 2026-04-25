import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScreenHeader } from "@/components/layout/screen-header";

describe("ScreenHeader", () => {
  it("renders the title as a level-1 heading", () => {
    render(<ScreenHeader title="Dashboard" />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it("renders the description when provided", () => {
    render(
      <ScreenHeader title="Dashboard" description="Review recent captures." />,
    );
    expect(screen.getByText("Review recent captures.")).toBeInTheDocument();
  });

  it("omits the description paragraph when not provided", () => {
    const { container } = render(<ScreenHeader title="Dashboard" />);
    expect(container.querySelectorAll("p")).toHaveLength(0);
  });

  it("renders the actions slot", () => {
    render(
      <ScreenHeader
        title="Dashboard"
        actions={<button type="button">Refresh</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });

  it("does not render an actions container when no actions are passed", () => {
    const { container } = render(<ScreenHeader title="Dashboard" />);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });
});
