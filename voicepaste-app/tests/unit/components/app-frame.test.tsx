import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { AppFrame } from "@/components/layout/app-frame";

describe("AppFrame", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("renders the children inside the main content area", () => {
    render(
      <AppFrame currentPath="/">
        <p data-testid="content">child content</p>
      </AppFrame>,
    );
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("starts expanded when no localStorage value is set", () => {
    render(
      <AppFrame currentPath="/">
        <p>content</p>
      </AppFrame>,
    );
    expect(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    ).toBeInTheDocument();
  });

  it("starts collapsed when localStorage flag is true", () => {
    window.localStorage.setItem("voicepaste-sidebar-collapsed", "true");
    render(
      <AppFrame currentPath="/">
        <p>content</p>
      </AppFrame>,
    );
    expect(
      screen.getByRole("button", { name: "Expand sidebar" }),
    ).toBeInTheDocument();
  });

  it("toggles the sidebar and persists the new state to localStorage", async () => {
    render(
      <AppFrame currentPath="/">
        <p>content</p>
      </AppFrame>,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    );

    expect(
      screen.getByRole("button", { name: "Expand sidebar" }),
    ).toBeInTheDocument();
    expect(
      window.localStorage.getItem("voicepaste-sidebar-collapsed"),
    ).toBe("true");

    await userEvent.click(
      screen.getByRole("button", { name: "Expand sidebar" }),
    );
    expect(
      window.localStorage.getItem("voicepaste-sidebar-collapsed"),
    ).toBe("false");
  });
});
