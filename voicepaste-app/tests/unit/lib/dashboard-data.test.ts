import { describe, expect, it } from "vitest";

import { dashboardNavItems } from "@/lib/dashboard-data";

describe("dashboardNavItems", () => {
  it("exposes exactly three navigation items", () => {
    expect(dashboardNavItems).toHaveLength(3);
  });

  it("uses the documented nav order: Dashboard, Voice Shortcuts, Settings", () => {
    expect(dashboardNavItems.map((item) => item.label)).toEqual([
      "Dashboard",
      "Voice Shortcuts",
      "Settings",
    ]);
  });

  it("maps each label to the expected href", () => {
    const byLabel = Object.fromEntries(
      dashboardNavItems.map((item) => [item.label, item.href]),
    );

    expect(byLabel).toEqual({
      Dashboard: "/",
      "Voice Shortcuts": "/voice-shortcuts",
      Settings: "/settings",
    });
  });

  it("provides a description and icon key for every item", () => {
    for (const item of dashboardNavItems) {
      expect(item.description.length).toBeGreaterThan(0);
      expect(item.icon).toMatch(/^(dashboard|shortcuts|settings)$/);
    }
  });

  it("contains unique hrefs", () => {
    const hrefs = dashboardNavItems.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
});
