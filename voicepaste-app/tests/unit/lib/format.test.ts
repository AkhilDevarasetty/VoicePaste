import { describe, expect, it } from "vitest";

import { formatLongDuration, formatShortDuration } from "@/lib/format";

describe("formatLongDuration", () => {
  it("formats whole minutes and zero-padded seconds", () => {
    expect(formatLongDuration(125)).toBe("2m 05s");
  });

  it("formats values under one minute as 0m", () => {
    expect(formatLongDuration(45)).toBe("0m 45s");
  });

  it("treats zero as 0m 00s", () => {
    expect(formatLongDuration(0)).toBe("0m 00s");
  });

  it("rounds fractional seconds to the nearest whole second", () => {
    expect(formatLongDuration(59.6)).toBe("1m 00s");
    expect(formatLongDuration(59.4)).toBe("0m 59s");
  });

  it("clamps negative inputs to zero", () => {
    expect(formatLongDuration(-12)).toBe("0m 00s");
  });

  it("zero-pads single-digit seconds", () => {
    expect(formatLongDuration(61)).toBe("1m 01s");
  });

  it("supports very large durations", () => {
    expect(formatLongDuration(3661)).toBe("61m 01s");
  });
});

describe("formatShortDuration", () => {
  it("returns an em-dash for null", () => {
    expect(formatShortDuration(null)).toBe("—");
  });

  it("returns an em-dash for NaN", () => {
    expect(formatShortDuration(Number.NaN)).toBe("—");
  });

  it("zero-pads minutes and seconds", () => {
    expect(formatShortDuration(5)).toBe("00:05");
    expect(formatShortDuration(65)).toBe("01:05");
  });

  it("formats zero as 00:00", () => {
    expect(formatShortDuration(0)).toBe("00:00");
  });

  it("rounds fractional seconds to the nearest whole second", () => {
    expect(formatShortDuration(0.4)).toBe("00:00");
    expect(formatShortDuration(0.5)).toBe("00:01");
  });

  it("clamps negative seconds to zero", () => {
    expect(formatShortDuration(-3)).toBe("00:00");
  });

  it("handles durations longer than an hour", () => {
    expect(formatShortDuration(3725)).toBe("62:05");
  });
});
