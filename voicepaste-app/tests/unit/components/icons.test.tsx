import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  CheckIcon,
  ChevronRightIcon,
  CopyIcon,
  GridIcon,
  ListIcon,
  MicrophoneIcon,
  SettingsIcon,
  SparkIcon,
  VoicePasteMark,
} from "@/components/ui/icons";

const ICONS = [
  ["GridIcon", GridIcon],
  ["ListIcon", ListIcon],
  ["MicrophoneIcon", MicrophoneIcon],
  ["SettingsIcon", SettingsIcon],
  ["CopyIcon", CopyIcon],
  ["CheckIcon", CheckIcon],
  ["ChevronRightIcon", ChevronRightIcon],
  ["SparkIcon", SparkIcon],
  ["VoicePasteMark", VoicePasteMark],
] as const;

describe("icons", () => {
  it.each(ICONS)("%s renders an aria-hidden svg with the default class", (_, Icon) => {
    const { container } = render(<Icon />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg?.getAttribute("class")).toBeTruthy();
  });

  it.each(ICONS)("%s honors a custom className", (_, Icon) => {
    const { container } = render(<Icon className="custom-class" />);
    expect(container.querySelector("svg")?.getAttribute("class")).toBe(
      "custom-class",
    );
  });
});
