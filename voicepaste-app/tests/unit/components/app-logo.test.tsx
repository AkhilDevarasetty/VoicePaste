import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppLogo } from "@/components/ui/app-logo";

describe("AppLogo", () => {
  it("renders an accessible label of VoicePaste by default", () => {
    render(<AppLogo />);
    expect(screen.getByRole("img", { name: "VoicePaste" })).toBeInTheDocument();
  });

  it("renders the Beta tag when expanded", () => {
    render(<AppLogo />);
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("renders only the mark and hides the wordmark text when collapsed", () => {
    render(<AppLogo collapsed />);
    expect(screen.getByRole("img", { name: "VoicePaste" })).toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.queryByText("oicePaste")).not.toBeInTheDocument();
  });
});
